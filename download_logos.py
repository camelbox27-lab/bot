#!/usr/bin/env python3
"""
Oddsy Logo Downloader
- GitHub luukhopman/football-logos reposundan 25 UEFA ligi logolarını indirir
- TheSportsDB API'den eksik takım logolarını tamamlar
- ALL_TEAM_LOGOS array'i ve specialCases mapping'i üretir
"""

import os
import re
import json
import time
import sys
import urllib.request
import urllib.parse
import urllib.error
import ssl

# Windows console encoding fix
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# SSL verification skip (bazı sistemlerde gerekebilir)
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

LOGOS_DIR = os.path.join(os.path.dirname(__file__), '..', 'public', 'logos')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'oddsy-data')

GITHUB_API = "https://api.github.com/repos/luukhopman/football-logos/contents/logos"
THESPORTSDB_API = "https://www.thesportsdb.com/api/v1/json/123/searchteams.php"

GITHUB_LEAGUES = [
    "Austria - Bundesliga",
    "Belgium - Jupiler Pro League",
    "Bulgaria - efbet Liga",
    "Croatia - SuperSport HNL",
    "Czech Republic - Chance Liga",
    "Denmark - Superliga",
    "England - Premier League",
    "France - Ligue 1",
    "Germany - Bundesliga",
    "Greece - Super League 1",
    "Israel - Ligat ha'Al",
    "Italy - Serie A",
    "Netherlands - Eredivisie",
    "Norway - Eliteserien",
    "Poland - PKO BP Ekstraklasa",
    "Portugal - Liga Portugal",
    "Romania - SuperLiga",
    "Russia - Premier Liga",
    "Scotland - Scottish Premiership",
    "Serbia - Super liga Srbije",
    "Spain - LaLiga",
    "Sweden - Allsvenskan",
    "Switzerland - Super League",
    "Türkiye - Süper Lig",
    "Ukraine - Premier Liga",
]


def normalize_filename(name):
    """Dosya adını convention'a çevir: lowercase, hyphens, no special chars."""
    name = name.lower().strip()
    # .png uzantısını kaldır
    if name.endswith('.png'):
        name = name[:-4]
    # Özel karakter dönüşümleri
    replacements = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n',
        'ä': 'a', 'ë': 'e', 'ï': 'i', 'ô': 'o', 'û': 'u', 'ø': 'o',
        'å': 'a', 'æ': 'ae', 'ð': 'd', 'þ': 'th', 'ß': 'ss',
        'ã': 'a', 'õ': 'o', 'ê': 'e', 'â': 'a', 'î': 'i', 'ù': 'u',
        'è': 'e', 'à': 'a', 'ò': 'o', 'ý': 'y', 'ž': 'z', 'š': 's',
        'č': 'c', 'ř': 'r', 'ď': 'd', 'ť': 't', 'ň': 'n', 'ě': 'e',
        'ů': 'u', 'ć': 'c', 'đ': 'd', 'ł': 'l', 'ź': 'z', 'ą': 'a',
        'ę': 'e', 'ś': 's', 'ń': 'n', 'ţ': 't', 'ă': 'a', 'ĭ': 'i',
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    # Boşluk, nokta, apostrof -> tire
    name = re.sub(r'[\s.\'\&\+]+', '-', name)
    # Alfanumerik ve tire dışındaki karakterleri kaldır
    name = re.sub(r'[^a-z0-9-]', '', name)
    # Çoklu tireleri tekle
    name = re.sub(r'-+', '-', name).strip('-')
    return name


def fetch_json(url):
    """URL'den JSON çek."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Oddsy-Logo-Downloader'})
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"  [HATA] {url}: {e}")
        return None


def encode_url(url):
    """URL'deki ozel karakterleri encode et."""
    parsed = urllib.parse.urlparse(url)
    encoded_path = urllib.parse.quote(parsed.path, safe='/')
    return urllib.parse.urlunparse(parsed._replace(path=encoded_path))


def download_file(url, filepath):
    """Dosya indir."""
    # download_url zaten encode'lu geliyor, tekrar encode etme
    req = urllib.request.Request(url, headers={'User-Agent': 'Oddsy-Logo-Downloader'})
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=30) as resp:
            with open(filepath, 'wb') as f:
                f.write(resp.read())
        return True
    except Exception as e:
        print(f"  [HATA] Indirilemedi: {e}")
        return False


