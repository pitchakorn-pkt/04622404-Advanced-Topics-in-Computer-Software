from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://dl06:dl06@postgres:5432/dl06")

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)

def _now() -> datetime:
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32), default="student")
    password_hash: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(128))
    pages: Mapped[int] = mapped_column(Integer, default=0)
    chars: Mapped[int] = mapped_column(Integer, default=0)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

def _pw(password: str) -> bytes:
    return password.encode("utf-8")[:72]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw(password), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_pw(password), hashed.encode())
    except ValueError:
        return False


def user_id_for(username: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, username)

DEMO_USERS = [
    {"username": "student", "password": "student", "display_name": "student", "role": "student"},
    {"username": "staff", "password": "staff", "display_name": "staff", "role": "staff"},
    {"username": "demo", "password": "demo", "display_name": "demo", "role": "student"},
]

async def get_user(username: str) -> User | None:
    async with Session() as session:
        result = await session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

async def _seed_users() -> int:
    added = 0
    async with Session() as session:
        for demo in DEMO_USERS:
            exists = await session.execute(select(User.id).where(User.username == demo["username"]))
            if exists.scalar_one_or_none() is not None:
                continue
            session.add(User(id=user_id_for(demo["username"]), username=demo["username"],
                             display_name=demo["display_name"], role=demo["role"],
                             password_hash=hash_password(demo["password"])))
            added += 1
        await session.commit()
    return added


async def init_db(retries: int = 15, delay: float = 2.0) -> int:
    last: Exception | None = None
    for _ in range(retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return await _seed_users()
        except Exception as exc:
            last = exc
            await asyncio.sleep(delay)
    raise RuntimeError(f"ต่อฐานข้อมูลไม่ได้: {last}")