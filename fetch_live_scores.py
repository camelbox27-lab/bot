# fetch_live_scores.py
import requests
import json
from firebase_admin import credentials, firestore, initialize_app
import time

cred = credentials.Certificate("serviceAccountKey.json")
initialize_app(cred)
db = firestore.client()

def fetch_sofascore():
    try:
        response = requests.get('https://www.sofascore.com/api/v1/sport/football/events/live')
        data = response.json()
        
        matches = []
        for event in data.get('events', []):
            matches.append({
                'id': str(event['id']),
                'league': event['tournament']['name'],
                'country': event['tournament']['category']['name'],
                'homeTeam': event['homeTeam']['name'],
                'awayTeam': event['awayTeam']['name'],
                'homeScore': event.get('homeScore', {}).get('current', 0),
                'awayScore': event.get('awayScore', {}).get('current', 0),
                'status': event['status']['type']
            })
        
        db.collection('liveMatches').document('current').set({
            'matches': matches,
            'lastUpdate': firestore.SERVER_TIMESTAMP
        })
        
        print("Basarili! " + str(len(matches)) + " mac guncellendi")
        return True
    
    except Exception as e:
        print("Hata: " + str(e))
        return False

if __name__ == "__main__":
    print("Canli mac botu baslatildi...")
    while True:
        fetch_sofascore()
        time.sleep(30)