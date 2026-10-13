@echo off
chcp 65001 >nul
setlocal
title ODDSY FUTBOL BOT
cd /d "%~dp0"

:: Sessiz mod: alt scriptlerin ciktisi ekrana dokulmez, bot_log.txt'ye yazilir.
:: Ekranda yalnizca 9 adimin durumu gorunur.
set SESSIZ=1

:: --- Python bul (PATH'te "python" olmayabilir, Windows'ta "py" yaygin) ---
set PY=
where python >nul 2>&1 && set PY=python
if not defined PY where py >nul 2>&1 && set PY=py
if not defined PY (
    echo.
    echo   HATA: Python bulunamadi.
    echo.
    echo   Kurulum: https://www.python.org/downloads/
    echo   Kurarken "Add Python to PATH" kutusunu isaretle.
    echo.
    pause
    exit /b 1
)

:: --- Paketler kurulu mu? Degilse bir kereye mahsus kur ---
%PY% -c "import pandas, requests, bs4, cloudscraper" >nul 2>&1
if errorlevel 1 (
    echo.
    echo   Eksik paketler kuruluyor ^(ilk calistirmada bir kez, birkac dakika^)...
    %PY% -m pip install --quiet --upgrade pip
    %PY% -m pip install --quiet -r requirements.txt
    echo   Paketler hazir.
)

:: --- Pipeline. main.py kendi git push'unu yapar, burada tekrar edilmez. ---
%PY% "%~dp0main.py"
set SONUC=%ERRORLEVEL%

echo.
if %SONUC% NEQ 0 (
    echo   Ayrintili dokum: "%~dp0bot_log.txt"
    echo.
)
pause
exit /b %SONUC%