def get_existing_logos():
    """Mevcut logo dosya adlarını döndür (uzantısız)."""
    logos = set()
    if os.path.exists(LOGOS_DIR):
        for f in os.listdir(LOGOS_DIR):
            if f.endswith('.png'):
                logos.add(f[:-4])  # .png kaldır
    return logos


def download_github_logos():
    """GitHub reposundan tüm liglerin logolarını indir."""
    print("=" * 60)
    print("ADIM 1: GitHub reposundan logolar indiriliyor...")
    print("=" * 60)

    existing = get_existing_logos()
    downloaded = 0
    skipped = 0
    failed = 0
    name_mappings = {}  # original_name -> local_filename

    for league in GITHUB_LEAGUES:
        encoded = urllib.parse.quote(league)
        url = f"{GITHUB_API}/{encoded}"
        print(f"\n[LIG] {league}...")

        data = fetch_json(url)
        if not data or not isinstance(data, list):
            print(f"  [HATA] Veri alınamadı!")
            failed += 1
            continue

        for item in data:
            if item.get('type') != 'file' or not item['name'].endswith('.png'):
                continue

            original_name = item['name'][:-4]  # .png kaldır
            local_name = normalize_filename(original_name)
            download_url = item.get('download_url', '')

            if not download_url:
                continue

            name_mappings[original_name.lower()] = local_name

            if local_name in existing:
                skipped += 1
                continue

            filepath = os.path.join(LOGOS_DIR, f"{local_name}.png")
            if download_file(download_url, filepath):
                downloaded += 1
                existing.add(local_name)
                print(f"  [OK] {original_name} -> {local_name}.png")
            else:
                failed += 1

        time.sleep(0.5)  # GitHub API rate limit

    print(f"\n[SONUC] GitHub: {downloaded} indirildi, {skipped} zaten vardı, {failed} başarısız")
    return name_mappings


