from http import HTTPStatus

from aiobotocore.session import get_session
from botocore.exceptions import ClientError
from httpx import AsyncClient
import httpx
import mimesis
import pytest
import pytest_asyncio
from sqlmodel import Session, select

from app.db import UploadBatch, engine
from app.logging import logger
from app.models import UploadBatchResult
from app.settings import get_settings



_SETTINGS = get_settings()
_S3_BUCKET_NAME = 'ahead-fcs-files'



mimesis_binary_file = mimesis.BinaryFile()
mimesis_file = mimesis.File()



@pytest_asyncio.fixture
async def db_session():
    with Session(engine) as session:
        yield session



class TestFile:
    upload_batch_idno: str

    fcs_file1_idno: str
    fcs_file2_idno: str

    fcs_file1_s3_key: str
    fcs_file2_s3_key: str


    @pytest.mark.asyncio
    async def test_upload_fcs_files(self, async_client: AsyncClient):
        fcs_file = mimesis_binary_file.compressed()
        fcs_file_1_name = mimesis_file.file_name() + '.fcs'
        fcs_file_2_name = mimesis_file.file_name() + '.fcs'

        response = await async_client.post(
            '/files/upload',
            # files={'upload_files': (fcs_file_1_name, fcs_file_1)},
            files=[
                ('upload_files', (fcs_file_1_name, fcs_file)),
                ('upload_files', (fcs_file_2_name, fcs_file)),
            ],
        )
        assert response.status_code == HTTPStatus.CREATED
        
        result = UploadBatchResult.model_validate(response.json())
        assert result
        assert result.batch_idno
        TestFile.upload_batch_idno = result.batch_idno

        assert result.files[0]
        assert result.files[1]
        assert result.files[0].file_idno
        assert result.files[1].file_idno
        TestFile.fcs_file1_idno = result.files[0].file_idno
        TestFile.fcs_file2_idno = result.files[1].file_idno

        assert result.files[0].s3_key
        assert result.files[1].s3_key
        TestFile.fcs_file1_s3_key = result.files[0].s3_key
        TestFile.fcs_file2_s3_key = result.files[1].s3_key
        

    @pytest.mark.asyncio
    async def test_get_file_info(self, async_client: AsyncClient):
        response1 = await async_client.get(f'/files/{TestFile.fcs_file1_idno}')
        assert response1.status_code == HTTPStatus.OK

        response2 = await async_client.get(f'/files/{TestFile.fcs_file2_idno}')
        assert response2.status_code == HTTPStatus.OK


    @pytest.mark.asyncio
    async def test_get_file_info_invalid_idno(self, async_client: AsyncClient):
        invalid_idno = "nonexistent_idno"
        response = await async_client.get(f'/files/{invalid_idno}')
        assert response.status_code == HTTPStatus.NOT_FOUND


    @pytest.mark.asyncio
    async def test_generate_download_url(self, async_client: AsyncClient):
        response1 = await async_client.get(f'/files/{TestFile.fcs_file1_idno}/generate-download-url')
        assert response1.status_code == HTTPStatus.CREATED

        response2 = await async_client.get(f'/files/{TestFile.fcs_file2_idno}/generate-download-url')
        assert response2.status_code == HTTPStatus.CREATED

        assert httpx.get(response1.json())
        assert httpx.get(response2.json())


    @pytest.mark.asyncio
    async def test_generate_download_url_invalid_file_idno(self, async_client: AsyncClient):
        invalid_file_idno = "nonexistent-file-idno"
        response = await async_client.get(f'/files/{invalid_file_idno}/generate-download-url')
        assert response.status_code == HTTPStatus.NOT_FOUND


    @pytest.mark.asyncio
    async def test_teardown(self, db_session: Session):
        s3_session = get_session()
        async with s3_session.create_client(
            service_name='s3',
            region_name=_SETTINGS.AWS_DEFAULT_REGION,
            endpoint_url='https://2d318ba7bbba6520730569a4819999c4.r2.cloudflarestorage.com',
            aws_access_key_id=_SETTINGS.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=_SETTINGS.AWS_SECRET_ACCESS_KEY.get_secret_value(),
        ) as s3_client:
            response1_before_delete = await s3_client.head_object(Bucket=_S3_BUCKET_NAME, Key=TestFile.fcs_file1_s3_key)
            response2_before_delete = await s3_client.head_object(Bucket=_S3_BUCKET_NAME, Key=TestFile.fcs_file2_s3_key)
            # logger.debug(response1_before_delete)
            '''
            {'ResponseMetadata': {'HTTPStatusCode': 200, 'HTTPHeaders': {'date': 'Fri, 17 Oct 2025 19:31:14 GMT', 'content-type': 'application/octet-stream', 'content-length': '673', 'connection': 'keep-alive', 'accept-ranges': 'bytes', 'etag': '"7638498a3b4b630380b875951118a02c"', 'last-modified': 'Fri, 17 Oct 2025 19:31:08 GMT', 'vary': 'Accept-Encoding', 'server': 'cloudflare', 'cf-ray': '9902370d8f2a4a4d-TPE'}, 'RetryAttempts': 0}, 'AcceptRanges': 'bytes', 'LastModified': datetime.datetime(2025, 10, 17, 19, 31, 8, tzinfo=tzutc()), 'ContentLength': 673, 'ETag': '"7638498a3b4b630380b875951118a02c"', 'ContentType': 'application/octet-stream', 'Metadata': {}}
            '''
            assert response1_before_delete
            assert response2_before_delete

            await s3_client.delete_object(Bucket=_S3_BUCKET_NAME, Key=TestFile.fcs_file1_s3_key)
            await s3_client.delete_object(Bucket=_S3_BUCKET_NAME, Key=TestFile.fcs_file2_s3_key)

            try: response1_after_delete = await s3_client.head_object(Bucket=_S3_BUCKET_NAME, Key=TestFile.fcs_file1_s3_key)
            except ClientError as e1: assert e1
            
            try: response2_after_delete = await s3_client.head_object(Bucket=_S3_BUCKET_NAME, Key=TestFile.fcs_file2_s3_key)
            except ClientError as e2: assert e2

        statement = select(UploadBatch).where(UploadBatch.batch_idno == TestFile.upload_batch_idno)
        batch = db_session.exec(statement).one_or_none()
        assert batch
        
        for f in batch.files: db_session.delete(f)
        db_session.delete(batch)
        db_session.commit()
        batch = db_session.exec(statement).one_or_none()
        assert not batch
