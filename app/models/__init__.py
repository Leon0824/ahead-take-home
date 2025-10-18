from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, TypeAdapter

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



class Token(BaseModel):
    token_type: Literal['Bearer'] = 'Bearer'
    access_token: str # 欄位名一定要叫 access_token，Swagger UI 的登入功能才會正常。

    model_config = ConfigDict(json_schema_extra={
        'examples': [{
            'token_type': 'Bearer',
            'token_string': 'eyJh.eyJz.SflK',
        }],
    })



class UploadFileSetting(BaseModel):
    filename: str
    public: bool

upload_file_setting_list_adapter = TypeAdapter(list[UploadFileSetting])



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
    public: bool
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