#!/bin/bash
# IddaaPro - Mac baslatici (cift tiklayarak acilir)
cd "$(dirname "$0")" || exit 1

VENV="../venv/bin/activate"
if [ ! -f "$VENV" ]; then
    echo "[HATA] venv bulunamadi: $VENV"
    echo "Once bot klasorunde kurulum yapin."
    read -p "Kapatmak icin Enter..."
    exit 1
fi

source "$VENV"
python iddaapro.py
