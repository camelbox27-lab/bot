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
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# SESSIZ=1 (masaustu kisayolu bunu ayarlar): alt scriptlerin ciktisi ekrana
# dokulmez, bot_log.txt'ye yazilir; ekranda yalnizca adim durumlari kalir.
# Hata halinde ilgili adimin son satirlari yine gosterilir, yoksa kullanici
# neyin bozuldugunu goremez.
SESSIZ = os.environ.get('SESSIZ') == '1'

# MOBIL=1 (yalnizca telefondaki BULTEN YUKLE butonu bunu ayarlar):
# SofaScore ve Mackolik'in mac sayfalari GitHub'in veri merkezi IP'lerinden
# 403 donuyor; her ikisi de kritik adim oldugu icin zincir oradan ilerlemiyor.
# Mobilde bu adimlarin yerine merged dosyasi Flashscore'dan dogrudan
# uretiliyor (otomasyon/bulten_uret.py), sonuc guncelleme ise atlaniyor.
# PC bu degiskeni ASLA ayarlamaz, orada davranis birebir ayni kalir.
MOBIL = os.environ.get('MOBIL') == '1'
MOBILDE_ATLANAN = {
    'update_results.py',    # sonuclar SofaScore event_id ister, mobilde yok
    'dropping_odds_bot.py', # SofaScore 403; mevcut droppingOdds.json korunur
    'bet365data.py',        # SofaScore 403
    'guncel_bulten.py',     # Mackolik mac sayfalari 403
    'match_merger_bot.py',  # birlestirecek iki kaynak yok, merged hazir geliyor
}
LOG_DOSYA = os.path.join(BASE_DIR, 'bot_log.txt')
HATA_SATIR = 15   # basarisiz adimda ekrana basilacak son satir sayisi
# oddsy-data: CI'da ./oddsy-data, lokalde ../oddsy-data
_ci_path = os.path.join(BASE_DIR, 'oddsy-data')
_local_path = os.path.abspath(os.path.join(BASE_DIR, '..', 'oddsy-data'))
ODDSY_DATA_DIR = _ci_path if os.path.exists(_ci_path) else _local_path


def print_header(text):
    if SESSIZ:
        return
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")


def log_yaz(baslik, metin):
    """Adim ciktisini bot_log.txt'ye ekler (sessiz modda ayrinti burada kalir)."""
    try:
        with open(LOG_DOSYA, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*70}\n{baslik}\n{'='*70}\n{metin}\n")
    except Exception:
        pass


def run_step(step_name, script_name, work_dir=None, extra_args=None):
    """Bir pipeline adimini calistirir. extra_args: ek komut satiri argumanlari."""
    print_header(step_name)
    cwd = work_dir or BASE_DIR
    script_path = os.path.join(cwd, script_name)

    if not os.path.exists(script_path):
        print(f"[ERROR] Script bulunamadi: {script_path}")
        return False

    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    cmd = [sys.executable, script_path] + (extra_args or [])

    if not SESSIZ:
        try:
            subprocess.run(cmd, cwd=cwd, check=True, env=env)
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] {script_name} basarisiz (exit code: {e.returncode})")
            return False
        except Exception as e:
            print(f"[ERROR] {script_name} hatasi: {e}")
            return False

    # --- Sessiz mod: cikti yakalanir, ekranda tek satir kalir
    print(f"  {step_name:<42}", end="", flush=True)
    basla = time.time()
    try:
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True,
                           text=True, encoding='utf-8', errors='replace')
    except Exception as e:
        print(f"HATA  ({e})")
        log_yaz(step_name, f"calistirilamadi: {e}")
        return False

    sure = time.time() - basla
    cikti = (r.stdout or '') + (r.stderr or '')
    log_yaz(step_name, cikti)

    if r.returncode == 0:
        print(f"BASARILI   ({sure:4.1f} sn)")
        return True

    print(f"BASARISIZ  ({sure:4.1f} sn)")
    satirlar = [x for x in cikti.splitlines() if x.strip()]
    for satir in satirlar[-HATA_SATIR:]:
        print(f"       | {satir}")
    print(f"       | (tam dokum: bot_log.txt)")
    return False


def _git(args, **kw):
    """git komutu calistirir. SESSIZ modda cikti ekrana degil bot_log.txt'ye gider;
    alt surecler dogrudan terminale yazdigi icin burada yakalanmasi sart, yoksa
    adim satirlarinin hizasi bozulur."""
    if SESSIZ:
        kw.setdefault('capture_output', True)
        kw.setdefault('text', True)
        kw.setdefault('encoding', 'utf-8')
        kw.setdefault('errors', 'replace')
    try:
        r = subprocess.run(args, **kw)
    except subprocess.CalledProcessError as e:
        if SESSIZ:
            log_yaz(f"git {' '.join(args[1:])}", (e.stdout or '') + (e.stderr or ''))
        raise
    if SESSIZ:
        log_yaz(f"git {' '.join(args[1:])}", (r.stdout or '') + (r.stderr or ''))
    return r


