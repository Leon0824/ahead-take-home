import asyncio
from datetime import UTC, datetime
import json
import pathlib
from typing import BinaryIO

from aiobotocore.session import get_session
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Security, UploadFile, status
from pathvalidate import ValidationError as FileNameValidationError, validate_filename
from pydantic import HttpUrl, ValidationError
from sqlmodel import Session, select
from ulid import ULID

from app.auth import get_requestor_user
from app.db import FcsFile, UploadBatch, User, get_db_session
from app.logging import logger
from app.models import FileInfo, UploadBatchResult, upload_file_setting_list_adapter
from app.settings import get_settings



_SETTINGS = get_settings()
_S3_BUCKET_NAME = 'ahead-fcs-files'



async def upload(filename: str, size_byte: int, key: str, body: bytes | BinaryIO, public: bool = True):
    s3_session = get_session()
    async with s3_session.create_client(
        service_name='s3',
        region_name=_SETTINGS.AWS_DEFAULT_REGION,
        endpoint_url='https://2d318ba7bbba6520730569a4819999c4.r2.cloudflarestorage.com',
        aws_access_key_id=_SETTINGS.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=_SETTINGS.AWS_SECRET_ACCESS_KEY.get_secret_value(),
    ) as s3_client:
        try:
            s3_response: dict = await s3_client.put_object(Bucket=_S3_BUCKET_NAME, Key=key, Body=body, ContentType='application/octet-stream')
            # logger.debug(s3_response)
            '''
            {'ResponseMetadata': {'HTTPStatusCode': 200, 'HTTPHeaders': {'date': 'Thu, 16 Oct 2025 14:45:04 GMT', 'content-type': 'text/plain;charset=UTF-8', 'content-length': '0', 'connection': 'keep-alive', 'etag': '"4c884a90dcf6e100b3f6253963853dde"', 'x-amz-checksum-crc32': 'GCi94w==', 'x-amz-version-id': '7e661284cdd47d843f625da7b730f3c9', 'vary': 'Accept-Encoding', 'server': 'cloudflare', 'cf-ray': '98f85655ddf9a9c2-TPE'}, 'RetryAttempts': 0}, 'ETag': '"4c884a90dcf6e100b3f6253963853dde"', 'ChecksumCRC32': 'GCi94w==', 'VersionId': '7e661284cdd47d843f625da7b730f3c9'}            
            '''
            return {'filename': filename, 'size_byte': size_byte, 'key': key, 'success': True, 'public': public}
        except BotoCoreError as boto_error:
            logger.error(boto_error)
            return {'filename': filename, 'size_byte': size_byte, 'key': key, 'success': False, 'error': boto_error}
        except ClientError as client_error:
            logger.error(client_error)
            return {'filename': filename, 'size_byte': size_byte, 'key': key, 'success': False, 'error': client_error}



router = APIRouter(prefix='/files', tags=['file'])



