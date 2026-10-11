#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean JSON verilerini siler - filter_bot.py öncesinde çalışır
"""
import os
import json

def clean_old_data():
    """Eski JSON dosyalarını siler.

    GUVENLIK: Silme islemi ancak bugunun merged verisi hazirsa yapilir.
    Aksi halde filter_bot.py yerine yenisini yazamaz ve site bos kalirdi.
    """
    from datetime import datetime

    repo_root = os.path.abspath(os.path.dirname(__file__))
    ci_path = os.path.join(repo_root, 'oddsy-data')
    local_path = os.path.abspath(os.path.join(repo_root, '..', 'oddsy-data'))
    oddsy_data_dir = ci_path if os.path.exists(ci_path) else local_path
    data_dir = os.path.join(oddsy_data_dir, 'data')

    print("="*70)
    print("ESKI VERILERI TEMİZLEME")
    print("="*70)

    # Bugunun merged dosyasi yoksa silme yapma (site verisini koru)
    today = datetime.now().strftime("%d.%m.%Y")
    merged_file = os.path.join(repo_root, "merged", "merged_json", f"merged_{today}.json")
    if not os.path.exists(merged_file):
        print(f"[ABORT] Bugunun merged verisi yok: {os.path.basename(merged_file)}")
        print("[ABORT] Silme iptal edildi, mevcut site verisi korunuyor.")
        print("="*70 + "\n")
        return False

    files_to_delete = [
        'halfTimeGoals.json',
        'dailyChoices.json',
        'dailySurprises.json'
    ]
    
    deleted_count = 0
    for filename in files_to_delete:
        filepath = os.path.join(data_dir, filename)
        
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"[DELETE] {filename} silindi")
                deleted_count += 1
            except Exception as e:
                print(f"[ERROR] {filename} silinirken hata: {e}")
        else:
            print(f"[SKIP] {filename} bulunamadı")
    
    print(f"\n[OK] {deleted_count}/{len(files_to_delete)} dosya silindi")
    print("="*70 + "\n")
    return True

if __name__ == "__main__":
    import sys
    sys.exit(0 if clean_old_data() else 1)
