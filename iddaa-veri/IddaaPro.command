#!/bin/bash
# IddaaPro - Mac baslatici (cift tiklayarak acilir)
cd "$(dirname "$0")" || exit 1

VENV="../venv/bin/activate"
if [ ! -f "$VENV" ]; then
    echo "[HATA] venv bulunamadi: $VENV"
    read -p "Kapatmak icin Enter..."
    exit 1
fi

source "$VENV"
python iddaapro.py

# Hata olursa pencere kapanmasin, mesaji gorelim
echo ""
echo "--- Uygulama kapandi ---"
read -p "Kapatmak icin Enter..."
