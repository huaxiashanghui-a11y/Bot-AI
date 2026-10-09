import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config
from .database import Base, engine, SessionLocal
from .models import Admin
from .auth import hash_password
from .routers import admin, dashboard, bot, user, chat, stat, system, log

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "frontend")

def run_migrations():
    """轻量列迁移：给旧库 bot 表补新增列（幂等）。"""
    from sqlalchemy import text, inspect
    insp = inspect(engine)
    if "bot" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("bot")]
    with engine.begin() as conn:
        if "vision_model_id" not in cols:
            conn.execute(text("ALTER TABLE bot ADD COLUMN vision_model_id VARCHAR(100) DEFAULT ''"))
        if "base_url" not in cols:
            conn.execute(text("ALTER TABLE bot ADD COLUMN base_url VARCHAR(200) "
                              "DEFAULT 'https://ark.cn-beijing.volces.com/api/v3'"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 建表 + 迁移
    Base.metadata.create_all(bind=engine)
    run_migrations()
    # 2. 初始化默认管理员
    db = SessionLocal()
    try:
        if not db.query(Admin).filter(Admin.username == config.DEFAULT_ADMIN_USERNAME).first():
            db.add(Admin(username=config.DEFAULT_ADMIN_USERNAME,
                         password_hash=hash_password(config.DEFAULT_ADMIN_PASSWORD),
                         name="超级管理员"))
            db.commit()
    finally:
        db.close()
    # 3. 启动所有已启用的 Bot
    from .bot_runner import runner
    runner.set_loop(asyncio.get_running_loop())
    await runner.startup_all()
    yield
    await runner.shutdown_all()

app = FastAPI(title="Bot超级管理后台", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(bot.router)
app.include_router(user.router)
app.include_router(chat.router)
app.include_router(stat.router)
app.include_router(system.router)
app.include_router(log.router)

@app.get("/api/health")
def health():
    return {"status": "ok"}

# 前端静态页面（单文件 SPA）
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