@router.post('/upload', status_code=status.HTTP_201_CREATED, operation_id='uplaod_fcs_files')
async def upload_fcs_files(
    request: Request,
    upload_files: list[UploadFile],
    db_session: Session = Depends(get_db_session),
    user: User | None = Security(get_requestor_user),
    upload_file_settings: str | None = Form(None, json_schema_extra={'example': json.dumps([{'filename': 'file1.fcs', 'public': True}, {'filename': 'file2.fcs', 'public': False}]) }),
) -> UploadBatchResult:
    for f in upload_files:
        if pathlib.Path(f.filename).suffix != '.fcs':
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"File '{f.filename}' is not a .fcs file")
        if f.size > 1000 * 1024 * 1024:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"File '{f.filename}' exceeds 1000MB")
        try: validate_filename(f.filename)
        except FileNameValidationError as e:
            logger.warning({'title': 'Invalid uploading filename', 'error': e, 'filename': f.filename})
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"File name '{f.filename}' is invalid") from e
    
    if user:
        if not upload_file_settings: raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, 'For signed-in users, upload_file_settings is required.')
        try: upload_file_setting_list = upload_file_setting_list_adapter.validate_json(upload_file_settings)
        except ValidationError as e: raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, {'title': 'Upload file settings validation error', 'detail': e.errors()})

        for f in upload_files:
            file_setting = next((setting for setting in upload_file_setting_list if setting.filename == f.filename), None)
            if not file_setting: raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f'File {f.filename} setting is required')
        logger.info({'title': 'User uploading files', 'files': [f.filename for f in upload_files]})

    batch = UploadBatch(batch_idno=str(ULID()), upload_time=datetime.now(UTC).replace(microsecond=0))
    tasks = []
    for f in upload_files:
        if user: file_setting = next((setting for setting in upload_file_setting_list if setting.filename == f.filename))
        key = f'{batch.batch_idno}/{f.filename}'
        task = asyncio.create_task(upload(
            filename=f.filename,
            size_byte=f.size,
            key=key,
            body=f.file,
            public=file_setting.public if user else True,
        ))
        tasks.append(task)

    results: list[dict[str, str | bool]] = await asyncio.gather(*tasks)
    failed_files: list[dict] = []
    for result in results:
        if not result['success']: failed_files.append({'filename': result['filename'], 'error': result['error']})
        else:
            fcs = FcsFile(
                file_idno=str(ULID()),
                file_name=result['filename'],
                file_size_byte=result['size_byte'],
                s3_key=result['key'],
                public=result['public'],
                user_id=user.id if user else None,
                upload_batch_id=batch.id,
            )
            batch.files.append(fcs)
    
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    response = UploadBatchResult.model_validate(batch, from_attributes=True)
    response.files = batch.files
    response.failed_files = failed_files
    return response



@router.get('/mine', operation_id='get_user_files_info')
async def get_user_files_info(
    user: User | None = Security(get_requestor_user),
    db_session: Session = Depends(get_db_session),
) -> list[FileInfo]:
    if not user: raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    files = db_session.exec(select(FcsFile).where(FcsFile.user_id == user.id)).all()
    return [FileInfo(file_idno=f.file_idno, file_name=f.file_name, file_size_byte=f.file_size_byte, public=f.public, upload_time=f.upload_batch.upload_time) for f in files]



@router.get('/{file_idno}', operation_id='get_file_info')
async def get_file_info(
    file_idno: str,
    db_session: Session = Depends(get_db_session),
    user: User | None = Security(get_requestor_user),
) -> FileInfo:
    file = db_session.exec(select(FcsFile).where(FcsFile.file_idno == file_idno)).one_or_none()
    if not file: raise HTTPException(status.HTTP_404_NOT_FOUND)

    # Check if the file is private
    if not file.public:
        if not user: raise HTTPException(status.HTTP_404_NOT_FOUND)
        if file.user_id != user.id: raise HTTPException(status.HTTP_404_NOT_FOUND)

    batch = file.upload_batch
    return FileInfo(file_idno=file.file_idno, file_name=file.file_name, file_size_byte=file.file_size_byte, public=file.public, upload_time=batch.upload_time)



@router.get('/{file_idno}/generate-download-url', status_code=status.HTTP_201_CREATED, operation_id='generate_download_url')
async def generate_download_url(
    file_idno: str,
    db_session: Session = Depends(get_db_session),
    user: User | None = Security(get_requestor_user),
) -> HttpUrl:
    file = db_session.exec(select(FcsFile).where(FcsFile.file_idno == file_idno)).one_or_none()
    if not file: raise HTTPException(status.HTTP_404_NOT_FOUND)

    # Check if the file is private
    if not file.public:
        if not user: raise HTTPException(status.HTTP_404_NOT_FOUND)
        if file.user_id != user.id: raise HTTPException(status.HTTP_404_NOT_FOUND)

    if user: logger.info(f'User {user.username} is downloading file {file.s3_key}')

    s3_session = get_session()
    async with s3_session.create_client(
        service_name='s3',
        region_name=_SETTINGS.AWS_DEFAULT_REGION,
        endpoint_url='https://2d318ba7bbba6520730569a4819999c4.r2.cloudflarestorage.com',
        aws_access_key_id=_SETTINGS.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=_SETTINGS.AWS_SECRET_ACCESS_KEY.get_secret_value(),
    ) as s3_client:
        return await s3_client.generate_presigned_url('get_object', {'Bucket': _S3_BUCKET_NAME, 'Key': file.s3_key}, 60) # 一分鐘過期
    
