from datetime import timedelta
from typing import Annotated, Literal
from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Request, Response, Security, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from sqlmodel import Session, select

from app.auth import authenticate_account, decode_token, generate_token, get_requestor_user, password_hash
from app.db import User, get_db_session
from app.logging import logger
from app.models import Token
from app.settings import Settings, get_settings



router = APIRouter(prefix='/auth', tags=['auth'])



@router.post('/send-verification-mail', operation_id='send_verification_mail')
async def send_verification_mail(
    email: EmailStr,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> bool:
    user = db_session.exec(select(User).where(User.username == email)).one_or_none()
    if not user: return False

    _verification_code = generate_token(key=settings.JWT_KEY.get_secret_value(), sub=email, exp_hours=24)
    # 寄信
    ...
    return True



@router.post('/sign-up', status_code=status.HTTP_201_CREATED, operation_id='sign_up')
async def sign_up(
    email: EmailStr = Body(embed=True),
    password: str = Body(embed=True, min_length=8),
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> Literal[True]:
    _existed = db_session.exec(select(User).where(User.username == email)).one_or_none()
    if _existed: raise HTTPException(status.HTTP_409_CONFLICT)

    _hashed_password = password_hash.hash(password)
    user = User(username=email, hashed_password=_hashed_password, email_verified=False)
    db_session.add(user)
    db_session.commit()
    await send_verification_mail(email=user.username, db_session=db_session, settings=settings)
    return True



@router.post('/verify-email', operation_id='verify_email')
async def verify_email(
    email: EmailStr = Body(embed=True),
    verification_code: str = Body(embed=True),
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> bool:
    user = db_session.exec(select(User).where(User.username == email)).one_or_none()
    if not user: return False

    # 目前寄不了信，先不真的驗證。
    # try: decoded = decode_token(settings=settings, token=verification_code, verify_exp=True)
    # except HTTPException as e: return False
    # if decoded['sub'] != email: return False

    user.email_verified = True
    db_session.add(user)
    db_session.commit()
    return True



@router.post('/sign-in', operation_id='sign-in')
async def sign_in(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> Token:
    _user = authenticate_account(username=form_data.username, password=form_data.password, db_session=db_session)

    # if not _user.email_verified: raise HTTPException(status.HTTP_403_FORBIDDEN, {'email_verified': _user.email_verified})

    _refresh_token = generate_token(key=settings.JWT_KEY.get_secret_value(), sub=_user.username, exp_weeks=1)
    response.set_cookie(
        'refresh_token',
        _refresh_token,
        int(timedelta(weeks=1).total_seconds()), # 604,800 seconds
        httponly=True,
    )

    _access_token = generate_token(key=settings.JWT_KEY.get_secret_value(), sub=_user.username, exp_days=1)

    logger.info({'title': 'User signed-in', 'user': _user.username})
    return Token(access_token=_access_token)



@router.post('/sign-out', operation_id='sign-out')
async def sign_out(
    response: Response,
    user: User | None = Security(get_requestor_user),
) -> Literal[True]:
    logger.info(f'User {user.username} is signing out')
    response.delete_cookie('refresh_token')
    return True



@router.post('/refresh', operation_id='refresh_tokens')
async def refresh_tokens(
    response: Response,
    refresh_token: Annotated[str, Cookie(include_in_schema=False)] = None,
    user: User | None = Security(get_requestor_user),
    settings: Settings = Depends(get_settings),
) -> Token:
    '''
    '''
    if not user: raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    if not refresh_token: raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    _new_access_token = generate_token(key=settings.JWT_KEY.get_secret_value(), sub=user.username, exp_days=1)
    _new_refresh_token = generate_token(key=settings.JWT_KEY.get_secret_value(), sub=user.username, exp_weeks=1)
    response.set_cookie(
        'refresh_token',
        _new_refresh_token,
        int(timedelta(weeks=1).total_seconds()), # 604,800 seconds
        httponly=True,
    )
    # logger.debug(refresh_token)
    # logger.debug(_new_refresh_token)
    # logger.debug(_new_access_token)
    return Token(access_token=_new_access_token)
