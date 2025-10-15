from httpx import ASGITransport, AsyncClient
import pytest_asyncio

from app.main import app



@pytest_asyncio.fixture
async def async_client():
    return AsyncClient(base_url='http://test', transport=ASGITransport(app))