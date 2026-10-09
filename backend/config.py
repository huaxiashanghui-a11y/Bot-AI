"""全局配置。开发期默认使用 SQLite，生产切换为 MySQL 只需改 DATABASE_URL。"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 默认开发库 SQLite；生产改为 mysql+pymysql://user:pass@host:3306/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "dev.db"))

# JWT 密钥（生产环境务必通过环境变量覆盖）
JWT_SECRET = os.getenv("JWT_SECRET", "bot-admin-super-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 12  # 12 小时

# 火山方舟豆包 API 端点（多 Bot 时每个 Bot 可在后台覆盖自己的 key / model）
ARK_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

# 默认管理员（首次启动自动创建）
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
