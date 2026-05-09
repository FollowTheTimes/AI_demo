@echo off
chcp 65001 >nul 2>&1
set PYTHON=C:\Users\aa\AppData\Local\Programs\Python\Python312\python.exe

%PYTHON% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python未安装，请安装Python 3.8+后重试
    pause
    exit /b 1
)

echo 正在安装依赖...
%PYTHON% -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 依赖安装失败
    pause
    exit /b 1
)

echo 正在启动AI智能建模引擎...
echo 访问地址: http://localhost:8000/static/index.html
echo API地址: http://localhost:8000/api/health
echo.
%PYTHON% main.py
if %errorlevel% neq 0 (
    echo 启动失败
    pause
    exit /b 1
)
