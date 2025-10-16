import pathlib

import boto3
from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from pathvalidate import ValidationError, validate_filename
from s3transfer import MB, TransferConfig

from app.logging import logger
from app.settings import get_settings



_SETTINGS = get_settings()



router = APIRouter(prefix='/files', tags=['file'])



s3_client = boto3.client(
    's3',
    endpoint_url='https://us-003.s3.synologyc2.net',
    aws_access_key_id=_SETTINGS.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=_SETTINGS.AWS_SECRET_ACCESS_KEY.get_secret_value(),
)
s3_bucket_name = 'ahead-fcs-files'



@router.post('/upload', operation_id='uplaod_fcs_files')
async def upload_fcs_files(
    request: Request,
    upload_files: list[UploadFile],
):
    for f in upload_files:
        if pathlib.Path(f.filename).suffix != '.fcs':
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"File '{f.filename}' is not a .fcs file")
        if f.size > 1000 * 1024 * 1024:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"File '{f.filename}' exceeds 1000MB")
        try: validate_filename(f.filename)
        except ValidationError as e:
            logger.warning({'title': 'Invalid uploading filename', 'error': e, 'filename': f.filename})
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"File '{f.filename}' in invalid") from e
        
    for f in upload_files:
        file_io = f.file # 下面函式會呼叫 .read()，但 f.read 為異步函式，會錯，改取得 BinaryIO 物件，它的 read() 為普通同步函式。
        s3_client.upload_fileobj(
            file_io, s3_bucket_name, f'{f.filename}',
            # {'ContentDisposition': 'attachment'}, # 使下載時帶上此對 HTTP 標頭，強迫瀏覽器下載而不是開啟。
        )
