from datetime import UTC, datetime
from http import HTTPStatus

from aiobotocore.session import get_session
from httpx import AsyncClient
import mimesis
import pytest

from app.models import UploadBatchResult
from app.settings import get_settings



_SETTINGS = get_settings()



mimesis_binary_file = mimesis.BinaryFile()
mimesis_file = mimesis.File()


class TestFile:
    upload_batch_idno: str
    fcs_file1_idno: str
    fcs_file2_idno: str

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
        

    @pytest.mark.asyncio
    async def test_get_file_info(self, async_client: AsyncClient):
        response1 = await async_client.get(f'/files/{TestFile.fcs_file1_idno}')
        assert response1.status_code == HTTPStatus.OK

        response2 = await async_client.get(f'/files/{TestFile.fcs_file2_idno}')
        assert response2.status_code == HTTPStatus.OK

        s3_session = get_session()
        async with s3_session.create_client(
            service_name='s3',
            region_name=_SETTINGS.AWS_DEFAULT_REGION,
            endpoint_url='https://2d318ba7bbba6520730569a4819999c4.r2.cloudflarestorage.com',
            aws_access_key_id=_SETTINGS.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=_SETTINGS.AWS_SECRET_ACCESS_KEY.get_secret_value(),
        ) as s3_client:
            ...