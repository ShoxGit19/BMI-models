"""CSV (sensor_data_part1+2.csv) → Parquet konvertatsiya.

Bir martalik ishga tushiriladi:
    python scripts/csv_to_parquet.py

Natijada `data/sensor_data.parquet` yaratiladi (snappy kompressiya).
Yuklash 5–10× tez, fayl hajmi ~70% kichik.
"""
import os
import sys
import time
import pandas as pd

PARQUET_OUT = "data/sensor_data.parquet"
CSV_PARTS = ["data/sensor_data_part1.csv", "data/sensor_data_part2.csv"]


def main():
    if not all(os.path.exists(p) for p in CSV_PARTS):
        print(f"❌ CSV fayllar topilmadi: {CSV_PARTS}")
        sys.exit(1)

    if os.path.exists(PARQUET_OUT):
        print(f"⚠️  Parquet allaqachon mavjud: {PARQUET_OUT}")
        ans = input("Qayta yaratay? (y/N): ").strip().lower()
        if ans != "y":
            return

    t0 = time.time()
    print(f"📥 CSV o'qish...")
    dfs = []
    for p in CSV_PARTS:
        sz = os.path.getsize(p) / 1024 / 1024
        print(f"   {p} ({sz:.1f} MB)")
        dfs.append(pd.read_csv(p))
    df = pd.concat(dfs, ignore_index=True)
    csv_time = time.time() - t0
    print(f"✅ CSV yuklandi: {len(df):,} satr · {csv_time:.1f}s")

    # Timestamp ni datetime ga
    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

    # Kategorik ustunlar uchun category dtype (parquet uchun samarali)
    for col in ("District", "SensorID"):
        if col in df.columns:
            df[col] = df[col].astype("category")

    t1 = time.time()
    print(f"💾 Parquet saqlash...")
    df.to_parquet(PARQUET_OUT, engine="pyarrow", compression="snappy", index=False)
    write_time = time.time() - t1

    out_sz = os.path.getsize(PARQUET_OUT) / 1024 / 1024
    in_sz = sum(os.path.getsize(p) for p in CSV_PARTS) / 1024 / 1024
    print(f"✅ Parquet yaratildi: {PARQUET_OUT}")
    print(f"   Hajmi: {in_sz:.1f} MB → {out_sz:.1f} MB ({out_sz/in_sz*100:.0f}%)")
    print(f"   Saqlash vaqti: {write_time:.1f}s")

    # Test: parquetdan qayta o'qish
    t2 = time.time()
    df2 = pd.read_parquet(PARQUET_OUT, engine="pyarrow")
    read_time = time.time() - t2
    print(f"\n📊 Tezlik solishtiruv:")
    print(f"   CSV o'qish:     {csv_time:.2f}s")
    print(f"   Parquet o'qish: {read_time:.2f}s ({csv_time/read_time:.1f}× tez)")


if __name__ == "__main__":
    main()
