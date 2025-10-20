from http import HTTPStatus
from httpx import AsyncClient
import mimesis
from pydantic import EmailStr
import pytest
from sqlmodel import Session, select

from app.db import User
from app.logging import logger
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
    async def test_sign_in_to_sign_out(self, async_client: AsyncClient):
        # Sign in
        async_client.cookies.clear() # Clear all cookies before testing!
        sign_in_response = await async_client.post('/auth/sign-in', data={'username': TestAuth.email, 'password': TestAuth.email})
        assert sign_in_response.status_code == HTTPStatus.OK
        
        refresh_token_cookie = sign_in_response.cookies.get('refresh_token')
        assert refresh_token_cookie
        
        access_token = Token.model_validate(sign_in_response.json())
        assert access_token
        async_client.headers.update({'Authorization': f'{access_token.token_type} {access_token.access_token}'})

        # Refresh
        refresh_response = await async_client.post('/auth/refresh')
        refresh_response = await async_client.post('/auth/refresh')
        assert refresh_response.status_code == HTTPStatus.OK
        
        refresh_token_cookie2 = refresh_response.cookies.get('refresh_token')
        assert refresh_token_cookie2
        assert refresh_token_cookie != refresh_token_cookie2
        
        access_token2 = Token.model_validate(refresh_response.json())
        assert access_token2
        assert access_token != access_token2
        async_client.headers.update({'Authorization': f'{access_token2.token_type} {access_token2.access_token}'})

        # Sign out
        sign_out_response = await async_client.post('/auth/sign-out')
        assert sign_out_response.status_code == HTTPStatus.OK
        refresh_token_cookie3 = sign_out_response.cookies.get('refresh_token')
        assert not refresh_token_cookie3


    @pytest.mark.asyncio
    async def test_teardown(self, db_session: Session):
        db_session.delete(TestAuth.user)
        db_session.commit()
        