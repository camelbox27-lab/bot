import openpyxl
from datetime import datetime
from collections import Counter

def parse_date(d):
    if not d:
        return None
    s = str(d).strip()
    for fmt in ['%d.%m.%Y', '%m/%d/%y', '%Y-%m-%d', '%d/%m/%Y']:
        try:
            return datetime.strptime(s, fmt)
        except:
            pass
    return None

fpath = 'output/artifacts/patch/patch-clean-excel/iddaagecmismaclar_patched.xlsx'
wb = openpyxl.load_workbook(fpath, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
header = list(rows[0])
data = rows[1:]

iy_idx = header.index('IY Skor')
ms_idx = header.index('MS Skor')
tarih_idx = header.index('Tarih')
ev_idx = header.index('Ev Sahibi')
dep_idx = header.index('Deplasman')
lig_idx = header.index('Lig')
kod_idx = header.index('MS Kodu')

def is_empty(v):
    return not v or str(v).strip() in ('', '-', 'nan', 'None')

# IY encoding bozuk ama ms skor var olanlar (bunlar aslinda tamam, encoding sorunu)
iy_enc_bozuk = [r for r in data if r[iy_idx] and '?' in str(r[iy_idx]) and not is_empty(r[ms_idx])]
# IY encoding bozuk VE ms skor da yok
iy_enc_bozuk_ms_de_yok = [r for r in data if r[iy_idx] and '?' in str(r[iy_idx]) and is_empty(r[ms_idx])]
# MS skor yok (IY durumundan bagimsiz)
ms_eksik = [r for r in data if is_empty(r[ms_idx])]
# Hem IY hem MS yok
ikisi_de_yok = [r for r in data if is_empty(r[iy_idx]) and is_empty(r[ms_idx])]

print('=== GENEL DURUM ===')
print(f'Toplam mac       : {len(data):,}')
print(f'MS Skor eksik    : {len(ms_eksik):,}')
print(f'IY enc bozuk     : {len(iy_enc_bozuk):,}  (IY="?Y ..." ama MS skoru VAR)')
print(f'IY+MS ikisi eksik: {len(ikisi_de_yok):,}')
print()

# MS eksik olanlar - lig dagilimi
print('=== MS EKSİK - LİG DAĞILIMI (top 20) ===')
lig_counter = Counter(str(r[lig_idx]) for r in ms_eksik)
for lig, cnt in lig_counter.most_common(20):
    print(f'  {cnt:4d}  {lig}')

print()
print('=== MS EKSİK - YIL DAĞILIMI ===')
yil_counter = Counter()
for r in ms_eksik:
    d = parse_date(r[tarih_idx])
    yil_counter[d.year if d else 'bilinmiyor'] += 1
for yil in sorted(yil_counter.keys(), key=str):
    print(f'  {yil}: {yil_counter[yil]} mac')

print()
print('=== MS EKSİK - IY SKOR DURUMU ===')
iy_durumu = Counter()
for r in ms_eksik:
    iy_val = str(r[iy_idx]).strip() if r[iy_idx] else ''
    if not iy_val or iy_val == '-':
        iy_durumu['IY de bos'] += 1
    elif '?' in iy_val:
        iy_durumu['IY enc bozuk (?Y...)'] += 1
    else:
        iy_durumu['IY mevcut'] += 1
for k, v in iy_durumu.items():
    print(f'  {k}: {v}')

print()
print('=== IY ENCODİNG BOZUK - ORNEK (5 adet) ===')
for r in iy_enc_bozuk[:5]:
    print(f'  {r[tarih_idx]} | {r[ev_idx]} vs {r[dep_idx]} | IY={repr(r[iy_idx])} | MS={r[ms_idx]}')

wb.close()
