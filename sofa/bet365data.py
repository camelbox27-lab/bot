try:
    from curl_cffi import requests as curl_requests
    USE_CURL = True
except ImportError:
    import requests
    USE_CURL = False
    print("[WARN] curl_cffi yüklü değil, 403 alabilirsiniz. Yüklemek için: pip install curl_cffi")
import json
import pandas as pd
from datetime import datetime, timedelta
import pytz
import time
import os
from fractions import Fraction

class SofascoreScraper:
    def __init__(self):
        self.base_url = "https://api.sofascore.com/api/v1"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Origin': 'https://www.sofascore.com',
            'Referer': 'https://www.sofascore.com/',
        }
        if USE_CURL:
            self.session = curl_requests.Session(impersonate="chrome120")
        else:
            import requests as std_requests
            self.session = std_requests.Session()
        self.session.headers.update(self.headers)

    def warm_up(self):
        """Önce ana siteye gir, cookie al"""
        try:
            self.session.get("https://www.sofascore.com/", timeout=10)
            print("✅ Session hazır")
        except:
            print("⚠️ Warm-up atlandı")

    def is_allowed_league(self, league_name, country_name):
        if not league_name:
            return False

        league_lower = league_name.lower().strip()
        country_lower = country_name.lower() if country_name else ''

        allowed_combinations = {
            'australia': ['a-league men'],
            'austria': ['bundesliga', '2. liga', 'admiral bundesliga'],
            'belgium': ['pro league', 'jupiler pro league', 'challenger pro league'],
            'denmark': ['superliga', 'superligaen', '1. division'],
            'england': ['premier league', 'championship', 'efl championship'],
            'germany': ['bundesliga', '2. bundesliga'],
            'france': ['ligue 1', 'ligue 2'],
            'netherlands': ['eredivisie', 'vriendenloterij eredivisie', 'eerste divisie', 'keuken kampioen divisie'],
            'italy': ['serie a', 'serie b'],
            'spain': ['laliga', 'la liga'],
            'norway': ['eliteserien'],
            'sweden': ['allsvenskan'],
            'switzerland': ['super league', 'raiffeisen super league', 'challenge league'],
            'turkey': ['süper lig', '1. lig', 'super lig', 'trendyol süper lig'],
            'portugal': ['primeira liga', 'liga portugal', 'liga portugal 2'],
            'scotland': ['premiership', 'scottish premiership', 'championship', 'scottish championship']
        }

        european_cups = [
            'champions league', 'uefa champions league',
            'europa league', 'uefa europa league',
            'conference league', 'uefa conference league'
        ]

        for cup in european_cups:
            if cup == league_lower or cup in league_lower:
                return True

        for country, leagues in allowed_combinations.items():
            if country in country_lower:
                for allowed_league in leagues:
                    if league_lower == allowed_league:
                        return True
                    if allowed_league in league_lower:
                        if any(x in league_lower for x in ['women', 'u23', 'u21', 'reserve', 'fa cup', 'cup']):
                            continue
                        if 'laliga 2' in league_lower or 'la liga 2' in league_lower:
                            continue
                        return True

        return False

    def fractional_to_decimal(self, fractional_str):
        try:
            if not fractional_str or fractional_str == 'N/A':
                return None
            fraction = Fraction(fractional_str)
            decimal = float(fraction) + 1.0
            return round(decimal, 2)
        except:
            return None

    def get_current_date_gmt3(self):
        tz_gmt3 = pytz.timezone('Europe/Istanbul')
        now = datetime.now(tz_gmt3)
        return now.strftime('%Y-%m-%d')

    def get_timezone(self):
        return pytz.timezone('Europe/Istanbul')

    def get_match_details(self, event_id):
        url = f"{self.base_url}/event/{event_id}"
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                event = data.get('event', {})
                status_code = event.get('status', {}).get('code')
                status_type = event.get('status', {}).get('type')
                is_not_started = status_code in [0, 1] or status_type == 'notstarted'
                hs = event.get('homeScore', {})
                as_ = event.get('awayScore', {})
                return {
                    'is_not_started': is_not_started,
                    'home_score': hs.get('current') if not is_not_started else None,
                    'away_score': as_.get('current') if not is_not_started else None,
                    'home_period1': hs.get('period1', 0) or 0,
                    'away_period1': as_.get('period1', 0) or 0,
                    'home_period2': hs.get('period2', 0) or 0,
                    'away_period2': as_.get('period2', 0) or 0,
                    'status_code': status_code,
                    'status_type': status_type
                }
            return None
        except Exception as e:
            print(f"  Detay çekme hatası: {e}")
            return None

    def get_scheduled_tournament_ids(self, date, max_pages=15):
        """O gun mac oynanan turnuvalarin uniqueTournament ID'lerini doner.

        NOT: Sofascore eski toplu /sport/football/scheduled-events/{date}
        endpointini kaldirdi (404). Site artik gunun turnuva listesini cekip
        her turnuvanin maclarini ayri ayri istiyor; burada ayni akis izleniyor.
        """
        tournament_ids = []
        seen = set()
        page = 1

        while page <= max_pages:
            url = f"{self.base_url}/sport/football/scheduled-tournaments/{date}/page/{page}"
            try:
                response = self.session.get(url, timeout=15)
            except Exception as e:
                print(f"  Turnuva listesi hatasi (sayfa {page}): {e}")
                break

            if response.status_code != 200:
                if page == 1:
                    print(f"Turnuva listesi cekilemedi. Status code: {response.status_code}")
                break

            data = response.json()
            for item in data.get('scheduled', []):
                tournament = item.get('tournament', {})
                unique_tournament = tournament.get('uniqueTournament') or {}
                unique_id = unique_tournament.get('id')
                if unique_id and unique_id not in seen:
                    seen.add(unique_id)
                    tournament_ids.append(unique_id)

            if not data.get('hasNextPage'):
                break
            page += 1

        return tournament_ids

    def get_daily_matches(self, date):
        tz_gmt3 = pytz.timezone('Europe/Istanbul')
        now = datetime.now(tz_gmt3)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        tournament_ids = self.get_scheduled_tournament_ids(date)
        if not tournament_ids:
            print("Gunun turnuva listesi bos.")
            return None

        print(f"{len(tournament_ids)} turnuva bulundu, maclar cekiliyor...")

        filtered_events = []
        seen_event_ids = set()

        for idx, tournament_id in enumerate(tournament_ids, 1):
            url = f"{self.base_url}/unique-tournament/{tournament_id}/scheduled-events/{date}"
            try:
                response = self.session.get(url, timeout=15)
            except Exception:
                continue

            if response.status_code != 200:
                continue

            for event in response.json().get('events', []):
                event_id = event.get('id')
                if event_id in seen_event_ids:
                    continue

                # Sadece bugune ait maclar (turnuva endpointi komsu gunleri de dondurebiliyor)
                start_timestamp = event.get('startTimestamp')
                if not start_timestamp:
                    continue
                match_time = datetime.fromtimestamp(start_timestamp, tz_gmt3)
                if not (today_start <= match_time < tomorrow_start):
                    continue

                seen_event_ids.add(event_id)
                filtered_events.append(event)

            print(f"\r  {idx}/{len(tournament_ids)} turnuva islendi, {len(filtered_events)} mac",
                  end='', flush=True)

        print()
        return {'events': filtered_events}

    def get_all_odds_markets(self, event_id, max_retries=3):
        endpoints = [
            f"{self.base_url}/event/{event_id}/odds/1/all",
            f"{self.base_url}/event/{event_id}/markets",
        ]

        all_markets = []

        for endpoint in endpoints:
            for attempt in range(max_retries):
                try:
                    response = self.session.get(endpoint, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        if 'markets' in data:
                            all_markets.extend(data['markets'])
                        break
                    elif response.status_code == 404:
                        break
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(0.5)
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                    continue

        return {'markets': all_markets} if all_markets else None

    def parse_all_odds(self, odds_data):
        result = {
            'home_win': None, 'draw': None, 'away_win': None,
            'over_0_5': None, 'under_0_5': None,
            'over_1_5': None, 'under_1_5': None,
            'over_2_5': None, 'under_2_5': None,
            'over_3_5': None, 'under_3_5': None,
            'btts_yes': None, 'btts_no': None
        }

        if not odds_data or 'markets' not in odds_data:
            return result

        for market in odds_data['markets']:
            market_name = market.get('marketName', '').lower()
            market_id = market.get('marketId')

            if market_id == 1 or '1x2' in market_name or 'full time' in market_name:
                choices = market.get('choices', [])
                if len(choices) >= 3:
                    if choices[0].get('fractionalValue'):
                        result['home_win'] = self.fractional_to_decimal(choices[0]['fractionalValue'])
                    if choices[1].get('fractionalValue'):
                        result['draw'] = self.fractional_to_decimal(choices[1]['fractionalValue'])
                    if choices[2].get('fractionalValue'):
                        result['away_win'] = self.fractional_to_decimal(choices[2]['fractionalValue'])

            if 'over/under' in market_name or 'total' in market_name or 'goals' in market_name:
                for choice in market.get('choices', []):
                    choice_name = choice.get('name', '').lower()
                    fractional = choice.get('fractionalValue')
                    if fractional:
                        decimal = self.fractional_to_decimal(fractional)
                        for line in ['0.5', '1.5', '2.5', '3.5']:
                            if line in choice_name:
                                key = line.replace('.', '_')
                                if 'over' in choice_name:
                                    result[f'over_{key}'] = decimal
                                elif 'under' in choice_name:
                                    result[f'under_{key}'] = decimal

            if 'both teams to score' in market_name or 'btts' in market_name:
                for choice in market.get('choices', []):
                    choice_name = choice.get('name', '').lower()
                    fractional = choice.get('fractionalValue')
                    if fractional:
                        decimal = self.fractional_to_decimal(fractional)
                        if 'yes' in choice_name:
                            result['btts_yes'] = decimal
                        elif 'no' in choice_name:
                            result['btts_no'] = decimal

        return result

    def scrape_matches_with_odds(self, show_debug=True):
        current_date = self.get_current_date_gmt3()
        print(f"Tarih (GMT+3): {current_date}")
        print("Maçlar çekiliyor...")

        matches_data = self.get_daily_matches(current_date)

        if not matches_data or 'events' not in matches_data:
            print("Maç bulunamadı veya veri çekilemedi.")
            return []

        events = matches_data['events']
        print(f"Toplam {len(events)} maç bulundu.")

        all_matches = []
        skipped_no_odds = 0
        skipped_already_started = 0
        skipped_league = 0

        for idx, event in enumerate(events, 1):
            try:
                event_id = event.get('id')
                home_team = event.get('homeTeam', {}).get('name', 'N/A')
                away_team = event.get('awayTeam', {}).get('name', 'N/A')
                tournament = event.get('tournament', {}).get('name', 'N/A')
                category = event.get('tournament', {}).get('category', {}).get('name', 'N/A')

                if not self.is_allowed_league(tournament, category):
                    skipped_league += 1
                    continue

                start_timestamp = event.get('startTimestamp')
                if start_timestamp:
                    tz_gmt3 = pytz.timezone('Europe/Istanbul')
                    match_time = datetime.fromtimestamp(start_timestamp, tz_gmt3)
                    match_time_str = match_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    match_time_str = 'N/A'

                print(f"\r  {idx}/{len(events)} isleniyor...", end='', flush=True)

                match_details = self.get_match_details(event_id)

                if match_details and not match_details['is_not_started']:
                    skipped_already_started += 1
                    time.sleep(0.3)
                    continue

                odds_data = self.get_all_odds_markets(event_id)
                odds = self.parse_all_odds(odds_data)

                has_1x2 = odds['home_win'] and odds['draw'] and odds['away_win']

                if not has_1x2:
                    skipped_no_odds += 1
                    time.sleep(0.3)
                    continue

                home_team_id = event.get('homeTeam', {}).get('id')
                away_team_id = event.get('awayTeam', {}).get('id')

                match_info = {
                    'event_id': event_id,
                    'date_time': match_time_str,
                    'country': category,
                    'league': tournament,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_team_id': home_team_id,
                    'away_team_id': away_team_id,
                    'home_win': odds['home_win'],
                    'draw': odds['draw'],
                    'away_win': odds['away_win'],
                    'over_2_5': odds['over_2_5'],
                    'under_2_5': odds['under_2_5'],
                    'over_0_5': odds['over_0_5'],
                    'under_0_5': odds['under_0_5'],
                    'over_1_5': odds['over_1_5'],
                    'under_1_5': odds['under_1_5'],
                    'over_3_5': odds['over_3_5'],
                    'under_3_5': odds['under_3_5'],
                    'btts_yes': odds['btts_yes'],
                    'btts_no': odds['btts_no']
                }

                all_matches.append(match_info)

                time.sleep(0.7)

            except Exception as e:
                print(f"Hata (Event ID: {event.get('id')}): {e}")
                continue

        print(f"\n📊 Özet:")
        print(f"   Toplam maç: {len(events)}")
        print(f"   Lig filtresinden elendi: {skipped_league}")
        print(f"   Başlamış/bitti: {skipped_already_started}")
        print(f"   Oransız: {skipped_no_odds}")
        print(f"   ✅ Kaydedilen: {len(all_matches)}")

        return all_matches

    def save_to_json(self, data, filename='sofascore_matches.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ JSON kaydedildi: {filename}")

    def save_to_excel(self, data, filename='sofascore_matches.xlsx'):
        df = pd.DataFrame(data)

        column_order = [
            'event_id', 'date_time', 'country', 'league',
            'home_team', 'away_team',
            'home_win', 'draw', 'away_win',
            'over_2_5', 'under_2_5',
            'over_0_5', 'under_0_5',
            'over_1_5', 'under_1_5',
            'over_3_5', 'under_3_5',
            'btts_yes', 'btts_no'
        ]

        df = df[column_order]

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Maçlar')
            worksheet = writer.sheets['Maçlar']
            odds_columns = ['G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R']
            for col in odds_columns:
                for row in range(2, len(df) + 2):
                    cell = worksheet[f'{col}{row}']
                    cell.number_format = '0.00'

        print(f"✓ Excel kaydedildi: {filename}")

    def run(self, show_debug=True):
        print("=" * 60)
        print("SOFASCORE MAÇ VE ORAN ÇEKİCİ (LİG FİLTRELİ)")
        print("=" * 60)

        self.warm_up()
        matches = self.scrape_matches_with_odds(show_debug=show_debug)

        if not matches:
            print("\n! Kaydedilecek veri bulunamadı.")
            return False

        print(f"\n✓ Toplam {len(matches)} maç verisi çekildi.")
        print("\nDosyalar kaydediliyor...")

        current_date = self.get_current_date_gmt3()
        json_filename = f'sofascore_matches_{current_date}.json'
        excel_filename = f'sofascore_matches_{current_date}.xlsx'

        self.save_to_json(matches, json_filename)
        self.save_to_excel(matches, excel_filename)

        print("\n✅ TAMAMLANDI!")
        return True

if __name__ == "__main__":
    import sys
    scraper = SofascoreScraper()
    # Mac cekilemediyse exit code 1 -> pipeline zinciri sessizce devam etmesin
    sys.exit(0 if scraper.run() else 1)
                            
