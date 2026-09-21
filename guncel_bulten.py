#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MACKOLIK GUNCEL BULTEN - Tum mackolik oranlarini ceker (IY KG dahil)
JSON + Excel cikti uretir. Merger pipeline icin kullanilir.
"""
import sys, io, os, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pytz

# Otomatik tarih (GMT+3)
tz = pytz.timezone('Europe/Istanbul')
TARIH = datetime.now(tz).strftime('%Y-%m-%d')

scraper = cloudscraper.create_scraper()

# Cekilecek marketler (4,5 Alt/Ust eklendi)
ISTENEN_MARKETLER = [
    "Mac Sonucu",
    "Ilk Yari Sonucu",
    "Karsilikli Gol",
    "Cifte Sans",
    "1,5 Alt/Ust",
    "1. Yari 1,5 Alt/Ust",
    "2,5 Alt/Ust",
    "3,5 Alt/Ust",
    "4,5 Alt/Ust",
    "5,5 Alt/Ust",
    "Toplam Gol Araligi",
    "1. Yari Karsilikli Gol",
]

# Excel sutun sirasi
SUTUN_SIRASI = [
    "Saat", "Lig", "Kod", "MBS", "Ev Sahibi", "Deplasman",
    "MS 1", "MS X", "MS 2",
    "IY 1", "IY X", "IY 2",
    "KG Var", "KG Yok",
    "CS 1/X", "CS 1/2", "CS X/2",
    "IY 1,5 Alt", "IY 1,5 Ust",
    "AU 1,5 Alt", "AU 1,5 Ust",
    "AU 2,5 Alt", "AU 2,5 Ust",
    "AU 3,5 Alt", "AU 3,5 Ust",
    "AU 4,5 Alt", "AU 4,5 Ust",
    "AU 5,5 Alt", "AU 5,5 Ust",
    "TG 0-1", "TG 2-3", "TG 4-6", "TG 7+",
    "IY KG Var", "IY KG Yok",
]

# Mackolik market adi -> Excel sutun adi eslestirmesi
MARKET_MAP = {
    "Ma\u00e7 Sonucu": {"1": "MS 1", "X": "MS X", "2": "MS 2"},
    "1. Yar\u0131 Sonucu": {"1": "IY 1", "X": "IY X", "2": "IY 2"},
    "Kar\u015f\u0131l\u0131kl\u0131 Gol": {"Var": "KG Var", "Yok": "KG Yok"},
    "\u00c7ifte \u015eans": {"1-X": "CS 1/X", "1-2": "CS 1/2", "X-2": "CS X/2"},
    "1. Yar\u0131 1,5 Alt/\u00dcst": {"Alt": "IY 1,5 Alt", "\u00dcst": "IY 1,5 Ust"},
    "1,5 Alt/\u00dcst": {"Alt": "AU 1,5 Alt", "\u00dcst": "AU 1,5 Ust"},
    "2,5 Alt/\u00dcst": {"Alt": "AU 2,5 Alt", "\u00dcst": "AU 2,5 Ust"},
    "3,5 Alt/\u00dcst": {"Alt": "AU 3,5 Alt", "\u00dcst": "AU 3,5 Ust"},
    "4,5 Alt/\u00dcst": {"Alt": "AU 4,5 Alt", "\u00dcst": "AU 4,5 Ust"},
    "5,5 Alt/\u00dcst": {"Alt": "AU 5,5 Alt", "\u00dcst": "AU 5,5 Ust"},
    "Toplam Gol Aral\u0131\u011f\u0131": {
        "0-1 Gol": "TG 0-1", "2-3 Gol": "TG 2-3",
        "4-6 Gol": "TG 4-6", "7+ Gol": "TG 7+",
    },
    "1. Yar\u0131 Kar\u015f\u0131l\u0131kl\u0131 Gol": {"Var": "IY KG Var", "Yok": "IY KG Yok"},
}


def mac_listesi_cek(tarih):
    url = "https://www.mackolik.com/perform/p0/ajax/components/competition/livescores/json?"
    params = {"sports[]": "Soccer", "matchDate": tarih}
    resp = scraper.get(url, params=params).json()["data"]
    matches = resp["matches"]
    competitions = resp.get("competitions", {})

    rows = []
    for mid, mdata in matches.items():
        iddaa_code = mdata.get("iddaaCode")
        if iddaa_code is None:
            continue

        mac_adi = mdata["matchName"]
        parts = mac_adi.split(" vs ")
        ev = parts[0].strip() if len(parts) == 2 else mac_adi
        dep = parts[1].strip() if len(parts) == 2 else ""
        slug = mdata.get("matchSlug", "")

        comp_id = mdata.get("competitionId", "")
        comp = competitions.get(comp_id, {})
        lig_kodu = comp.get("code", "")

        t = pd.to_datetime(mdata["mstUtc"], unit="ms", utc=True)
        t = t.tz_convert("Europe/Istanbul")

        rows.append({
            "ID": mid,
            "Slug": slug,
            "Saat": t.strftime("%H:%M"),
            "Lig": lig_kodu,
            "Kod": iddaa_code,
            "Ev Sahibi": ev,
            "Deplasman": dep,
        })
    return pd.DataFrame(rows)


def bahis_oranlarini_cek(match_id, slug):
    url = f"https://www.mackolik.com/mac/{slug}/iddaa/{match_id}"
    try:
        r = scraper.get(url, timeout=20).text
    except Exception:
        return {}

    s = BeautifulSoup(r, "html.parser")
    ul_main = s.find("ul", {"class": "widget-iddaa-markets__markets-list"})
    if not ul_main:
        return {}

    h2_tags = ul_main.find_all("h2")
    div_tags = ul_main.find_all("div", {
        "class": "widget-base__content widget-iddaa-markets__market-content"
    })

    # MBS bilgisi
    mbs = ""
    if h2_tags:
        mbs_span = h2_tags[0].find("span", {"class": "widget-iddaa-markets__mbc"})
        if mbs_span:
            mbs_text = mbs_span.text.strip()
            m = re.search(r"\d+", mbs_text)
            mbs = m.group() if m else ""

    bahis_tipleri = [h2.find("span").text.strip() for h2 in h2_tags]
    ul_tags = [div.find("ul") for div in div_tags]

    sonuc = {"MBS": mbs}

    for idx, bahis_tipi in enumerate(bahis_tipleri):
        if bahis_tipi not in MARKET_MAP:
            continue
        if idx >= len(ul_tags) or ul_tags[idx] is None:
            continue

        mapping = MARKET_MAP[bahis_tipi]

        for li in ul_tags[idx].find_all("li"):
            spans = [sp.get_text(strip=True) for sp in li.find_all("span")]
            for k in range(0, len(spans) - 1, 2):
                label = spans[k]
                val = spans[k + 1]
                if label in mapping:
                    sonuc[mapping[label]] = val

    return sonuc


def safe_val(v):
    """Deger float'a cevir, bos/NaN ise 0 dondur."""
    if v is None or v == '':
        return 0.0
    if isinstance(v, float) and pd.isna(v):
        return 0.0
    try:
        if isinstance(v, str):
            v = v.strip().replace(',', '.')
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def main():
    print(f"\n{'='*60}")
    print(f"  MACKOLIK GUNCEL BULTEN")
    print(f"  Tarih: {TARIH}")
    print(f"{'='*60}")

    maclar = mac_listesi_cek(TARIH)
    print(f"  {len(maclar)} mac bulundu (iddaa kodlu).")

    if maclar.empty:
        print("Mac bulunamadi!")
        return False

    all_rows = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for i, row in maclar.iterrows():
            f = executor.submit(bahis_oranlarini_cek, row["ID"], row["Slug"])
            futures[f] = i

        done_count = 0
        total = len(futures)
        for f in as_completed(futures):
            idx = futures[f]
            row = maclar.loc[idx]
            oranlar = f.result()
            satir = {
                "Saat": row["Saat"],
                "Lig": row["Lig"],
                "Kod": row["Kod"],
                "Ev Sahibi": row["Ev Sahibi"],
                "Deplasman": row["Deplasman"],
            }
            satir.update(oranlar)
            all_rows.append(satir)
            done_count += 1
            print(f"\r  {done_count}/{total} mac islendi", end='', flush=True)

    df = pd.DataFrame(all_rows)

    # Sutun sirasini ayarla
    for col in SUTUN_SIRASI:
        if col not in df.columns:
            df[col] = None
    df = df[SUTUN_SIRASI]

    df.sort_values(by=["Saat", "Ev Sahibi"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # --- EXCEL KAYDET ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dosya = os.path.join(script_dir, f"guncel_bulten_{TARIH}.xlsx")
    df.to_excel(dosya, index=False, engine="openpyxl")
    print(f"\nExcel kaydedildi: {dosya} ({len(df)} mac)")

    # --- JSON KAYDET (Merger pipeline icin) ---
    json_matches = []
    for _, row in df.iterrows():
        match = {
            'home_team': str(row.get('Ev Sahibi', '')),
            'away_team': str(row.get('Deplasman', '')),
            'saat': str(row.get('Saat', '')),
            'ms_1': safe_val(row.get('MS 1')),
            'ms_x': safe_val(row.get('MS X')),
            'ms_2': safe_val(row.get('MS 2')),
            'kg_var': safe_val(row.get('KG Var')),
            'kg_yok': safe_val(row.get('KG Yok')),
            'ust_2_5': safe_val(row.get('AU 2,5 Ust')),
            'alt_2_5': safe_val(row.get('AU 2,5 Alt')),
            'ust_3_5': safe_val(row.get('AU 3,5 Ust')),
            'alt_3_5': safe_val(row.get('AU 3,5 Alt')),
            'ust_5_5': safe_val(row.get('AU 5,5 Ust')),
            'iy_kg_var': safe_val(row.get('IY KG Var')),
            'iy_kg_yok': safe_val(row.get('IY KG Yok')),
        }
        json_matches.append(match)

    date_tr = datetime.now(tz).strftime('%d.%m.%Y')
    date_compact = date_tr.replace('.', '')

    json_data = {
        'date': date_tr,
        'total_matches': len(json_matches),
        'matches': json_matches
    }

    json_dir = os.path.join(script_dir, 'mackolik-excel-json', 'json_output')
    os.makedirs(json_dir, exist_ok=True)
    json_file = os.path.join(json_dir, f'{date_compact}.json')

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    print(f"JSON kaydedildi: {json_file} ({len(json_matches)} mac)")
    print(f"\nTAMAMLANDI!")
    return True


if __name__ == "__main__":
    # Mac cekilemediyse exit code 1 -> pipeline zinciri sessizce devam etmesin
    sys.exit(0 if main() else 1)
