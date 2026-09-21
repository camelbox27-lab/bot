import json
import os

merged_files = [f for f in os.listdir('merged_json') if f.endswith('.json')]
merged_files.sort()

if merged_files:
    latest = merged_files[-1]
    with open(f'merged_json/{latest}', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f'Latest merged file: {latest}')
    print(f'Total merged: {data.get("total_merged", 0)}')
    print(f'\nFirst 5 merged matches:')
    for i, m in enumerate(data.get('matches', [])[:5], 1):
        print(f'{i}. {m.get("home_team")} vs {m.get("away_team")}')
else:
    print('No merged JSON files found')
