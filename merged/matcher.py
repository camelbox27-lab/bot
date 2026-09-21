#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DEBUG: Merger Test Script - Emojisiz"""
import json
import sys
sys.path.insert(0, '.')

from match_merger_bot import MatchMergerBot

merger = MatchMergerBot()

# Test data load
mackolik_data = merger.load_json("../mackolik-excel-json/json_output/09022026.json")
sofascore_data = merger.load_json("../sofa/sofascore_matches_2026-02-09.json")

if not mackolik_data or not sofascore_data:
    print("ERROR: could not load files")
    sys.exit(1)

# Get sofascore matches
if isinstance(sofascore_data, list):
    sofascore_matches = sofascore_data
else:
    sofascore_matches = sofascore_data.get('matches', [])

print(f"Mackolik: {mackolik_data.get('total_matches')} matches")
print(f"Sofascore: {len(sofascore_matches)} matches\n")

# Create dict
sofascore_dict = {}
for match in sofascore_matches:
    key = f"{match['home_team']}_{match['away_team']}"
    sofascore_dict[key] = match

# Test Turkey matches
turkey_keywords = ['gaziantep', 'fenerbahçe', 'kayserispor', 'kasim', 'sakaryaspor', 'erzurum', 'gençler']

merged_count = 0
for i, mackolik_match in enumerate(mackolik_data.get('matches', []), 1):
    home_team = mackolik_match['home_team']
    away_team = mackolik_match['away_team']
    
    # Check if Turkey match
    is_turkey = any(kw in f"{home_team}_{away_team}".lower() for kw in turkey_keywords)
    
    best_home, home_score = merger.find_best_match(home_team, [m['home_team'] for m in sofascore_matches])
    best_away, away_score = merger.find_best_match(away_team, [m['away_team'] for m in sofascore_matches])
    
    if is_turkey:
        match_status = "MATCH" if (best_home and best_away and home_score > 0.60 and away_score > 0.60) else "NO_MATCH"
        print(f"[{i:2}] {home_team:20} vs {away_team:20} | {match_status}")
        print(f"      home: '{best_home}' ({home_score:.2f}) | away: '{best_away}' ({away_score:.2f})")
        
        if best_home and best_away and home_score > 0.60 and away_score > 0.60:
            sofa_key = f"{best_home}_{best_away}"
            if sofa_key in sofascore_dict:
                merged_count += 1
                print(f"      KEY FOUND: {sofa_key}")
        print()

print(f"\nTurkey matches merged: {merged_count}")
