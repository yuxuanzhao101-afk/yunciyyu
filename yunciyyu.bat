@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ====================================================
echo           yunicyyu 个人网站启动器
echo ====================================================
echo.

start "" python app.py

timeout /t 2 /nobreak >nul

start "" http://127.0.0.1:212

echo [信息] 网站已启动，浏览器即将打开...
echo [信息] 关闭此窗口不会停止网站
echo.