def git_push(today_str, label="tahminler"):
    """oddsy-data reposuna data/ klasorunu push eder. Degisiklik yoksa atlar."""
    if not os.path.exists(ODDSY_DATA_DIR):
        print(f"[ERROR] oddsy-data klasoru bulunamadi: {ODDSY_DATA_DIR}")
        return False
    try:
        _git(['git', 'add', 'data/'], cwd=ODDSY_DATA_DIR, check=True)
        diff = _git(['git', 'diff', '--staged', '--quiet'], cwd=ODDSY_DATA_DIR)
        if diff.returncode != 0:
            _git(['git', 'commit', '-m', f'chore: update {label} {today_str}'],
                 cwd=ODDSY_DATA_DIR, check=True)

            # Pipeline calisirken telefondaki butonlardan biri push etmis
            # olabilir; o zaman push reddedilir. Bizim commit'imiz yalnizca
            # data/ klasorune dokundugu, telefon butonlari ise iddaa/ ve
            # bet365/ yazdigi icin rebase temiz gecer.
            itildi = _git(['git', 'push', 'origin', 'main'],
                          cwd=ODDSY_DATA_DIR, check=False)
            if itildi.returncode != 0:
                print("[INFO] Uzakta yeni commit var, rebase edilip tekrar denenecek...")
                _git(['git', 'pull', '--rebase', 'origin', 'main'],
                     cwd=ODDSY_DATA_DIR, check=True)
                _git(['git', 'push', 'origin', 'main'],
                     cwd=ODDSY_DATA_DIR, check=True)

            print(f"[OK] Git push basarili ({label})! Frontend otomatik guncellenecek.")
            return True
        else:
            print("[INFO] Veri degismedi, push gerekmiyor.")
            return False
    except Exception as e:
        print(f"[ERROR] Git push hatasi: {e}")
        return False


