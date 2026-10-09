from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Admin, TgUser, Bot, ChatHistory
from ..auth import get_current_admin, write_log
from ..schemas import QuotaReq

router = APIRouter(prefix="/api/user", tags=["user"])

@router.get("/list")
def user_list(bot_id: int = 0, keyword: str = "", black: int = -1,
              page: int = 1, size: int = 20,
              db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    q = db.query(TgUser)
    if bot_id:
        q = q.filter(TgUser.bot_id == bot_id)
    if black >= 0:
        q = q.filter(TgUser.is_black == bool(black))
    if keyword:
        q = q.filter((TgUser.username.contains(keyword))
                     | (TgUser.first_name.contains(keyword)))
    total = q.count()
    rows = q.order_by(TgUser.id.desc()).offset((page - 1) * size).limit(size).all()
    bot_names = {b.id: b.bot_name for b in db.query(Bot).all()}
    return {"total": total, "items": [
        {"id": r.id, "bot_id": r.bot_id, "bot_name": bot_names.get(r.bot_id, ""),
         "tg_user_id": r.tg_user_id, "username": r.username or "",
         "first_name": r.first_name or "", "is_black": r.is_black,
         "total_token_used": r.total_token_used, "remain_quota": r.remain_quota,
         "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")}
        for r in rows]}

@router.get("/detail/{uid}")
def user_detail(uid: int, db: Session = Depends(get_db),
                _: Admin = Depends(get_current_admin)):
    u = db.get(TgUser, uid)
    if not u:
        raise HTTPException(404, "用户不存在")
    chats = (db.query(ChatHistory)
             .filter(ChatHistory.bot_id == u.bot_id,
                     ChatHistory.tg_user_id == u.tg_user_id)
             .order_by(ChatHistory.id.desc()).limit(50).all())
    return {"user": {"id": u.id, "bot_id": u.bot_id, "tg_user_id": u.tg_user_id,
                     "username": u.username, "first_name": u.first_name,
                     "is_black": u.is_black, "total_token_used": u.total_token_used,
                     "remain_quota": u.remain_quota},
            "chats": [{"role": c.role, "content": c.content,
                       "created_at": c.created_at.strftime("%Y-%m-%d %H:%M")}
                      for c in chats]}

@router.put("/black/{uid}")
def toggle_black(uid: int, db: Session = Depends(get_db),
                 admin: Admin = Depends(get_current_admin)):
    u = db.get(TgUser, uid)
    if not u:
        raise HTTPException(404, "用户不存在")
    u.is_black = not u.is_black
    db.commit()
    write_log(db, admin, "拉黑/解黑用户",
              f"tg={u.tg_user_id} -> {u.is_black}")
    return {"ok": True, "is_black": u.is_black}

@router.put("/quota/{uid}")
def set_quota(uid: int, body: QuotaReq, db: Session = Depends(get_db),
              admin: Admin = Depends(get_current_admin)):
    u = db.get(TgUser, uid)
    if not u:
        raise HTTPException(404, "用户不存在")
    u.remain_quota = body.remain_quota
    db.commit()
    write_log(db, admin, "调整用户额度",
              f"tg={u.tg_user_id} -> {body.remain_quota}")
    return {"ok": True}
