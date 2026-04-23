#!/usr/bin/env python3
"""
Toshkent tumanlari uchun sensorlar koordinatalarini haqiqiy geografik chegaralarga
mos ravishda yangilaydi.  CSV fayllar in-place o'zgartiriladi.
"""
import numpy as np
import pandas as pd
import os

# --- Har bir tumanning haqiqiy bounding-box chegaralari ---
# (lat_min, lat_max, lon_min, lon_max)
# Toshkent shahri geografiyasiga mos, har bir tumanchi haqiqiy o'lchamiga qarab
DISTRICT_BOUNDS = {
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

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
PART1 = os.path.join(DATA_DIR, 'sensor_data_part1.csv')
PART2 = os.path.join(DATA_DIR, 'sensor_data_part2.csv')

print("=" * 60)
print("Koordinatalarni yangilash boshlanmoqda...")
print("=" * 60)

rng = np.random.default_rng(99)

frames = []
for path in [PART1, PART2]:
    print(f"\n  Yuklanmoqda: {os.path.basename(path)}")
    df = pd.read_csv(path)
    frames.append(df)

full_df = pd.concat(frames, ignore_index=True)

# Har bir sensor uchun bir marta koordinata belgilash
sensor_coords = {}
for sensor_id, grp in full_df.groupby("SensorID"):
    district = grp["District"].iloc[0]
    if district not in DISTRICT_BOUNDS:
        print(f"  [SKIP] Noma'lum tuman: {district}")
        continue
    lat_min, lat_max, lon_min, lon_max = DISTRICT_BOUNDS[district]
    lat = round(float(rng.uniform(lat_min, lat_max)), 6)
    lon = round(float(rng.uniform(lon_min, lon_max)), 6)
    sensor_coords[sensor_id] = (lat, lon)

# Koordinatalarni to'g'irdan-to'g'ri yangilash
updated = 0
for sensor_id, (lat, lon) in sensor_coords.items():
    mask = full_df["SensorID"] == sensor_id
    full_df.loc[mask, "Latitude"]  = lat
    full_df.loc[mask, "Longitude"] = lon
    updated += 1

print(f"\n  {updated} ta sensor koordinatasi yangilandi")

# CSV fayllarni qayta yozish (original hajmga mos bo'linib)
n1 = len(pd.read_csv(PART1))
part1_new = full_df.iloc[:n1].reset_index(drop=True)
part2_new = full_df.iloc[n1:].reset_index(drop=True)

part1_new.to_csv(PART1, index=False)
part2_new.to_csv(PART2, index=False)
print(f"  {os.path.basename(PART1)}: {len(part1_new):,} qator saqlandi")
print(f"  {os.path.basename(PART2)}: {len(part2_new):,} qator saqlandi")

# Tekshirish
print("\nNatija — tumanlardagi tarqalish:")
check = full_df.groupby("SensorID")[["Latitude","Longitude","District"]].first()
for d, grp in check.groupby("District"):
    lat_s = round(grp["Latitude"].max() - grp["Latitude"].min(), 4)
    lon_s = round(grp["Longitude"].max() - grp["Longitude"].min(), 4)
    bounds = DISTRICT_BOUNDS.get(d, ("?",)*4)
    expected_lat = round(bounds[1] - bounds[0], 4) if d in DISTRICT_BOUNDS else "?"
    expected_lon = round(bounds[3] - bounds[2], 4) if d in DISTRICT_BOUNDS else "?"
    print(f"  {d:20s}  tarqalish: lat={lat_s:.4f}/{expected_lat}  lon={lon_s:.4f}/{expected_lon}")

print("\nTayyor! Flask serverni qayta ishga tushiring.")
