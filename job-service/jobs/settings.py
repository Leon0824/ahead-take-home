from typing import ClassVar, Literal

from pydantic import UUID4, AnyUrl, EmailStr, Field, FilePath, HttpUrl, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    ENVIRONMENT_MODE: Literal[
        'DEVELOPMENT', # 本機開發環境
        'STAGING', # 測試站
        'PRODUCTION', # 正式站
        'TEST', # CI 測試環境
    ]

    DATABASE_URL: str
    REDIS_URL: RedisDsn

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: SecretStr
    AWS_DEFAULT_REGION: str

    _example: ClassVar[dict] = {
        'ENVIRONMENT_MODE': 'DEVELOPMENT',

        'DATABASE_URL': 'sqlite:///database.db',
        'REDIS_URL': 'redis://redis-15500.c290.ap-northeast-1-2.ec2.redns.redis-cloud.com:15500',

        'AWS_ACCESS_KEY_ID': 'AWSID',
        'AWS_SECRET_ACCESS_KEY': 'AWSSECRET',
        'AWS_DEFAULT_REGION': 'ap-northeast-1',
    }
    model_config = SettingsConfigDict(
        json_schema_extra={'examples': [_example]},
        extra='allow',
        env_file='.env',
        secrets_dir='/run/secrets',
    )



def get_settings(): return Settings()
