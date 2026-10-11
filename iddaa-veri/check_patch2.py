import openpyxl
from datetime import datetime

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
header = rows[0]
data = rows[1:]

iy_idx = header.index('IY Skor')
ms_idx = header.index('MS Skor')
tarih_idx = header.index('Tarih')

# 1) IY Skor bozuk (encoding sorunu - "?Y" içerenler)
iy_bozuk = [r for r in data if r[iy_idx] and '?' in str(r[iy_idx])]
iy_bozuk2 = [r for r in data if r[iy_idx] and '�' in str(r[iy_idx])]
iy_bozuk_all = [r for r in data if r[iy_idx] and not any(c.isdigit() for c in str(r[iy_idx]))]

print('=== IY SKOR SORUNU ===')
print(f'Rakam icermeyen IY Skor: {len(iy_bozuk_all)} adet')
# Ornek goster
for r in iy_bozuk_all[:5]:
    print(f'  Tarih={r[tarih_idx]}, HS={r[0]}, MS={r[1]}, IY={repr(r[iy_idx])}, MS Skor={r[ms_idx]}')

print()
# Yil bazinda dagılım
from collections import Counter
yil_bozuk = Counter()
for r in iy_bozuk_all:
    d = parse_date(r[tarih_idx])
    if d:
        yil_bozuk[d.year] += 1
    else:
        yil_bozuk['bilinmiyor'] += 1

print('IY Skor bozuk - yil dagılımı:')
for yil in sorted(yil_bozuk.keys(), key=str):
    print(f'  {yil}: {yil_bozuk[yil]} mac')

print()
print('=== MS SKOR EKSİK ("-") ===')
ms_eksik = [r for r in data if str(r[ms_idx]).strip() == '-']
print(f'MS Skor "-" olan mac sayisi: {len(ms_eksik)}')

yil_ms = Counter()
for r in ms_eksik:
    d = parse_date(r[tarih_idx])
    if d:
        yil_ms[d.year] += 1
    else:
        yil_ms['bilinmiyor'] += 1

print('MS Skor eksik - yil dagılımı:')
for yil in sorted(yil_ms.keys(), key=str):
    print(f'  {yil}: {yil_ms[yil]} mac')

print()
print('MS Skor eksik - ornek (son 5):')
for r in ms_eksik[-5:]:
    print(f'  Tarih={r[tarih_idx]}, {r[0]} vs {r[1]}, IY={r[iy_idx]}, MS={r[ms_idx]}')

wb.close()
