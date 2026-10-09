import csv
import io
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Admin, ChatHistory, Bot
from ..auth import get_current_admin

router = APIRouter(prefix="/api/chat", tags=["chat"])

def _query(db: Session, bot_id: int, tg_user_id: str, start: str, end: str):
    q = db.query(ChatHistory)
    if bot_id:
        q = q.filter(ChatHistory.bot_id == bot_id)
    if tg_user_id:
        q = q.filter(ChatHistory.tg_user_id == int(tg_user_id))
    if start:
        q = q.filter(ChatHistory.created_at >= datetime.fromisoformat(start))
    if end:
        q = q.filter(ChatHistory.created_at <= datetime.fromisoformat(end) + timedelta(days=1))
    return q

@router.get("/list")
def chat_list(bot_id: int = 0, tg_user_id: str = "", start: str = "",
              end: str = "", page: int = 1, size: int = 20,
              db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    q = _query(db, bot_id, tg_user_id, start, end)
    total = q.count()
    rows = q.order_by(ChatHistory.id.desc()).offset((page - 1) * size).limit(size).all()
    bot_names = {b.id: b.bot_name for b in db.query(Bot).all()}
    return {"total": total, "items": [
        {"id": r.id, "bot_name": bot_names.get(r.bot_id, ""),
         "tg_user_id": r.tg_user_id, "role": r.role, "content": r.content,
         "token_count": r.token_count,
         "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")}
        for r in rows]}

@router.get("/export")
def chat_export(bot_id: int = 0, tg_user_id: str = "", start: str = "",
                end: str = "", db: Session = Depends(get_db),
                _: Admin = Depends(get_current_admin)):
    rows = _query(db, bot_id, tg_user_id, start, end).order_by(ChatHistory.id.asc()).all()
    buf = io.StringIO()
    buf.write("\ufeff")  # BOM for Excel
    w = csv.writer(buf)
    w.writerow(["时间", "Bot", "TG用户ID", "角色", "内容", "Token数"])
    for r in rows:
        w.writerow([r.created_at.strftime("%Y-%m-%d %H:%M"), r.bot_id,
                    r.tg_user_id, r.role, r.content, r.token_count])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=chats.csv"})
