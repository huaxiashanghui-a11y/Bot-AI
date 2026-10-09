import csv
import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Admin, TokenStat, Bot
from ..auth import get_current_admin

router = APIRouter(prefix="/api/stat", tags=["stat"])

@router.get("/list")
def stat_list(bot_id: int = 0, days: int = 30, db: Session = Depends(get_db),
              _: Admin = Depends(get_current_admin)):
    start = date.today() - timedelta(days=days - 1)
    q = db.query(TokenStat).filter(TokenStat.stat_date >= start)
    if bot_id:
        q = q.filter(TokenStat.bot_id == bot_id)
    rows = q.order_by(TokenStat.stat_date.desc(), TokenStat.bot_id.asc()).all()
    bot_names = {b.id: b.bot_name for b in db.query(Bot).all()}
    return {"items": [
        {"stat_date": str(r.stat_date), "bot_id": r.bot_id,
         "bot_name": bot_names.get(r.bot_id, ""),
         "input_tokens": r.total_input_tokens, "output_tokens": r.total_output_tokens,
         "total_tokens": r.total_input_tokens + r.total_output_tokens,
         "requests": r.total_request}
        for r in rows]}

@router.get("/export")
def stat_export(bot_id: int = 0, days: int = 30, db: Session = Depends(get_db),
                _: Admin = Depends(get_current_admin)):
    start = date.today() - timedelta(days=days - 1)
    q = db.query(TokenStat).filter(TokenStat.stat_date >= start)
    if bot_id:
        q = q.filter(TokenStat.bot_id == bot_id)
    rows = q.order_by(TokenStat.stat_date.asc()).all()
    buf = io.StringIO(); buf.write("\ufeff")
    w = csv.writer(buf)
    w.writerow(["日期", "BotID", "输入Token", "输出Token", "请求数"])
    for r in rows:
        w.writerow([str(r.stat_date), r.bot_id, r.total_input_tokens,
                    r.total_output_tokens, r.total_request])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition":
                                      "attachment; filename=token_stat.csv"})
