from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Admin, Bot, TokenStat
from ..auth import get_current_admin, write_log
from ..schemas import BotUpsert

router = APIRouter(prefix="/api/bot", tags=["bot"])

def _mask_token(t: str) -> str:
    return (t[:6] + "****" + t[-4:]) if t and len(t) > 12 else "****"

@router.get("/list")
def bot_list(keyword: str = "", db: Session = Depends(get_db),
             _: Admin = Depends(get_current_admin)):
    q = db.query(Bot)
    if keyword:
        q = q.filter(Bot.bot_name.contains(keyword))
    rows = q.order_by(Bot.id.desc()).all()
    today = date.today()
    items = []
    for b in rows:
        s = db.query(func.coalesce(func.sum(TokenStat.total_request), 0),
                     func.coalesce(func.sum(TokenStat.total_input_tokens)
                                   + func.sum(TokenStat.total_output_tokens), 0)
                     ).filter(TokenStat.bot_id == b.id,
                              TokenStat.stat_date == today).one()
        items.append({
            "id": b.id, "bot_name": b.bot_name,
            "tg_bot_token": _mask_token(b.tg_bot_token),
            "ark_model_id": b.ark_model_id, "vision_model_id": b.vision_model_id or "",
            "bot_switch": b.bot_switch, "stream_enable": b.stream_enable,
            "today_requests": s[0], "today_tokens": s[1],
            "description": b.description,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M"),
        })
    return {"total": len(items), "items": items}

@router.post("/add")
def add_bot(body: BotUpsert, db: Session = Depends(get_db),
            admin: Admin = Depends(get_current_admin)):
    if db.query(Bot).filter(Bot.tg_bot_token == body.tg_bot_token).first():
        raise HTTPException(400, "该 Telegram Token 已存在")
    row = Bot(**body.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    write_log(db, admin, "新增Bot", body.bot_name)
    # 若开关打开，立即拉起进程
    if row.bot_switch:
        try:
            from ..bot_runner import runner
            runner.start_bot(row)
        except Exception as e:
            return {"ok": True, "id": row.id, "warn": f"已保存但启动失败: {e}"}
    return {"ok": True, "id": row.id}

@router.put("/update/{bid}")
def update_bot(bid: int, body: BotUpsert, db: Session = Depends(get_db),
               admin: Admin = Depends(get_current_admin)):
    row = db.get(Bot, bid)
    if not row:
        raise HTTPException(404, "Bot 不存在")
    # token/key 留空表示不修改（出于安全不回显）
    row.bot_name = body.bot_name
    row.ark_model_id = body.ark_model_id
    row.vision_model_id = body.vision_model_id or ""
    row.system_prompt = body.system_prompt
    row.temperature = body.temperature
    row.max_tokens = body.max_tokens
    row.stream_enable = body.stream_enable
    row.user_max_context_len = body.user_max_context_len
    row.description = body.description
    row.bot_switch = body.bot_switch
    if body.tg_bot_token:
        row.tg_bot_token = body.tg_bot_token
    if body.ark_api_key:
        row.ark_api_key = body.ark_api_key
    db.commit()
    db.refresh(row)
    write_log(db, admin, "编辑Bot", body.bot_name)
    # 配置变更后重启进程以生效
    try:
        from ..bot_runner import runner
        runner.restart_bot(row)
    except Exception as e:
        return {"ok": True, "warn": f"已保存但重启失败: {e}"}
    return {"ok": True}

@router.put("/switch/{bid}")
def switch_bot(bid: int, db: Session = Depends(get_db),
               admin: Admin = Depends(get_current_admin)):
    row = db.get(Bot, bid)
    if not row:
        raise HTTPException(404, "Bot 不存在")
    row.bot_switch = not row.bot_switch
    db.commit()
    write_log(db, admin, "启停Bot", f"{row.bot_name} -> {row.bot_switch}")
    try:
        from ..bot_runner import runner
        if row.bot_switch:
            runner.start_bot(row)
        else:
            runner.stop_bot(bid)
    except Exception as e:
        return {"ok": True, "warn": f"状态已保存但进程操作失败: {e}"}
    return {"ok": True, "bot_switch": row.bot_switch}

@router.post("/restart/{bid}")
def restart(bid: int, db: Session = Depends(get_db),
            admin: Admin = Depends(get_current_admin)):
    row = db.get(Bot, bid)
    if not row:
        raise HTTPException(404, "Bot 不存在")
    write_log(db, admin, "重启Bot", row.bot_name)
    try:
        from ..bot_runner import runner
        runner.restart_bot(row)
    except Exception as e:
        raise HTTPException(500, f"重启失败: {e}")
    return {"ok": True}

@router.delete("/delete/{bid}")
def delete_bot(bid: int, db: Session = Depends(get_db),
               admin: Admin = Depends(get_current_admin)):
    row = db.get(Bot, bid)
    if not row:
        raise HTTPException(404, "Bot 不存在")
    try:
        from ..bot_runner import runner
        runner.stop_bot(bid)
    except Exception:
        pass
    db.delete(row); db.commit()
    write_log(db, admin, "删除Bot", row.bot_name)
    return {"ok": True}

@router.get("/stats/{bid}")
def bot_stats(bid: int, db: Session = Depends(get_db),
              _: Admin = Depends(get_current_admin)):
    row = db.get(Bot, bid)
    if not row:
        raise HTTPException(404, "Bot 不存在")
    total = db.query(func.coalesce(func.sum(TokenStat.total_request), 0),
                     func.coalesce(func.sum(TokenStat.total_input_tokens)
                                   + func.sum(TokenStat.total_output_tokens), 0)
                     ).filter(TokenStat.bot_id == bid).one()
    users = db.query(func.count(TgUser.id)).filter(TgUser.bot_id == bid).scalar()
    return {"bot_name": row.bot_name, "model": row.ark_model_id,
            "total_requests": total[0], "total_tokens": total[1],
            "users": users}

@router.get("/process/status")
def process_status(_: Admin = Depends(get_current_admin)):
    try:
        from ..bot_runner import runner
        return {"running": runner.running_ids()}
    except Exception:
        return {"running": []}
