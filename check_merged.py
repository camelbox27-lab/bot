import json

with open('merged_json/merged_09.02.2026.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total merged: {data['total_merged']}")
print("\nMatches:")
for i, m in enumerate(data['matches'], 1):
    print(f"{i:2d}. {m['home_team']:30s} vs {m['away_team']:30s}")
