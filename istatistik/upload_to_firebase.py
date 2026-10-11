"""
Firebase'e JSON Yükleme Scripti
Kullanım: python upload_to_firebase.py
"""

import json
from pathlib import Path

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    print("Firebase Admin SDK yüklü değil!")
    print("Yüklemek için: pip install firebase-admin")
    exit(1)

# Dosya yolları
BASE_DIR = Path("output")
KORNER_FILE = BASE_DIR / "korner.json"
KART_FILE = BASE_DIR / "kart.json"

def initialize_firebase():
    """Firebase'i başlat"""
    
    # Service account key dosyası
    key_path = Path("firebase-key.json")
    
    if not key_path.exists():
        print("❌ firebase-key.json bulunamadı!")
        print("\n📝 Yapılacaklar:")
        print("1. GitHub Secrets > FIREBASE_KEY ekle")
        print("2. Dosyayı 'firebase-key.json' olarak kaydet")
        # Eğer serviceAccountKey varsa onu dene (yerel testler için)
        if Path("serviceAccountKey.json").exists():
            print("   (serviceAccountKey.json bulundu, o kullanılıyor...)")
            key_path = Path("serviceAccountKey.json")
        else:
            exit(1)

    
    try:
        cred = credentials.Certificate(str(key_path))
        firebase_admin.initialize_app(cred)
        print("✅ Firebase bağlantısı başarılı!")
        return firestore.client()
    except Exception as e:
        print(f"❌ Firebase başlatma hatası: {e}")
        exit(1)

def upload_data(db, collection_name: str, document_id: str, file_path: Path):
    """JSON dosyasını Firebase'e yükle"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n📤 Yükleniyor: {document_id}")
        print(f"   Dosya: {file_path.name}")
        print(f"   Boyut: {file_path.stat().st_size / 1024:.1f} KB")
        
        # Firestore'a yükle
        doc_ref = db.collection(collection_name).document(document_id)
        doc_ref.set({"data": data})
        
        print(f"✅ {document_id} başarıyla yüklendi!")
        
    except Exception as e:
        print(f"❌ Yükleme hatası ({document_id}): {e}")

def main():
    print("=" * 50)
    print("🔥 FIREBASE UPLOAD BAŞLIYOR")
    print("=" * 50)
    
    # Firebase'i başlat
    db = initialize_firebase()
    
    # Collection adı
    collection_name = "kartKornerData"
    
    # Korner verilerini yükle
    if KORNER_FILE.exists():
        upload_data(db, collection_name, "korner", KORNER_FILE)
    else:
        print(f"⚠️ {KORNER_FILE} bulunamadı!")
    
    # Kart verilerini yükle
    if KART_FILE.exists():
        upload_data(db, collection_name, "kart", KART_FILE)
    else:
        print(f"⚠️ {KART_FILE} bulunamadı!")
    
    print("\n" + "=" * 50)
    print("🎉 YÜKLEME TAMAMLANDI!")
    print("=" * 50)
    print(f"\n📍 Firestore Yolu:")
    print(f"   Collection: {collection_name}")
    print(f"   Documents: korner, kart")

if __name__ == "__main__":
    main()