"""
Excel to JSON Converter - Kart & Korner Verileri
Kullanım:
    python excel_to_json.py --tip korner
    python excel_to_json.py --tip kart
    python excel_to_json.py --tip hepsi
"""

import os
import json
import argparse
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("pandas yüklü değil. Yüklemek için: pip install pandas openpyxl")
    exit(1)

# Klasör yolları (cwd degil, script konumuna gore -> baska dizinden calissa da bozulmaz)
BASE_DIR = Path(__file__).resolve().parent
KORNER_DIR = BASE_DIR / "korner"
KART_DIR = BASE_DIR / "kart"
OUTPUT_DIR = BASE_DIR / "output"

# Lig isim eşleştirmeleri (dosya adından güzel isme)
LIG_ISIMLERI = {
    "England_Premier_League": "premier_lig",
    "Spain_La_Liga": "la_liga",
    "Italy_Serie_A": "serie_a",
    "Germany_Bundesliga": "bundesliga",
    "France_Ligue_1": "ligue_1",
    "Turkey_Turkish_Super_League": "super_lig",
    # scraper.py lig adini "Turkish Super Lig" olarak seciyor -> ayni anahtara esle
    "Turkey_Turkish_Super_Lig": "super_lig",
    "Netherlands_Eredivisie": "eredivisie",
    "Portugal_Portugese_Liga_NOS": "portekiz_ligi"
}

def extract_league_name(filename: str, is_kart: bool = False) -> str:
    """Dosya adından lig ismini çıkar"""
    name = filename.replace(".xlsx", "")
    
    # KART_DATA_ prefix'ini kaldır
    if is_kart and name.startswith("KART_DATA_"):
        name = name.replace("KART_DATA_", "")
    
    # Tarih/saat kısmını kaldır (son 9 karakter: _1201_1541)
    name = "_".join(name.split("_")[:-2])
    
    return LIG_ISIMLERI.get(name, name.lower().replace(" ", "_"))

def parse_score(score_str: str) -> tuple:
    """'8 - 3' formatını (8, 3) tuple'ına çevir"""
    try:
        if pd.isna(score_str):
            return (0, 0)
        parts = str(score_str).split("-")
        if len(parts) == 2:
            return (int(parts[0].strip()), int(parts[1].strip()))
    except:
        pass
    return (0, 0)

def process_excel(file_path: str, data_type: str) -> dict:
    """Excel dosyasını işle, her sheet bir takım"""
    result = {}
    
    try:
        excel_file = pd.ExcelFile(file_path)
        
        for sheet_name in excel_file.sheet_names:
            # "Tüm Maçlar" sheet'ini atla
            if sheet_name.lower() in ["tüm maçlar", "tum maclar", "sheet1"]:
                continue
            
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Kolon isimlerini kontrol et
            if len(df.columns) < 3:
                continue
            
            # İlk 3 kolon: Tarih, Rakip, Korner/Kart
            df.columns = ["tarih", "rakip", "skor"] + list(df.columns[3:])
            
            matches = []
            for _, row in df.iterrows():
                if pd.isna(row.get("rakip")):
                    continue
                    
                takim_skor, rakip_skor = parse_score(row.get("skor", "0-0"))
                
                matches.append({
                    "rakip": str(row["rakip"]).strip(),
                    "takim": takim_skor,
                    "rakipSayi": rakip_skor
                })
            
            if matches:
                result[sheet_name.strip()] = matches
                
    except Exception as e:
        print(f"Hata ({file_path}): {e}")
    
    return result

def convert_folder(folder_path: Path, data_type: str) -> dict:
    """Klasördeki tüm Excel dosyalarını işle"""
    all_data = {}
    is_kart = (data_type == "kart")
    
    for file in folder_path.glob("*.xlsx"):
        print(f"İşleniyor: {file.name}")
        
        league_name = extract_league_name(file.name, is_kart)
        league_data = process_excel(str(file), data_type)
        
        if league_data:
            all_data[league_name] = league_data
    
    return all_data

def main():
    parser = argparse.ArgumentParser(description="Excel to JSON Converter")
    parser.add_argument("--tip", choices=["korner", "kart", "hepsi"], required=True,
                        help="Dönüştürülecek veri tipi")
    args = parser.parse_args()
    
    # Output klasörünü oluştur
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    result = {}
    
    if args.tip in ["korner", "hepsi"]:
        print("\n=== KORNER VERİLERİ ===")
        result["korner"] = convert_folder(KORNER_DIR, "korner")
        
        # Ayrı dosya olarak da kaydet
        with open(OUTPUT_DIR / "korner.json", "w", encoding="utf-8") as f:
            json.dump(result["korner"], f, ensure_ascii=False, indent=2)
        print(f"✅ Korner verileri kaydedildi: {OUTPUT_DIR / 'korner.json'}")
    
    if args.tip in ["kart", "hepsi"]:
        print("\n=== KART VERİLERİ ===")
        result["kart"] = convert_folder(KART_DIR, "kart")
        
        # Ayrı dosya olarak da kaydet
        with open(OUTPUT_DIR / "kart.json", "w", encoding="utf-8") as f:
            json.dump(result["kart"], f, ensure_ascii=False, indent=2)
        print(f"✅ Kart verileri kaydedildi: {OUTPUT_DIR / 'kart.json'}")
    
    if args.tip == "hepsi":
        # Birleşik dosya
        with open(OUTPUT_DIR / "tum_veriler.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ Tüm veriler kaydedildi: {OUTPUT_DIR / 'tum_veriler.json'}")
    
    print("\n🎉 Dönüşüm tamamlandı!")

if __name__ == "__main__":
    main()