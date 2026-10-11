"""
ANA KONTROL SCRIPTI - Tüm İşlemleri Sırayla Çalıştırır
Kullanım: python main.py
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

def print_header(text):
    """Başlık yazdır"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

SCRIPT_DIR = Path(__file__).resolve().parent


def run_script(script_name, args=None):
    """Script'i çalıştır ve sonucu döndür"""
    try:
        cmd = [sys.executable, str(SCRIPT_DIR / script_name)]
        if args:
            cmd.extend(args)

        print(f"🚀 Çalıştırılıyor: {script_name}")
        start_time = time.time()

        # cwd sabitlenir, boylece pipeline baska dizinden tetiklense de yollar dogru kalir
        result = subprocess.run(cmd, check=True, capture_output=False, text=True,
                                cwd=str(SCRIPT_DIR))

        elapsed = time.time() - start_time
        print(f"✅ {script_name} tamamlandı ({elapsed:.1f} saniye)")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ {script_name} HATA: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ {script_name} bulunamadı!")
        return False
    except Exception as e:
        print(f"❌ Beklenmeyen hata ({script_name}): {e}")
        return False

def check_files():
    required_files = [
        "scraper.py",
        "excel_to_json.py"
    ]
    
    missing = []
    for file in required_files:
        if not (SCRIPT_DIR / file).exists():
            missing.append(file)
    
    if missing:
        print("❌ Eksik dosyalar:")
        for f in missing:
            print(f"   - {f}")
        return False
    
    print("✅ Tüm scriptler mevcut")
    return True

def main():
    print_header("🎯 KART & KORNER VERİ İŞLEME PIPELINE")
    print(f"⏰ Başlangıç: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
    
    # Dosya kontrolü
    if not check_files():
        print("\n❌ Gerekli dosyalar eksik! İşlem iptal edildi.")
        return False

    results = {}
    
    # ADIM 1: Web Scraping (Kart & Korner Verileri)
    print_header("ADIM 1/3: WEB SCRAPING")
    print("📊 adamchoi.co.uk'dan veriler çekiliyor...")
    results['scraper'] = run_script("scraper.py")
    
    if not results['scraper']:
        print("\n⚠️ Scraping başarısız oldu!")
        # CI ortamında user input beklenmemeli, o yüzden direkt devam edilmeli mi yoksa durmalı mı?
        # Kullanıcı "PC kapalı" dediği için muhtemelen gözetimsiz çalışması lazım. 
        # Scraping olmazsa diğer adımlar da olmaz, o yüzden çıkmak mantıklı.
        print("❌ Scraping başarısız olduğu için diğer adımlar iptal ediliyor.")
        return False

    time.sleep(2)
    
    # ADIM 2: Excel → JSON Dönüşümü
    print_header("ADIM 2/3: EXCEL → JSON DÖNÜŞÜMÜ")
    print("📄 Excel dosyaları JSON formatına çevriliyor...")
    results['converter'] = run_script("excel_to_json.py", ["--tip", "hepsi"])
    
    if not results['converter']:
        print("\n❌ JSON dönüşümü başarısız! Firebase yüklemesi yapılamaz.")
        print_summary(results)
        return False

    time.sleep(2)
    
    # ADIM 3: Verileri oddsy-data'ya Kopyala
    print_header("ADIM 3/3: DOSYALARI TAŞIMA")
    print("☁️ Veriler oddsy-data reposuna kopyalanıyor...")
    
    # oddsy-data yolu: CI'da bot/oddsy-data, lokalde TahminApp/oddsy-data
    script_dir = SCRIPT_DIR
    bot_dir = script_dir.parent
    ci_path = bot_dir / "oddsy-data"
    local_path = bot_dir.parent / "oddsy-data"
    oddsy_data_dir = ci_path if ci_path.exists() else local_path

    # Frontend data/ altindan okuyor (src/components/Kart.jsx, Korner.jsx)
    target_dir = oddsy_data_dir / "data"

    if not oddsy_data_dir.exists():
        print(f"\n⚠️ oddsy-data klasörü bulunamadı yol: {oddsy_data_dir}")
        results['copy'] = False
    else:
        try:
            import shutil
            target_dir.mkdir(parents=True, exist_ok=True)
            output_dir = script_dir / "output"
            copied = 0
            for name in ("kart.json", "korner.json"):
                src = output_dir / name
                if not src.exists():
                    print(f"⚠️ {name} uretilmemis, kopyalanmadi")
                    continue
                # Bos/bozuk JSON'u siteye tasima
                try:
                    with open(src, encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    print(f"❌ {name} okunamadi, kopyalanmadi: {e}")
                    continue
                if not data:
                    print(f"❌ {name} bos, kopyalanmadi (site verisi korundu)")
                    continue
                shutil.copy2(src, target_dir / name)
                print(f"✅ {name} kopyalandı: {target_dir}")
                copied += 1
            results['copy'] = copied == 2
        except Exception as e:
            print(f"❌ Kopyalama hatası: {e}")
            results['copy'] = False
            
    # ÖZET
    print_summary(results)
    return all(results.get(k, False) for k in ('scraper', 'converter', 'copy'))

def print_summary(results):
    """İşlem özetini yazdır"""
    print_header("📋 İŞLEM ÖZETİ")
    
    steps = [
        ("Web Scraping", results.get('scraper', False)),
        ("JSON Dönüşümü", results.get('converter', False)),
        ("Dosya Kopyalama (Odds-Data)", results.get('copy', False))
    ]
    
    for step_name, success in steps:
        status = "✅ BAŞARILI" if success else "❌ BAŞARISIZ"
        print(f"   {step_name:20s} : {status}")
    
    success_count = sum(1 for _, success in steps if success)
    total = len(steps)
    
    print(f"\n📊 Sonuç: {success_count}/{total} adım başarılı")
    
    if success_count == total:
        print("\n🎉 TÜM İŞLEMLER TAMAMLANDI!")
    elif success_count > 0:
        print("\n⚠️ Bazı işlemler başarısız oldu.")
    else:
        print("\n❌ Hiçbir işlem tamamlanamadı!")
    
    print(f"\n⏰ Bitiş: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 70)

if __name__ == "__main__":
    try:
        # Basarisizlikta exit code 1 -> cagiran pipeline/CI hatayi gorebilsin
        sys.exit(0 if main() else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ İşlem kullanıcı tarafından durduruldu (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)