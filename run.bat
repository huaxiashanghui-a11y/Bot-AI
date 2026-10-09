@echo off
chcp 65001 >nul
cd /d %~dp0
echo ==========================================
echo   Bot超级管理后台 - 一键启动
echo ==========================================
if not exist venv (
  echo [1/2] 创建虚拟环境...
  python -m venv venv
)
echo [2/2] 安装依赖并启动服务...
call venv\Scripts\activate.bat
pip install -r requirements.txt
echo.
echo 启动成功后访问: http://127.0.0.1:8000
echo 默认账号: admin  密码: admin123
echo.
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
pause
