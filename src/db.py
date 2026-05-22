import os
from sqlmodel import create_engine, SQLModel

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///database.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
