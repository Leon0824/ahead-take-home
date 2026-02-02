from http import HTTPStatus
import json
from time import sleep
from uuid import UUID

import httpx
import mimesis
import pytest
from pytest_docker.plugin import Services

from tests.logging import logger



mimesis_person = mimesis.Person()
mimesis_binary_file = mimesis.BinaryFile()
mimesis_file = mimesis.File()



def is_responsive(url: str):
    logger.debug(url)
    try:
        response = httpx.get(f'{url}/system/health')
        if response.status_code == HTTPStatus.OK: return True
        else: return False
    except httpx.ConnectError: return False



@pytest.fixture(scope="session")
def traefik_service(docker_ip, docker_services: Services):
    url = 'http://localhost'
    docker_services.wait_until_responsive(
        timeout=60, pause=5, check=lambda: is_responsive(url),
    )
    return url



class TestUserFilesStatJob:
    client: httpx.Client

    queue_job_id: UUID


    def test_create_job(self, traefik_service: str):
        file = mimesis_binary_file.compressed()
        file_name = mimesis_file.file_name() + '.fcs'

        TestUserFilesStatJob.client = httpx.Client()

        # Sign up
        email = mimesis_person.email(unique=True)
        response = TestUserFilesStatJob.client.post(f'{traefik_service}/auth/sign-up', json={'email': email, 'password': email})
        assert response.status_code == 201

        # Sign in
        sign_in_response = TestUserFilesStatJob.client.post(f'{traefik_service}/auth/sign-in', data={'username': email, 'password': email})
        token: dict = sign_in_response.json()
        TestUserFilesStatJob.client.headers.update({'Authorization': f'{token['token_type']} {token['access_token']}'})

        # Upload
        upload_response = TestUserFilesStatJob.client.post(
            f'{traefik_service}/files/upload',
            files={'upload_files': (file_name, file)},
            data={'upload_file_settings': json.dumps([{'filename': file_name, 'public': False}])},
        )
        assert upload_response.status_code == HTTPStatus.CREATED

        upload_result: dict = upload_response.json()
        _file_upload_batch_idno = upload_result['batch_idno']
        _file_idno = upload_result['files'][0]['file_idno']
        _file_s3_key = upload_result['files'][0]['s3_key']

        # Create job
        create_job_response = TestUserFilesStatJob.client.post(f'{traefik_service}/me/files/stat-jobs/create')
        assert create_job_response.status_code == HTTPStatus.CREATED
        TestUserFilesStatJob.queue_job_id = UUID(create_job_response.json())


    def test_get_job(self, traefik_service: str):
        sleep(10)  # Wait for the background job to complete

        response = TestUserFilesStatJob.client.get(f'{traefik_service}/me/files/stat-jobs/{TestUserFilesStatJob.queue_job_id}')
        assert response.status_code == HTTPStatus.OK

        job_read: dict = response.json()
        assert job_read['status'] == 'FINISHED'
        
