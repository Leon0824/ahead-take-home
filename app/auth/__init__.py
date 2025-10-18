from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from pwdlib import PasswordHash
from sqlmodel import Session, select, update

from app.db import User, get_db_session
from app.logging import logger
from app.models import JwtPayload
from app.settings import Settings, get_settings



password_hash = PasswordHash.recommended()



oauth2_password_bearer = OAuth2PasswordBearer('auth/sign-in', auto_error=False)



def generate_token(
    key: str,
    sub: str, exp_weeks: int = 0, exp_days: int = 0, exp_hours: int = 0, exp_minutes: int = 0,
):
    _expiration_time = datetime.now(UTC) + timedelta(weeks=exp_weeks, days=exp_days, hours=exp_hours, minutes=exp_minutes)
    _payload = JwtPayload(sub=sub, exp=_expiration_time)
    return jwt.encode(_payload.model_dump(), key)



def decode_token(settings: Settings, token: str, verify_exp: bool = True) -> dict:
    '''Decode JWT'''
    try: return jwt.decode(token, settings.JWT_KEY.get_secret_value(), ['HS256'], {'verify_exp': verify_exp})
    except jwt.InvalidTokenError as invalid_token_error:
        logger.error(invalid_token_error.args)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, {'message': 'Invalid token'}) from invalid_token_error



def verify_account_password(user: User, to_verify_password: str, db_session: Session):
    '''認證帳密'''
    valid, _new_hash = password_hash.verify_and_update(to_verify_password, user.hashed_password)
    if _new_hash: db_session.exec(update(User).where(User.id == user.id).values(hashed_password=_new_hash))
    return valid



def authenticate_account(username: str, password: str, db_session: Session):
    ...
    user = db_session.exec(select(User).where(User.username == username)).one_or_none()
    if not user:
        logger.warning({'title': 'User not found', 'email': username, 'password': password})
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    
    _account_valid = verify_account_password(user=user, to_verify_password=password, db_session=db_session)
    if not _account_valid:
        logger.error({'email': username, 'password': password})
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    return user



def _get_username_from_token(settings: Settings, token: str, verify_exp: bool = True):
    decoded_token_dict = decode_token(settings=settings, token=token, verify_exp=verify_exp)
    username: str = decoded_token_dict.get('sub')
    if username is None:
        logger.error(f'No username found in token {token}')
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, {'message': 'Token error'})
    return username



def get_requestor_user(
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    oauth2_token: str | None = Security(oauth2_password_bearer),
):
    if not oauth2_token: return None
    _username = _get_username_from_token(settings=settings, token=oauth2_token)
    return db_session.exec(select(User).where(User.username == _username)).one_or_none()
