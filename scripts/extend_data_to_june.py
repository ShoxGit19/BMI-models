"""
Sensor ma'lumotlarini 2026-06-26 gacha uzaytirish.
Har sensor uchun oxirgi yozuv vaqtidan shu kungacha ~20 soatlik oraliqda yangi yozuvlar.
Ishlatish: python scripts/extend_data_to_june.py
"""
import pandas as pd
import numpy as np
import datetime
import os
import sys

TARGET_DATE = datetime.datetime(2026, 6, 26, 23, 59, 0)
INTERVAL_HOURS = 20          # O'rtacha oraliq
PARQUET_PATH   = "data/sensor_data.parquet"

print("Mavjud ma'lumotlar yuklanmoqda...")
df = pd.read_parquet(PARQUET_PATH, engine="pyarrow")

# category → str
for col in ("District", "SensorID"):
    if str(df[col].dtype) == "category":
        df[col] = df[col].astype(str)

df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
print(f"Jami: {len(df):,} satr | Sensorlar: {df['SensorID'].nunique()} ta")
print(f"Oxirgi sana: {df['Timestamp'].max()}")

# Har sensor uchun so'nggi holat
latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()

# Ustunlar
PARAM_COLS = [
    "Muhit_harorat (C)", "Shamol_tezligi (km/h)", "Chastota (Hz)",
    "Kuchlanish (V)", "Vibratsiya", "Sim_mexanik_holati (%)",
    "Atrof_muhit_humidity (%)", "Quvvati (kW)"
]

# Iyun — Toshkent yozgi chegaralar
JUNE_PARAMS = {
    "Muhit_harorat (C)":      (32.0, 5.0,  20.0, 45.0),   # mean, std, min, max
    "Shamol_tezligi (km/h)":  (8.0,  4.0,  0.5,  28.0),
    "Chastota (Hz)":          (50.0, 0.15, 49.2, 50.8),
    "Kuchlanish (V)":         (220.0,6.0,  195.0,242.0),
    "Vibratsiya":             (0.55, 0.3,  0.05, 1.8),
    "Sim_mexanik_holati (%)": (85.0, 8.0,  60.0, 99.0),
    "Atrof_muhit_humidity (%)": (22.0,8.0, 8.0,  50.0),
    "Quvvati (kW)":           (3.2,  1.2,  0.5,  6.5),
}

# Global statistika (existing data asosida)
global_stats = {}
for col in PARAM_COLS:
    s = df[col].dropna()
    global_stats[col] = {
        "mean": float(s.mean()),
        "std":  max(float(s.std()), 0.01),
        "min":  float(s.quantile(0.01)),
        "max":  float(s.quantile(0.99)),
    }

rng = np.random.default_rng(42)

def gen_fault(n):
    """Raw Fault taqsimoti: ~36% safe, ~54% warn, ~10% danger"""
    r = rng.random(n)
    return np.where(r < 0.36, 0, np.where(r < 0.90, 1, 2)).astype(np.int8)

def gen_param(col, last_val, n, season="june"):
    if season == "june":
        m, s, lo, hi = JUNE_PARAMS.get(col, (
            global_stats[col]["mean"],
            global_stats[col]["std"],
            global_stats[col]["min"],
            global_stats[col]["max"]
        ))
    else:
        m  = global_stats[col]["mean"]
        s  = global_stats[col]["std"]
        lo = global_stats[col]["min"]
        hi = global_stats[col]["max"]

    # AR(1) jarayon — oldingi qiymatdan silliq o'zgarish
    vals = np.empty(n)
    cur = last_val if last_val is not None and not np.isnan(last_val) else m
    for i in range(n):
        noise = rng.normal(0, s * 0.12)
        revert = (m - cur) * 0.07   # Ortaga tortish
        cur = cur + revert + noise
        cur = float(np.clip(cur, lo, hi))
        vals[i] = cur
    return vals

new_rows = []
sensors = latest["SensorID"].tolist()
print(f"\nYangi yozuvlar yaratilmoqda ({len(sensors)} sensor)...")

for i, sid in enumerate(sensors):
    row = latest[latest["SensorID"] == sid].iloc[0]
    last_ts = row["Timestamp"]

    # Vaqt nuqtalarini yaratish
    ts = last_ts + pd.Timedelta(hours=INTERVAL_HOURS)
    timestamps = []
    while ts <= TARGET_DATE:
        jitter = pd.Timedelta(minutes=int(rng.integers(-90, 90)))
        timestamps.append(ts + jitter)
        ts += pd.Timedelta(hours=INTERVAL_HOURS)

    n = len(timestamps)
    if n == 0:
        continue

    # Parametr qiymatlari
    params = {}
    for col in PARAM_COLS:
        params[col] = gen_param(col, row.get(col), n)

    faults = gen_fault(n)

    chunk = pd.DataFrame({
        "Timestamp":  timestamps,
        "SensorID":   [str(row["SensorID"])] * n,
        "District":   [str(row["District"])] * n,
        "Latitude":   [float(row["Latitude"])] * n,
        "Longitude":  [float(row["Longitude"])] * n,
        **{col: params[col] for col in PARAM_COLS},
        "Fault":      faults,
    })
    new_rows.append(chunk)

    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(sensors)} sensor OK")

print("\nYangi ma'lumotlar birlashtirilmoqda...")
new_df  = pd.concat(new_rows, ignore_index=True)
full_df = pd.concat([df, new_df], ignore_index=True)
full_df  = full_df.sort_values(["SensorID", "Timestamp"]).reset_index(drop=True)

print(f"Yangi satrlar: {len(new_df):,}")
print(f"Jami satrlar: {len(full_df):,}")
print(f"Yangi oxirgi sana: {full_df['Timestamp'].max()}")

# Rounding
for col in PARAM_COLS:
    if col in ("Chastota (Hz)", "Vibratsiya"):
        full_df[col] = full_df[col].round(3)
    else:
        full_df[col] = full_df[col].round(1)

# Saqlash
print("\nParquet ga saqlanmoqda...")
full_df.to_parquet(PARQUET_PATH, engine="pyarrow", index=False, compression="snappy")

# CSV ni ham yangilash
for part, chunk_df in enumerate(
    [full_df.iloc[:len(full_df)//2], full_df.iloc[len(full_df)//2:]], start=1
):
    chunk_df.to_csv(f"data/sensor_data_part{part}.csv", index=False)

print(f"\nTayyor!")
print(f"   Parquet: {os.path.getsize(PARQUET_PATH) / 1024 / 1024:.1f} MB")
print(f"   Yangi sana oralig'i: {new_df['Timestamp'].min()} → {new_df['Timestamp'].max()}")
print(f"   Fault: safe={int((new_df['Fault']==0).sum())}, "
      f"warn={int((new_df['Fault']==1).sum())}, "
      f"danger={int((new_df['Fault']==2).sum())}")
