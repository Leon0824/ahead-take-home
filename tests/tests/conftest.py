import pytest



@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig): return '../compose.yaml'