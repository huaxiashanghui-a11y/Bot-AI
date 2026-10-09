from pydantic import BaseModel
from typing import Optional

class LoginReq(BaseModel):
    username: str
    password: str

class AdminUpsert(BaseModel):
    username: str
    password: Optional[str] = None
    name: Optional[str] = None

class BotUpsert(BaseModel):
    bot_name: str
    tg_bot_token: str
    ark_api_key: str
    ark_model_id: str = "doubao-pro-4k"
    vision_model_id: Optional[str] = ""
    base_url: Optional[str] = "https://ark.cn-beijing.volces.com/api/v3"
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    stream_enable: bool = False
    bot_switch: bool = True
    user_max_context_len: int = 10
    description: str = ""

class QuotaReq(BaseModel):
    remain_quota: int

class ConfigKV(BaseModel):
    values: dict
