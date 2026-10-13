@echo off
chcp 65001 >nul
title Masaustu Kisayolu Olustur
cd /d "%~dp0"

echo.
echo   Masaustune "Oddsy Bot" kisayolu olusturuluyor...
echo.

:: Kisayol PowerShell ile olusturulur; WorkingDirectory bot klasorune
:: sabitlenir, boylece kisayol nereden calisirsa calissin main.py kendi
:: klasorunu ve ../oddsy-data yolunu dogru bulur.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$masaustu = [Environment]::GetFolderPath('Desktop');" ^
  "$k = $ws.CreateShortcut((Join-Path $masaustu 'Oddsy Bot.lnk'));" ^
  "$k.TargetPath = '%~dp0BOTU_CALISTIR.bat';" ^
  "$k.WorkingDirectory = '%~dp0';" ^
  "$k.Description = 'Oddsy futbol bot pipeline - gunun verisini ceker ve siteye yukler';" ^
  "$k.IconLocation = 'shell32.dll,137';" ^
  "$k.Save();"

if errorlevel 1 (
    echo   HATA: Kisayol olusturulamadi.
    echo.
    echo   Elle yapmak icin: BOTU_CALISTIR.bat dosyasina sag tikla,
    echo   "Gonder" ^> "Masaustu ^(kisayol olustur^)" sec.
) else (
    echo   Tamam. Masaustunde "Oddsy Bot" ikonu olustu.
    echo   Cift tiklayinca bot calisir.
)
echo.
pause
