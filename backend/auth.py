from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .models import Admin

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False

def create_access_token(admin: Admin) -> str:
    expire = datetime.utcnow() + timedelta(minutes=config.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(admin.id), "username": admin.username, "exp": expire}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

def get_current_admin(token: str = Depends(oauth2_scheme),
                      db: Session = Depends(get_db)) -> Admin:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录已失效，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        admin_id = int(payload.get("sub"))
    except Exception:
        raise cred_exc
    admin = db.get(Admin, admin_id)
    if not admin or not admin.is_enable:
        raise cred_exc
    return admin

def write_log(db: Session, admin: Admin, action: str, detail: str = ""):
    from .models import OperLog
    db.add(OperLog(admin_id=admin.id, admin_name=admin.username,
                   action=action, detail=detail[:500]))
    db.commit()
