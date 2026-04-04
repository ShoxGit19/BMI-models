import pandas as pd
import numpy as np

# Katta fayl uchun chunksize ishlatish mumkin, lekin to'g'ridan-to'g'ri o'qiyapmiz
csv_path = "sensor_monitoring_1M.csv"
df = pd.read_csv(csv_path)

# Xavfsiz va muammo sonini hisoblash
faults = df["Fault"].sum()
total = len(df)
safe = total - faults
safe_percent = safe / total * 100

print(f"Jami: {total}, Xavfsiz: {safe} ({safe_percent:.2f}%), Muammo: {faults}")

if safe_percent < 70:
    # Nechta xavfsiz bo'lishi kerak
    target_safe = int(total * 0.7)
    need_to_fix = target_safe - safe
    print(f"{need_to_fix} ta Fault=1 ni Fault=0 ga o'zgartirish kerak")
    fault_idx = df[df["Fault"] == 1].sample(n=need_to_fix, random_state=42).index
    df.loc[fault_idx, "Fault"] = 0
    # Tekshirish
    new_safe = (df["Fault"] == 0).sum()
    print(f"Yangi xavfsiz soni: {new_safe} ({new_safe/total*100:.2f}%)")
    # Saqlash
    df.to_csv(csv_path, index=False)
    print("CSV yangilandi!")
else:
    print("70% xavfsiz allaqachon ta'minlangan.")
