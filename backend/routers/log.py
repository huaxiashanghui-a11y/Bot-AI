from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Admin, OperLog
from ..auth import get_current_admin

router = APIRouter(prefix="/api/log", tags=["log"])

@router.get("/list")
def log_list(page: int = 1, size: int = 20,
             db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    q = db.query(OperLog)
    total = q.count()
    rows = q.order_by(OperLog.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "items": [
        {"id": r.id, "admin_name": r.admin_name, "action": r.action,
         "detail": r.detail, "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")}
        for r in rows]}
