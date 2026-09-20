"""07 Response / Log / Feedback — ความจำของระบบ"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Depends, Response
from sqlalchemy.orm import Session
import csv
import io
from sqlalchemy import desc, func

from .common import health_payload, jlog, request_id_middleware
from .schemas import FeedbackIn, LogEntry
from .database import get_db, engine, Base
from .models import Conversation, Message, Feedback, RequestLog

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="chuayduay · response-log")
app.middleware("http")(request_id_middleware)

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

@app.get("/health")
async def health():
    return health_payload()

@app.post("/log", status_code=202)
async def write_log(entry: LogEntry, db: Session = Depends(get_db)):
    # กติกาข้อ 4 — ยิงซ้ำ request_id เดิมต้องไม่เกิดแถวซ้ำ
    if db.query(RequestLog).filter(RequestLog.request_id == entry.request_id).first():
        jlog(event="log_duplicate", session_id=entry.session_id)
        return {"accepted": True}

    now = _now_utc()
    db.add(RequestLog(request_id=entry.request_id, session_id=entry.session_id, created_at=now))

    # 07 สร้างแถว conversation ให้เอง
    conv = db.query(Conversation).filter(Conversation.session_id == entry.session_id).first()
    if not conv:
        conv = Conversation(
            session_id=entry.session_id,
            user_id=entry.user_id,
            title=entry.user_message[:40],
            created_at=now,
            updated_at=now
        )
        db.add(conv)
    else:
        conv.updated_at = now

    # Add messages
    user_msg = Message(
        message_id=entry.user_message_id,
        session_id=entry.session_id,
        request_id=entry.request_id,
        role="user",
        content=entry.user_message,
        sources=[],
        route=entry.route,
        created_at=now
    )
    
    decided_at = entry.trace.get("decided_at_layer") if entry.trace else None
    assistant_msg = Message(
        message_id=entry.assistant_message_id,
        session_id=entry.session_id,
        request_id=entry.request_id,
        role="assistant",
        content=entry.answer,
        sources=entry.sources,
        route=entry.route,
        engines_used=entry.engines_used,
        confidence=entry.confidence,
        reasoning=entry.reasoning,
        latency_ms=entry.latency_ms,
        token_usage=entry.token_usage.dict() if entry.token_usage else {},
        status=entry.status,
        error_code=entry.error_code,
        trace=entry.trace,
        decided_at_layer=decided_at,
        created_at=now + timedelta(microseconds=1)
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()

    jlog(event="log", session_id=entry.session_id, route=entry.route)
    return {"accepted": True}

@app.post("/feedback")
async def feedback(body: FeedbackIn, db: Session = Depends(get_db)):
    # กติกาข้อ 2 (ข้อ 4 ของ 07) — รับได้แม้ยังไม่มีแถว message นั้น แล้วค่อยเชื่อมกันตอนอ่าน (upsert)
    existing = db.query(Feedback).filter(Feedback.message_id == body.message_id).first()
    if existing:
        existing.rating = body.rating
        existing.comment = body.comment
    else:
        db.add(Feedback(
            message_id=body.message_id,
            user_id=body.user_id,
            rating=body.rating,
            comment=body.comment,
            created_at=_now_utc()
        ))
    db.commit()
    jlog(event="feedback", rating=body.rating)
    return {"ok": True}

@app.get("/sessions")
async def sessions(user_id: str, db: Session = Depends(get_db)):
    convs = db.query(Conversation).filter(Conversation.user_id == user_id).order_by(desc(Conversation.updated_at)).all()
    items = [{"session_id": c.session_id, "title": c.title, "updated_at": c.updated_at.isoformat()} for c in convs]
    return {"sessions": items}

@app.get("/history/{session_id}")
async def history(session_id: str, user_id: str, limit: int = 20, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.session_id == session_id).first()
    # กติกาข้อ 3 — ยังไม่มีข้อมูลให้ตอบ 200 พร้อม list ว่าง ห้าม 404
    if not conv:
        return {"session_id": session_id, "messages": []}
    
    # เช็กความเป็นเจ้าของ
    if conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="ไม่พบบทสนทนานี้")
        
    # กติกาข้อ 1 — เอา n รายการ "ล่าสุด" (ORDER BY created_at DESC LIMIT n) แล้วกลับลำดับ
    msgs = db.query(Message).filter(Message.session_id == session_id).order_by(desc(Message.created_at)).limit(limit).all()
    msgs.reverse()

    rows = []
    for m in msgs:
        fb = db.query(Feedback).filter(Feedback.message_id == m.message_id).first()
        rows.append({
            "message_id": m.message_id,
            "role": m.role,
            "content": m.content,
            "sources": m.sources,
            "route": m.route,
            "rating": fb.rating if fb else None,
            "created_at": m.created_at.isoformat() if m.created_at else None
        })
    return {"session_id": session_id, "messages": rows}

@app.get("/stats/routes")
async def stats_routes(days: int = 7, db: Session = Depends(get_db)):
    cutoff = _now_utc() - timedelta(days=days)
    layers = db.query(Message.decided_at_layer, func.count(Message.decided_at_layer)).filter(
        Message.role == "assistant",
        Message.created_at >= cutoff,
        Message.decided_at_layer != None
    ).group_by(Message.decided_at_layer).all()
    return {"by_layer": {r[0]: r[1] for r in layers}}

@app.get("/stats")
async def stats(days: int = 7, db: Session = Depends(get_db)):
    cutoff = _now_utc() - timedelta(days=days)
    
    # Total requests (from RequestLog)
    total_requests = db.query(RequestLog).filter(RequestLog.created_at >= cutoff).count()
    
    # Latency stats
    latencies = db.query(Message.latency_ms).filter(
        Message.role == "assistant", 
        Message.created_at >= cutoff,
        Message.latency_ms != None
    ).all()
    
    latencies = [l[0] for l in latencies if l[0] is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies)*0.95)] if latencies else 0

    # Route counts
    routes = db.query(Message.route, func.count(Message.route)).filter(
        Message.role == "assistant",
        Message.created_at >= cutoff,
        Message.route != None
    ).group_by(Message.route).all()
    by_route = {r[0]: r[1] for r in routes}

    # Feedback
    up = db.query(Feedback).filter(Feedback.created_at >= cutoff, Feedback.rating == 1).count()
    down = db.query(Feedback).filter(Feedback.created_at >= cutoff, Feedback.rating == -1).count()

    # Errors
    error_count = db.query(Message).filter(
        Message.role == "assistant",
        Message.created_at >= cutoff,
        Message.status == "error"
    ).count()
    error_rate = (error_count / total_requests) if total_requests > 0 else 0.0

    return {
        "total_requests": total_requests,
        "avg_latency_ms": int(avg_latency),
        "p95_latency_ms": int(p95_latency),
        "by_route": by_route,
        "feedback": {"up": up, "down": down},
        "error_rate": error_rate,
        "top_downvoted": []
    }

@app.get("/export/feedback.csv")
async def export_feedback_csv(days: int = 30, db: Session = Depends(get_db)):
    cutoff = _now_utc() - timedelta(days=days)
    
    # Get all feedback in the last X days, joined with the corresponding assistant message
    feedbacks = db.query(Feedback, Message).outerjoin(
        Message, Feedback.message_id == Message.message_id
    ).filter(
        Feedback.created_at >= cutoff
    ).order_by(desc(Feedback.created_at)).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["created_at", "rating", "user_id", "message_id", "comment", "route", "ai_answer"])
    
    for fb, msg in feedbacks:
        route = msg.route if msg else ""
        answer = msg.content if msg else ""
        writer.writerow([
            fb.created_at.isoformat(),
            fb.rating,
            fb.user_id,
            fb.message_id,
            fb.comment or "",
            route,
            answer
        ])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=feedback_{days}days.csv"}
    )

