from datetime import UTC, datetime, timedelta

from pydantic import AwareDatetime, BaseModel, ConfigDict

from app.db import FcsFile



class JwtPayload(BaseModel):
    sub: str
    exp: AwareDatetime

    model_config = ConfigDict(json_schema_extra={
        'examples': [{
            'sub': 'username',
            'exp': "2025-10-16T18:00:00Z",
        }],
    })



class UploadBatchResult(BaseModel):
    batch_idno: str
    upload_time: datetime
    files: list[FcsFile]
    failed_files: list[dict] = []

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [{
                "batch_idno": "01K7PXGBTMV8R5M3TZTJ79PSMF",
                'upload_time': "2025-10-16T18:00:00Z",
                "files": [],
                "failed_files": [],
            }],
        }
    )



class FileInfo(BaseModel):
    file_idno: str
    file_name: str
    file_size_byte: int
    upload_time: AwareDatetime

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [{
                "file_idno": "01K7Q22M2BEXAD9XZGT3JZV58V",
                "file_name": "abc.fcs",
                "file_size_byte": 12345,
                'upload_time': "2025-10-16T18:00:00Z",
            }],
        }
    )