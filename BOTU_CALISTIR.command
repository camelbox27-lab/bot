#!/bin/bash
# ODDSY FUTBOL BOT - macOS baslatici (Finder'da cift tiklanir)
cd "$(dirname "$0")" || exit 1

# Sessiz mod: alt scriptlerin ciktisi bot_log.txt'ye gider, ekranda
# yalnizca 9 adimin durumu kalir.
export SESSIZ=1

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo
    echo "  HATA: Python bulunamadi."
    echo "  Kurulum: brew install python3"
    echo "  ya da https://www.python.org/downloads/"
    echo
    read -n 1 -s -r -p "  Kapatmak icin bir tusa bas..."
    exit 1
fi

# Paketler kurulu mu? Degilse bir kereye mahsus kur
if ! $PY -c "import pandas, requests, bs4, cloudscraper" >/dev/null 2>&1; then
    echo
    echo "  Eksik paketler kuruluyor (ilk calistirmada bir kez, birkac dakika)..."
    $PY -m pip install --quiet --upgrade pip
    $PY -m pip install --quiet -r requirements.txt
    echo "  Paketler hazir."
fi

# main.py kendi git push'unu yapar, burada tekrar edilmez.
$PY main.py
SONUC=$?

echo
if [ $SONUC -ne 0 ]; then
    echo "  Ayrintili dokum: $(pwd)/bot_log.txt"
    echo
fi
read -n 1 -s -r -p "  Pencereyi kapatmak icin bir tusa bas..."
echo
exit $SONUC
