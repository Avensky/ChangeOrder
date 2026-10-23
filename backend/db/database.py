from sqlmodel import SQLModel, create_engine, Session
import os

engine = create_engine(os.environ["DATABASE_URL"], echo=True)


def create_db_and_tables():
    # only create tables if they don't exist
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session

