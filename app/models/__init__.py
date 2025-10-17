from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db import FcsFile


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