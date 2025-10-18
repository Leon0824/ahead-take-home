from http import HTTPStatus
import json

from aiobotocore.session import get_session
from botocore.exceptions import ClientError
from httpx import AsyncClient
import httpx
import mimesis
import pytest
from sqlmodel import Session, select

from app.db import UploadBatch, User
from app.logging import logger
from app.models import Token, UploadBatchResult, UploadFileSetting
from app.settings import get_settings



_SETTINGS = get_settings()
_S3_BUCKET_NAME = 'ahead-fcs-files'



mimesis_binary_file = mimesis.BinaryFile()
mimesis_file = mimesis.File()



class TestUserPrivateFile:
    user: User

    file_upload_batch_idno: str
    file_idno: str
    file_s3_key: str

    
    @pytest.mark.asyncio
    async def test_user_upload_private_files(self, async_client: AsyncClient, new_user: User, db_session: Session):
        file = mimesis_binary_file.compressed()
        file_name = mimesis_file.file_name() + '.fcs'

        TestUserPrivateFile.user = new_user

        # Sign in
        sign_in_response = await async_client.post('/auth/sign-in', data={'username': TestUserPrivateFile.user.username, 'password': TestUserPrivateFile.user.username})
        access_token = Token.model_validate(sign_in_response.json())
        async_client.headers.update({'Authorization': f'{access_token.token_type} {access_token.token_string}'})

        # Upload
        upload_response = await async_client.post(
            '/files/upload',
            files={'upload_files': (file_name, file)},
            data={'upload_file_settings': json.dumps([UploadFileSetting(filename=file_name, public=False).model_dump()])},
        )
        assert upload_response.status_code == HTTPStatus.CREATED
        logger.debug(async_client.headers.items())
        
        result = UploadBatchResult.model_validate(upload_response.json())
        TestUserPrivateFile.file_upload_batch_idno = result.batch_idno
        TestUserPrivateFile.file_idno = result.files[0].file_idno
        TestUserPrivateFile.file_s3_key = result.files[0].s3_key
        
        # Chcck DB
        db_session.refresh(TestUserPrivateFile.user)
        db_file = TestUserPrivateFile.user.files[0]
        assert db_file
        assert not db_file.public


    @pytest.mark.asyncio
    async def test_user_download_private_files(
        self,
        async_client: AsyncClient, # 這個 client fixture 是新的，沒有帶 token 標頭。
    ):
        # Sign in
        sign_in_response = await async_client.post('/auth/sign-in', data={'username': TestUserPrivateFile.user.username, 'password': TestUserPrivateFile.user.username})
        access_token = Token.model_validate(sign_in_response.json())
        async_client.headers.update({'Authorization': f'{access_token.token_type} {access_token.token_string}'})

        # Get file info
        info_response = await async_client.get(f'/files/{TestUserPrivateFile.file_idno}')
        assert info_response.status_code == HTTPStatus.OK

        # Download
        download_url_response = await async_client.get(f'/files/{TestUserPrivateFile.file_idno}/generate-download-url')
        assert download_url_response.status_code == HTTPStatus.CREATED
        assert httpx.get(download_url_response.json())


    @pytest.mark.asyncio
    async def test_download_private_files(
        self,
        async_client: AsyncClient, # 這個 client fixture 是新的，沒有帶 token 標頭。
    ):
        # Get file info
        info_response = await async_client.get(f'/files/{TestUserPrivateFile.file_idno}')
        assert info_response.status_code == HTTPStatus.NOT_FOUND

        # Download
        download_url_response = await async_client.get(f'/files/{TestUserPrivateFile.file_idno}/generate-download-url')
        assert download_url_response.status_code == HTTPStatus.NOT_FOUND


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
            response1_before_delete = await s3_client.head_object(Bucket=_S3_BUCKET_NAME, Key=TestUserPrivateFile.file_s3_key)
            assert response1_before_delete
            await s3_client.delete_object(Bucket=_S3_BUCKET_NAME, Key=TestUserPrivateFile.file_s3_key)
            try: response1_after_delete = await s3_client.head_object(Bucket=_S3_BUCKET_NAME, Key=TestUserPrivateFile.file_s3_key)
            except ClientError as e1: assert e1
        
        # Delete DB UploadBatch and FcsFile reocrds
        statement = select(UploadBatch).where(UploadBatch.batch_idno == TestUserPrivateFile.file_upload_batch_idno)
        batch = db_session.exec(statement).one_or_none()
        
        for f in batch.files: db_session.delete(f)
        db_session.delete(batch)
        db_session.commit()

        # Delete DB User and FcsFile records
        for f in TestUserPrivateFile.user.files: db_session.delete(f)
        db_session.delete(TestUserPrivateFile.user)
        db_session.commit()