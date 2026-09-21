#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

"""
LOGO INDIRICI
Bugunun sofascore_matches JSON'undaki tum takimlari tarar,
public/logos klasoründe olmayan takimlar icin SofaScore'dan
logo indirir ve frontend'e ekler.
"""

import os, json, re, time, glob

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
SOFA_DIR   = os.path.join(BASE_DIR, 'sofa')
LOGOS_DIR  = os.path.abspath(os.path.join(BASE_DIR, '..', 'public', 'logos'))

sys.path.insert(0, SOFA_DIR)
from bet365data import SofascoreScraper


def normalize_logo_name(team_name):
    """Takım adını logo dosya adına çevir (helper.js normalizeTeamName ile aynı mantık)"""
    name = team_name.lower().strip()
    # Türkçe ve diğer dil karakterleri
    replacements = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'á': 'a', 'à': 'a', 'ä': 'a', 'â': 'a', 'ã': 'a', 'å': 'a',
        'é': 'e', 'è': 'e', 'ë': 'e', 'ê': 'e',
        'í': 'i', 'ì': 'i', 'ï': 'i', 'î': 'i',
        'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ø': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u',
        'ý': 'y', 'ñ': 'n', 'ß': 'ss', 'æ': 'ae', 'œ': 'oe',
        'ć': 'c', 'č': 'c', 'ž': 'z', 'š': 's', 'đ': 'd',
        'ř': 'r', 'ě': 'e', 'ů': 'u', 'ď': 'd', 'ť': 't', 'ň': 'n',
        'ą': 'a', 'ę': 'e', 'ź': 'z', 'ż': 'z', 'ś': 's', 'ł': 'l',
        'ń': 'n',
    }
    for char, replacement in replacements.items():
        name = name.replace(char, replacement)
    name = re.sub(r'\s+', '-', name)
    name = re.sub(r'[^a-z0-9-]', '', name)
    return name


def logo_exists(team_name):
    norm = normalize_logo_name(team_name)
    path = os.path.join(LOGOS_DIR, f'{norm}.png')
    return os.path.exists(path), norm, path


def make_request(url, timeout=10):
    """Her istek için taze session oluştur"""
    try:
        from curl_cffi import requests as curl_requests
        s = curl_requests.Session(impersonate="chrome120")
        s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.sofascore.com/',
            'Accept': 'application/json, */*',
        })
        r = s.get(url, timeout=timeout)
        if r.status_code == 200:
            return r
    except Exception:
        pass
    return None


_team_id_cache = {}  # team_name -> team_id

def build_team_id_cache():
    """Günün maç listesinden tüm takım ID'lerini topla"""
    from datetime import datetime
    import pytz
    tz = pytz.timezone('Europe/Istanbul')
    today = datetime.now(tz).strftime('%Y-%m-%d')
    url = f'https://api.sofascore.com/api/v1/sport/football/scheduled-events/{today}'
    r = make_request(url)
    if not r:
        return
    try:
        events = r.json().get('events', [])
        for ev in events:
            ht = ev.get('homeTeam', {})
            at = ev.get('awayTeam', {})
            if ht.get('name') and ht.get('id'):
                _team_id_cache[ht['name'].lower()] = ht['id']
            if at.get('name') and at.get('id'):
                _team_id_cache[at['name'].lower()] = at['id']
        print(f'  [INFO] {len(_team_id_cache)} takim ID önbelleğe alindi')
    except Exception as e:
        print(f'  [WARN] Takim ID önbelleği olusturulamadi: {e}')


def get_team_id_by_name(team_name):
    """Takım adından ID bul"""
    return _team_id_cache.get(team_name.lower())


def download_logo(team_id, save_path):
    """SofaScore'dan takım logosunu indir"""
    url = f'https://api.sofascore.com/api/v1/team/{team_id}/image'
    r = make_request(url)
    if r and len(r.content) > 1000:
        with open(save_path, 'wb') as f:
            f.write(r.content)
        return True
    return False


def main():
    print('=' * 60)
    print('  LOGO INDIRICI')
    print('=' * 60)

    # Bugunün sofascore dosyasını bul
    sofa_files = sorted(glob.glob(os.path.join(SOFA_DIR, 'sofascore_matches_*.json')))
    if not sofa_files:
        print('[WARN] Sofascore dosyasi bulunamadi, atlanıyor.')
        return

    latest = sofa_files[-1]
    print(f'[INFO] Dosya: {os.path.basename(latest)}')

    with open(latest, 'r', encoding='utf-8') as f:
        matches = json.load(f)

    # Eksik logoları bul - team_id direkt JSON'dan al
    missing = {}  # team_name -> {team_id, norm, path}
    for m in matches:
        for side in ('home_team', 'away_team'):
            team = m.get(side, '')
            team_id = m.get(f'{side}_id')
            if not team or not team_id:
                continue
            exists, norm, path = logo_exists(team)
            if not exists and team not in missing:
                missing[team] = {'team_id': team_id, 'norm': norm, 'path': path}

    if not missing:
        print('[OK] Tum takimlarin logosu mevcut, islem gerekmez.')
        return

    print(f'\n[INFO] {len(missing)} takimin logosu eksik:')
    for t in missing:
        print(f'  - {t} ({missing[t]["norm"]}.png)')

    print(f'[INFO] Logolar indiriliyor...')
    downloaded = 0
    failed = 0

    for team_name, info in missing.items():
        norm    = info['norm']
        path    = info['path']
        team_id = info['team_id']

        ok = download_logo(team_id, path)
        if ok:
            print(f'  [OK] {team_name} -> {norm}.png')
            downloaded += 1
        else:
            print(f'  [FAIL] {team_name} -> logo indirilemedi (id={team_id})')
            failed += 1

        time.sleep(0.2)

    print(f'\n[OZET] {downloaded} logo indirildi, {failed} basarisiz')


if __name__ == '__main__':
    main()
