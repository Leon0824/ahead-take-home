from datetime import UTC, datetime

from pydantic import ConfigDict
from sqlalchemy import TIMESTAMP, MetaData, create_engine, DATETIME
from sqlmodel import Field, Relationship, SQLModel, Session, func

from app.settings import get_settings



class User(SQLModel, table=True):
    __tablename__ = 'users'

    id: int | None = Field(None, primary_key=True)
    username: str = Field(unique=True)
    hashed_password: str
    email_verified: bool = False

    files: list['FcsFile'] = Relationship(
        back_populates='user',
        sa_relationship_kwargs={'lazy': 'selectin'}, # 無效
    )

    model_config = ConfigDict(json_schema_extra={
        'examples': [{
            'id': 1,
            "username": "yin_che@gmail.com",
            'hashed_password': "ABCXYZ",
            "email_verified": False,
        }],
    })



class UploadBatch(SQLModel, table=True):
    __tablename__ = 'upload_batches'

    id: int | None = Field(None, primary_key=True)
    batch_idno: str = Field(unique=True)
    upload_time: datetime = Field(sa_type=TIMESTAMP(True))

    files: list['FcsFile'] = Relationship(
        back_populates='upload_batch',
        sa_relationship_kwargs={'lazy': 'selectin'}, # 無效
    )

    model_config = ConfigDict(json_schema_extra={
        'examples': [{
            'id': 1,
            "batch_idno": "01K7PXGBTMV8R5M3TZTJ79PSMF",
            'upload_time': "2025-10-16T18:00:00Z",
            "files": [],
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

    user_id: int | None = Field(None, foreign_key='users.id')
    user: User | None = Relationship(back_populates='files')

    upload_batch_id: int = Field(foreign_key='upload_batches.id')
    upload_batch: UploadBatch = Relationship(back_populates='files')

    model_config = ConfigDict(json_schema_extra={
        'examples': [{
            'id': 1,
            "file_idno": "01K7Q22M2BEXAD9XZGT3JZV58V",
            'file_name': "abc.fcs",
            "file_size_byte": 12345,
            "s3_key": "01K7PXGBTMV8R5M3TZTJ79PSMF/abc.fcs",
            "upload_batch_id": 1,
        }],
    })




_SETTINGS = get_settings()



engine = create_engine(
    _SETTINGS.DATABASE_URL,
    # echo='debug',
)
SQLModel.metadata.naming_convention = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}).naming_convention
metadata = SQLModel.metadata



def get_db_session():
    with Session(engine) as session: yield session
