from http import HTTPStatus
import json
from uuid import UUID

from aiobotocore.session import get_session
from botocore.exceptions import ClientError
from httpx import AsyncClient
import mimesis
import pytest
from sqlmodel import Session, select

from app.db import JobStatusEnum, JobTypeEnum, UploadBatch, User
from app.models import FilesStatJobRead, JobRead, Token, UploadBatchResult, UploadFileSetting
from app.settings import get_settings



_SETTINGS = get_settings()
_S3_BUCKET_NAME = 'ahead-fcs-files'



mimesis_binary_file = mimesis.BinaryFile()
mimesis_file = mimesis.File()



class TestUserFilesStatJob:
    async_client: AsyncClient

    user: User

    file_upload_batch_idno: str
    file_idno: str
    file_s3_key: str

    job_id: int
    queue_job_id: UUID

    
    @pytest.mark.asyncio
    async def test_create_job(self, async_client: AsyncClient, new_user: User):
        TestUserFilesStatJob.async_client = async_client
        TestUserFilesStatJob.user = new_user

        file = mimesis_binary_file.compressed()
        file_name = mimesis_file.file_name() + '.fcs'

        # Sign in
        sign_in_response = await TestUserFilesStatJob.async_client.post('/auth/sign-in', data={'username': TestUserFilesStatJob.user.username, 'password': TestUserFilesStatJob.user.username})
        access_token = Token.model_validate(sign_in_response.json())
        TestUserFilesStatJob.async_client.headers.update({'Authorization': f'{access_token.token_type} {access_token.access_token}'})

        # Upload
        upload_response = await TestUserFilesStatJob.async_client.post(
            '/files/upload',
            files={'upload_files': (file_name, file)},
            data={'upload_file_settings': json.dumps([UploadFileSetting(filename=file_name, public=False).model_dump()])},
        )
        assert upload_response.status_code == HTTPStatus.CREATED
        
        result = UploadBatchResult.model_validate(upload_response.json())
        TestUserFilesStatJob.file_upload_batch_idno = result.batch_idno
        TestUserFilesStatJob.file_idno = result.files[0].file_idno
        TestUserFilesStatJob.file_s3_key = result.files[0].s3_key

        # Create job
        # 這裡建立 job 後，下面 teardown 會立馬清除 DB 的 fcs_file 紀錄，所以在 worker 那邊，檔案計數和大小合計都會是 0。
        create_job_response = await TestUserFilesStatJob.async_client.post(f'/me/files/stat-jobs/create', params={'file_idno': TestUserFilesStatJob.file_idno})
        assert create_job_response.status_code == HTTPStatus.CREATED
        TestUserFilesStatJob.queue_job_id = UUID(create_job_response.json())


    @pytest.mark.asyncio
    async def test_get_job(self):
        response = await TestUserFilesStatJob.async_client.get(f'/me/files/stat-jobs/{TestUserFilesStatJob.queue_job_id}')
        assert response.status_code == HTTPStatus.OK
        job_read = FilesStatJobRead.model_validate(response.json())
        assert job_read.queue_job_id == TestUserFilesStatJob.queue_job_id
        assert job_read.job_type == JobTypeEnum.FILES_STAT
        assert job_read.status == JobStatusEnum.PENDING # 如果 worker 正在跑，會變成 RUNNING，就會報錯。
        assert job_read.user_id == TestUserFilesStatJob.user.id


    @pytest.mark.asyncio
    async def test_get_jobs(self):
        response = await TestUserFilesStatJob.async_client.get(f'/me/files/stat-jobs')
        assert response.status_code == HTTPStatus.OK
        job_read_dict_list: list[dict] = response.json()
        job_read_list = [JobRead.model_validate(j) for j in job_read_dict_list]
        job_read = next((j for j in job_read_list if j.queue_job_id == TestUserFilesStatJob.queue_job_id), None)
        assert job_read


    @pytest.mark.asyncio
    async def test_teardown(self, db_session: Session):
        # Delete S3 files
        s3_session = get_session()
        async with s3_session.create_client(
            service_name='s3',
            region_name=_SETTINGS.AWS_DEFAULT_REGION,
            endpoint_url='https://2d318ba7bbba6520730569a4819999c4.r2.cloudflarestorage.com',
            aws_access_key_id=_SETTINGS.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=_SETTINGS.AWS_SECRET_ACCESS_KEY.get_secret_value(),
        ) as s3_client:
            response1_before_delete = await s3_client.head_object(Bucket=_S3_BUCKET_NAME, Key=TestUserFilesStatJob.file_s3_key)
            assert response1_before_delete
            await s3_client.delete_object(Bucket=_S3_BUCKET_NAME, Key=TestUserFilesStatJob.file_s3_key)
            try: response1_after_delete = await s3_client.head_object(Bucket=_S3_BUCKET_NAME, Key=TestUserFilesStatJob.file_s3_key)
            except ClientError as e1: assert e1
        
        # Delete DB UploadBatch and FcsFile reocrds
        statement = select(UploadBatch).where(UploadBatch.batch_idno == TestUserFilesStatJob.file_upload_batch_idno)
        batch = db_session.exec(statement).one_or_none()
        
        for f in batch.files: db_session.delete(f)
        db_session.delete(batch)
        db_session.commit()