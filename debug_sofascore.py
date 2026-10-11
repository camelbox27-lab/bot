import json

with open('sofa/sofascore_matches_2026-02-09.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("🔍 SOFASCORE'DA TURKIYE MAÇLARI:\n")
for match in data:
    if match.get('country') == 'Turkey':
        home = match.get('home_team')
        away = match.get('away_team')
        print(f"Home: '{home}' | Away: '{away}'")
        print(f"  Key olacak: '{home}_{away}'")
        print()
