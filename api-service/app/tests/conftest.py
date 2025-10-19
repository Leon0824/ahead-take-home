from httpx import ASGITransport, AsyncClient
import mimesis
import pytest_asyncio
from sqlmodel import Session, select

from app.db import User, engine
from app.main import app



mimesis_person = mimesis.Person()



@pytest_asyncio.fixture
async def async_client():
    return AsyncClient(base_url='http://test', transport=ASGITransport(app))



@pytest_asyncio.fixture
async def db_session():
    with Session(engine) as session:
        yield session



@pytest_asyncio.fixture
async def new_user(async_client: AsyncClient, db_session: Session):
    email = mimesis_person.email(unique=True)
    response = await async_client.post('/auth/sign-up', json={'email': email, 'password': email})
    user = db_session.exec(select(User).where(User.username == email)).one_or_none()
    assert user
    return user