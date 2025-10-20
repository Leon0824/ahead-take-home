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

    BASE_URL: str
    ALLOW_ORIGINS: list[str]

    DATABASE_URL: str
    REDIS_URL: RedisDsn

    ADMIN_EMAIL: EmailStr
    ADMIN_PASSWORD: SecretStr

    JWT_KEY: SecretStr

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: SecretStr
    AWS_DEFAULT_REGION: str
    AWS_S3_ENDPOINT_URL: HttpUrl

    _example: ClassVar[dict] = {
        'ENVIRONMENT_MODE': 'DEVELOPMENT',

        'BASE_URL': 'https://api.wnc.net',
        'ALLOW_ORIGINS' : ['http://localhost:5173'],

        'DATABASE_URL': 'sqlite:///database.db',
        'REDIS_URL': 'redis://redis-15500.c290.ap-northeast-1-2.ec2.redns.redis-cloud.com:15500',

        'ADMIN_USERNAME': 'admin',
        'ADMIN_PASSWORD': '**********',

        'JWT_KEY': '**********',

        'AWS_ACCESS_KEY_ID': 'AWSID',
        'AWS_SECRET_ACCESS_KEY': 'AWSSECRET',
        'AWS_DEFAULT_REGION': 'ap-northeast-1',
        "AWS_S3_ENDPOINT_URL": 'https://s3.ap-northeast-1.amazonaws.com',
    }
    model_config = SettingsConfigDict(
        json_schema_extra={'examples': [_example]},
        extra='allow',
        env_file='.env',
        secrets_dir='/run/secrets',
    )



def get_settings(): return Settings()
