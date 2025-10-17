from datetime import UTC, datetime
from http import HTTPStatus
from httpx import AsyncClient
import mimesis
import pytest



mimesis_binary_file = mimesis.BinaryFile()
mimesis_file = mimesis.File()


class TestFile:
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
