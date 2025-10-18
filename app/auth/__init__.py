from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
import jwt
from pwdlib import PasswordHash

from app.logging import logger
from app.models import JwtPayload
from app.settings import Settings



password_hash = PasswordHash.recommended()



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
