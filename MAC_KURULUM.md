# Mac'te Kurulum ve Çalıştırma

Bu bot macOS'ta **çift tıklayarak** çalıştırılır. Windows'taki `BOTU_CALISTIR.bat`
dosyasının Mac karşılığı `BOTU_CALISTIR.command` dosyasıdır.

## 1. Repoyu klonla

Terminal'i aç (Spotlight → "Terminal") ve şunu yapıştır:

```bash
cd ~/Desktop
git clone https://github.com/camelbox27-lab/bot.git
```

Bu, Masaüstüne `bot` adında bir klasör oluşturur.

## 2. Python kurulu mu kontrol et

```bash
python3 --version
```

Bir sürüm numarası görüyorsan hazırsın. "command not found" diyorsa Python kur:

```bash
brew install python3
```

(Homebrew yoksa: https://www.python.org/downloads/ adresinden indir.)

## 3. Çift tıklayarak çalıştır

Finder'da `bot` klasörünü aç ve **`BOTU_CALISTIR.command`** dosyasına çift tıkla.
Terminal açılır, gerekli paketleri ilk seferde otomatik kurar ve bot çalışır.

### "İzin verilmedi" hatası alırsan

Klonlama sırasında çalıştırma izni kaybolmuş olabilir. Terminal'de bir kez çalıştır:

```bash
chmod +x ~/Desktop/bot/BOTU_CALISTIR.command
```

### "Apple kötü amaçlı yazılım taraması yapamadı" uyarısı

macOS internetten inen scriptleri ilk açılışta engeller. Çözüm:

- Dosyaya **sağ tıkla → Aç** (çift tıklama yerine), sonra **Aç** butonuna bas.
- Bu sadece ilk seferde gerekir; sonraki açılışlarda çift tıklama yeterli.

## Notlar

- **`oddsy-data` push adımı:** Script, bot klasörünün yanında `oddsy-data`
  klasörü ararsa oraya push eder. Yoksa bu adımı atlar ve sadece veri çeker —
  hata vermez. Push de isteniyorsa `oddsy-data` reposu `bot` ile aynı dizine
  klonlanmalı:

  ```
  Desktop/
    ├── bot/
    └── oddsy-data/
  ```

- **Firebase anahtarı repoda yok** (güvenlik nedeniyle). Firebase'e yazan
  adımlar (`istatistik/upload_to_firebase.py`) anahtar olmadan çalışmaz.
  Gerekiyorsa `serviceAccountKey.json` dosyası ayrıca, güvenli bir kanaldan
  paylaşılmalı — GitHub üzerinden **gönderilmemeli**.

- **Kart & korner istatistikleri** ana pipeline'a dahil değil. Elle çalıştır:

  ```bash
  cd ~/Desktop/bot/istatistik && python3 main.py
  ```
