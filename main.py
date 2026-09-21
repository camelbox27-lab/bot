#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FUTBOL BOT PIPELINE - TUM ADIMLAR SIRASIYLA CALISIR

Adimlar:
  0. Git Pull (oddsy-data'yi ONCE guncelle)
  1. Oran Dusen Maclar    (dropping_odds_bot.py)
  2. SofaScore Verileri   (sofa/bet365data.py)
  3. Mackolik Verileri    (guncel_bulten.py -> JSON)
  4. Verileri Birlestir   (merged/match_merger_bot.py)
  5. Eski Verileri Temizle (clean.py)
  6. Filtrele + JSON Kaydet (filter_bot.py)
  7. Mac Sonuclari Guncelle (update_results.py)
  8. Git Push (oddsy-data reposuna)

NOT: Firebase KULLANILMAZ. Veriler JSON olarak oddsy-data reposuna push edilir.
     Frontend bu JSON'lari GitHub raw URL'lerinden ceker.
NOT: Kart & Korner istatistikleri ayri pipeline ile calisir -> istatistik/main.py
NOT: Aksam sonuclari icin: python update_results.py  (kendi push'unu yapar)
"""
import subprocess
import sys
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# oddsy-data: CI'da ./oddsy-data, lokalde ../oddsy-data
_ci_path = os.path.join(BASE_DIR, 'oddsy-data')
_local_path = os.path.abspath(os.path.join(BASE_DIR, '..', 'oddsy-data'))
ODDSY_DATA_DIR = _ci_path if os.path.exists(_ci_path) else _local_path


def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")


def run_step(step_name, script_name, work_dir=None, extra_args=None):
    """Bir pipeline adimini calistirir. extra_args: ek komut satiri argumanlari."""
    print_header(step_name)
    cwd = work_dir or BASE_DIR
    script_path = os.path.join(cwd, script_name)

    if not os.path.exists(script_path):
        print(f"[ERROR] Script bulunamadi: {script_path}")
        return False

    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        cmd = [sys.executable, script_path] + (extra_args or [])
        subprocess.run(cmd, cwd=cwd, check=True, env=env)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {script_name} basarisiz (exit code: {e.returncode})")
        return False
    except Exception as e:
        print(f"[ERROR] {script_name} hatasi: {e}")
        return False


def git_push(today_str, label="tahminler"):
    """oddsy-data reposuna data/ klasorunu push eder. Degisiklik yoksa atlar."""
    if not os.path.exists(ODDSY_DATA_DIR):
        print(f"[ERROR] oddsy-data klasoru bulunamadi: {ODDSY_DATA_DIR}")
        return False
    try:
        subprocess.run(['git', 'add', 'data/'], cwd=ODDSY_DATA_DIR, check=True)
        diff = subprocess.run(['git', 'diff', '--staged', '--quiet'], cwd=ODDSY_DATA_DIR)
        if diff.returncode != 0:
            subprocess.run(
                ['git', 'commit', '-m', f'chore: update {label} {today_str}'],
                cwd=ODDSY_DATA_DIR, check=True
            )
            subprocess.run(['git', 'push', 'origin', 'main'], cwd=ODDSY_DATA_DIR, check=True)
            print(f"[OK] Git push basarili ({label})! Frontend otomatik guncellenecek.")
            return True
        else:
            print("[INFO] Veri degismedi, push gerekmiyor.")
            return False
    except Exception as e:
        print(f"[ERROR] Git push hatasi: {e}")
        return False


def main():
    print_header("FUTBOL BOT PIPELINE BASLANIYOR")
    print(f"[START] {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"[DIR]   {BASE_DIR}\n")

    # Gerekli klasorleri olustur
    os.makedirs(os.path.join(BASE_DIR, "filtered"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "merged", "merged_json"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "mackolik-excel-json", "json_output"), exist_ok=True)
    os.makedirs(os.path.join(ODDSY_DATA_DIR, "data"), exist_ok=True)

    # --- 0: GIT PULL (pipeline ONCESINDE yap, bitis degil!) ---
    # Boylece clean.py ve filter_bot.py calisirken yerel repo guncel olur.
    # Eger pull sonraya birakilirsa, filter_bot basarisiz olunca git pull
    # eski dosyalari remote'dan geri getirir ve diff 0 cikar -> push olmaz.
    print_header("0/8: GIT PULL (pipeline oncesi)")
    if os.path.exists(ODDSY_DATA_DIR):
        try:
            subprocess.run(['git', 'pull', 'origin', 'main', '--rebase'],
                           cwd=ODDSY_DATA_DIR, check=False)
            print("[OK] oddsy-data pull tamamlandi.")
        except Exception as e:
            print(f"[WARN] Git pull hatasi (devam ediliyor): {e}")

    # Pipeline adimlari: (isim, script, calisma_dizini, [extra_args], kritik_mi)
    # NOT: Kart & Korner istatistikleri bu pipeline'a DAHIL DEGIL - bu pipeline
    #      sadece gunun maclarini ceker ve siteye yukler.
    #      Kart/korner icin ayrica: python istatistik/main.py
    # NOT: update_results.py --no-push: pipeline push'unu kullan, kendi yapmasi
    # critical=True: bu adim basarisizsa zincir durur (sonraki adimlar bos veri
    # uretir ya da clean.py sitedeki veriyi silip yerine yenisini koyamaz).
    steps = [
        # --- ONCE: Sitedeki mevcut maclari sonuclandir ---
        ("1/10: MAC SONUCLARI GUNCELLE",       "update_results.py",     BASE_DIR,                          ["--no-push"], False),
        # --- SONRA: Yeni gunun maclarini cek ve yukle ---
        ("2/10: ORAN DUSEN MACLAR",            "dropping_odds_bot.py",  BASE_DIR,                          None,          False),
        ("3/10: SOFASCORE VERILERI",           "bet365data.py",         os.path.join(BASE_DIR, "sofa"),    None,          True),
        ("4/10: EKSIK LOGOLARI INDIR",         "logo_downloader.py",    BASE_DIR,                          None,          False),
        ("5/10: MACKOLIK VERILERI",            "guncel_bulten.py",      BASE_DIR,                          None,          True),
        ("6/10: VERILERI BIRLESTIR",           "match_merger_bot.py",   os.path.join(BASE_DIR, "merged"),  None,          True),
        ("7/10: ESKI VERILERI TEMIZLE",        "clean.py",              BASE_DIR,                          None,          True),
        ("8/10: PENDING TAHMINLERI TEMIZLE",   "clear_predictions.py",  BASE_DIR,                          None,          False),
        ("9/10: FILTRELE + JSON KAYDET",       "filter_bot.py",         BASE_DIR,                          None,          True),
    ]

    results = []
    aborted = False
    for step_name, script, cwd, extra, critical in steps:
        success = run_step(step_name, script, cwd, extra)
        results.append((step_name, success))
        if critical and not success:
            print(f"\n[ABORT] Kritik adim basarisiz: {step_name}")
            print("[ABORT] Sonraki adimlar iptal edildi (bos veri yayinlanmasin).")
            aborted = True
            break

    # --- OZET ---
    print_header("ISLEM OZETI")

    success_count = 0
    for step_name, success in results:
        status = "[OK]  " if success else "[FAIL]"
        print(f"   {status} {step_name}")
        if success:
            success_count += 1

    if aborted:
        print(f"   [SKIP] {len(steps) - len(results)} adim calistirilmadi (zincir durduruldu)")

    print(f"\n[RESULT] {success_count}/{len(results)} adim basarili")

    all_ok = (not aborted) and success_count == len(results)

    if all_ok:
        print("\n[SUCCESS] TUM ISLEMLER TAMAMLANDI!")
    else:
        print("\n[WARN] Bazi adimlar basarisiz oldu.")

    # --- GIT PUSH (oddsy-data reposuna) ---
    # Zincir kritik bir adimda koptuysa push YAPILMAZ: yarim/bos veri siteye gitmesin.
    if aborted:
        print_header("GIT PUSH ATLANDI")
        print("[SKIP] Kritik adim basarisiz oldugu icin push yapilmadi.")
    else:
        print_header("9/9: GIT PUSH (oddsy-data reposuna)")
        today_str = datetime.now().strftime('%d.%m.%Y')
        git_push(today_str, label="daily predictions")

    print(f"\n[END] {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 70)
    print("\n[NOT] Aksam maclar bittikten sonra sonuclari guncelle:")
    print("      python update_results.py")
    print("=" * 70)

    return all_ok


if __name__ == "__main__":
    try:
        # Basarisizlikta exit code 1 -> GitHub Actions kirmizi yansin
        sys.exit(0 if main() else 1)
    except KeyboardInterrupt:
        print("\n\n[WARN] Islem durduruldu (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        print(f"\n[CRITICAL] Kritik hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
