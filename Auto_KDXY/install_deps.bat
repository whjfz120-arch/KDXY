@echo off
chcp 65001 >nul
echo ========================================================
echo   【游戏自动化总控台】环境配置与依赖安装脚本
echo ========================================================
echo.

:: 1. 检查电脑是否已安装 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 检测到您的电脑未安装 Python，或者未将 Python 添加到环境变量！
    echo 正在尝试通过系统 winget 工具为您自动安装 Python...
    
    :: 尝试使用 Windows 自带的 winget 安装 Python 3.10
    winget install Python.Python.3.10
    
    echo.
    echo ⚠️ 如果刚才自动安装失败，请手动前往 Python 官网下载安装：
    echo 🔗 https://www.python.org/downloads/
    echo 📌 【非常重要】安装时请务必勾选底部的 "Add Python to PATH"（添加到环境变量）！
    echo.
    echo 安装完成后，请重新关闭并双击运行本脚本。
    pause
    exit
) else (
    echo ✅ 检测到已安装的 Python 环境：
    python --version
)

echo.
echo ========================================================
echo [步骤 1/2] 正在升级 pip 到最新版本...
echo ========================================================
python -m pip install --upgrade pip

echo.
echo ========================================================
echo [步骤 2/2] 正在安装项目所需的第三方依赖库...
echo (包含: PySide6, opencv-python, numpy, pywin32, Pillow, easyocr)
echo ========================================================
pip install PySide6 opencv-python numpy pywin32 Pillow easyocr -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ========================================================
echo   🎉 所有环境与依赖库安装流程已执行完毕！
echo   如果上方没有红色的报错提示，您可以直接运行总控台了。
echo ========================================================
pause