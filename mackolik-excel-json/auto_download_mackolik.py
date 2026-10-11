#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mackolik'ten POST request göndererek Excel indir (Otomatik)
"""
import requests
from datetime import datetime
import time

def download_mackolik_excel():
    """Mackolik'ten Excel dosyasını indir"""
    
    print(f"[INFO] Mackolik'ten Excel indiriliyor...")
    print(f"[INFO] Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
    
    try:
        # Mackolik'in form POST endpoint'i
        url = "https://arsiv.mackolik.com/Genis-Iddaa-Programi"
        
        # Headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # POST datası (form parametreleri)
        data = {
            'export': 'excel'
        }
        
        print("[INFO] Excel export request gönderiliyor...")
        
        # POST request yap
        response = requests.post(url, data=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Dosya türünü kontrol et
            content_type = response.headers.get('content-type', '')
            
            if 'spreadsheet' in content_type or 'excel' in content_type:
                # Excel dosyası kaydet
                filename = 'gunlukmaclar.xlsx'
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                print(f"[OK] Excel indirildi: {filename}")
                print(f"[OK] Dosya boyutu: {file_size} bytes")
                print(f"[SUCCESS] Mackolik verisi basarili sekilde indirildi!\n")
                return True
            else:
                print(f"[WARN] Content-Type: {content_type}")
                print(f"[INFO] Dosya kaydediliyor (unknown format)...")
                
                # Yine de kaydet
                filename = 'gunlukmaclar.xlsx'
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                print(f"[OK] Dosya kaydedildi: {filename}\n")
                return True
        else:
            print(f"[ERROR] HTTP Error: {response.status_code}")
            
            # Download link'i direkt dene
            print("[INFO] Alternatif: Direct download linki deneniyor...\n")
            
            # Alternatif URL'ler
            alt_urls = [
                "https://arsiv.mackolik.com/Genis-Iddaa-Programi?export=excel",
                "https://arsiv.mackolik.com/api/export/excel",
                "https://arsiv.mackolik.com/download/matches.xlsx"
            ]
            
            for alt_url in alt_urls:
                try:
                    print(f"[INFO] Deneniyor: {alt_url}")
                    alt_response = requests.get(alt_url, headers=headers, timeout=15)
                    
                    if alt_response.status_code == 200 and len(alt_response.content) > 1000:
                        filename = 'gunlukmaclar.xlsx'
                        with open(filename, 'wb') as f:
                            f.write(alt_response.content)
                        
                        print(f"[OK] Dosya indirildi: {filename}\n")
                        return True
                except:
                    continue
            
            print("[ERROR] Excel indirilemiyor!")
            return False
    
    except requests.exceptions.Timeout:
        print("[ERROR] Timeout - Mackolik'e baglanamadi (cok yavaş)")
        return False
    except requests.exceptions.ConnectionError:
        print("[ERROR] Connection Error - Internet baglantisiniz kontrol edin")
        return False
    except Exception as e:
        print(f"[ERROR] Hata: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = download_mackolik_excel()
    exit(0 if success else 1)