def main():
    if SESSIZ:
        # Her calistirmada log bastan yazilsin
        try:
            open(LOG_DOSYA, 'w', encoding='utf-8').close()
        except Exception:
            pass
        print()
        print("=" * 62)
        print("  ODDSY FUTBOL BOT")
        print(f"  {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print("=" * 62)
        print()
    else:
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
    print_header("0/9: VERI DEPOSUNU ESITLE (pipeline oncesi)")
    if SESSIZ:
        print(f"  {'VERI DEPOSU ESITLENIYOR...':<42}", end="", flush=True)

    if os.path.exists(ODDSY_DATA_DIR):
        try:
            # Bu bot yalnizca data/ klasorunun sahibi. iddaa/ ve bet365/
            # klasorlerini telefondaki butonlar (GitHub Actions) yaziyor.
            # Oradaki .xlsx dosyalari binary oldugu icin git birlestiremiyor;
            # "needs merge" ile index kilitleniyor ve ne stash ne commit
            # calisiyordu. Birlestirmeye calismak yerine depo dogrudan
            # uzaktaki surume esitlenir.
            #
            # Bu adim pipeline data/ yazmadan ONCE calistigi icin bu
            # calismanin ciktisi etkilenmez. Atilan tek sey onceki
            # calismadan kalmis, push edilememis yerel degisikliklerdir;
            # data/ her calismada yeniden uretildigi icin kayip olmaz.
            _git(['git', 'fetch', 'origin', 'main'], cwd=ODDSY_DATA_DIR, check=True)

            kirli = subprocess.run(['git', 'status', '--porcelain'],
                                   cwd=ODDSY_DATA_DIR, capture_output=True,
                                   text=True, check=False).stdout.strip()

            _git(['git', 'reset', '--hard', 'origin/main'],
                 cwd=ODDSY_DATA_DIR, check=True)

            print("TAMAM" if SESSIZ else "[OK] oddsy-data uzaktaki surume esitlendi.")

            if kirli:
                n = len(kirli.splitlines())
                if SESSIZ:
                    print(f"  {'':<42}({n} push edilmemis yerel degisiklik atildi)")
                else:
                    print(f"[INFO] {n} push edilmemis yerel degisiklik atildi.")
        except Exception as e:
            print(f"HATA ({e})" if SESSIZ
                  else f"[WARN] Esitleme hatasi (devam ediliyor): {e}")
    else:
        print("DEPO YOK" if SESSIZ
              else f"[WARN] oddsy-data bulunamadi: {ODDSY_DATA_DIR}")

    # Pipeline adimlari: (isim, script, calisma_dizini, [extra_args], kritik_mi)
    # NOT: Kart & Korner istatistikleri bu pipeline'a DAHIL DEGIL - bu pipeline
    #      sadece gunun maclarini ceker ve siteye yukler.
    #      Kart/korner icin ayrica: python istatistik/main.py
    # NOT: update_results.py --no-push: pipeline push'unu kullan, kendi yapmasi
    # critical=True: bu adim basarisizsa zincir durur (sonraki adimlar bos veri
    # uretir ya da clean.py sitedeki veriyi silip yerine yenisini koyamaz).
    steps = [
        # --- ONCE: Sitedeki mevcut maclari sonuclandir ---
        ("1/9: MAC SONUCLARI GUNCELLE",       "update_results.py",     BASE_DIR,                          ["--no-push"], False),
        # --- SONRA: Yeni gunun maclarini cek ve yukle ---
        ("2/9: ORAN DUSEN MACLAR",            "dropping_odds_bot.py",  BASE_DIR,                          None,          False),
        ("3/9: SOFASCORE VERILERI",           "bet365data.py",         os.path.join(BASE_DIR, "sofa"),    None,          True),
        ("4/9: EKSIK LOGOLARI INDIR",         "logo_downloader.py",    BASE_DIR,                          None,          False),
        ("5/9: MACKOLIK VERILERI",            "guncel_bulten.py",      BASE_DIR,                          None,          True),
        ("6/9: VERILERI BIRLESTIR",           "match_merger_bot.py",   os.path.join(BASE_DIR, "merged"),  None,          True),
        ("7/9: ESKI VERILERI TEMIZLE",        "clean.py",              BASE_DIR,                          None,          True),
        ("8/9: PENDING TAHMINLERI TEMIZLE",   "clear_predictions.py",  BASE_DIR,                          None,          False),
        ("9/9: FILTRELE + JSON KAYDET",       "filter_bot.py",         BASE_DIR,                          None,          True),
    ]

    results = []
    aborted = False
    for step_name, script, cwd, extra, critical in steps:
        if MOBIL and script in MOBILDE_ATLANAN:
            if SESSIZ:
                print(f"  {step_name:<42}ATLANDI (mobil)")
            else:
                print_header(step_name)
                print("[ATLANDI] Mobil yolda bu adimin verisi Flashscore'dan geliyor.")
            continue
        success = run_step(step_name, script, cwd, extra)
        results.append((step_name, success))
        if critical and not success:
            print(f"\n[ABORT] Kritik adim basarisiz: {step_name}")
            print("[ABORT] Sonraki adimlar iptal edildi (bos veri yayinlanmasin).")
            aborted = True
            break

    # --- OZET ---
    success_count = sum(1 for _, ok in results if ok)

    if SESSIZ:
        print()
        print("-" * 62)
        print(f"  {success_count}/{len(results)} adim basarili", end="")
        if aborted:
            print(f"  ({len(steps) - len(results)} adim calistirilmadi)")
        else:
            print()
        print("-" * 62)
    else:
        print_header("ISLEM OZETI")
        for step_name, success in results:
            status = "[OK]  " if success else "[FAIL]"
            print(f"   {status} {step_name}")

    if aborted and not SESSIZ:
        print(f"   [SKIP] {len(steps) - len(results)} adim calistirilmadi (zincir durduruldu)")

    if not SESSIZ:
        print(f"\n[RESULT] {success_count}/{len(results)} adim basarili")

    all_ok = (not aborted) and success_count == len(results)

    if not SESSIZ:
        if all_ok:
            print("\n[SUCCESS] TUM ISLEMLER TAMAMLANDI!")
        else:
            print("\n[WARN] Bazi adimlar basarisiz oldu.")

    # --- GIT PUSH (oddsy-data reposuna) ---
    # Zincir kritik bir adimda koptuysa push YAPILMAZ: yarim/bos veri siteye gitmesin.
    if aborted:
        if SESSIZ:
            print("\n  SITEYE YUKLEME ATLANDI")
            print("  Kritik bir adim basarisiz oldugu icin yarim veri gonderilmedi.")
        else:
            print_header("GIT PUSH ATLANDI")
            print("[SKIP] Kritik adim basarisiz oldugu icin push yapilmadi.")
    else:
        today_str = datetime.now().strftime('%d.%m.%Y')
        if SESSIZ:
            print(f"\n  {'SITEYE YUKLENIYOR...':<42}", end="", flush=True)
            import io, contextlib
            tampon = io.StringIO()
            with contextlib.redirect_stdout(tampon):
                gonderildi = git_push(today_str, label="daily predictions")
            log_yaz("GIT PUSH", tampon.getvalue())
            print("TAMAM" if gonderildi else "DEGISIKLIK YOK")
        else:
            print_header("GIT PUSH (oddsy-data reposuna)")
            git_push(today_str, label="daily predictions")

    if SESSIZ:
        print()
        print("=" * 62)
        if all_ok:
            print("  TAMAMLANDI - site guncellendi")
        else:
            print("  BAZI ADIMLAR BASARISIZ - ayrinti icin bot_log.txt")
        print(f"  Bitis: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 62)
    else:
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
