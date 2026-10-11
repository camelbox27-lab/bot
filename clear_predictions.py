#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eski JSON tahminlerini temizler.
Firebase artik kullanilmiyor - tahminler oddsy-data JSON dosyalarinda tutulur.
clean.py zaten halfTimeGoals/dailyChoices/dailySurprises dosyalarini siler,
bu script droppingOdds.json'u sifirlar ve eski merged/filtered dosyalari temizler.
"""
import os
import json
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ci_path = os.path.join(BASE_DIR, 'oddsy-data')
_local_path = os.path.abspath(os.path.join(BASE_DIR, '..', 'oddsy-data'))
ODDSY_DATA_DIR = _ci_path if os.path.exists(_ci_path) else _local_path
DATA_DIR = os.path.join(ODDSY_DATA_DIR, 'data')


def clear_predictions():
    print("=" * 70)
    print("PENDING TAHMINLERI TEMIZLE")
    print("(Firebase kullanilmiyor - JSON bazli sistem)")
    print("=" * 70)

    deleted = 0

    # 1. droppingOdds.json'u bos liste ile sifirla
    dropping_path = os.path.join(DATA_DIR, 'droppingOdds.json')
    if os.path.exists(dropping_path):
        with open(dropping_path, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print(f"[TEMIZLENDI] droppingOdds.json sifirlandi")
        deleted += 1

    # 2. filtered/ klasoründeki eski Excel ve JSON dosyalari sil (3 gundan eski)
    filtered_dir = os.path.join(BASE_DIR, 'filtered')
    if os.path.exists(filtered_dir):
        import time
        now = time.time()
        for pattern in ['*.xlsx', '*.json']:
            for filepath in glob.glob(os.path.join(filtered_dir, pattern)):
                try:
                    age_days = (now - os.path.getmtime(filepath)) / 86400
                    if age_days > 3:
                        os.remove(filepath)
                        print(f"[SILINDI] {os.path.basename(filepath)} ({age_days:.0f} gun eski)")
                        deleted += 1
                except Exception as e:
                    print(f"[HATA] {os.path.basename(filepath)}: {e}")

    # 3. merged/merged_json/ klasoründeki eski merged dosyalari sil (3 gundan eski)
    merged_dir = os.path.join(BASE_DIR, 'merged', 'merged_json')
    if os.path.exists(merged_dir):
        import time
        now = time.time()
        for filepath in glob.glob(os.path.join(merged_dir, 'merged_*.json')):
            try:
                age_days = (now - os.path.getmtime(filepath)) / 86400
                if age_days > 3:
                    os.remove(filepath)
                    print(f"[SILINDI] {os.path.basename(filepath)} ({age_days:.0f} gun eski)")
                    deleted += 1
            except Exception as e:
                print(f"[HATA] {os.path.basename(filepath)}: {e}")

    print(f"\n[OK] Toplam {deleted} islem tamamlandi.")
    print("=" * 70 + "\n")
    return True


if __name__ == "__main__":
    clear_predictions()
