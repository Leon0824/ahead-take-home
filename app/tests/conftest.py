from httpx import ASGITransport, AsyncClient
import pytest_asyncio
from sqlmodel import Session

from app.db import engine
from app.main import app



@pytest_asyncio.fixture
async def async_client():
    return AsyncClient(base_url='http://test', transport=ASGITransport(app))



@pytest_asyncio.fixture
async def db_session():
    with Session(engine) as session:
        yield session