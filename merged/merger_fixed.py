#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
from difflib import SequenceMatcher
from datetime import datetime
import glob
import pytz

class MatchMergerBot:
    def __init__(self, mackolik_folder="../mackolik-excel-json/json_output", 
                 sofascore_folder="../sofa", 
                 output_folder="merged_json"):
        self.mackolik_folder = mackolik_folder
        self.sofascore_folder = sofascore_folder
        self.output_folder = output_folder
        
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"[OK] '{output_folder}' klasoru olusturuldu")
    
    def extract_date_from_filename(self, filename):
        """sofascore_matches_2026-02-09.json -> 2026-02-09"""
        basename = os.path.basename(filename)
        # Format: sofascore_matches_2026-02-09.json
        parts = basename.replace('sofascore_matches_', '').replace('.json', '')
        return parts
    
    def similarity(self, a, b):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def normalize_team_name(self, name):
        name = name.lower().strip()
        name = name.replace("'", "").replace("-", " ").replace(".", "")
        
        replacements = {
            'fc': '', 'cf': '', 'sc': '', 'ac': '', 'as': '', 'us': '',
            'cd': '', 'ud': '', 'sd': '', 'sk': '', 'fk': '', 'ca': '',
            'athletic': 'ath', 'united': 'utd', 'sporting': 'sp',
            'olympique': 'ol', 'real': 'r', 'club': '', 'city': '',
            'town': '', 'metropolitan': 'metro',
            'phoenix': 'phx', 'wanderers': 'wand', 'rovers': 'rov',
        }
        
        for old, new in replacements.items():
            name = name.replace(f' {old} ', f' {new} ')
            name = name.replace(f' {old}', f' {new}')
            name = name.replace(f'{old} ', f'{new} ')
        
        return ' '.join(name.split())
    
    def find_best_match(self, team_name, candidates):
        normalized_team = self.normalize_team_name(team_name)
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            normalized_candidate = self.normalize_team_name(candidate)
            
            if normalized_team == normalized_candidate:
                return candidate, 1.0
            
            score = self.similarity(normalized_team, normalized_candidate)
            
            if normalized_team in normalized_candidate or normalized_candidate in normalized_team:
                score += 0.3
            
            team_words = normalized_team.split()
            candidate_words = normalized_candidate.split()
            if team_words and candidate_words and team_words[0] == candidate_words[0]:
                score += 0.2
            
            common_words = set(team_words) & set(candidate_words)
            if common_words:
                score += len(common_words) * 0.1
            
            if score > best_score:
                best_score = score
                best_match = candidate
        
        if best_score < 0.60:
            return None, best_score
        return best_match, best_score
    
    def load_json(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] JSON okuma hatasi ({file_path}): {e}")
            return None
    
    def find_sofascore_file_for_date(self, date_str):
        """Tarih string'ini (DD.MM.YYYY) -> YYYY-MM-DD'ye cevir ve matching dosya bul"""
        try:
            # DD.MM.YYYY -> YYYY-MM-DD
            parts = date_str.split('.')
            if len(parts) == 3:
                target_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:
                target_date = None
        except:
            target_date = None
        
        sofascore_files = glob.glob(os.path.join(self.sofascore_folder, "sofascore_matches_*.json"))
        
        if not sofascore_files:
            print("[ERROR] SofaScore dosyasi bulunamadi")
            return None
        
        # Exact match ixinden ariyoruz
        if target_date:
            for f in sofascore_files:
                file_date = self.extract_date_from_filename(f)
                if file_date == target_date:
                    print(f"[OK] SofaScore dosyasi bulundu: {os.path.basename(f)}")
                    return f
        
        # Fallback: most recent file
        sofascore_files.sort(reverse=True)
        print(f"[WARN] Exact date match bulunamadi, en yeni dosya kullanilacak: {os.path.basename(sofascore_files[0])}")
        return sofascore_files[0]
    
    def merge_matches(self, mackolik_file):
        try:
            if not os.path.exists(mackolik_file):
                print(f"[ERROR] Mackolik dosyasi bulunamadi: {mackolik_file}")
                return False
            
            mackolik_data = self.load_json(mackolik_file)
            if not mackolik_data:
                return False
            
            date_str = mackolik_data.get('date', 'unknown')
            
            # SofaScore dosyasini bul
            sofascore_file = self.find_sofascore_file_for_date(date_str)
            if not sofascore_file or not os.path.exists(sofascore_file):
                print(f"[ERROR] SofaScore dosyasi bulunamadi: {sofascore_file}")
                return False
            
            sofascore_data = self.load_json(sofascore_file)
            if not sofascore_data:
                return False
            
            print(f"\n[INFO] {date_str} tarihi icin eslestirme baslaniyor...")
            print(f"[INFO] Mackolik: {mackolik_data.get('total_matches', 0)} mac")
            
            if isinstance(sofascore_data, list):
                sofascore_matches = sofascore_data
            else:
                sofascore_matches = sofascore_data.get('matches', [])
            
            print(f"[INFO] SofaScore: {len(sofascore_matches)} mac")
            
            sofascore_dict = {}
            for match in sofascore_matches:
                key = f"{match['home_team']}_{match['away_team']}"
                sofascore_dict[key] = match
            
            merged_matches = []
            unmatched_mackolik = []
            
            for i, mackolik_match in enumerate(mackolik_data.get('matches', []), 1):
                home_team = mackolik_match['home_team']
                away_team = mackolik_match['away_team']
                
                best_home, home_score = self.find_best_match(
                    home_team, 
                    [m['home_team'] for m in sofascore_matches]
                )
                
                best_away, away_score = self.find_best_match(
                    away_team,
                    [m['away_team'] for m in sofascore_matches]
                )
                
                if best_home and best_away and home_score > 0.60 and away_score > 0.60:
                    sofa_key = f"{best_home}_{best_away}"
                    
                    if sofa_key in sofascore_dict:
                        sofascore_match = sofascore_dict[sofa_key]
                        
                        merged_match = {
                            'event_id': sofascore_match.get('event_id'),
                            'date_time': sofascore_match.get('date_time'),
                            'home_team': home_team,
                            'away_team': away_team,
                            'saat': mackolik_match.get('saat'),
                            'beraberlik_orani': sofascore_match.get('draw'),
                            'kg_var': mackolik_match.get('kg_var'),
                            '2_5_ust': mackolik_match.get('ust_2_5'),
                            '3_5_ust': mackolik_match.get('ust_3_5'),
                            'ms_5_5_ust': mackolik_match.get('ust_5_5'),
                        }
                        
                        merged_matches.append(merged_match)
                        
                        print(f"[MATCH] {home_team} vs {away_team}")
                    else:
                        unmatched_mackolik.append(f"{home_team} vs {away_team}")
                        print(f"[NOMATCH-KEY] {home_team} vs {away_team} (key: {sofa_key} bulunamadi)")
                else:
                    unmatched_mackolik.append(f"{home_team} vs {away_team}")
                    print(f"[NOMATCH] {home_team} vs {away_team} (home={home_score:.2f}, away={away_score:.2f})")
            
            print(f"\n[RESULT] Eslesme raporu:")
            print(f"[RESULT] Eslesilen: {len(merged_matches)}")
            print(f"[RESULT] Eslesmeyen: {len(unmatched_mackolik)}")
            
            output_data = {
                'date': date_str,
                'timestamp': datetime.now().isoformat(),
                'total_merged': len(merged_matches),
                'matches': merged_matches
            }
            
            output_file = os.path.join(self.output_folder, f"merged_{date_str}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"[OK] JSON kaydedildi: {output_file}")
            return True
        
        except Exception as e:
            print(f"[ERROR] Hata: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def merge_all_dates(self):
        try:
            tz = pytz.timezone('Europe/Istanbul')
            today = datetime.now(tz).date()
            
            mackolik_files = glob.glob(os.path.join(self.mackolik_folder, "*.json"))
            
            if not mackolik_files:
                print(f"[ERROR] Mackolik klsoeunde JSON bulunamadi!")
                return
            
            print(f"\n[INFO] {len(mackolik_files)} dosya bulundu")
            print(f"[INFO] Bugun tarihi: {today.strftime('%d.%m.%Y')}")
            print("=" * 80)
            
            success_count = 0
            skipped_count = 0
            
            for mackolik_file in sorted(mackolik_files):
                mackolik_data = self.load_json(mackolik_file)
                if not mackolik_data:
                    print(f"[SKIP] Dosya okunamadi: {os.path.basename(mackolik_file)}")
                    skipped_count += 1
                    continue
                
                date_str = mackolik_data.get('date', 'unknown')
                
                try:
                    file_date = datetime.strptime(date_str, '%d.%m.%Y').date()
                    
                    if file_date < today:
                        print(f"[SKIP] Eski tarih: {date_str} (Dosya: {os.path.basename(mackolik_file)})")
                        skipped_count += 1
                        continue
                except:
                    print(f"[SKIP] Tarih parse edilemedi: {date_str}")
                    skipped_count += 1
                    continue
                
                if self.merge_matches(mackolik_file):
                    success_count += 1
                
                print("-" * 80)
            
            print(f"\n[SUMMARY] {success_count} eslestirme basarili, {skipped_count} eski tarih atildi")
        
        except Exception as e:
            print(f"[ERROR] Hata: {e}")
            import traceback
            traceback.print_exc()

def main():
    print("\n" + "=" * 80)
    print("MERGER BOT (TARIH FILTERELI)")
    print("=" * 80)
    
    merger = MatchMergerBot(
        mackolik_folder="../mackolik-excel-json/json_output",
        sofascore_folder="../sofa",
        output_folder="merged_json"
    )
    
    merger.merge_all_dates()

if __name__ == "__main__":
    main()
