from http import HTTPStatus
import json
from pathlib import PurePath
from uuid import UUID

from aiobotocore.session import get_session
from botocore.exceptions import ClientError
from httpx import AsyncClient
import mimesis
import pytest
from sqlmodel import Session, select

from app.db import Job, JobStatusEnum, JobTypeEnum, UploadBatch, User
from app.job import queue
from app.models import FcsInfoJobRead, FilesStatJobRead, JobRead, Token, UploadBatchResult, UploadFileSetting
from app.settings import get_settings



_SETTINGS = get_settings()
_S3_BUCKET_NAME = 'ahead-fcs-files'



mimesis_binary_file = mimesis.BinaryFile()
mimesis_file = mimesis.File()



class TestUserFcsInfoJob:
    async_client: AsyncClient

    user: User

    file_upload_batch_idno: str
    file_idno: str
    file_s3_key: str

    job_id: int
    queue_job_id: UUID

    
    @pytest.mark.asyncio
    async def test_create_job(self, async_client: AsyncClient, new_user: User):
        TestUserFcsInfoJob.async_client = async_client
        TestUserFcsInfoJob.user = new_user

        # Sign in
        sign_in_response = await TestUserFcsInfoJob.async_client.post('/auth/sign-in', data={'username': TestUserFcsInfoJob.user.username, 'password': TestUserFcsInfoJob.user.username})
        access_token = Token.model_validate(sign_in_response.json())
        TestUserFcsInfoJob.async_client.headers.update({'Authorization': f'{access_token.token_type} {access_token.access_token}'})

        # Upload
        file_path = './app/tests/0000123456_1234567_AML_ClearLLab10C_BTube.fcs'
        setting = UploadFileSetting(
            filename=PurePath(file_path).name,
            public=False,
        )
        with open(file_path, 'rb') as file:
            upload_response = await TestUserFcsInfoJob.async_client.post(
                '/files/upload',
                files={'upload_files': file},
                data={'upload_file_settings': json.dumps([setting.model_dump()])},
            )
        assert upload_response.status_code == HTTPStatus.CREATED
        
        result = UploadBatchResult.model_validate(upload_response.json())
        TestUserFcsInfoJob.file_upload_batch_idno = result.batch_idno
        TestUserFcsInfoJob.file_idno = result.files[0].file_idno
        TestUserFcsInfoJob.file_s3_key = result.files[0].s3_key

        # Create job
        # 這裡建立 job 後，下面 teardown 會立馬清除 DB 的 fcs_file 紀錄，所以在 worker 那邊會報找不到 DB 紀錄的錯誤。
        create_job_response = await TestUserFcsInfoJob.async_client.post(f'/fcs-files/fcs-info-jobs/create', params={'file_idno': TestUserFcsInfoJob.file_idno})
        assert create_job_response.status_code == HTTPStatus.CREATED
        TestUserFcsInfoJob.queue_job_id = UUID(create_job_response.json())


    @pytest.mark.asyncio
    async def test_get_job(self):
        response = await TestUserFcsInfoJob.async_client.get(f'/fcs-files/fcs-info-jobs/{TestUserFcsInfoJob.queue_job_id}')
        assert response.status_code == HTTPStatus.OK
        job_read = FcsInfoJobRead.model_validate(response.json())
        assert job_read.queue_job_id == TestUserFcsInfoJob.queue_job_id
        assert job_read.job_type == JobTypeEnum.FCS_INFO
        assert job_read.status == JobStatusEnum.PENDING # 如果 worker 正在跑，會變成 RUNNING，就會報錯。
        assert job_read.user_id == TestUserFcsInfoJob.user.id


    @pytest.mark.asyncio
    async def test_get_jobs(self):
        response = await TestUserFcsInfoJob.async_client.get(f'/fcs-files/fcs-info-jobs')
        assert response.status_code == HTTPStatus.OK
        job_read_dict_list: list[dict] = response.json()
        job_read_list = [JobRead.model_validate(j) for j in job_read_dict_list]
        job_read = next((j for j in job_read_list if j.queue_job_id == TestUserFcsInfoJob.queue_job_id), None)
        assert job_read


    @pytest.mark.asyncio
    async def test_teardown(self, db_session: Session):
        # Delete S3 files
        s3_session = get_session()
        async with s3_session.create_client(
            service_name='s3',
            region_name=_SETTINGS.AWS_DEFAULT_REGION,
            endpoint_url=str(_SETTINGS.AWS_S3_ENDPOINT_URL),
            aws_access_key_id=_SETTINGS.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=_SETTINGS.AWS_SECRET_ACCESS_KEY.get_secret_value(),
        ) as s3_client:
            response1_before_delete = await s3_client.head_object(Bucket=_S3_BUCKET_NAME, Key=TestUserFcsInfoJob.file_s3_key)
            assert response1_before_delete
            await s3_client.delete_object(Bucket=_S3_BUCKET_NAME, Key=TestUserFcsInfoJob.file_s3_key)
            try: response1_after_delete = await s3_client.head_object(Bucket=_S3_BUCKET_NAME, Key=TestUserFcsInfoJob.file_s3_key)
            except ClientError as e1: assert e1
        
        # Delete DB UploadBatch and FcsFile reocrds
        statement = select(UploadBatch).where(UploadBatch.batch_idno == TestUserFcsInfoJob.file_upload_batch_idno)
        batch = db_session.exec(statement).one_or_none()
        
        for f in batch.files: db_session.delete(f)
        db_session.delete(batch)
        db_session.commit()

        # Delete job record in DB and queue
        db_job = db_session.exec(select(Job).where(Job.queue_job_id == TestUserFcsInfoJob.queue_job_id)).one_or_none()
        assert db_job
        db_session.delete(db_job)
        db_session.commit()

        queue.remove(str(TestUserFcsInfoJob.queue_job_id))