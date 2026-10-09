# Bot超级管理后台

多 Telegram 机器人统一管理平台，每个 Bot 独立配置，底层调用火山方舟豆包 API。

## 一键启动（Windows）
双击 `run.bat`，首次会自动建虚拟环境、装依赖并启动。
启动后浏览器访问： http://127.0.0.1:8000
默认账号： `admin` / `admin123` （登录后请尽快在「管理员账号」改密）

## 手动启动
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 目录结构
```
├── backend/
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # 全局配置（JWT、方舟端点、默认管理员）
│   ├── database.py       # SQLAlchemy 连接
│   ├── models.py          # 数据模型
│   ├── auth.py            # JWT + bcrypt
│   ├── routers/           # 8 组 API 路由
│   └── bot_runner/        # 多 Bot 进程 + 豆包 API 调用
├── frontend/index.html    # Vue3 + Element Plus 单页后台
└── requirements.txt
```

## 接入一个新 Bot
1. 在 Telegram 找 @BotFather 创建 Bot，拿到 HTTP API Token。
2. 在火山方舟控制台创建 API Key（`sk-...`）并选择模型 ID（如 `doubao-pro-4k`）。
3. 后台「机器人管理 → 新增Bot」填入 Token、Key、模型 ID，保存即自动启动 polling。

## 切换到 MySQL
设置环境变量 `DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname` 后重启即可，模型无需改动。

## 部署注意
- 生产环境务必修改 `JWT_SECRET` 环境变量。
- TG Bot 需要能访问 `api.telegram.org`，国内服务器需部署在海外/香港节点。
- 方舟 API 按 token 计费，请在后台关注 Token 报表并为用户设置额度。
