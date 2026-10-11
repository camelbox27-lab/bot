#!/bin/bash
# ============================================================
#  ODDSY FUTBOL BOT - macOS BASLATICI
#  Finder'da CIFT TIKLAYARAK calistirilir.
#  (Windows'taki BOTU_CALISTIR.bat dosyasinin Mac karsiligi)
# ============================================================

# Script nerede durursa dursun, kendi klasorunde calissin
cd "$(dirname "$0")" || exit 1
BOT_DIR="$(pwd)"

clear
echo
echo " ========================================================"
echo "      ODDSY FUTBOL BOT BASLATILIYOR..."
echo " ========================================================"
echo
echo " Baslangic: $(date '+%d.%m.%Y %H:%M:%S')"
echo " Klasor   : $BOT_DIR"
echo " --------------------------------------------------------"
echo

# --- Python bulunuyor mu? (Mac'te 'python' degil 'python3' olur) ---
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo " !! HATA: Python bulunamadi."
    echo
    echo " Kurulum icin Terminal'e sunu yaz:"
    echo "     brew install python3"
    echo " ya da https://www.python.org/downloads/ adresinden indir."
    echo
    read -n 1 -s -r -p " Kapatmak icin bir tusa bas..."
    exit 1
fi
echo " Python   : $($PY --version 2>&1)"
echo

# --- Bagimliliklar kurulu mu? Degilse bir kereye mahsus kur ---
if ! $PY -c "import pandas, requests" >/dev/null 2>&1; then
    echo " [KURULUM] Eksik Python paketleri kuruluyor (ilk calistirmada bir kez)..."
    echo " --------------------------------------------------------"
    $PY -m pip install --quiet --upgrade pip
    $PY -m pip install --quiet -r requirements.txt
    echo " [OK] Paketler hazir."
    echo
fi

# ------------------------------------------------------------
# ADIM 1: Ana Pipeline (SofaScore + Mackolik + Filtre)
# ------------------------------------------------------------
echo " [1/2] Ana Pipeline Calisiyor (Veri Cekimi)..."
echo " --------------------------------------------------------"
echo

$PY "$BOT_DIR/main.py"
PIPELINE_SONUC=$?

if [ $PIPELINE_SONUC -ne 0 ]; then
    echo
    echo " !! ANA PIPELINE HATA VERDI !!"
    echo
else
    echo
    echo " [OK] Ana Pipeline Tamamlandi."
    echo
fi

echo " --------------------------------------------------------"
echo

# ------------------------------------------------------------
# ADIM 2: GitHub Push (oddsy-data klasorundeki guncel json'lar)
#
# NOT: Kart & Korner istatistikleri bu pipeline'a DAHIL DEGIL.
#      Gerektiginde elle calistir: cd istatistik && python3 main.py
# ------------------------------------------------------------
ODDSY_DATA="$BOT_DIR/../oddsy-data"

if [ ! -d "$ODDSY_DATA" ]; then
    echo " [ATLANDI] oddsy-data klasoru bulunamadi:"
    echo "           $ODDSY_DATA"
    echo "           Veri push'u yapilmadi (pipeline ciktilari yerelde duruyor)."
    echo
else
    echo " [2/2] Guncel JSON'lar GitHub 'oddsy-data' reposuna yukleniyor..."
    echo " --------------------------------------------------------"
    echo

    cd "$ODDSY_DATA" || exit 1

    # Bot ciktilari calisma agacini kirli birakir ve 'pull --rebase' bunu
    # reddeder. Bu dosyalar zaten commitlenmiyor (sadece data/ stage'leniyor),
    # bu yuzden pull oncesi gecici saklanip sonrasinda geri aliniyor.
    STASHLENDI=0
    if [ -n "$(git status --porcelain)" ]; then
        if git stash push -u -m "launcher-autostash" >/dev/null 2>&1; then
            STASHLENDI=1
            echo " [INFO] Yerel degisiklikler gecici saklandi (stash)."
        fi
    fi

    echo " Sira GitHub'da (Pull/Add/Commit/Push)..."
    git pull origin main --rebase

    if [ $STASHLENDI -eq 1 ]; then
        if ! git stash pop >/dev/null 2>&1; then
            git checkout --theirs . >/dev/null 2>&1
            git stash drop >/dev/null 2>&1
            echo " [UYARI] Stash geri alinamadi (cakisma), remote surum korundu."
        fi
    fi

    git add data/
    git commit -m "chore: guncel tahmin ve analiz json'lari yuklendi" >/dev/null 2>&1

    if git push origin main; then
        echo
        echo " [BASARILI] Tum JSON'lar GitHub'a iletildi!"
        echo " Websitesi verileri GitHub uzerinden otomatik guncelleyecek."
        echo
    else
        echo
        echo " !! GIT PUSH HATA VERDI veya YUKLENECEK YENI VERI YOK !!"
        echo
    fi

    cd "$BOT_DIR" || exit 1
fi

echo " ========================================================"
echo " Bitis: $(date '+%d.%m.%Y %H:%M:%S')"
echo " ========================================================"
echo
read -n 1 -s -r -p " Pencereyi kapatmak icin bir tusa bas..."
echo
