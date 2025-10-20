import pytest

from tests.logging import logger



@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig): return '../compose.yaml'