from datetime import UTC, datetime

from fastapi import FastAPI
from sqlmodel import SQLModel, Field, create_engine, Session 
from sqlalchemy import CheckConstraint, DateTime

import os

app = FastAPI(title="Change Order API")

class user(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    role: str = Field(sa_column_args=[CheckConstraint("role IN ('contractor', 'admin', 'client')")])
    name: str = Field(index=True)
    phone: str = Field(index=True)

class change_orders(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    contractor_id: int = Field(index=True)
    client_id: int = Field(index=True)
    photo_key: str
    status: str = Field(default="pending", sa_column_args=[CheckConstraint("status IN ('pending', 'approved', 'rejected')")])
    approved_by_id: int | None = Field(index=True)
    approved_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class notifications(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    report_id: int = Field(index=True)
    recipient_user_id: int = Field(index=True)
    type: str = Field(default="report_submitted", sa_column_args=[CheckConstraint("type IN ('report_submitted', 'report_approved', 'report_rejected')")])
    status: str = Field(default="pending", sa_column_args=[CheckConstraint("status IN ('pending', 'sent')")])
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sent_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

engine = create_engine(os.environ["DATABASE_URL"], echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine) #only create tables if they don't exist

def get_session():
    with Session(engine) as session:
        yield session

@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/health")
def health():
    return {"status": "ok"}