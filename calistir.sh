#!/bin/bash
# Wondiyo bot baslatici - Mac/Linux
# Kullanim: ./calistir.sh   veya   bot  (kisayol kuruluysa)

cd "$(dirname "$0")" || exit 1

if [ ! -d "venv" ]; then
    echo "[HATA] venv klasoru yok. Once kurulum yapin:"
    echo "  python3.11 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

source venv/bin/activate
python main.py
