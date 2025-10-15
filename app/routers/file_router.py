import pathlib

from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from pathvalidate import ValidationError, validate_filename

from app.logging import logger



router = APIRouter(prefix='/files', tags=['file'])



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