def get_all_team_names():
    """Tüm JSON dosyalarından takım adlarını topla."""
    teams = set()

    # Güncel maçlar
    guncel_path = os.path.join(DATA_DIR, 'guncel_json', 'gunlukmaclar.json')
    if os.path.exists(guncel_path):
        try:
            with open(guncel_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for m in data:
                if m.get('Ev'): teams.add(m['Ev'])
                if m.get('Dep'): teams.add(m['Dep'])
        except:
            pass

    # Lig JSON'ları
    ligler_dir = os.path.join(DATA_DIR, 'ligler_json')
    if os.path.exists(ligler_dir):
        for fname in os.listdir(ligler_dir):
            if fname.endswith('.json'):
                try:
                    with open(os.path.join(ligler_dir, fname), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for m in data:
                        if m.get('Ev'): teams.add(m['Ev'])
                        if m.get('Dep'): teams.add(m['Dep'])
                except:
                    pass

    return teams


def check_logo_exists(team_name, existing_logos):
    """Bir takımın logosu var mı kontrol et (helper.js mantığıyla)."""
    lower = team_name.lower().strip()

    # Exact match
    exact = re.sub(r'[\s]+', '-', lower)
    exact = re.sub(r'[.\']', '', exact)
    if exact in existing_logos:
        return True

    # Normalized
    normalized = normalize_filename(team_name)
    if normalized in existing_logos:
        return True

    # Partial
    if normalized and len(normalized) > 3:
        for logo in existing_logos:
            if normalized in logo:
                return True
            if logo in normalized and len(logo) > 3:
                return True

    # FC prefix/suffix removed
    stripped = re.sub(r'^(fc-|fk-|sc-|cf-|afc-|rsc-)', '', normalized)
    stripped = re.sub(r'-(fc|fk|sc|cf|f)$', '', stripped)
    if stripped != normalized and stripped in existing_logos:
        return True
    if stripped and len(stripped) > 3:
        for logo in existing_logos:
            if stripped in logo or logo in stripped:
                return True

    return False


def download_thesportsdb_logos(all_teams):
    """TheSportsDB API'den eksik logoları indir."""
    print("\n" + "=" * 60)
    print("ADIM 2: TheSportsDB API'den eksik logolar tamamlanıyor...")
    print("=" * 60)

    existing = get_existing_logos()
    missing_teams = []

    for team in sorted(all_teams):
        if not check_logo_exists(team, existing):
            missing_teams.append(team)

    print(f"\n{len(missing_teams)} takımın logosu eksik. TheSportsDB'den aranıyor...\n")

    downloaded = 0
    not_found = 0
    name_mappings = {}

    for team in missing_teams:
        # Arama terimi hazırla - "FC " prefix'i kaldır
        search_term = team.strip()
        search_term = re.sub(r'\s+F$', '', search_term)  # "Real Madrid F" -> "Real Madrid"
        search_term = re.sub(r'^FC\s+', '', search_term)  # "FC Bologna" -> "Bologna"
        search_term = re.sub(r'\s+FC$', '', search_term)

        encoded = urllib.parse.quote(search_term)
        url = f"{THESPORTSDB_API}?t={encoded}"

        data = fetch_json(url)
        time.sleep(1)  # Rate limiting

        if not data or not data.get('teams'):
            # İkinci deneme: sadece ilk kelime
            words = search_term.split()
            if len(words) > 1:
                # Ana kelimeyi dene (genellikle şehir adı)
                main_word = words[0] if words[0] not in ('Real', 'Sporting', 'Athletic', 'FC', 'Union', 'Young', 'Go') else ' '.join(words[:2])
                encoded2 = urllib.parse.quote(main_word)
                url2 = f"{THESPORTSDB_API}?t={encoded2}"
                data = fetch_json(url2)
                time.sleep(1)

        if data and data.get('teams'):
            badge_url = data['teams'][0].get('strBadge') or data['teams'][0].get('strTeamBadge')
            if badge_url:
                local_name = normalize_filename(team)
                filepath = os.path.join(LOGOS_DIR, f"{local_name}.png")

                if local_name not in existing:
                    if download_file(badge_url, filepath):
                        downloaded += 1
                        existing.add(local_name)
                        name_mappings[team.lower()] = local_name
                        print(f"  [OK] {team} -> {local_name}.png")
                        continue

        not_found += 1
        print(f"  [MISS] {team} - bulunamadı")

    print(f"\n[SONUC] TheSportsDB: {downloaded} indirildi, {not_found} bulunamadı")
    return name_mappings


def generate_js_output():
    """ALL_TEAM_LOGOS array'ini ve specialCases güncellemelerini üret."""
    print("\n" + "=" * 60)
    print("ADIM 3: JavaScript çıktısı üretiliyor...")
    print("=" * 60)

    logos = sorted(get_existing_logos())
    print(f"\nToplam {len(logos)} logo dosyası mevcut.")

    # ALL_TEAM_LOGOS array'i dosyaya yaz
    output_path = os.path.join(os.path.dirname(__file__), 'generated_logos_array.js')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("const ALL_TEAM_LOGOS = [\n")
        for i, logo in enumerate(logos):
            comma = "," if i < len(logos) - 1 else ""
            f.write(f'    "{logo}"{comma}\n')
        f.write("];\n")

    print(f"✅ Array yazıldı: {output_path}")
    return logos


def main():
    os.makedirs(LOGOS_DIR, exist_ok=True)

    # Adım 1: GitHub'dan indir
    github_mappings = download_github_logos()

    # Adım 2: Tüm takım adlarını topla
    all_teams = get_all_team_names()
    print(f"\n[INFO] Toplam {len(all_teams)} benzersiz takım adı bulundu.")

    # Adım 3: Eksik olanları TheSportsDB'den indir
    sportsdb_mappings = download_thesportsdb_logos(all_teams)

    # Adım 4: JS çıktısı üret
    logos = generate_js_output()

    print("\n" + "=" * 60)
    print("TAMAMLANDI!")
    print(f"Toplam logo sayısı: {len(logos)}")
    print("=" * 60)
    print("\nSonraki adım: bot/generated_logos_array.js dosyasındaki array'i")
    print("src/helper.js'deki ALL_TEAM_LOGOS ile değiştirin.")


if __name__ == '__main__':
    main()
