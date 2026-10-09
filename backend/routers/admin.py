from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Admin
from ..auth import (verify_password, create_access_token, hash_password,
                    get_current_admin, write_log)
from ..schemas import LoginReq, AdminUpsert

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/login")
def login(body: LoginReq, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == body.username).first()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(400, "用户名或密码错误")
    if not admin.is_enable:
        raise HTTPException(403, "账号已被禁用")
    token = create_access_token(admin)
    return {"access_token": token, "token_type": "bearer",
            "admin": {"id": admin.id, "username": admin.username, "name": admin.name}}

@router.get("/info")
def info(admin: Admin = Depends(get_current_admin)):
    return {"id": admin.id, "username": admin.username, "name": admin.name}

@router.get("/list")
def list_admins(db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    rows = db.query(Admin).order_by(Admin.id.desc()).all()
    return {"total": len(rows), "items": [
        {"id": r.id, "username": r.username, "name": r.name,
         "is_enable": r.is_enable, "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")}
        for r in rows]}

@router.post("/add")
def add(body: AdminUpsert, db: Session = Depends(get_db),
        admin: Admin = Depends(get_current_admin)):
    if db.query(Admin).filter(Admin.username == body.username).first():
        raise HTTPException(400, "用户名已存在")
    if not body.password:
        raise HTTPException(400, "初始密码不能为空")
    row = Admin(username=body.username, password_hash=hash_password(body.password),
                name=body.name)
    db.add(row); db.commit(); db.refresh(row)
    write_log(db, admin, "新增管理员", body.username)
    return {"ok": True, "id": row.id}

@router.put("/update/{aid}")
def update(aid: int, body: AdminUpsert, db: Session = Depends(get_db),
           admin: Admin = Depends(get_current_admin)):
    row = db.get(Admin, aid)
    if not row:
        raise HTTPException(404, "管理员不存在")
    row.name = body.name or row.name
    if body.password:
        row.password_hash = hash_password(body.password)
    db.commit()
    write_log(db, admin, "修改管理员", body.username)
    return {"ok": True}

@router.put("/status/{aid}")
def set_status(aid: int, is_enable: bool, db: Session = Depends(get_db),
               admin: Admin = Depends(get_current_admin)):
    row = db.get(Admin, aid)
    if not row:
        raise HTTPException(404, "管理员不存在")
    if row.id == admin.id and not is_enable:
        raise HTTPException(400, "不能禁用当前登录账号")
    row.is_enable = is_enable
    db.commit()
    write_log(db, admin, "启停管理员", f"{row.username} -> {is_enable}")
    return {"ok": True}

@router.delete("/delete/{aid}")
def delete(aid: int, db: Session = Depends(get_db),
           admin: Admin = Depends(get_current_admin)):
    if aid == admin.id:
        raise HTTPException(400, "不能删除当前登录账号")
    row = db.get(Admin, aid)
    if not row:
        raise HTTPException(404, "管理员不存在")
    db.delete(row); db.commit()
    write_log(db, admin, "删除管理员", row.username)
    return {"ok": True}
