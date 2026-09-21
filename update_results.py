#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
MAC SONUCLARINI OTOMATIK BELIRLE VE JSON'A YAZ

Calisma mantigi:
  1. Eski gunlere ait maclar JSON'dan silinir
  2. Bugunun maclari icin Sofascore'dan sonuc cekılır
  3. Mac bittiyse kategoriye gore KAZANDI/KAYBETTI belirlenir
  4. JSON dosyalari guncellenerek oddsy-data reposuna push edilir

Kullanim:
  python update_results.py              -> bugunun maclarini isle
  python update_results.py --dry-run   -> sadece goster, yazma
  python update_results.py --no-push   -> git push yapma (pipeline icinden)
"""

import json
import os
import argparse
import hashlib
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sofa'))
try:
    from bet365data import SofascoreScraper
except ImportError as e:
    print(f"[HATA] SofascoreScraper import edilemedi: {e}")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ci_path = os.path.join(BASE_DIR, 'oddsy-data')
_local_path = os.path.abspath(os.path.join(BASE_DIR, '..', 'oddsy-data'))
ODDSY_DATA_DIR = _ci_path if os.path.exists(_ci_path) else _local_path
DATA_DIR = os.path.join(ODDSY_DATA_DIR, 'data')

CATEGORIES = [
    {
        'categoryKey': 0,
        'name': 'Ilk Yari Gol',
        'file': 'halfTimeGoals.json',
        'determine': lambda h1, a1, h2, a2: 'won' if (h1 + a1) > 0 else 'lost',
    },
    {
        'categoryKey': 1,
        'name': '2.5 Ust',
        'file': 'dailyChoices.json',
        'kategori_filter': '2.5 Üst',
        'determine': lambda h1, a1, h2, a2: 'won' if (h1 + a1 + h2 + a2) > 2 else 'lost',
    },
    {
        'categoryKey': 1,
        'name': '3.5 Ust',
        'file': 'dailyChoices.json',
        'kategori_filter': '3.5 Üst',
        'determine': lambda h1, a1, h2, a2: 'won' if (h1 + a1 + h2 + a2) > 3 else 'lost',
    },
    {
        'categoryKey': 2,
        'name': 'MS 5.5 Ust',
        'file': 'dailySurprises.json',
        'determine': lambda h1, a1, h2, a2: 'won' if (h1 + a1 + h2 + a2) > 5 else 'lost',
    },
]


def build_match_key(home_team, away_team, prediction='ilk yari gol', odds=''):
    return f"{home_team.lower().strip()}|{away_team.lower().strip()}|{prediction.lower().strip()}|{odds.lower().strip()}"


def make_doc_id(match_key, category_key):
    raw = f"{match_key}||{category_key}"
    return hashlib.md5(raw.encode()).hexdigest()


_merged_cache = {}

def get_event_id_from_merged(home_team, away_team):
    global _merged_cache
    if not _merged_cache:
        merged_dir = os.path.join(BASE_DIR, 'merged', 'merged_json')
        if os.path.exists(merged_dir):
            import glob
            for merged_file in glob.glob(os.path.join(merged_dir, 'merged_*.json')):
                try:
                    with open(merged_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for m in data.get('matches', []):
                        key = f"{m.get('home_team','').lower().strip()}|||{m.get('away_team','').lower().strip()}"
                        _merged_cache[key] = m.get('event_id')
                except Exception:
                    pass
    key = f"{home_team.lower().strip()}|||{away_team.lower().strip()}"
    return _merged_cache.get(key)


def get_sofascore_result(scraper, event_id):
    try:
        url = f"{scraper.base_url}/event/{event_id}"
        response = scraper.session.get(url, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        event = data.get('event', {})
        status_type = event.get('status', {}).get('type', '')
        if status_type != 'finished':
            return None
        hs = event.get('homeScore', {})
        as_ = event.get('awayScore', {})
        return {
            'home_period1': hs.get('period1', 0) or 0,
            'away_period1': as_.get('period1', 0) or 0,
            'home_period2': hs.get('period2', 0) or 0,
            'away_period2': as_.get('period2', 0) or 0,
            'home_final': hs.get('current', 0) or 0,
            'away_final': as_.get('current', 0) or 0,
        }
    except Exception as e:
        print(f"    [UYARI] Sofascore hatasi (event_id={event_id}): {e}")
        return None


def purge_old_matches(matches, today, file_label):
    """
    Bugunun tarihine ait olmayan maclari siler.
    - tarih alani varsa ve != bugun -> sil
    - tarih alani yoksa + autoUpdated=True ve status won/lost -> sil (eski format)
    Silinen maclar icin CMD'e bilgi yazilir.
    """
    keep = []
    deleted = []

    for m in matches:
        tarih = m.get('tarih')
        status = m.get('status', 'pending')
        auto = m.get('autoUpdated', False)

        if tarih and tarih != today:
            # Baska gune ait, kesinlikle sil
            deleted.append(m)
        elif not tarih and auto and status in ('won', 'lost'):
            # tarih alani yok ama sonuclanmis (eski format) -> sil
            deleted.append(m)
        else:
            keep.append(m)

    if deleted:
        print(f"\n  [SIL] {file_label}: {len(deleted)} eski mac silindi:")
        for m in deleted:
            tarih_str = m.get('tarih', '?')
            st = m.get('status', '-')
            print(f"        - {m.get('home_team','?')} vs {m.get('away_team','?')} "
                  f"| Tarih: {tarih_str} | Durum: {st}")
    else:
        print(f"  [OK] {file_label}: Silinecek eski mac yok.")

    return keep, len(deleted)


def update_results(dry_run=False):
    today = datetime.now().strftime("%d.%m.%Y")
    now_time = datetime.now().strftime("%H:%M:%S")

    print(f"\n{'='*65}")
    print(f"  MAC SONUCLARI - OTOMATIK GUNCELLEME")
    print(f"  Tarih : {today}  Saat: {now_time}")
    print(f"{'='*65}\n")

    scraper = SofascoreScraper()
    print("[*] Sofascore baglantisi kuruluyor...")
    scraper.warm_up()
    print("[OK] Sofascore hazir.\n")

    total_updated  = 0
    total_skipped  = 0
    total_pending  = 0
    total_deleted  = 0

    # Her dosyayi bir kez ac; birden fazla kategori ayni dosyayi kullanabilir
    # Once butun dosyalari oku + eski maclari temizle
    file_data = {}
    processed_files = set()

    for cat in CATEGORIES:
        fname = cat['file']
        if fname in processed_files:
            continue
        processed_files.add(fname)

        file_path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(file_path):
            print(f"[UYARI] {fname} bulunamadi, atlaniyor.\n")
            file_data[fname] = []
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            matches = json.load(f)

        print(f"--- {fname} ({len(matches)} mac okundu) ---")
        cleaned, n_del = purge_old_matches(matches, today, fname)
        total_deleted += n_del
        file_data[fname] = cleaned

        # Temizlenmis halini hemen yaz (dry_run degilse)
        if not dry_run and n_del > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned, f, ensure_ascii=False, indent=2)
            print(f"  [KAYIT] {fname} -> {n_del} mac silindi, kaydedildi.")

        print()

    print(f"{'='*65}")
    print(f"  SONUC GUNCELLEME BASLANIYOR")
    print(f"{'='*65}\n")

    for cat in CATEGORIES:
        fname = cat['file']
        matches = file_data.get(fname, [])
        kategori_filter = cat.get('kategori_filter')

        filtered = [m for m in matches if not kategori_filter or m.get('kategori') == kategori_filter]
        pending_count = sum(1 for m in filtered if m.get('status') not in ('won', 'lost'))

        print(f"[{cat['name']}] {fname} -> {len(filtered)} mac, {pending_count} bekliyor")

        for match in matches:
            if kategori_filter and match.get('kategori') != kategori_filter:
                continue

            # Zaten sonuclanmis -> atla
            if match.get('status') in ('won', 'lost') and match.get('autoUpdated'):
                print(f"  [ATLA] {match.get('home_team')} vs {match.get('away_team')} "
                      f"-> zaten {match.get('status').upper()}")
                total_skipped += 1
                continue

            home_team = match.get('home_team', '')
            away_team = match.get('away_team', '')
            event_id  = match.get('event_id')

            if not home_team or not away_team:
                continue

            if not event_id:
                event_id = get_event_id_from_merged(home_team, away_team)
                if not event_id:
                    print(f"  [?] event_id bulunamadi: {home_team} vs {away_team}")
                    total_skipped += 1
                    continue

            result = get_sofascore_result(scraper, event_id)
            if not result:
                print(f"  [BEKLE] {home_team} vs {away_team} (id={event_id}) -> mac bitmemis veya veri yok")
                total_pending += 1
                continue

            status = cat['determine'](
                result['home_period1'], result['away_period1'],
                result['home_period2'], result['away_period2']
            )

            score_str = (
                f"IY: {result['home_period1']}-{result['away_period1']} | "
                f"MS: {result['home_final']}-{result['away_final']}"
            )
            icon = '[KAZANDI]' if status == 'won' else '[KAYBETTI]'
            print(f"  {icon} {home_team} vs {away_team} -> {score_str}")

            match['status']      = status
            match['score']       = score_str
            match['autoUpdated'] = True
            match['tarih']       = today
            match['updatedAt']   = datetime.now().strftime("%H:%M:%S")

            total_updated += 1

        # Kategori bitti, guncellenmis JSON'u kaydet
        if not dry_run:
            file_path = os.path.join(DATA_DIR, fname)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(file_data[fname], f, ensure_ascii=False, indent=2)
            print(f"  [KAYIT] {fname} guncellendi.\n")
        else:
            print(f"  [DRY-RUN] {fname} yazilmadi.\n")

    print(f"{'='*65}")
    print(f"  OZET")
    print(f"  Silinen  (eski mac) : {total_deleted}")
    print(f"  Guncellendi         : {total_updated}")
    print(f"  Atlandi (zaten OK)  : {total_skipped}")
    print(f"  Bekleniyor          : {total_pending}")
    print(f"{'='*65}\n")


if __name__ == '__main__':
    import subprocess as _sp
    parser = argparse.ArgumentParser(description='Mac sonuclarini otomatik guncelle')
    parser.add_argument('--dry-run', action='store_true', help='Sadece goster, yazma')
    parser.add_argument('--no-push', action='store_true', help='Git push yapma')
    args = parser.parse_args()

    update_results(dry_run=args.dry_run)

    # Git push - ISLEM SONUNDA (asla basta degil)
    if not args.dry_run and not args.no_push and os.path.exists(ODDSY_DATA_DIR):
        print("="*65)
        print("  GIT PUSH - SONUCLAR YUKLENIYOR")
        print("="*65)
        try:
            today_str = datetime.now().strftime('%d.%m.%Y')
            _sp.run(['git', 'add', 'data/'], cwd=ODDSY_DATA_DIR, check=True)
            diff = _sp.run(['git', 'diff', '--staged', '--quiet'], cwd=ODDSY_DATA_DIR)
            if diff.returncode != 0:
                _sp.run(
                    ['git', 'commit', '-m', f'chore: update match results {today_str}'],
                    cwd=ODDSY_DATA_DIR, check=True
                )
                _sp.run(['git', 'push', 'origin', 'main'], cwd=ODDSY_DATA_DIR, check=True)
                print("[OK] Sonuclar siteye yuklendi!")
            else:
                print("[BILGI] Degisiklik yok, push gerekmiyor.")
        except Exception as e:
            print(f"[HATA] Git push hatasi: {e}")
