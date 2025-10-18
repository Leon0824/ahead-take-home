from typing import Literal
from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import EmailStr
from sqlmodel import Session, select

from app.auth import decode_token, generate_token, password_hash
from app.db import User, get_db_session
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
    password: str = Body(embed=True),
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

