import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# =========================
# PAGE STATE
# =========================
if "page" not in st.session_state:
    
    st.session_state.page = "home"

def go(page):
    st.session_state.page = page

# =========================
# DATA LOAD
# =========================
df = pd.read_csv("excel_file.csv")
df["Timestamp"] = pd.to_datetime(df["Timestamp"])

# 🔥 FAOL YILNI 2025 QILAMIZ
df["Timestamp"] = df["Timestamp"].apply(lambda x: x.replace(year=2025))

# =========================
# TIME COLUMNLAR
# =========================
df["Year"] = df["Timestamp"].dt.year
df["Month"] = df["Timestamp"].dt.month
df["Month_name"] = df["Timestamp"].dt.strftime("%B")
df["Hour"] = df["Timestamp"].dt.hour

# =========================
# STANDARTLAR (DUNYO STANDARTLARI)
# =========================
LIMITS = {
    "Current": 20,
    "Voltage_min": 210,
    "Voltage_max": 230,
    "Temperature": 50,
    "Vibration": 1.5
}

# =========================
# HOME PAGE
# =========================
if st.session_state.page == "home":

    st.title("⚡ Elektr uzatish liniyasini monitoring tizimi")

    st.write("Parametrni tanlang:")

    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        if st.button("⚡ Tok"):
            go("current")

    with col2:
        if st.button("🔋 Kuchlanish"):
            go("voltage")

    with col3:
        if st.button("🌡 Harorat"):
            go("temperature")

    with col4:
        if st.button("📳 Vibratsiya"):
            go("vibration")

# =========================
# TOK PAGE
# =========================
elif st.session_state.page == "current":

    st.title("⚡ Tok monitoring")

    if st.button("⬅️ Ortga"):
        go("home")

    df_plot = df.copy()
    df_plot["danger"] = df_plot["Current"] > LIMITS["Current"]

    st.line_chart(df_plot.set_index("Timestamp")["Current"])

    danger_df = df_plot[df_plot["danger"] == True]

    if len(danger_df) > 0:
        st.error(f"❌ {len(danger_df)} ta tok xavfli holati")
        st.dataframe(danger_df[["Timestamp","Current"]])
    else:
        st.success("✅ Normal")

    st.subheader("📊 Statistik")
    col1, col2 = st.columns(2)
    col1.metric("Max tok", f"{df['Current'].max():.2f}")
    col2.metric("O‘rtacha tok", f"{df['Current'].mean():.2f}")

# =========================
# KUCHLANISH PAGE
# =========================
elif st.session_state.page == "voltage":

    st.title("🔋 Kuchlanish monitoring")

    if st.button("⬅️ Ortga"):
        go("home")

    df_plot = df.copy()
    df_plot["danger"] = (
        (df_plot["Voltage"] < LIMITS["Voltage_min"]) |
        (df_plot["Voltage"] > LIMITS["Voltage_max"])
    )

    st.line_chart(df_plot.set_index("Timestamp")["Voltage"])

    danger_df = df_plot[df_plot["danger"] == True]

    if len(danger_df) > 0:
        st.error(f"❌ {len(danger_df)} ta kuchlanish muammo")
        st.dataframe(danger_df[["Timestamp","Voltage"]])
    else:
        st.success("✅ Normal")

# =========================
# TEMPERATURE PAGE
# =========================
elif st.session_state.page == "temperature":

    st.title("🌡 Harorat monitoring")

    if st.button("⬅️ Ortga"):
        go("home")

    df_plot = df.copy()
    df_plot["danger"] = df_plot["Temperature"] > LIMITS["Temperature"]

    st.line_chart(df_plot.set_index("Timestamp")["Temperature"])

    danger_df = df_plot[df_plot["danger"] == True]

    if len(danger_df) > 0:
        st.error(f"❌ {len(danger_df)} ta harorat xavfli")
        st.dataframe(danger_df[["Timestamp","Temperature"]])
    else:
        st.success("✅ Normal")

# =========================
# VIBRATION PAGE
# =========================
elif st.session_state.page == "vibration":

    st.title("📳 Vibratsiya monitoring")

    if st.button("⬅️ Ortga"):
        go("home")

    df_plot = df.copy()
    df_plot["danger"] = df_plot["Vibration"] > LIMITS["Vibration"]

    st.line_chart(df_plot.set_index("Timestamp")["Vibration"])

    danger_df = df_plot[df_plot["danger"] == True]

    if len(danger_df) > 0:
        st.error(f"❌ {len(danger_df)} ta vibratsiya xavfli")
        st.dataframe(danger_df[["Timestamp","Vibration"]])
    else:
        st.success("✅ Normal")

# =========================
# RANDOM FOREST MODEL
# =========================
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Modelga tayyorlash
X = df[["Current", "Voltage", "Temperature", "Vibration"]]
y = df["Fault"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# Modelni yaratish
rf_model = RandomForestClassifier(n_estimators=100)
rf_model.fit(X_train, y_train)

# Test qilish
y_pred = rf_model.predict(X_test)

from sklearn.metrics import accuracy_score
accuracy = accuracy_score(y_test, y_pred)

st.subheader("📊 Random Forest Modeli Accuracy")
st.write(f"Random Forest Accuracy: {accuracy * 100:.2f}%")
