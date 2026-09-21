#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mackolik sayfasını Selenium'la screenshot al, EasyOCR ile metin çevir, Excel'e yaz
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import easyocr
from openpyxl import Workbook
from datetime import datetime
import time
import os

def scrape_mackolik_with_ocr():
    """Mackolik sayfasını OCR ile scrape et"""
    
    print(f"[INFO] Mackolik OCR Scraper")
    print(f"[INFO] Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
    
    driver = None
    try:
        # Selenium Chrome driver
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        print("[INFO] Browser baslatiliyor...")
        driver = webdriver.Chrome(options=options)
        driver.get("https://arsiv.mackolik.com/Genis-Iddaa-Programi")
        
        print("[INFO] Sayfa yükleniyor...")
        time.sleep(3)
        
        # Tüm sayfayı screenshot al
        screenshot_path = "mackolik_screenshot.png"
        driver.save_screenshot(screenshot_path)
        print(f"[OK] Screenshot kaydedildi: {screenshot_path}")
        
        # EasyOCR ile metin çıkar
        print("[INFO] OCR çalıştırılıyor (ilk kez uzun sürebilir)...")
        reader = easyocr.Reader(['tr', 'en'])  # Turkish + English
        
        results = reader.readtext(screenshot_path)
        print(f"[OK] OCR tamamlandı, {len(results)} text box bulundu")
        
        # OCR sonuçlarını düzenle
        extracted_text = []
        for (bbox, text, confidence) in results:
            if confidence > 0.5:  # Düşük confidence'ı filtrele
                extracted_text.append(text)
        
        print(f"[INFO] Toplam {len(extracted_text)} text çıkartıldı\n")
        
        # Satırları parse et (tab/boşluk ile ayrılmış)
        lines = []
        current_line = []
        
        for i, text in enumerate(extracted_text):
            current_line.append(text)
            
            # Her 10 element'ten sonra yeni satır
            if (i + 1) % 10 == 0:
                lines.append(current_line)
                current_line = []
        
        if current_line:
            lines.append(current_line)
        
        print(f"[INFO] {len(lines)} satır oluşturuldu\n")
        
        # Excel'e yaz
        if len(lines) > 1:
            wb = Workbook()
            ws = wb.active
            
            for row_idx, line_data in enumerate(lines, 1):
                for col_idx, value in enumerate(line_data, 1):
                    try:
                        # Sayıya çevirmeye çalış
                        if '.' in value and len(value) < 10:
                            value = float(value)
                        elif ':' not in value:
                            value = int(value) if value.isdigit() else value
                    except:
                        pass
                    
                    ws.cell(row=row_idx, column=col_idx, value=value)
            
            # Dosya kaydet
            filename = 'gunlukmaclar.xlsx'
            wb.save(filename)
            print(f"[OK] Excel kaydedildi: {filename}")
            print(f"[SUCCESS] OCR ile {len(lines)} satir, {len(lines[0]) if lines else 0} sutun islendu!\n")
            
            return True
        else:
            print("[ERROR] Yeterince veri yok!")
            return False
            
    except Exception as e:
        print(f"[ERROR] Hata: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if driver:
            driver.quit()
            print("[INFO] Browser kapatildi")

if __name__ == "__main__":
    success = scrape_mackolik_with_ocr()
    exit(0 if success else 1)
