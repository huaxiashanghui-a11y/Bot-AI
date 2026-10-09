from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Admin, SystemConfig, Keyword
from ..auth import get_current_admin, write_log
from ..schemas import ConfigKV

router = APIRouter(prefix="/api/system", tags=["system"])

DEFAULTS = {
    "alert_balance_threshold": "100000",   # 方舟余额告警（token估算，仅提示用）
    "daily_bot_quota": "1000000",          # 单Bot日消耗上限
    "default_user_quota": "10000",         # 新用户默认额度
}

def _ensure_defaults(db: Session):
    for k, v in DEFAULTS.items():
        if not db.query(SystemConfig).filter(SystemConfig.key == k).first():
            db.add(SystemConfig(key=k, value=v))
    db.commit()

@router.get("/config")
def get_config(db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    _ensure_defaults(db)
    rows = db.query(SystemConfig).all()
    return {"values": {r.key: r.value for r in rows}}

@router.put("/config")
def set_config(body: ConfigKV, db: Session = Depends(get_db),
               admin: Admin = Depends(get_current_admin)):
    for k, v in body.values.items():
        row = db.query(SystemConfig).filter(SystemConfig.key == k).first()
        if row:
            row.value = str(v)
        else:
            db.add(SystemConfig(key=k, value=str(v)))
    db.commit()
    write_log(db, admin, "修改系统设置", str(body.values))
    return {"ok": True}

@router.get("/keywords")
def list_keywords(db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    rows = db.query(Keyword).order_by(Keyword.id.desc()).all()
    return {"items": [{"id": r.id, "word": r.word} for r in rows]}

@router.post("/keywords")
def add_keyword(word: str, db: Session = Depends(get_db),
                admin: Admin = Depends(get_current_admin)):
    if db.query(Keyword).filter(Keyword.word == word).first():
        raise HTTPException(400, "关键词已存在")
    db.add(Keyword(word=word)); db.commit()
    write_log(db, admin, "新增关键词", word)
    return {"ok": True}

@router.delete("/keywords/{kid}")
def del_keyword(kid: int, db: Session = Depends(get_db),
                admin: Admin = Depends(get_current_admin)):
    row = db.get(Keyword, kid)
    if not row:
        raise HTTPException(404, "关键词不存在")
    db.delete(row); db.commit()
    write_log(db, admin, "删除关键词", row.word)
    return {"ok": True}
