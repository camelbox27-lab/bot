from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import sys
import pandas as pd
import time
from datetime import datetime
import os
import re

# Veri tipine gore kaynak sayfa ve etiketler
DATA_TYPES = {
    'kart': {
        'url': 'https://www.adamchoi.co.uk/cards/detailed',
        'emoji': '🟨',
        'label': 'KART',
    },
    'korner': {
        'url': 'https://www.adamchoi.co.uk/corners/detailed',
        'emoji': '🚩',
        'label': 'KORNER',
    },
}


def scrape_league_cards(driver, wait, country, league_name, is_turkey=False, data_type='kart'):
    """Belirli bir lig icin kart/korner verilerini ceker"""
    cfg = DATA_TYPES[data_type]
    print(f"\n{'='*60}")
    print(f"{cfg['emoji']} {country} - {league_name} {cfg['label']} VERİSİ İŞLENİYOR...")
    print(f"{'='*60}")

    max_retries = 3 if not is_turkey else 5  # Türkiye için daha fazla deneme
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Her denemede sayfayı yenile
            print("🔄 Sayfa yenileniyor...")
            driver.get(cfg['url'])
            time.sleep(5)

            print(f"\r  [Deneme {retry_count + 1}/{max_retries}] 🌍 {country} / ⚽ {league_name} araniyor... ", end='', flush=True)

            # Ülke seç
            time.sleep(2)
            
            country_select = Select(wait.until(EC.presence_of_element_located((By.ID, 'country'))))
            
            # Ülke seç
            country_found = False
            for option in country_select.options:
                option_text = option.text.strip()
                if country.lower() == option_text.lower() or country.lower() in option_text.lower():
                    country_select.select_by_visible_text(option_text)
                    country_found = True
                    break
            
            if not country_found:
                country_select.select_by_visible_text(country)
            
            wait_time = 5 if is_turkey else 3
            time.sleep(wait_time)
            
            # Lig seç
            league_select = Select(wait.until(EC.presence_of_element_located((By.ID, 'league'))))
            
            # Lig ismini esnek şekilde bul
            league_found = False
            for option in league_select.options:
                option_text = option.text.strip()
                if not option_text:
                    continue
                
                # Türkiye için özel kontrol
                if is_turkey:
                    if ('turkish' in option_text.lower() and 'super' in option_text.lower()) or \
                       ('turkish' in option_text.lower() and 'lig' in option_text.lower()) or \
                       'süper lig' in option_text.lower():
                        league_select.select_by_visible_text(option_text)
                        league_found = True
                        break
                else:
                    # Diğer ligler için
                    if league_name.lower() in option_text.lower():
                        league_select.select_by_visible_text(option_text)
                        league_found = True
                        break
            
            if not league_found:
                league_select.select_by_visible_text(league_name)
            
            wait_time = 8 if is_turkey else 6
            time.sleep(wait_time)
            
            # Tabloyu kontrol et
            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

            if len(rows) == 0:
                print(f"⚠️ Veri bulunamadı, tekrar deneniyor...")
                retry_count += 1
                continue

            raw_data = []
            seen_matches = set()
            
            for idx, row in enumerate(rows):
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cols) == 5:
                        tarih_idx, ev_idx, skor_idx, dep_idx = 0, 1, 2, 3
                    elif len(cols) >= 6:
                        tarih_idx, ev_idx, skor_idx, dep_idx = 0, 2, 3, 4
                    else:
                        continue
                    
                    tarih = cols[tarih_idx].get_attribute("textContent").strip()
                    ev = cols[ev_idx].get_attribute("textContent").strip()
                    skor = cols[skor_idx].get_attribute("textContent").strip()
                    dep = cols[dep_idx].get_attribute("textContent").strip()
                    
                    if not tarih or not ev or not dep or not skor:
                        continue
                    
                    ev_kart = ""
                    dep_kart = ""
                    if " - " in skor:
                        parts = skor.split(" - ")
                        if len(parts) == 2:
                            ev_kart = parts[0].strip()
                            dep_kart = parts[1].strip()
                    elif "-" in skor:
                        parts = skor.split("-")
                        if len(parts) == 2:
                            ev_kart = parts[0].strip()
                            dep_kart = parts[1].strip()
                    
                    if ev_kart and dep_kart:
                        match_key = f"{tarih}_{ev}_{dep}_{ev_kart}_{dep_kart}"
                        if match_key not in seen_matches:
                            seen_matches.add(match_key)
                            raw_data.append({
                                'Tarih': tarih,
                                'Ev Sahibi': ev,
                                'Ev Kart': ev_kart,
                                'Deplasman': dep,
                                'Dep Kart': dep_kart
                            })
                            
                            pass
                except:
                    continue

            if not raw_data:
                print(f"❌ {league_name} için veri bulunamadı!")
                retry_count += 1
                time.sleep(3)
                continue

            df = pd.DataFrame(raw_data)
            print(f"✅ {len(df)} maç çekildi!")
            
            return df
            
        except Exception as e:
            print(f"❌ Deneme {retry_count + 1} başarısız: {e}")
            retry_count += 1
            if retry_count < max_retries:
                print(f"🔄 {max_retries - retry_count} deneme hakkı kaldı...")
                time.sleep(5)
            else:
                print(f"❌ {country} - {league_name} için tüm denemeler başarısız!")
                import traceback
                traceback.print_exc()
                return None
    
    return None


