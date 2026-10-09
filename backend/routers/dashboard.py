from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Admin, Bot, TgUser, ChatHistory, TokenStat
from ..auth import get_current_admin

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/summary")
def summary(db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    today = date.today()
    total_users = db.query(TgUser).count()
    black_users = db.query(TgUser).filter(TgUser.is_black == True).count()  # noqa: E712
    total_bots = db.query(Bot).count()
    active_bots = db.query(Bot).filter(Bot.bot_switch == True).count()  # noqa: E712

    t = db.query(
        func.coalesce(func.sum(TokenStat.total_request), 0),
        func.coalesce(func.sum(TokenStat.total_input_tokens), 0),
        func.coalesce(func.sum(TokenStat.total_output_tokens), 0),
    ).filter(TokenStat.stat_date == today).one()

    return {
        "total_users": total_users,
        "black_users": black_users,
        "total_bots": total_bots,
        "active_bots": active_bots,
        "today_requests": t[0],
        "today_input_tokens": t[1],
        "today_output_tokens": t[2],
    }

@router.get("/bot-stats")
def bot_stats(db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    today = date.today()
    rows = db.query(Bot).order_by(Bot.id.asc()).all()
    result = []
    for b in rows:
        s = db.query(
            func.coalesce(func.sum(TokenStat.total_request), 0),
            func.coalesce(func.sum(TokenStat.total_input_tokens)
                          + func.sum(TokenStat.total_output_tokens), 0),
        ).filter(TokenStat.bot_id == b.id, TokenStat.stat_date == today).one()
        result.append({
            "bot_id": b.id, "bot_name": b.bot_name, "model": b.ark_model_id,
            "bot_switch": b.bot_switch,
            "today_requests": s[0], "today_tokens": s[1],
        })
    return {"items": result}

@router.get("/trend")
def trend(days: int = 7, db: Session = Depends(get_db),
          _: Admin = Depends(get_current_admin)):
    end = date.today()
    start = end - timedelta(days=days - 1)
    rows = db.query(
        TokenStat.stat_date,
        func.coalesce(func.sum(TokenStat.total_request), 0),
        func.coalesce(func.sum(TokenStat.total_input_tokens)
                      + func.sum(TokenStat.total_output_tokens), 0),
    ).filter(TokenStat.stat_date >= start).group_by(TokenStat.stat_date).all()
    stat_map = {str(r[0]): {"req": r[1], "tokens": r[2]} for r in rows}
    dates, reqs, tokens = [], [], []
    for i in range(days):
        d = (start + timedelta(days=i)).isoformat()
        dates.append(d)
        reqs.append(stat_map.get(d, {}).get("req", 0))
        tokens.append(stat_map.get(d, {}).get("tokens", 0))
    return {"dates": dates, "requests": reqs, "tokens": tokens}

@router.get("/alerts")
def alerts(db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    items = []
    disabled = db.query(Bot).filter(Bot.bot_switch == False).all()  # noqa: E712
    for b in disabled:
        items.append({"level": "warn", "msg": f"Bot「{b.bot_name}」已被停用"})
    low_quota = db.query(TgUser).filter(TgUser.remain_quota <= 100).count()
    if low_quota:
        items.append({"level": "info", "msg": f"{low_quota} 个用户剩余额度不足 100"})
    return {"items": items}
