import openpyxl

fpath = 'output/artifacts/patch/patch-clean-excel/iddaagecmismaclar_patched.xlsx'
wb = openpyxl.load_workbook(fpath, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
header = rows[0]
data = rows[1:]

# Kolon indekslerini bul
iy_skor_idx = header.index('IY Skor') if 'IY Skor' in header else None
ms_skor_idx = header.index('MS Skor') if 'MS Skor' in header else None

print('IY Skor kolonu:', iy_skor_idx)
print('MS Skor kolonu:', ms_skor_idx)
print('Toplam mac:', len(data))
print()

# IY Skor bos olan maclar
iy_bos = [r for r in data if not r[iy_skor_idx] or str(r[iy_skor_idx]).strip() in ('', '-', 'None')]
ms_bos = [r for r in data if not r[ms_skor_idx] or str(r[ms_skor_idx]).strip() in ('', '-', 'None')]

print(f'IY Skor BOZUK/EKSIK olan mac sayisi: {len(iy_bos)}')
print(f'MS Skor BOZUK/EKSIK olan mac sayisi: {len(ms_bos)}')
print()

# IY skor degerlerini say (bozuk format varsa goster)
from collections import Counter
iy_vals = Counter()
for r in data:
    v = str(r[iy_skor_idx]).strip() if r[iy_skor_idx] else 'BOŞ'
    # IY skor formatı genelde "X-X" olmalı
    if not any(c.isdigit() for c in v):
        iy_vals[v] += 1

print('IY Skor - gecersiz degerler (rakam icermeyenler):')
for v, c in iy_vals.most_common(20):
    print(f'  {repr(v)}: {c} adet')

print()
ms_vals = Counter()
for r in data:
    v = str(r[ms_skor_idx]).strip() if r[ms_skor_idx] else 'BOŞ'
    if not any(c.isdigit() for c in v):
        ms_vals[v] += 1

print('MS Skor - gecersiz degerler:')
for v, c in ms_vals.most_common(20):
    print(f'  {repr(v)}: {c} adet')

wb.close()
