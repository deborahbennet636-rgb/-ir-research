@echo off
chcp 65001 > nul
echo ========================================
echo   国际关系研判系统 - 启动中...
echo ========================================
echo.

:: 检查Python是否安装
python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查依赖
echo [1/3] 检查依赖包...
pip show flask > nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖包...
    pip install -r requirements.txt
)

:: 检查配置文件
if not exist "config.py" (
    echo [警告] 未找到 config.py，正在创建模板...
    echo 请编辑 config.py 填入你的API密钥！
    pause
    exit /b 1
)

:: 检查API配置
findstr /C:"YOUR_API_KEY_HERE" config.py > nul
if not errorlevel 1 (
    echo [错误] 请先编辑 config.py，填入你的AI API密钥！
    echo 按任意键打开配置文件...
    pause
    start notepad config.py
    exit /b 1
)

echo [2/3] 启动服务...
echo [3/3] 打开浏览器访问: http://127.0.0.1:5000
echo.
echo ========================================
echo   按 Ctrl+C 停止服务
echo ========================================

python local_app.py
