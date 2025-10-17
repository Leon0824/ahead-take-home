import asyncio
from datetime import UTC, datetime
import pathlib
from typing import BinaryIO

from aiobotocore.session import get_session
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from pathvalidate import ValidationError, validate_filename
from sqlmodel import Session, select
from ulid import ULID

from app.db import FcsFile, UploadBatch, get_db_session
from app.logging import logger
from app.models import UploadBatchResult
from app.settings import get_settings



_SETTINGS = get_settings()



async def upload(filename: str, size_byte: int, key: str, body: bytes | BinaryIO):
    s3_session = get_session()
    async with s3_session.create_client(
        service_name='s3',
        region_name=_SETTINGS.AWS_DEFAULT_REGION,
        endpoint_url='https://2d318ba7bbba6520730569a4819999c4.r2.cloudflarestorage.com',
        aws_access_key_id=_SETTINGS.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=_SETTINGS.AWS_SECRET_ACCESS_KEY.get_secret_value(),
    ) as s3_client:
        try:
            s3_response: dict = await s3_client.put_object(Bucket='ahead-fcs-files', Key=key, Body=body)
            # logger.debug(s3_response)
            '''
            {'ResponseMetadata': {'HTTPStatusCode': 200, 'HTTPHeaders': {'date': 'Thu, 16 Oct 2025 14:45:04 GMT', 'content-type': 'text/plain;charset=UTF-8', 'content-length': '0', 'connection': 'keep-alive', 'etag': '"4c884a90dcf6e100b3f6253963853dde"', 'x-amz-checksum-crc32': 'GCi94w==', 'x-amz-version-id': '7e661284cdd47d843f625da7b730f3c9', 'vary': 'Accept-Encoding', 'server': 'cloudflare', 'cf-ray': '98f85655ddf9a9c2-TPE'}, 'RetryAttempts': 0}, 'ETag': '"4c884a90dcf6e100b3f6253963853dde"', 'ChecksumCRC32': 'GCi94w==', 'VersionId': '7e661284cdd47d843f625da7b730f3c9'}            
            '''
            return {'filename': filename, 'size_byte': size_byte, 'key': key, 'success': True}
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
) -> UploadBatchResult:
    for f in upload_files:
        if pathlib.Path(f.filename).suffix != '.fcs':
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"File '{f.filename}' is not a .fcs file")
        if f.size > 1000 * 1024 * 1024:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"File '{f.filename}' exceeds 1000MB")
        try: validate_filename(f.filename)
        except ValidationError as e:
            logger.warning({'title': 'Invalid uploading filename', 'error': e, 'filename': f.filename})
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"File name '{f.filename}' is invalid") from e
    
    batch = UploadBatch(batch_idno=str(ULID()), upload_time=datetime.now(UTC).replace(microsecond=0))
    tasks = []
    for f in upload_files:
        key = f'{batch.batch_idno}/{f.filename}'
        task = asyncio.create_task(upload(filename=f.filename, size_byte=f.size, key=key, body=f.file))
        tasks.append(task)

    results: list[dict[str, str | bool]] = await asyncio.gather(*tasks)
    failed_files: list[dict] = []
    for result in results:
        if not result['success']: failed_files.append({'filename': result['filename'], 'error': result['error']})
        else:
            fcs = FcsFile(file_idno=str(ULID()), file_name=result['filename'], file_size_byte=result['size_byte'], s3_key=result['key'], upload_batch_id=batch.id)
            batch.files.append(fcs)
    
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    response = UploadBatchResult.model_validate(batch, from_attributes=True)
    response.files = batch.files
    response.failed_files = failed_files
    return response
