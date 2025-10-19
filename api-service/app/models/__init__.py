from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, TypeAdapter

from app.db import FcsFile, JobStatusEnum, JobTypeEnum



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
            'access_token': 'eyJh.eyJz.SflK',
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



class JobRead(BaseModel):
    queue_job_id: UUID
    job_type: JobTypeEnum
    job_args: dict[str, Any] | None = None
    job_working_duration_second: float | None
    status: JobStatusEnum
    result: dict[str, Any] | None = None

    user_id: int

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [{
                "queue_job_id": "43f62c95-8b3d-43ce-9151-04000deb09e9",
                "job_type": JobTypeEnum.FILES_STAT,
                "job_args": {'user_id': 1},
                "job_working_duration_second": None,
                'status': JobStatusEnum.PENDING,
                "result": {"files_count": 2, "files_size_byte_sum": 123},
            }],
        }
    )



class FilesStat(BaseModel):
    files_count: int
    files_size_byte_sum: int

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [{
                "files_count": 2,
                "files_size_byte_sum": 123,
            }],
        }
    )



class FilesStatJobRead(JobRead):
    result: FilesStat | None

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [{
                "queue_job_id": "43f62c95-8b3d-43ce-9151-04000deb09e9",
                "job_type": JobTypeEnum.FILES_STAT,
                "job_args": {'user_id': 1},
                'status': JobStatusEnum.PENDING,
                "result": {"files_count": 2, "files_size_byte_sum": 123},
            }],
        }
    )



class FcsInfo(BaseModel):
    file_name: str
    file_size_byte: int
    file_upload_time: AwareDatetime
    fcs_version: str
    fcs_pnn_labels: list[str]
    fcs_event_count: int
    
    model_config = ConfigDict(
        json_schema_extra={
            'examples': [{
                "file_name": "create_fcs_example.fcs",
                "file_size_byte": 216432,
                "file_upload_time": "2025-10-16T18:00:00Z",
                "fcs_version": "2.0",
                "fcs_pnn_labels": ['FSC-H', 'SSC-H', 'FL1-H', 'FL2-H', 'FL3-H', 'FL2-A', 'FL4-H', 'Time'],
                "fcs_event_count": 13367,
            }],
        }
    )



class FcsInfoJobRead(JobRead):
    result: FcsInfo | None

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [{
                "queue_job_id": "43f62c95-8b3d-43ce-9151-04000deb09e9",
                "job_type": JobTypeEnum.FCS_INFO,
                "job_args": {'user_id': 1},
                'status': JobStatusEnum.PENDING,
                "result": {
                    "file_name": "create_fcs_example.fcs",
                    "file_size_byte": 216432,
                    "file_upload_time": "2025-10-16T18:00:00Z",
                    "fcs_version": "2.0",
                    "fcs_pnn_labels": ['FSC-H', 'SSC-H', 'FL1-H', 'FL2-H', 'FL3-H', 'FL2-A', 'FL4-H', 'Time'],
                    "fcs_event_count": 13367,
                },
            }],
        }
    )