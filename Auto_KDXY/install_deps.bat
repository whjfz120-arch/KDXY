@echo off
chcp 65001 >nul
echo ========================================================
echo   正在为【游戏自动化多功能总控台】安装所需的 Python 依赖库...
echo ========================================================

echo [1/2] 正在升级 pip 到最新版本...
python -m pip install --upgrade pip

echo.
echo [2/2] 正在安装项目依赖库 (PySide6, opencv-python, numpy, pywin32, Pillow, easyocr)...
pip install PySide6 opencv-python numpy pywin32 Pillow easyocr

echo.
echo ========================================================
echo   安装流程执行完毕！
echo   如果上方没有红色的报错提示，说明所有库已成功安装。
echo ========================================================
pause