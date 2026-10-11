@echo off
chcp 65001 >nul
title FUTBOL BOT PIPELINE
color 07

cls
echo.
echo  ========================================================
echo       🚀 ODDSY FUTBOL BOT BASLATILIYOR...
echo  ========================================================
echo.
echo  Baslangic: %date% %time%
echo  --------------------------------------------------------
echo.

:: -------------------------------------------------------------
:: ADIM 1: Ana Pipeline (SofaScore + Mackolik + Filtre)
:: -------------------------------------------------------------
echo  [1/2] Ana Pipeline Calisiyor (Veri Cekimi)...
echo  --------------------------------------------------------
echo.

python "%~dp0main.py" 2>nul

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  !! ANA PIPELINE HATA VERDI !!
    echo.
) else (
    echo.
    echo  [OK] Ana Pipeline Tamamlandi.
    echo.
)

echo  --------------------------------------------------------
echo.

:: -------------------------------------------------------------
:: ADIM 2: GitHub Push (oddsy-data klasöründeki güncel jsonları)
::
:: NOT: Kart & Korner istatistikleri bu pipeline'dan CIKARILDI.
::      Gerektiginde elle calistir: cd istatistik ^&^& python main.py
:: -------------------------------------------------------------
echo  [2/2] Guncel JSON'lar GitHub "oddsy-data" reposuna yukleniyor...
echo  --------------------------------------------------------
echo.

:: Oddsy-data reposunun bulunduğu klasöre gidiyoruz
cd /d "%~dp0..\oddsy-data"

echo  ☁️  Sira GitHub'da (Pull/Add/Commit/Push)...
git pull origin main --rebase
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [UYARI] Git Pull sirasinda hata olustu.
    echo.
)

:: Tüm 'data' içindeki dosyaları beklede olanlara ekle
git add data/
git commit -m "chore: guncel tahmin ve analiz json'lari yüklendi"

:: Git commit bazen değişiklik olmadığında hata kodu çevirir, o yüzden push ile devam ediyoruz
git push origin main
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  !! GIT PUSH HATA VERDI veya YUKLENECEK YENI VERI YOK !!
    echo.
) else (
    echo.
    echo  [🎉 BASARILI] Tum JSON'lar GitHub'a basariyla iletildi!
    echo  Websitesi (Frontend) verileri GitHub uzerinden otomatik guncelleyecek.
    echo.
)

:: İşlemin bittiği yer klasörünü eski haline döndür
cd /d "%~dp0"

echo  ========================================================
echo  Bitis: %date% %time%
echo  ========================================================
echo.
pause
