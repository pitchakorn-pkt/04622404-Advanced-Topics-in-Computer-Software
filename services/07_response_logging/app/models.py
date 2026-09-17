from __future__ import annotations

from sqlalchemy import Column, String, Integer, Float, JSON, DateTime
from .database import Base

class Conversation(Base):
    __tablename__ = "conversations"

    session_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    title = Column(String)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(String, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(String, nullable=False)
    sources = Column(JSON, default=list)
    route = Column(String)
    engines_used = Column(JSON, default=list)
    confidence = Column(Float)
    reasoning = Column(String)
    latency_ms = Column(Integer)
    token_usage = Column(JSON)
    status = Column(String, default="ok")
    error_code = Column(String)
    trace = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False)

class Feedback(Base):
    __tablename__ = "feedback"

    message_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)  # 1 or -1
    comment = Column(String)
    created_at = Column(DateTime(timezone=True), nullable=False)

class RequestLog(Base):
    __tablename__ = "request_logs"

    request_id = Column(String, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
