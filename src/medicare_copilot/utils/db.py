from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from src.medicare_copilot.utils.settings import settings

Base = declarative_base()

engine = create_engine(url=settings.DB_CONNECTION)

LocalSession = sessionmaker(bind=engine)


def get_db():
    session = LocalSession()
    try:
        yield session

    finally:
        session.close()
