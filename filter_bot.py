import json
import os
import glob
import pandas as pd
from datetime import datetime

"""
FILTER BOT - Firebase KULLANMAZ
Verileri filtreler ve JSON dosyaları olarak oddsy-data reposuna kaydeder.
Frontend bu JSON'ları GitHub raw URL'lerinden çeker.
"""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# oddsy-data: CI'da ./oddsy-data, lokalde ../oddsy-data
_ci_path = os.path.join(BASE_DIR, 'oddsy-data')
_local_path = os.path.abspath(os.path.join(BASE_DIR, '..', 'oddsy-data'))
ODDSY_DATA_DIR = _ci_path if os.path.exists(_ci_path) else _local_path
DATA_OUTPUT_DIR = os.path.join(ODDSY_DATA_DIR, 'data')


def filter_matches():
    today = datetime.now().strftime("%d.%m.%Y")

    # Çıktı klasörünü oluştur
    os.makedirs(DATA_OUTPUT_DIR, exist_ok=True)

    # 🔻 ORAN DÜŞEN MAÇLARI OKU
    dropping_odds_file = os.path.join(BASE_DIR, "filtered", "oran_dusen_maclar.json")
    dropping_odds = []

    if os.path.exists(dropping_odds_file):
        try:
            with open(dropping_odds_file, 'r', encoding='utf-8') as f:
                dropping_odds = json.load(f)
            print(f"✅ {len(dropping_odds)} oran düşen maç yüklendi\n")
        except Exception as e:
            print(f"⚠️ Oran düşen maçlar okunamadı: {e}\n")

    # Sadece bugünün merged dosyasını bul (Eski dosyalar karışmasın)
    today_merged_file = os.path.join(BASE_DIR, "merged", "merged_json", f"merged_{today}.json")
    merged_files = [today_merged_file] if os.path.exists(today_merged_file) else []

    if not merged_files:
        print(f"❌ Merged klasöründe JSON bulunamadı!")
        return False

    all_matches = []

    # Tüm merged dosyalarını oku
    for merged_file in merged_files:
        try:
            with open(merged_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_matches.extend(data.get('matches', []))
        except Exception as e:
            print(f"⚠️ Dosya okuma hatası ({merged_file}): {e}")

    print(f"✅ {len(all_matches)} maç yüklendi\n")

    # ===== İLK YARI GOL LİSTESİ =====
    ilk_yari_gol_listesi = []
    for match in all_matches:
        oran = match.get('beraberlik_orani')
        if oran and 3.50 <= oran <= 8.00:
            ilk_yari_gol_listesi.append({
                "event_id": match.get('event_id'),
                "home_team": match.get('home_team', ''),
                "away_team": match.get('away_team', ''),
                "league": match.get('league', ''),
                "saat": match.get('saat', ''),
                "tarih": today
            })

    # ===== GÜNÜN TERCİHLERİ =====
    gunun_tercihleri = []

    # 2.5 Üst
    ust_25_oranlari = [4.00, 4.10, 4.33, 4.50, 4.75]
    for match in all_matches:
        oran = match.get('beraberlik_orani')
        if oran in ust_25_oranlari and match.get('2_5_ust'):
            gunun_tercihleri.append({
                "event_id": match.get('event_id'),
                "home_team": match.get('home_team', ''),
                "away_team": match.get('away_team', ''),
                "league": match.get('league', ''),
                "saat": match.get('saat', ''),
                "kategori": "2.5 Üst",
                "2_5_ust": match['2_5_ust'],
                "tarih": today
            })

    # 3.5 Üst
    ust_35_oranlari = [5.00, 5.25, 5.75, 6.00, 7.00, 8.00]
    for match in all_matches:
        oran = match.get('beraberlik_orani')
        if oran in ust_35_oranlari and match.get('3_5_ust'):
            gunun_tercihleri.append({
                "event_id": match.get('event_id'),
                "home_team": match.get('home_team', ''),
                "away_team": match.get('away_team', ''),
                "league": match.get('league', ''),
                "saat": match.get('saat', ''),
                "kategori": "3.5 Üst",
                "3_5_ust": match['3_5_ust'],
                "tarih": today
            })

    # ===== GÜNÜN SÜPRİZLERİ =====
    gunun_surprizleri = []
    surpriz_oranlari = [4.50, 4.75, 5.00, 5.25, 5.75, 6.00, 7.00, 8.00]

    for match in all_matches:
        oran = match.get('beraberlik_orani')
        if oran in surpriz_oranlari and match.get('ms_5_5_ust'):
            gunun_surprizleri.append({
                "event_id": match.get('event_id'),
                "home_team": match.get('home_team', ''),
                "away_team": match.get('away_team', ''),
                "league": match.get('league', ''),
                "saat": match.get('saat', ''),
                "kategori": "MS 5.5 Üst",
                "ms_5_5_ust": match['ms_5_5_ust'],
                "tarih": today
            })

    # ===== JSON DOSYALARINA KAYDET (oddsy-data/data/) =====
    print("📁 JSON dosyaları oluşturuluyor...\n")

    # halfTimeGoals.json
    half_time_path = os.path.join(DATA_OUTPUT_DIR, 'halfTimeGoals.json')
    with open(half_time_path, 'w', encoding='utf-8') as f:
        json.dump(ilk_yari_gol_listesi, f, ensure_ascii=False, indent=2)
    print(f"  ✅ halfTimeGoals.json -> {len(ilk_yari_gol_listesi)} maç")

    # dailyChoices.json
    daily_choices_path = os.path.join(DATA_OUTPUT_DIR, 'dailyChoices.json')
    with open(daily_choices_path, 'w', encoding='utf-8') as f:
        json.dump(gunun_tercihleri, f, ensure_ascii=False, indent=2)
    print(f"  ✅ dailyChoices.json -> {len(gunun_tercihleri)} maç")

    # dailySurprises.json
    daily_surprises_path = os.path.join(DATA_OUTPUT_DIR, 'dailySurprises.json')
    with open(daily_surprises_path, 'w', encoding='utf-8') as f:
        json.dump(gunun_surprizleri, f, ensure_ascii=False, indent=2)
    print(f"  ✅ dailySurprises.json -> {len(gunun_surprizleri)} maç")

    # droppingOdds.json
    dropping_odds_path = os.path.join(DATA_OUTPUT_DIR, 'droppingOdds.json')
    with open(dropping_odds_path, 'w', encoding='utf-8') as f:
        json.dump(dropping_odds, f, ensure_ascii=False, indent=2)
    print(f"  ✅ droppingOdds.json -> {len(dropping_odds)} maç")

    print(f"\n📊 ÖZET:")
    print(f"  🔻 Oran Düşen Maçlar: {len(dropping_odds)} maç")
    print(f"  📋 İlk Yarı Gol: {len(ilk_yari_gol_listesi)} maç")
    print(f"  ⭐ Günün Tercihleri: {len(gunun_tercihleri)} maç")
    print(f"  🔥 Günün Sürprizleri: {len(gunun_surprizleri)} maç")
    print(f"  📁 Çıktı dizini: {os.path.abspath(DATA_OUTPUT_DIR)}\n")

    # Excel'e de kaydet (yedek)
    output_dir = os.path.join(BASE_DIR, "filtered")
    os.makedirs(output_dir, exist_ok=True)

    if ilk_yari_gol_listesi:
        df = pd.DataFrame(ilk_yari_gol_listesi)
        df.to_excel(f"{output_dir}/ilk_yari_gol_{today}.xlsx", index=False)

    if gunun_tercihleri:
        df = pd.DataFrame(gunun_tercihleri)
        df.to_excel(f"{output_dir}/gunun_tercihleri_{today}.xlsx", index=False)

    if gunun_surprizleri:
        df = pd.DataFrame(gunun_surprizleri)
        df.to_excel(f"{output_dir}/gunun_surprizleri_{today}.xlsx", index=False)

    return True


if __name__ == "__main__":
    import sys
    # Veri uretilemediyse exit code 1 -> pipeline sessizce "basarili" saymasin
    sys.exit(0 if filter_matches() else 1)