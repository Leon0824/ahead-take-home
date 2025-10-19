from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel import JSON, AutoString, Field, SQLModel, Session, create_engine

from jobs.settings import get_settings



_SETTINGS = get_settings()



class JobTypeEnum(StrEnum):
    FILES_STAT = 'FILES_STAT'
    FCS_INFO = 'FCS_INFO'



class JobStatusEnum(StrEnum):
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    FINISHED = 'FINISHED'



class Job(SQLModel, table=True):
    __tablename__ = 'jobs'

    id: int | None = Field(None, primary_key=True)
    queue_job_id: UUID | None = Field(None, unique=True)
    job_type: JobTypeEnum = Field(sa_type=AutoString)
    job_args: dict[str, Any] | None = Field(None, sa_type=JSON)
    status: JobStatusEnum = Field(JobStatusEnum.PENDING, sa_type=AutoString)
    job_working_duration_second: float | None = None
    result: dict[str, Any] | None = Field(None, sa_type=JSON)

    user_id: int

    model_config = ConfigDict(json_schema_extra={
        'examples': [{
            'id': 1,
            "queue_job_id": "9786d1be-ae6b-4902-b366-106d9e7aca70V",
            'job_type': JobTypeEnum.FILES_STAT,
            "job_args": {},
            "job_working_duration_second": None,
            "status": JobStatusEnum.PENDING,
            "result": {},
            "user_id": 1,
        }],
    })


class FcsFile(SQLModel, table=True):
    __tablename__ = 'fcs_files'

    id: int | None = Field(None, primary_key=True)
    file_idno: str = Field(unique=True)
    file_name: str
    file_size_byte: int
    s3_key: str | None = Field(unique=True)
    public: bool = True

    user_id: int | None

    model_config = ConfigDict(json_schema_extra={
        'examples': [{
            'id': 1,
            "file_idno": "01K7Q22M2BEXAD9XZGT3JZV58V",
            'file_name': "abc.fcs",
            "file_size_byte": 12345,
            "s3_key": "01K7PXGBTMV8R5M3TZTJ79PSMF/abc.fcs",
            "user_id": 1,
        }],
    })



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



engine = create_engine(
    _SETTINGS.DATABASE_URL,
    # echo='debug',
)
