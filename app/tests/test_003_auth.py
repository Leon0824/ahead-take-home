from http import HTTPStatus
from httpx import AsyncClient
import mimesis
from pydantic import EmailStr
import pytest
from sqlmodel import Session, select

from app.db import User
from app.models import Token



mimesis_person = mimesis.Person()



class TestAuth:
    email: EmailStr
    user: User


    @pytest.mark.asyncio
    async def test_sign_up(self, async_client: AsyncClient):
        TestAuth.email = mimesis_person.email(unique=True)

        response = await async_client.post('/auth/sign-up', json={'email': TestAuth.email, 'password': TestAuth.email})
        assert response.status_code == HTTPStatus.CREATED
        assert response.json() == True

        


    @pytest.mark.asyncio
    async def test_verify_email(self, async_client: AsyncClient, db_session: Session):
        response = await async_client.post('/auth/verify-email', json={'email': TestAuth.email, 'verification_code': 'ABC'})
        assert response.status_code == HTTPStatus.OK
        assert response.json() == True

        TestAuth.user = db_session.exec(select(User).where(User.username == TestAuth.email)).one_or_none()
        assert TestAuth.user
        assert TestAuth.user.email_verified == True


    @pytest.mark.asyncio
    async def test_sign_in(self, async_client: AsyncClient):
        response = await async_client.post('/auth/sign-in', data={'username': TestAuth.email, 'password': TestAuth.email})
        assert response.status_code == HTTPStatus.OK
        assert response.cookies.get('refresh_token')
        access_token = Token.model_validate(response.json())
        assert access_token


    @pytest.mark.asyncio
    async def test_teardown(self, db_session: Session):
        db_session.delete(TestAuth.user)
        db_session.commit()
        