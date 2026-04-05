#!/usr/bin/env python3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import csv
import time

print("🚀 YANGILANGAN 1 MILLION ROW GENERATOR")
print("=" * 80)
print("📊 7 ta parametr bilan:")
print("  1. Harorat (°C)")
print("  2. Tok kuchi (A)")
print("  3. Kuchlanish (V)")
print("  4. Vibratsiya")
print("  5. Simlarning mexanik holati (0-100%)")
print("  6. Atrof-muhit sharoitlari (Humidity %)")
print("  7. Quvvati (kW)")
print("=" * 80)

districts_data = {
    "Tashkent_City": (41.3646, 69.2603),
    "Chilonzor": (41.2897, 69.1640),
    "Yunusobod": (41.3442, 69.3230),
    "Mirabad": (41.2550, 69.2240),
    "Shayxontohur": (41.3050, 69.2780),
    "Uchtepa": (41.3850, 69.2100),
    "Sergeli": (41.2145, 69.2850),
    "Bektemir": (41.4100, 69.1500),
    "Olmazor": (41.3648, 69.3480)
}

TOTAL_ROWS = 1000000
BATCH_SIZE = 50000

start_time = time.time()
district_names = list(districts_data.keys())
base_time = datetime.now()

print(f"\n📝 {TOTAL_ROWS:,} ta row generate qilmoqda...\n")

with open('sensor_monitoring_1M.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    # Headers
    writer.writerow([
        'District', 'Latitude', 'Longitude',
        'Harorat (C)', 'Tok_kuchi (A)', 'Kuchlanish (V)', 'Vibratsiya',
        'Sim_mexanik_holati (%)', 'Atrof_muhit_humidity (%)', 'Quvvati (kW)',
        'Fault', 'Timestamp'
    ])

    for batch in range(0, TOTAL_ROWS, BATCH_SIZE):
        batch_data = []
        for i in range(batch, min(batch + BATCH_SIZE, TOTAL_ROWS)):
            dist = district_names[i % len(district_names)]
            lat_c, lon_c = districts_data[dist]

            # Generate values
            harorat = round(np.random.uniform(10, 50), 1)
            tok = round(np.random.uniform(5, 25), 2)
            kuchlanish = round(np.random.uniform(200, 240), 1)
            vibratsiya = round(np.random.uniform(0.05, 2.0), 4)
            sim_holati = round(np.random.uniform(70, 100), 1)  # 70-100% healthy
            humidity = round(np.random.uniform(30, 90), 1)
            quvvat = round(tok * kuchlanish / 1000, 2)  # P = I * V / 1000 kW

            # Fault detection logic
            fault = 0
            if harorat > 45 or harorat < 15:
                fault = 1
            if tok > 22 or tok < 8:
                fault = 1
            if kuchlanish < 210 or kuchlanish > 235:
                fault = 1
            if vibratsiya > 1.8:
                fault = 1
            if sim_holati < 75:
                fault = 1
            if humidity > 85 or humidity < 35:
                fault = 1

            row = [
                dist,
                round(np.random.uniform(lat_c - 0.05, lat_c + 0.05), 6),
                round(np.random.uniform(lon_c - 0.05, lon_c + 0.05), 6),
                harorat,
                tok,
                kuchlanish,
                vibratsiya,
                sim_holati,
                humidity,
                quvvat,
                int(fault),
                (base_time + timedelta(minutes=i)).isoformat()
            ]
            batch_data.append(row)

        writer.writerows(batch_data)

        if (batch // BATCH_SIZE + 1) % 10 == 0:
            elapsed = time.time() - start_time
            rows_done = min(batch + BATCH_SIZE, TOTAL_ROWS)
            rate = rows_done / elapsed
            eta = (TOTAL_ROWS - rows_done) / rate if rate > 0 else 0
            print(f"  ✓ {rows_done:,} / {TOTAL_ROWS:,} | {rate:.0f} rows/sec | ETA: {eta:.0f}s")

elapsed = time.time() - start_time
print(f"\n{'='*80}")
print(f"✅ TAYYOR!")
print(f"{'='*80}")
print(f"📁 Fayl: sensor_monitoring_1M.csv")
print(f"📊 Rowlar: {TOTAL_ROWS:,}")
print(f"🏙️  Tumanlar: {len(districts_data)}")
print(f"⏱️  Vaqt: {elapsed:.1f} sekund")
print(f"🚀 Tezlik: {TOTAL_ROWS/elapsed:.0f} rows/sec")
print(f"{'='*80}")
