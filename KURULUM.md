# Bot Kurulumu (Mac)

## Gereksinimler
- Python 3.11 (3.13 KULLANMA - paketler uyumsuz)
- git

## Klasor yerlesimi

Bu repo ile `oddsy-data` YAN YANA olmali:

```
Desktop/
├── oddsy-bot/      <- bu repo
└── oddsy-data/     <- veri reposu
```

## Kurulum

```bash
cd ~/Desktop
git clone <bu-repo-url> oddsy-bot
git clone https://github.com/camelbox27-lab/oddsy-data.git

cd oddsy-bot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Calistirma

```bash
cd ~/Desktop/oddsy-bot
source venv/bin/activate
python main.py
```

Pipeline biter bitmez `oddsy-data` reposuna otomatik push eder,
site birkac dakika icinde guncellenir.

## Sorun giderme

**"oddsy-data klasoru bulunamadi"**
-> Iki klasor yan yana degil. Yerlesime bak.

**Git push sifre soruyor**
-> GitHub kullanici adi + Personal Access Token gir (sifre degil).

**Her seferinde sifre sormasin**
```bash
git config --global credential.helper osxkeychain
```
