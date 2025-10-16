from sqlalchemy import MetaData, create_engine
from sqlmodel import SQLModel, Session

from app.settings import get_settings



_SETTINGS = get_settings()



engine = create_engine(
    _SETTINGS.DATABASE_URL,
    # echo='debug',
)
SQLModel.metadata.naming_convention = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}).naming_convention
metadata = SQLModel.metadata



def get_db_session():
    with Session(engine) as session: yield session
