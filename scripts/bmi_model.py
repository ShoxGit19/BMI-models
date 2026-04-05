import pandas as pd
import streamlit as st
import datetime
import pickle
from sklearn.metrics import classification_report, accuracy_score

# =========================
# MA'LUMOTLARNI YUKLASH
# =========================
df = pd.read_csv("sensor_monitoring_1M.csv")
df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
df.dropna(subset=["Timestamp"], inplace=True)

# =========================
# LIMITLAR (7 PARAMETR)
# =========================
LIMITS = {
    "Harorat_min": 15,
    "Harorat_max": 45,
    "Tok_min": 8,
    "Tok_max": 22,
    "Kuchlanish_min": 210,
    "Kuchlanish_max": 235,
    "Vibratsiya_max": 1.8,
    "Sim_holati_min": 75,
    "Humidity_min": 35,
    "Humidity_max": 85
}

# =========================
# STREAMLIT CONFIG
# =========================
st.set_page_config(page_title="Elektr tarmogi monitoringi", layout="wide")
st.markdown("<h1 style='color:#004080;text-align:center;'>⚡ Elektr uzatish liniyasi real-time monitoring tizimi</h1>", unsafe_allow_html=True)

menu = st.sidebar.radio("📌 Sahifani tanlang:", ["🏠 Bosh sahifa", "📋 Jadval", "🗺️ Xarita", "📈 Grafiklar", "🤖 Model"])

# =========================
# MODEL - use pre-trained pipeline
# =========================
if menu == "🤖 Model":
    st.header("🤖 Gibrid AI Model (pre-trained)")

    # Try loading pre-trained pipeline
    hybrid_model = None
    try:
        with open("hybrid_model.pkl", "rb") as f:
            hybrid_model = pickle.load(f)
        st.success("✅ Model yuklandi: hybrid_model.pkl")
    except Exception as e:
        st.error(f"❌ Model yuklab bo'lmadi: {e}")

    st.subheader("🔮 Real-time prognoz (7 parametr)")
    harorat = st.number_input("Harorat (C):", value=25.0)
    tok = st.number_input("Tok_kuchi (A):", value=15.0)
    kuchlanish = st.number_input("Kuchlanish (V):", value=220.0)
    vibratsiya = st.number_input("Vibratsiya:", value=0.1)
    sim_holati = st.number_input("Sim_mexanik_holati (%):", value=90.0)
    humidity = st.number_input("Atrof_muhit_humidity (%):", value=50.0)
    quvvat = st.number_input("Quvvati (kW):", value=3.0)

    # Check limits (partial check)
    if st.button("Prognoz qilish"):
        if hybrid_model is None:
            st.error("❌ Model mavjud emas — avval `train_model.py` bilan modelni o'rgating.")
        else:
            features = [[harorat, tok, kuchlanish, vibratsiya, sim_holati, humidity, quvvat]]
            try:
                pred = hybrid_model.predict(features)
                if int(pred[0]) == 1:
                    st.error("⚠️ Nosozlik aniqlandi!")
                else:
                    st.success("✅ Liniya normal ishlayapti.")
            except Exception as e:
                st.error(f"Model bilan prognoz qilishda xato: {e}")