from chatbot_engine import answer
import pandas as pd

df = pd.read_parquet("data/sensor_data.parquet", engine="pyarrow")
for c in ("District", "SensorID"):
    if str(df[c].dtype) == "category":
        df[c] = df[c].astype(str)
df["Timestamp"] = pd.to_datetime(df["Timestamp"])
latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
latest["Fault"] = latest["Fault"].fillna(0).astype(int)

tests = [
    "salom",
    "Chilonzorda muammo bormi?",
    "eng past kuchlanish",
    "S0045 holati",
    "statistika",
    "kuchlanish 210V dan past",
    "so'nggi nosozliklar",
    "vibratsiya yuqori",
    "o'rtacha kuchlanish",
    "yordam",
]

for q in tests:
    r = answer(q, df=latest)
    text_preview = r["text"][:70].replace("\n", " ")
    print(f"Q: {q}")
    print(f"   Intent: {r['intent']} (score={r['confidence']})")
    print(f"   Text: {text_preview}...")
    print()

print("Chatbot test muvaffaqiyatli!")
