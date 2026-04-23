#!/usr/bin/env python3
"""
Toshkent shahari barcha 12 tumani uchun sensor ma'lumotlari generatori.
1000 ta sensor, 2024-01-01 dan bugungi kungacha.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

print("=" * 70)
print("🚀 TOSHKENT MONITORING DATA GENERATOR (1000 sensor, 12 tuman)")
print("=" * 70)

# --- Toshkent shahrining barcha 12 tumani — haqiqiy geografik bounding-box ---
# (lat_min, lat_max, lon_min, lon_max) — real tuman o'lchamiga mos
DISTRICTS = {
    "Bektemir":        (41.265, 41.310, 69.330, 69.395),   # Kichik, janubi-sharq
    "Chilonzor":       (41.260, 41.330, 69.140, 69.215),   # Katta, g'arb
    "Mirabad":         (41.255, 41.300, 69.195, 69.260),   # O'rta, markaziy janub
    "Mirobod":         (41.270, 41.315, 69.240, 69.295),   # Kichik, markaziy
    "Mirzo Ulug'bek":  (41.305, 41.395, 69.330, 69.400),   # Katta, shimoli-sharq
    "Olmazor":         (41.330, 41.395, 69.215, 69.295),   # Katta, shimol
    "Sergeli":         (41.170, 41.260, 69.240, 69.340),   # Eng katta, janub
    "Shayxontohur":    (41.285, 41.335, 69.245, 69.305),   # O'rta, markaziy
    "Uchtepa":         (41.285, 41.365, 69.150, 69.230),   # Katta, g'arb
    "Yakkasaroy":      (41.270, 41.310, 69.195, 69.245),   # Kichik, markaziy-g'arb
    "Yashnobod":       (41.215, 41.275, 69.270, 69.355),   # O'rta, janubi-sharq
    "Yunusobod":       (41.315, 41.390, 69.285, 69.375),   # Katta, shimoli-sharq
}

N_DISTRICTS = len(DISTRICTS)
N_SENSORS = 1200          # ~100 ta sensor har bir tumanda
SENSORS_PER_DISTRICT = N_SENSORS // N_DISTRICTS
READINGS_PER_SENSOR = 1000  # har bir sensor uchun o'lchovlar soni

START_DATE = datetime(2024, 1, 1)
END_DATE   = datetime.now()

rng = np.random.default_rng(42)

district_list  = list(DISTRICTS.keys())
district_coords = list(DISTRICTS.values())

print(f"📍 Tumanlar: {N_DISTRICTS} ta")
print(f"📡 Sensorlar: ~{N_SENSORS} ta (~{SENSORS_PER_DISTRICT} har bir tumanda)")
print(f"📅 Davr: {START_DATE.date()} — {END_DATE.date()}")
print(f"📊 Jami taxminiy rows: {N_SENSORS * READINGS_PER_SENSOR:,}")
print()

all_rows = []

sensor_counter = 1
for d_idx, (district, (lat_min, lat_max, lon_min, lon_max)) in enumerate(DISTRICTS.items()):
    print(f"  [{d_idx+1}/{N_DISTRICTS}] {district} — ", end="", flush=True)
    
    n_sensors_here = SENSORS_PER_DISTRICT + (1 if d_idx < N_SENSORS % N_DISTRICTS else 0)
    
    for s in range(n_sensors_here):
        sensor_id = f"S{sensor_counter:04d}"
        sensor_counter += 1
        
        # Sensorning aniq koordinatasi — haqiqiy tuman chegaralari ichida
        lat = round(float(rng.uniform(lat_min, lat_max)), 6)
        lon = round(float(rng.uniform(lon_min, lon_max)), 6)
        
        # Sensor uchun tasodifiy vaqtlar (to'g'ri tartiblangan)
        seconds_range = int((END_DATE - START_DATE).total_seconds())
        offsets = np.sort(rng.integers(0, seconds_range, size=READINGS_PER_SENSOR))
        timestamps = [START_DATE + timedelta(seconds=int(o)) for o in offsets]
        
        # Sensor "sog'liq" ehtimoli (ba'zi sensorlar ko'proq buziladi)
        fault_prob = rng.uniform(0.02, 0.20)  # 2-20% buzilish ehtimoli
        
        for ts in timestamps:
            # Mavsum ta'siri (qish: past harorat, yoz: yuqori harorat)
            month = ts.month
            season_factor = np.sin((month - 3) * np.pi / 6)  # yozda maksimal
            
            # Asosiy parametrlar (normal taqsimot)
            harorat    = round(float(rng.normal(25 + 15 * season_factor, 5)), 1)
            shamol     = round(float(abs(rng.normal(8, 4))), 1)
            chastota   = round(float(rng.normal(50.0, 0.3)), 2)
            kuchlanish = round(float(rng.normal(220, 8)), 1)
            vibratsiya = round(float(abs(rng.normal(0.5, 0.25))), 4)
            sim_holati = round(float(np.clip(rng.normal(88, 6), 60, 100)), 1)
            humidity   = round(float(np.clip(rng.normal(60, 15), 25, 95)), 1)
            quvvat     = round(float(abs(rng.normal(3.5, 0.8))), 2)
            
            # Qiymatlarni chegaralash
            harorat    = float(np.clip(harorat, -5, 55))
            shamol     = float(np.clip(shamol, 0, 40))
            chastota   = float(np.clip(chastota, 48.0, 52.0))
            kuchlanish = float(np.clip(kuchlanish, 195, 245))
            vibratsiya = float(np.clip(vibratsiya, 0.01, 2.5))
            quvvat     = float(np.clip(quvvat, 0.5, 7.0))
            
            # Fault aniqlash (3 daraja: 0-normal, 1-ogohlantirish, 2-xavfli)
            fault = 0
            danger_count = 0
            warn_count   = 0
            
            if kuchlanish < 200 or kuchlanish > 240: danger_count += 1
            elif kuchlanish < 210 or kuchlanish > 230: warn_count += 1
            
            if chastota < 49.0 or chastota > 51.0: danger_count += 1
            elif chastota < 49.5 or chastota > 50.5: warn_count += 1
            
            if harorat > 45: danger_count += 1
            elif harorat > 40: warn_count += 1
            
            if vibratsiya > 1.5: danger_count += 1
            elif vibratsiya > 1.0: warn_count += 1
            
            if sim_holati < 75: danger_count += 1
            elif sim_holati < 85: warn_count += 1
            
            if humidity < 30 or humidity > 90: warn_count += 1
            if quvvat > 5.5: danger_count += 1
            elif quvvat > 5.0: warn_count += 1
            
            # Tasodifiy buzilish (sensor fault_prob ga qarab)
            if rng.random() < fault_prob:
                if rng.random() < 0.4:
                    danger_count += 1
                else:
                    warn_count += 1
            
            if danger_count >= 1:
                fault = 2
            elif warn_count >= 1:
                fault = 1
            
            all_rows.append({
                "Timestamp":               ts.strftime("%Y-%m-%d %H:%M:%S"),
                "SensorID":                sensor_id,
                "District":                district,
                "Latitude":                round(lat, 6),
                "Longitude":               round(lon, 6),
                "Muhit_harorat (C)":       harorat,
                "Shamol_tezligi (km/h)":   shamol,
                "Chastota (Hz)":           chastota,
                "Kuchlanish (V)":          kuchlanish,
                "Vibratsiya":              vibratsiya,
                "Sim_mexanik_holati (%)":  sim_holati,
                "Atrof_muhit_humidity (%)": humidity,
                "Quvvati (kW)":            quvvat,
                "Fault":                   fault,
            })
    
    print(f"{n_sensors_here} sensor ✓")

print(f"\n✅ Jami {len(all_rows):,} ta row yaratildi")
print("📁 DataFrame yaratilmoqda...")

df = pd.DataFrame(all_rows)
df = df.sort_values(["SensorID", "Timestamp"]).reset_index(drop=True)

# Ikkita qismga bo'lish
half = len(df) // 2
df1 = df.iloc[:half]
df2 = df.iloc[half:]

os.makedirs("data", exist_ok=True)

print("💾 data/sensor_data_part1.csv yozilmoqda...")
df1.to_csv("data/sensor_data_part1.csv", index=False)
print(f"   ✅ {len(df1):,} rows yozildi")

print("💾 data/sensor_data_part2.csv yozilmoqda...")
df2.to_csv("data/sensor_data_part2.csv", index=False)
print(f"   ✅ {len(df2):,} rows yozildi")

print("\n📊 XULOSA:")
print(f"   Jami sensors  : {df['SensorID'].nunique()}")
print(f"   Jami districts: {df['District'].nunique()}")
print(f"   Districts list: {sorted(df['District'].unique().tolist())}")
print(f"   Min vaqt      : {df['Timestamp'].min()}")
print(f"   Max vaqt      : {df['Timestamp'].max()}")
print(f"   Fault=0 (normal)    : {(df['Fault']==0).sum():,} ({100*(df['Fault']==0).mean():.1f}%)")
print(f"   Fault=1 (ogohlant.) : {(df['Fault']==1).sum():,} ({100*(df['Fault']==1).mean():.1f}%)")
print(f"   Fault=2 (xavfli)    : {(df['Fault']==2).sum():,} ({100*(df['Fault']==2).mean():.1f}%)")
print("\n🎉 Tayyor! endi: python train_model.py")