def create_card_excel(df, country, league_name, data_type='kart'):
    """Kart/korner verisinden Excel dosyası oluşturur"""

    all_teams = sorted(set(df['Ev Sahibi'].unique()) | set(df['Deplasman'].unique()))

    # Dosya adı oluştur
    safe_name = re.sub(r'[\\/*?:\[\]]', '', f"{country}_{league_name}").replace(' ', '_')
    # excel_to_json.py kart/ ve korner/ klasorlerinden okuyor -> cwd'ye degil oraya yaz
    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base_dir, data_type)
    os.makedirs(out_dir, exist_ok=True)
    # kart dosyalari KART_DATA_ prefixli (excel_to_json bunu bekliyor), korner prefixsiz
    prefix = 'KART_DATA_' if data_type == 'kart' else ''
    file_name = os.path.join(
        out_dir,
        f"{prefix}{safe_name}_{datetime.now().strftime('%d%m_%H%M')}.xlsx"
    )

    print(f"✅ Excel kaydedildi: {file_name}")

    # Sutun basligi veri tipine gore (excel_to_json ilk 3 kolonu konuma gore okur)
    value_col = 'Kart' if data_type == 'kart' else 'Korner'

    with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
        # Tüm maçlar sayfası
        df_all = df.copy()
        df_all[value_col] = df_all['Ev Kart'] + ' - ' + df_all['Dep Kart']
        df_all_sorted = df_all.sort_values('Tarih', ascending=False)
        df_all_sorted[['Tarih', 'Ev Sahibi', value_col, 'Deplasman']].to_excel(
            writer, sheet_name='Tüm Maçlar', index=False
        )
        
        # Her takım için ayrı sayfa
        for team in all_teams:
            if not team or len(team.strip()) == 0:
                continue
            
            team_matches = []
            
            # İç saha maçları
            home = df[df['Ev Sahibi'] == team].copy()
            for _, match in home.iterrows():
                team_matches.append({
                    'Tarih': match['Tarih'],
                    'Rakip': match['Deplasman'],
                    'Kart': f"{match['Ev Kart']} - {match['Dep Kart']}"
                })
            
            # Dış saha maçları
            away = df[df['Deplasman'] == team].copy()
            for _, match in away.iterrows():
                team_matches.append({
                    'Tarih': match['Tarih'],
                    'Rakip': match['Ev Sahibi'],
                    'Kart': f"{match['Dep Kart']} - {match['Ev Kart']}"
                })
            
            # Tarihe göre sırala
            team_df = pd.DataFrame(team_matches)
            team_df = team_df.sort_values('Tarih', ascending=False).reset_index(drop=True)
            
            # Excel sekme ismi temizleme
            clean_name = re.sub(r'[\\/*?:\[\]]', '', team)[:30].strip()
            if not clean_name:
                clean_name = "Team_Data"

            team_df.to_excel(writer, sheet_name=clean_name, index=False)
        
    return file_name


def scrape_all_cards(data_types=('kart', 'korner')):
    """Tüm ligler için kart ve korner verilerini çeker"""

    # Ligler listesi (Ülke, Lig Adı, Türkiye mi?)
    leagues = [
        ('England', 'Premier League', False),
        ('Germany', 'Bundesliga', False),
        ('Italy', 'Serie A', False),
        ('France', 'Ligue 1', False),
        ('Spain', 'La Liga', False),
        ('Turkey', 'Turkish Super Lig', True),  # Türkiye bayrağı!
        ('Netherlands', 'Eredivisie', False),
        ('Portugal', 'Portugese Liga NOS', False)
    ]

    chrome_options = Options()
    chrome_options.add_argument('--start-maximized')
    # Cloud/Server settings
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 25)

    created_files = []
    failed_leagues = []

    try:
        for data_type in data_types:
            cfg = DATA_TYPES[data_type]
            print(f"\n🌐 {cfg['label']} VERİSİ SAYFASINA GİDİLİYOR...")
            driver.get(cfg['url'])
            time.sleep(4)

            for country, league, is_turkey in leagues:
                df = scrape_league_cards(driver, wait, country, league, is_turkey, data_type)

                if df is not None and len(df) > 0:
                    file_name = create_card_excel(df, country, league, data_type)
                    created_files.append(file_name)

                    if is_turkey:
                        print("\n" + "🇹🇷"*20)
                        print("TÜRKİYE BAŞARIYLA TAMAMLANDI!")
                        print("🇹🇷"*20 + "\n")
                else:
                    print(f"⚠️ {country} - {league} atlandı (veri yok)")
                    failed_leagues.append(f"[{data_type}] {country} - {league}")

                time.sleep(4)  # Ligler arası daha uzun bekleme

            print(f"\n{'='*60}")
            print(f"🎉 TÜM LİGLER {cfg['label']} VERİSİ TAMAMLANDI!")
            print(f"{'='*60}")

        print(f"\n📊 Oluşturulan Dosyalar ({len(created_files)}):")
        for i, file in enumerate(created_files, 1):
            emoji = "🇹🇷" if "Turkey" in file else "⚽"
            print(f"  {emoji} {i}. {os.path.basename(file)}")

        if failed_leagues:
            print(f"\n⚠️ Başarısız Ligler ({len(failed_leagues)}):")
            for i, league in enumerate(failed_leagues, 1):
                print(f"  {i}. {league}")
        else:
            print(f"\n✨✨✨ TAMAMI BAŞARILI - HİÇ HATA YOK! ✨✨✨")

        return len(created_files) > 0

    except Exception as e:
        print(f"\n❌ GENEL HATA: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("\n🔒 Tarayıcı kapatılıyor...")
        driver.quit()
        print("✅ İşlem tamamlandı!")


if __name__ == "__main__":
    # Hicbir dosya uretilemediyse exit code 1 -> pipeline bunu gorsun
    sys.exit(0 if scrape_all_cards() else 1)