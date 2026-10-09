from datetime import datetime, date

from sqlalchemy import (Column, Integer, BigInteger, String, Text, Float,
                        Boolean, DateTime, Date, UniqueConstraint)

from .database import Base

class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    name = Column(String(50))
    is_enable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

class Bot(Base):
    __tablename__ = "bot"
    id = Column(Integer, primary_key=True, index=True)
    bot_name = Column(String(100), nullable=False)
    tg_bot_token = Column(String(100), nullable=False, unique=True)
    ark_api_key = Column(String(200), nullable=False)
    ark_model_id = Column(String(100), nullable=False, default="doubao-pro-4k")
    vision_model_id = Column(String(100), nullable=True, default="")
    base_url = Column(String(200), nullable=False,
                      default="https://ark.cn-beijing.volces.com/api/v3")
    system_prompt = Column(Text, default="")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2048)
    stream_enable = Column(Boolean, default=False)
    bot_switch = Column(Boolean, default=True)
    user_max_context_len = Column(Integer, default=10)
    description = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class TgUser(Base):
    __tablename__ = "tg_user"
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, nullable=False, index=True)
    tg_user_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_black = Column(Boolean, default=False)
    total_token_used = Column(BigInteger, default=0)
    remain_quota = Column(BigInteger, default=10000)
    created_at = Column(DateTime, default=datetime.now)
    __table_args__ = (UniqueConstraint("bot_id", "tg_user_id", name="uq_bot_user"),)

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, nullable=False, index=True)
    tg_user_id = Column(BigInteger, nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user / assistant / system
    content = Column(Text)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now, index=True)

class TokenStat(Base):
    __tablename__ = "token_stat"
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, nullable=False, index=True)
    stat_date = Column(Date, nullable=False, index=True)
    total_input_tokens = Column(BigInteger, default=0)
    total_output_tokens = Column(BigInteger, default=0)
    total_request = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("bot_id", "stat_date", name="uq_bot_date"),)

class OperLog(Base):
    __tablename__ = "oper_log"
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer)
    admin_name = Column(String(50))
    action = Column(String(100))
    detail = Column(Text)
    created_at = Column(DateTime, default=datetime.now, index=True)

class Keyword(Base):
    __tablename__ = "keyword"
    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class SystemConfig(Base):
    """全局 KV 设置：alert_balance_threshold / daily_bot_quota / default_user_quota 等"""
    __tablename__ = "system_config"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(String(500))
