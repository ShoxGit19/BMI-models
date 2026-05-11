#!/usr/bin/env python3
"""
update_and_forecast.py

Ikki vazifa:
  1. Gap to'ldirish  — May 11 gacha bo'lgan bo'sh kunlarni sensor
                       tarixiy statistikasi asosida to'ldiradi va
                       CSV + Parquet fayllarini yangilaydi.
  2. 7 kunlik prognoz — May 12-18 uchun har bir sensor bo'yicha
                       hamma 8 ta parametr + Fault qiymatlari bilan
                       data/forecast_7day.csv ga saqlaydi.
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ──────────────────────────────────────────────────────────────
# SOZLAMALAR
# ──────────────────────────────────────────────────────────────
DATA_DIR        = "data"
PART1_CSV       = os.path.join(DATA_DIR, "sensor_data_part1.csv")
PART2_CSV       = os.path.join(DATA_DIR, "sensor_data_part2.csv")
PARQUET_FILE    = os.path.join(DATA_DIR, "sensor_data.parquet")
FORECAST_CSV    = os.path.join(DATA_DIR, "forecast_7day.csv")

GAP_END         = datetime(2026, 5, 11, 23, 59, 59)   # bugun oxiri
FORECAST_DAYS   = 7
FORECAST_START  = datetime(2026, 5, 12)
FORECAST_END    = FORECAST_START + timedelta(days=FORECAST_DAYS - 1)
GAP_READINGS_PER_DAY = 4   # har 6 soatda bir o'lchov

FEATURE_COLS = [
    "Muhit_harorat (C)",
    "Shamol_tezligi (km/h)",
    "Chastota (Hz)",
    "Kuchlanish (V)",
    "Vibratsiya",
    "Sim_mexanik_holati (%)",
    "Atrof_muhit_humidity (%)",
    "Quvvati (kW)",
]

# Maylik mavsumiy moslashuv (bahor-yoz o'tish)
# sin((5-3)*pi/6) ≈ 0.866  →  harorat yuqoriroq, namlik biroz yuqori
MAY_SEASON = float(np.sin((5 - 3) * np.pi / 6))

rng = np.random.default_rng(2026)

print("=" * 65)
print("  SENSOR DATA YANGILASH + 7 KUNLIK PROGNOZ")
print("=" * 65)

# ──────────────────────────────────────────────────────────────
# 1. MA'LUMOT YUKLASH
# ──────────────────────────────────────────────────────────────
print("\n[1/4] Mavjud ma'lumotlar yuklanmoqda...")
if os.path.exists(PARQUET_FILE):
    df = pd.read_parquet(PARQUET_FILE, engine="pyarrow")
    print(f"      Parquet: {len(df):,} qator")
else:
    df1 = pd.read_csv(PART1_CSV)
    df2 = pd.read_csv(PART2_CSV)
    df  = pd.concat([df1, df2], ignore_index=True)
    print(f"      CSV: {len(df):,} qator")

df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
df = df.dropna(subset=["Timestamp"])

print(f"      Sensorlar : {df['SensorID'].nunique()}")
print(f"      Vaqt oralig'i: {df['Timestamp'].min().date()} → {df['Timestamp'].max().date()}")

# Har bir sensorning meta ma'lumotlari (ID, District, lat, lon) — bitta qatordan
sensor_meta = (
    df.sort_values("Timestamp")
      .groupby("SensorID", as_index=False)
      .last()[["SensorID", "District", "Latitude", "Longitude"]]
)

# ──────────────────────────────────────────────────────────────
# YORDAMCHI: Fault aniqlash (generate_data.py mantiqiga mos)
# ──────────────────────────────────────────────────────────────
def compute_fault(v, hz, temp, vib, sim, hum, pw):
    danger = warn = 0
    if v < 200 or v > 240:  danger += 1
    elif v < 210 or v > 230: warn += 1
    if hz < 49.0 or hz > 51.0: danger += 1
    elif hz < 49.5 or hz > 50.5: warn += 1
    if temp > 45: danger += 1
    elif temp > 40: warn += 1
    if vib > 1.5: danger += 1
    elif vib > 1.0: warn += 1
    if sim < 75: danger += 1
    elif sim < 85: warn += 1
    if hum < 30 or hum > 90: warn += 1
    if pw > 5.5: danger += 1
    elif pw > 5.0: warn += 1
    return 2 if danger >= 1 else (1 if warn >= 1 else 0)

def vfault(rows: pd.DataFrame) -> np.ndarray:
    return np.array([
        compute_fault(r.v, r.hz, r.temp, r.vib, r.sim, r.hum, r.pw)
        for r in rows.itertuples()
    ])

# ──────────────────────────────────────────────────────────────
# YORDAMCHI: Sensor statistikasi (30 kunlik oyna)
# ──────────────────────────────────────────────────────────────
WINDOW_DAYS = 30
window_start = df["Timestamp"].max() - timedelta(days=WINDOW_DAYS)
recent = df[df["Timestamp"] >= window_start].copy()

# Har bir sensor uchun: mean va std
stats = (
    recent.groupby("SensorID")[FEATURE_COLS]
    .agg(["mean", "std"])
)
stats.columns = ["_".join(c) for c in stats.columns]

# Fallback: butun dataframe statistikasi (yangi sensorlar uchun)
global_mean = df[FEATURE_COLS].mean()
global_std  = df[FEATURE_COLS].std().clip(lower=0.01)

def sensor_stats(sid):
    if sid in stats.index:
        row = stats.loc[sid]
        means = {c: row[f"{c}_mean"] for c in FEATURE_COLS}
        stds  = {c: max(row[f"{c}_std"], 0.01) for c in FEATURE_COLS}
    else:
        means = global_mean.to_dict()
        stds  = global_std.to_dict()
    return means, stds

# ──────────────────────────────────────────────────────────────
# 2. GAP TO'LDIRISH (Apr 23 → May 11)
# ──────────────────────────────────────────────────────────────
print("\n[2/4] Gap to'ldirilmoqda (Apr 23 → May 11)...")

# Har bir sensorning oxirgi timestamp'i
last_ts = (
    df.sort_values("Timestamp")
      .groupby("SensorID")["Timestamp"]
      .last()
)

gap_rows = []

for sid, last in last_ts.items():
    if last >= GAP_END:
        continue  # bu sensor allaqachon yangilangan

    meta_row = sensor_meta[sensor_meta["SensorID"] == sid]
    if meta_row.empty:
        continue
    district = meta_row["District"].values[0]
    lat      = float(meta_row["Latitude"].values[0])
    lon      = float(meta_row["Longitude"].values[0])

    means, stds = sensor_stats(sid)

    # Gap davomida har 6 soatda bir o'lchov
    cur = last + timedelta(hours=6)
    while cur <= GAP_END:
        month = cur.month
        season = float(np.sin((month - 3) * np.pi / 6))

        temp = float(np.clip(rng.normal(means["Muhit_harorat (C)"] + 2 * season,
                                        stds["Muhit_harorat (C)"]), -5, 55))
        wind = float(np.clip(abs(rng.normal(means["Shamol_tezligi (km/h)"],
                                            stds["Shamol_tezligi (km/h)"])), 0, 40))
        hz   = float(np.clip(rng.normal(means["Chastota (Hz)"],
                                        stds["Chastota (Hz)"]), 48.0, 52.0))
        v    = float(np.clip(rng.normal(means["Kuchlanish (V)"],
                                        stds["Kuchlanish (V)"]), 195, 245))
        vib  = float(np.clip(abs(rng.normal(means["Vibratsiya"],
                                            stds["Vibratsiya"])), 0.01, 2.5))
        sim  = float(np.clip(rng.normal(means["Sim_mexanik_holati (%)"],
                                        stds["Sim_mexanik_holati (%)"]), 60, 100))
        hum  = float(np.clip(rng.normal(means["Atrof_muhit_humidity (%)"] + season * 3,
                                        stds["Atrof_muhit_humidity (%)"]), 25, 95))
        pw   = float(np.clip(abs(rng.normal(means["Quvvati (kW)"],
                                            stds["Quvvati (kW)"])), 0.5, 7.0))
        fault = compute_fault(v, hz, temp, vib, sim, hum, pw)

        gap_rows.append({
            "Timestamp":                cur.strftime("%Y-%m-%d %H:%M:%S"),
            "SensorID":                 sid,
            "District":                 district,
            "Latitude":                 round(lat, 6),
            "Longitude":                round(lon, 6),
            "Muhit_harorat (C)":        round(temp, 1),
            "Shamol_tezligi (km/h)":    round(wind, 1),
            "Chastota (Hz)":            round(hz, 2),
            "Kuchlanish (V)":           round(v, 1),
            "Vibratsiya":               round(vib, 4),
            "Sim_mexanik_holati (%)":   round(sim, 1),
            "Atrof_muhit_humidity (%)": round(hum, 1),
            "Quvvati (kW)":             round(pw, 2),
            "Fault":                    fault,
        })
        cur += timedelta(hours=6)

print(f"      Gap qatorlar: {len(gap_rows):,} ta")

if gap_rows:
    gap_df = pd.DataFrame(gap_rows)
    # Mavjud df ga qo'shamiz
    df = pd.concat([df, gap_df], ignore_index=True)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.sort_values(["SensorID", "Timestamp"]).reset_index(drop=True)
    print(f"      Yangilangan jami: {len(df):,} qator")
    print(f"      Yangi max vaqt  : {df['Timestamp'].max().date()}")

    # CSV ni yangilash (ikkiga bo'lish)
    half = len(df) // 2
    df.iloc[:half].to_csv(PART1_CSV, index=False)
    df.iloc[half:].to_csv(PART2_CSV, index=False)
    print(f"      ✅ {PART1_CSV} va {PART2_CSV} yangilandi")

    # Parquet yangilash
    df_parquet = df.copy()
    df_parquet["Timestamp"] = pd.to_datetime(df_parquet["Timestamp"])
    df_parquet.to_parquet(PARQUET_FILE, engine="pyarrow", index=False)
    print(f"      ✅ {PARQUET_FILE} yangilandi")
else:
    print("      ℹ️  Gap yo'q — barcha sensorlar yangilangan")

# ──────────────────────────────────────────────────────────────
# 3. 7 KUNLIK PROGNOZ (May 12-18)
# ──────────────────────────────────────────────────────────────
print(f"\n[3/4] 7 kunlik prognoz yaratilmoqda ({FORECAST_START.date()} → {FORECAST_END.date()})...")

# So'nggi 7 kunlik o'rtacha (yangilangan df dan)
df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
last7_start = pd.Timestamp(FORECAST_START) - pd.Timedelta(days=7)
recent7 = df[df["Timestamp"] >= last7_start].copy()

# Sensor bo'yicha so'nggi 7 kun kunlik o'rtacha
recent7["date"] = recent7["Timestamp"].dt.date
daily_avg = (
    recent7.groupby(["SensorID", "date"])[FEATURE_COLS]
    .mean()
    .reset_index()
)

# Har bir sensor uchun parametrlar bo'yicha trend (linear slope per day)
def get_trend(series):
    """Kunlik o'rtachalar bo'yicha linear trend koeffitsienti."""
    n = len(series)
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    slope = np.polyfit(x, series.values, 1)[0]
    return float(slope)

sensor_trends = {}
for sid, grp in daily_avg.groupby("SensorID"):
    grp = grp.sort_values("date")
    sensor_trends[sid] = {col: get_trend(grp[col]) for col in FEATURE_COLS}

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
forecast_rows = []

# Sensor metani dict ga o'tkazamiz (tez qidirish uchun)
meta_dict = sensor_meta.set_index("SensorID").to_dict("index")

all_sensors = df["SensorID"].unique()

for sid in all_sensors:
    meta = meta_dict.get(sid, {})
    district = meta.get("District", "Noma'lum")
    lat      = float(meta.get("Latitude", 0))
    lon      = float(meta.get("Longitude", 0))

    means, stds = sensor_stats(sid)
    trends = sensor_trends.get(sid, {c: 0.0 for c in FEATURE_COLS})

    # So'nggi ma'lum qiymat (gap to'ldirilgandan keyin)
    sensor_df = df[df["SensorID"] == sid].sort_values("Timestamp")
    last_row  = sensor_df.iloc[-1] if not sensor_df.empty else None

    for day_offset in range(FORECAST_DAYS):
        forecast_date = FORECAST_START + timedelta(days=day_offset)
        month = forecast_date.month
        season = float(np.sin((month - 3) * np.pi / 6))

        # Har bir parametr uchun bazaviy qiymat = so'nggi ma'lum + trend * kun
        def pred(col, clip_lo, clip_hi, seasonal_add=0.0, noise_scale=1.0):
            base = float(last_row[col]) if last_row is not None else means[col]
            trend_adj = trends.get(col, 0.0) * (day_offset + 1)
            noise = float(rng.normal(0, stds[col] * noise_scale * 0.3))
            val = base + trend_adj + noise + seasonal_add * season
            return float(np.clip(val, clip_lo, clip_hi))

        temp = round(pred("Muhit_harorat (C)",      -5,   55, seasonal_add=3.0), 1)
        wind = round(abs(pred("Shamol_tezligi (km/h)", 0,  40)),                  1)
        hz   = round(pred("Chastota (Hz)",           48.0, 52.0),                 2)
        v    = round(pred("Kuchlanish (V)",           195,  245),                  1)
        vib  = round(abs(pred("Vibratsiya",            0.01, 2.5)),                4)
        sim  = round(pred("Sim_mexanik_holati (%)",   60,   100),                  1)
        hum  = round(pred("Atrof_muhit_humidity (%)", 25,   95,  seasonal_add=4.0),1)
        pw   = round(abs(pred("Quvvati (kW)",          0.5,  7.0)),                2)

        # Fault ehtimolini ham hisoblash (0.0–1.0)
        fault = compute_fault(v, hz, temp, vib, sim, hum, pw)
        # Qo'shimcha tasodifiy buzilish ehtimoli (sensor tarixi asosida)
        fault_history_rate = float(
            (sensor_df["Fault"] == 2).mean() if last_row is not None else 0.05
        )
        fault_prob = round(
            (fault / 2) * 0.7 + fault_history_rate * 0.3, 4
        )

        forecast_rows.append({
            "forecast_date":            forecast_date.strftime("%Y-%m-%d"),
            "generated_at":             generated_at,
            "SensorID":                 sid,
            "District":                 district,
            "Latitude":                 round(lat, 6),
            "Longitude":                round(lon, 6),
            "Muhit_harorat (C)":        temp,
            "Shamol_tezligi (km/h)":    wind,
            "Chastota (Hz)":            hz,
            "Kuchlanish (V)":           v,
            "Vibratsiya":               vib,
            "Sim_mexanik_holati (%)":   sim,
            "Atrof_muhit_humidity (%)": hum,
            "Quvvati (kW)":             pw,
            "Fault_predicted":          fault,
            "Fault_probability":        fault_prob,
        })

forecast_df = pd.DataFrame(forecast_rows)

# ──────────────────────────────────────────────────────────────
# 4. SAQLASH
# ──────────────────────────────────────────────────────────────
print(f"\n[4/4] {FORECAST_CSV} ga saqlanmoqda...")
forecast_df.to_csv(FORECAST_CSV, index=False)

print(f"\n{'=' * 65}")
print("  XULOSA")
print(f"{'=' * 65}")
print(f"  Prognoz qatorlar  : {len(forecast_df):,}")
print(f"  Sensorlar soni    : {forecast_df['SensorID'].nunique()}")
print(f"  Prognoz davri     : {forecast_df['forecast_date'].min()} → {forecast_df['forecast_date'].max()}")
print(f"  Ustunlar          : {list(forecast_df.columns)}")
print()
print("  Kunlik Fault taqsimoti:")
day_fault = (
    forecast_df.groupby("forecast_date")["Fault_predicted"]
    .value_counts()
    .unstack(fill_value=0)
    .rename(columns={0: "Normal", 1: "Ogohlantirish", 2: "Xavfli"})
)
print(day_fault.to_string())
print()
print(f"  ✅ Fayl saqlandi: {FORECAST_CSV}")
print(f"  ✅ Barcha ma'lumotlar May 11 gacha yangilandi")
