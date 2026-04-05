# --- Yagona importlar va sozlamalar ---
import os
import io
import logging
import datetime
import pickle
import hashlib
import functools
import pandas as pd
import numpy as np
import requests as http_requests
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_file, flash

# --- Flask va logger ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "monitoring-secret-2026-toshkent")
logger = logging.getLogger("bmi-app")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

# --- Foydalanuvchilar (oddiy demo uchun) ---
USERS = {
    "admin": hashlib.sha256("admin123".encode()).hexdigest(),
    "operator": hashlib.sha256("operator123".encode()).hexdigest(),
}

# --- Telegram sozlamalari ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# --- Ma'lumot va modelni yuklash funksiyasi ---
def load_data_and_model():
    df, hybrid_model = None, None
    try:
        # CSV: data/ papkadan yuklash
        if os.path.exists("data/sensor_data_part1.csv") and os.path.exists("data/sensor_data_part2.csv"):
            df = pd.concat([
                pd.read_csv("data/sensor_data_part1.csv"),
                pd.read_csv("data/sensor_data_part2.csv")
            ], ignore_index=True)
            if "Timestamp" in df.columns:
                df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
        elif os.path.exists("sensor_data_part1.csv") and os.path.exists("sensor_data_part2.csv"):
            df = pd.concat([
                pd.read_csv("sensor_data_part1.csv"),
                pd.read_csv("sensor_data_part2.csv")
            ], ignore_index=True)
            if "Timestamp" in df.columns:
                df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')

        # Model: models/ papkadan yuklash
        if os.path.exists("models/hybrid_model_part1.pkl") and os.path.exists("models/hybrid_model_part2.pkl"):
            merged = b""
            for p in ["models/hybrid_model_part1.pkl", "models/hybrid_model_part2.pkl"]:
                with open(p, "rb") as f:
                    merged += f.read()
            hybrid_model = pickle.loads(merged)
        elif os.path.exists("hybrid_model_part1.pkl") and os.path.exists("hybrid_model_part2.pkl"):
            merged = b""
            for p in ["hybrid_model_part1.pkl", "hybrid_model_part2.pkl"]:
                with open(p, "rb") as f:
                    merged += f.read()
            hybrid_model = pickle.loads(merged)
    except Exception as e:
        logger.error(f"Yuklash xatosi: {e}")
    return df, hybrid_model

df, hybrid_model = load_data_and_model()

# --- ROUTES ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect("/")
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        if username in USERS and USERS[username] == pw_hash:
            session["user"] = username
            logger.info(f"Login: {username}")
            return redirect("/")
        error = "Login yoki parol noto'g'ri!"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/")
@login_required
def home():
    return render_template("index.html")

@app.route("/graphs")
@login_required
def graphs():
    return render_template("graphs.html")

@app.route("/table")
@login_required
def table():
    return render_template("table.html")

@app.route("/map")
@login_required
def map_page():
    return render_template("map.html")

@app.route("/model", methods=["GET", "POST"])
@login_required
def model_page():
    result = None
    if request.method == "POST":
        try:
            harorat = float(request.form.get("harorat", 30))
            shamol = float(request.form.get("shamol", 7))
            chastota = float(request.form.get("chastota", 50))
            kuchlanish = float(request.form.get("kuchlanish", 220))
            vibratsiya = float(request.form.get("vibratsiya", 0.5))
            sim_holati = float(request.form.get("sim_holati", 90))
            humidity = float(request.form.get("humidity", 60))
            quvvat = float(request.form.get("quvvat", 3))

            # --- HAR BIR PARAMETRNI 3 DARAJA BILAN TEKSHIRISH ---
            params_status = []

            # Kuchlanish
            if 210 <= kuchlanish <= 230:
                params_status.append({"name": "Kuchlanish", "icon": "🔌", "value": kuchlanish, "unit": "V", "status": "normal", "msg": "Normal chegarada (210-230V)"})
            elif 200 <= kuchlanish < 210 or 230 < kuchlanish <= 240:
                params_status.append({"name": "Kuchlanish", "icon": "🔌", "value": kuchlanish, "unit": "V", "status": "warning", "msg": f"Ogohlantirish! {kuchlanish}V — normal chegara 210-230V dan tashqarida. Transformator sozlanishi kerak."})
            else:
                params_status.append({"name": "Kuchlanish", "icon": "🔌", "value": kuchlanish, "unit": "V", "status": "danger", "msg": f"XAVF! {kuchlanish}V — favqulodda holat! Uskunalar shikastlanishi mumkin. Darhol o'chirish kerak!"})

            # Chastota
            if 49.5 <= chastota <= 50.5:
                params_status.append({"name": "Chastota", "icon": "🔄", "value": chastota, "unit": "Hz", "status": "normal", "msg": "Normal chegarada (49.5-50.5 Hz)"})
            elif 49.0 <= chastota < 49.5 or 50.5 < chastota <= 51.0:
                params_status.append({"name": "Chastota", "icon": "🔄", "value": chastota, "unit": "Hz", "status": "warning", "msg": f"Ogohlantirish! {chastota} Hz — chastota normal chegaradan (49.5-50.5 Hz) chiqmoqda. Generator yuklamasi tekshirilsin."})
            else:
                params_status.append({"name": "Chastota", "icon": "🔄", "value": chastota, "unit": "Hz", "status": "danger", "msg": f"XAVF! {chastota} Hz — favqulodda chastota o'zgarishi! Tarmog'da jiddiy yuklama muvozanati buzilgan. Darhol choralar ko'rilsin!"})

            # Harorat (muhit)
            if harorat < 40:
                params_status.append({"name": "Muhit harorat", "icon": "🌡️", "value": harorat, "unit": "°C", "status": "normal", "msg": "Normal chegarada (<40°C)"})
            elif 40 <= harorat <= 45:
                params_status.append({"name": "Muhit harorat", "icon": "🌡️", "value": harorat, "unit": "°C", "status": "warning", "msg": f"Ogohlantirish! {harorat}°C — havo issiq. Uskunalar qizishi mumkin. Normal <40°C."})
            else:
                params_status.append({"name": "Muhit harorat", "icon": "🌡️", "value": harorat, "unit": "°C", "status": "danger", "msg": f"XAVF! {harorat}°C — haddan tashqari issiq muhit! Uskunalar ortiqcha qizishi va nosozlik xavfi!"})

            # Vibratsiya (faslga/haroratga bog'liq)
            vib_reason = ""
            if harorat < 0:
                vib_reason = " Sovuq havoda simlar qisqarib muzlaydi (zaminiya)."
            elif harorat > 40:
                vib_reason = " Issiq havoda simlar cho'zilib tebranadi (zaminiya)."
            if vibratsiya < 1.0:
                params_status.append({"name": "Vibratsiya", "icon": "📳", "value": vibratsiya, "unit": "", "status": "normal", "msg": "Normal chegarada (<1.0)"})
            elif 1.0 <= vibratsiya <= 1.5:
                params_status.append({"name": "Vibratsiya", "icon": "📳", "value": vibratsiya, "unit": "", "status": "warning", "msg": f"Ogohlantirish! Vibratsiya {vibratsiya} — mexanik tebranish boshlanmoqda.{vib_reason} Mahkamlash tekshirilsin."})
            else:
                params_status.append({"name": "Vibratsiya", "icon": "📳", "value": vibratsiya, "unit": "", "status": "danger", "msg": f"XAVF! Vibratsiya {vibratsiya} — kuchli tebranish!{vib_reason} Sim uzilishi yoki uskuna buzilishi mumkin!"})

            # Sim holati
            if sim_holati > 85:
                params_status.append({"name": "Sim holati", "icon": "🔗", "value": sim_holati, "unit": "%", "status": "normal", "msg": "Normal chegarada (>85%)"})
            elif 75 <= sim_holati <= 85:
                params_status.append({"name": "Sim holati", "icon": "🔗", "value": sim_holati, "unit": "%", "status": "warning", "msg": f"Ogohlantirish! Sim holati {sim_holati}% — eskirish belgilari bor. Texnik ko'rik rejalashtirilsin."})
            else:
                params_status.append({"name": "Sim holati", "icon": "🔗", "value": sim_holati, "unit": "%", "status": "danger", "msg": f"XAVF! Sim holati {sim_holati}% — jiddiy eskirish! Sim uzilishi mumkin. Almashtirilsin!"})

            # Namlik
            if 35 <= humidity <= 85:
                params_status.append({"name": "Namlik", "icon": "💨", "value": humidity, "unit": "%", "status": "normal", "msg": "Normal chegarada (35-85%)"})
            elif 30 <= humidity < 35 or 85 < humidity <= 90:
                params_status.append({"name": "Namlik", "icon": "💨", "value": humidity, "unit": "%", "status": "warning", "msg": f"Ogohlantirish! Namlik {humidity}% — normal chegara 35-85%. Korroziya yoki quruqlik xavfi."})
            else:
                params_status.append({"name": "Namlik", "icon": "💨", "value": humidity, "unit": "%", "status": "danger", "msg": f"XAVF! Namlik {humidity}% — favqulodda! Izolyatsiya buzilishi yoki korroziya tezlashadi!"})

            # Quvvat
            if quvvat <= 5.0:
                params_status.append({"name": "Quvvat", "icon": "⚙️", "value": quvvat, "unit": "kW", "status": "normal", "msg": "Normal chegarada (≤5.0 kW)"})
            elif 5.0 < quvvat <= 5.5:
                params_status.append({"name": "Quvvat", "icon": "⚙️", "value": quvvat, "unit": "kW", "status": "warning", "msg": f"Ogohlantirish! Quvvat {quvvat} kW — yuklama ortmoqda. Taqsimlovchini tekshiring."})
            else:
                params_status.append({"name": "Quvvat", "icon": "⚙️", "value": quvvat, "unit": "kW", "status": "danger", "msg": f"XAVF! Quvvat {quvvat} kW — haddan tashqari yuklama! Simlar qizishi va yong'in xavfi!"})

            # Shamol tezligi
            if shamol < 15:
                params_status.append({"name": "Shamol", "icon": "🌬️", "value": shamol, "unit": "km/h", "status": "normal", "msg": "Normal chegarada (<15 km/h)"})
            elif 15 <= shamol <= 25:
                params_status.append({"name": "Shamol", "icon": "🌬️", "value": shamol, "unit": "km/h", "status": "warning", "msg": f"Ogohlantirish! Shamol {shamol} km/h — kuchli shamol. Simlar tebranishi ortadi."})
            else:
                params_status.append({"name": "Shamol", "icon": "🌬️", "value": shamol, "unit": "km/h", "status": "danger", "msg": f"XAVF! Shamol {shamol} km/h — juda kuchli shamol! Sim uzilishi va ustunlar qiyshayishi xavfi!"})

            # --- UMUMIY XULOSA ---
            danger_count = sum(1 for p in params_status if p["status"] == "danger")
            warning_count = sum(1 for p in params_status if p["status"] == "warning")
            normal_count = sum(1 for p in params_status if p["status"] == "normal")

            danger_params = [p for p in params_status if p["status"] == "danger"]
            warning_params = [p for p in params_status if p["status"] == "warning"]

            if danger_count >= 2:
                level = "danger"
                level_text = "⛔ MUAMMO"
                level_msg = f"{danger_count} ta parametr favqulodda holatda! Darhol choralar ko'rilsin."
            elif danger_count == 1:
                level = "danger"
                level_text = "⚠️ MUAMMO"
                level_msg = f"1 ta parametr favqulodda holatda: {danger_params[0]['icon']} {danger_params[0]['name']}. Tezda tekshirilsin."
            elif warning_count >= 2:
                level = "warning"
                level_text = "🟡 OGOHLANTIRISH"
                level_msg = f"{warning_count} ta parametr ogohlantirish chegarasida. Monitoring kuchaytirilsin."
            elif warning_count == 1:
                level = "warning"
                level_text = "🟡 OGOHLANTIRISH"
                level_msg = f"1 ta parametr ogohlantirish chegarasida: {warning_params[0]['icon']} {warning_params[0]['name']}."
            else:
                level = "success"
                level_text = "✅ HAVFSIZ"
                level_msg = "Barcha parametrlar normal chegarada. Tizim barqaror ishlayapti."

            result = {
                "level": level,
                "level_text": level_text,
                "level_msg": level_msg,
                "params": params_status,
                "danger_count": danger_count,
                "warning_count": warning_count,
                "normal_count": normal_count,
                "values": {
                    "harorat": harorat, "shamol": shamol, "chastota": chastota, "kuchlanish": kuchlanish,
                    "vibratsiya": vibratsiya, "sim_holati": sim_holati,
                    "humidity": humidity, "quvvat": quvvat
                }
            }
        except Exception as e:
            result = {"level": "danger", "level_text": "❌ XATO", "level_msg": str(e), "params": [], "danger_count": 0, "warning_count": 0, "normal_count": 0, "values": {}}
    return render_template("model.html", result=result)

@app.route("/forecast")
@login_required
def forecast_page():
    return render_template("forecast.html")

# --- Sensor detail sahifasi ---
@app.route("/sensor/<sensor_id>")
@login_required
def sensor_detail(sensor_id):
    return render_template("sensor_detail.html", sensor_id=sensor_id)

# --- API ROUTES ---
@app.route("/api/forecast")
def forecast():
    """So'nggi 7 kun va kelajak uchun xavf prognozi"""
    try:
        if df is None or df.empty or hybrid_model is None:
            return jsonify({"error": "Ma'lumot yoki model yo'q"}), 404

        # So'nggi 7 kun
        now = datetime.datetime.now()
        week_ago = now - datetime.timedelta(days=7)
        last_week = df[df["Timestamp"] >= week_ago]

        feature_cols = [
            "Muhit_harorat (C)", "Shamol_tezligi (km/h)", "Chastota (Hz)", "Kuchlanish (V)",
            "Vibratsiya", "Sim_mexanik_holati (%)",
            "Atrof_muhit_humidity (%)", "Quvvati (kW)"
        ]

        # Natijalar - 6 soatlik o'rtacha
        last_week_resampled = last_week.set_index("Timestamp")[feature_cols].resample("6h").mean().dropna()
        lw_preds = hybrid_model.predict(last_week_resampled)
        result = []
        for t, p in zip(last_week_resampled.index, lw_preds):
            result.append({"timestamp": str(t), "xavf": int(p)})

        # ===== KELAJAK 7 KUN PROGNOZI =====
        future = []

        # 1) REAL ob-havo prognozi (Open-Meteo API)
        weather_forecast = {}
        try:
            resp = http_requests.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": 41.3111, "longitude": 69.2797,
                "hourly": "temperature_2m,wind_speed_10m,relative_humidity_2m",
                "timezone": "Asia/Tashkent",
                "forecast_days": 7
            }, timeout=10)
            wd = resp.json().get("hourly", {})
            if wd.get("time"):
                for i, t in enumerate(wd["time"]):
                    weather_forecast[t[:13]] = {  # "2026-04-05T06" format
                        "temp": wd["temperature_2m"][i],
                        "wind": wd["wind_speed_10m"][i],
                        "humid": wd["relative_humidity_2m"][i]
                    }
            logger.info(f"Open-Meteo: {len(weather_forecast)} soatlik ob-havo yuklandi")
        except Exception as e:
            logger.warning(f"Open-Meteo xatosi, fallback ishlatiladi: {e}")

        # 2) So'nggi ma'lum qiymatlar (elektr parametrlar uchun baza)
        if not last_week.empty:
            recent = last_week.set_index("Timestamp")[feature_cols].resample("6h").mean().dropna()
            base_vals = recent.iloc[-1].values.copy() if len(recent) >= 1 else None
        else:
            base_vals = None

        if base_vals is not None:
            rng = np.random.default_rng(42)

            # Normal qiymatlar (o'rtacha) — mean-reversion uchun
            normal_center = np.array([
                15.0,   # Harorat — real API to'ldiradi
                5.0,    # Shamol — real API to'ldiradi
                50.0,   # Chastota (Hz)
                220.0,  # Kuchlanish (V)
                0.35,   # Vibratsiya
                90.0,   # Sim holati (%)
                60.0,   # Namlik — real API to'ldiradi
                3.2     # Quvvat (kW)
            ])

            # Noise masshtabi (kichik — realistik)
            noise_scale = np.array([1.5, 1.0, 0.15, 3.0, 0.08, 1.5, 3.0, 0.25])

            # Mean-reversion kuchi (0-1, katta = tezroq normalga qaytadi)
            reversion = np.array([0.3, 0.3, 0.4, 0.3, 0.3, 0.15, 0.3, 0.3])

            # Normal chegaralar
            normal_bounds = {
                0: (-5, 50),     # Harorat
                1: (0, 35),      # Shamol
                2: (49.2, 50.8), # Chastota
                3: (205, 235),   # Kuchlanish
                4: (0.05, 1.2),  # Vibratsiya
                5: (70, 100),    # Sim holati
                6: (25, 95),     # Namlik
                7: (1.5, 5.5),   # Quvvat
            }

            prev_vals = base_vals.copy()

            for i in range(1, 29):  # 28 nuqta = 7 kun * 4
                future_time = now + datetime.timedelta(hours=i * 6)
                hour = future_time.hour
                time_key = future_time.strftime("%Y-%m-%dT%H")

                # Kunduzgi yuklama effekti
                is_peak = 1.0 if (8 <= hour <= 12 or 18 <= hour <= 22) else 0.0
                peak_effect = np.array([0.0, 0.0, -0.05, 0.5, 0.03, 0.0, 0.0, 0.2]) * is_peak

                # Mean-reverting noise: prev + reversion*(normal - prev) + noise
                noise = rng.normal(0, 1, len(feature_cols)) * noise_scale
                vals = prev_vals + reversion * (normal_center - prev_vals) + noise + peak_effect

                # REAL ob-havo ma'lumotlarini qo'yish (harorat, shamol, namlik)
                if time_key in weather_forecast:
                    w = weather_forecast[time_key]
                    vals[0] = w["temp"] + rng.normal(0, 0.5)   # Harorat ± 0.5°C
                    vals[1] = w["wind"] + rng.normal(0, 0.3)   # Shamol ± 0.3 km/h
                    vals[6] = w["humid"] + rng.normal(0, 1.0)  # Namlik ± 1%

                # Chegaralar
                for j, (lo, hi) in normal_bounds.items():
                    vals[j] = np.clip(vals[j], lo, hi)

                # Model bilan prognoz
                pred_input = pd.DataFrame([vals], columns=feature_cols)
                pred = int(hybrid_model.predict(pred_input)[0])

                future.append({
                    "timestamp": future_time.strftime("%Y-%m-%d %H:00"),
                    "xavf": pred,
                    "params": {
                        feature_cols[k]: round(float(vals[k]), 2) for k in range(len(feature_cols))
                    }
                })
                prev_vals = vals.copy()

        return jsonify({"last_week": result, "future": future})
    except Exception as e:
        logger.error(f"Forecast error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/forecast-params")
def forecast_params_api():
    if df is None or df.empty or hybrid_model is None:
        return jsonify({"error": "Ma'lumot yoki model yo'q"}), 404
    now = datetime.datetime.now()
    week_ago = now - datetime.timedelta(days=7)
    last_week = df[df["Timestamp"] >= week_ago].copy()
    feature_cols = [
        "Muhit_harorat (C)", "Shamol_tezligi (km/h)", "Chastota (Hz)", "Kuchlanish (V)",
        "Vibratsiya", "Sim_mexanik_holati (%)",
        "Atrof_muhit_humidity (%)", "Quvvati (kW)"
    ]
    param = request.args.get("param")
    # Resample to 6-hourly means for clarity
    if "Timestamp" in last_week.columns:
        last_week = last_week.set_index("Timestamp")[feature_cols].resample("6h").mean().dropna().reset_index()
    result = {"timestamp": last_week["Timestamp"].astype(str).tolist()}
    # Add both raw and smoothed (trend) values
    if param and param in feature_cols:
        values = last_week[param].tolist()
        result[param] = values
        # Only add trend if not Vibratsiya
        if param != "Vibratsiya":
            trend = pd.Series(values).rolling(window=4, min_periods=1).mean().tolist()
            result[param+"_trend"] = trend
    else:
        for col in feature_cols:
            values = last_week[col].tolist()
            result[col] = values
            if col != "Vibratsiya":
                trend = pd.Series(values).rolling(window=4, min_periods=1).mean().tolist()
                result[col+"_trend"] = trend
    # Predict xavf for each resampled row
    if not last_week.empty:
        result["xavf"] = [int(x) for x in hybrid_model.predict(last_week[feature_cols])]
    else:
        result["xavf"] = []
    return jsonify(result)

@app.route("/api/stats")
def get_stats():
    """Statistics — 500 sensor, har birining oxirgi holatini ko'rsatish"""
    try:
        if df is None or df.empty:
            return jsonify({"error": "Ma'lumot yo'q"}), 404

        # Har bir sensorning OXIRGI o'lchovini olish
        latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
        total = len(latest)
        safe_count = int((latest["Fault"] == 0).sum())
        warn_count = int((latest["Fault"] == 1).sum())
        danger_count = int((latest["Fault"] == 2).sum())
        safe_percent = round(100 * safe_count / total, 1) if total > 0 else 0

        # So'nggi 7 kun uchun xavfli vaqtlar
        last_week = df[df["Timestamp"] >= (datetime.datetime.now() - datetime.timedelta(days=7))]
        week_dangers = int((last_week["Fault"] == 2).sum()) if not last_week.empty else 0
        week_warns = int((last_week["Fault"] == 1).sum()) if not last_week.empty else 0

        # Tumanlar bo'yicha statistika
        tuman_stats = latest.groupby("District").agg(
            sensorlar=("SensorID", "count"),
            havfsiz=("Fault", lambda x: int((x == 0).sum())),
            ogohlantirish=("Fault", lambda x: int((x == 1).sum())),
            muammo=("Fault", lambda x: int((x == 2).sum())),
        ).to_dict(orient="index")

        return jsonify({
            "total_sensors": total,
            "safe_sensors": safe_count,
            "warn_sensors": warn_count,
            "danger_sensors": danger_count,
            "faults": warn_count + danger_count,
            "safe_percent": safe_percent,
            "week_dangers": week_dangers,
            "week_warns": week_warns,
            "status": "🟢 Barqaror" if safe_percent >= 60 else ("🟡 Ogohlantirish" if safe_percent >= 40 else "🔴 Muammolar"),
            "avg_harorat": round(latest["Muhit_harorat (C)"].mean(), 1),
            "avg_shamol": round(latest["Shamol_tezligi (km/h)"].mean(), 1),
            "avg_chastota": round(latest["Chastota (Hz)"].mean(), 2),
            "avg_kuchlanish": round(latest["Kuchlanish (V)"].mean(), 1),
            "avg_vibratsiya": round(latest["Vibratsiya"].mean(), 3),
            "avg_sim_holati": round(latest["Sim_mexanik_holati (%)"].mean(), 1),
            "avg_humidity": round(latest["Atrof_muhit_humidity (%)"].mean(), 1),
            "avg_quvvat": round(latest["Quvvati (kW)"].mean(), 2),
            "tumanlar": tuman_stats,
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/map-data")
def map_data():
    """Map data — har bir sensorning oxirgi o'lchovi (500 ta nuqta)"""
    try:
        if df is None or df.empty:
            return jsonify([]), 404

        # Har bir sensorning OXIRGI o'lchovini olish
        latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()

        result = []
        for idx, row in latest.iterrows():
            fault = int(row.get("Fault", 0))
            result.append({
                "SensorID": str(row.get("SensorID", "")),
                "District": str(row.get("District", "Unknown")),
                "Latitude": float(row.get("Latitude", 41.3111)),
                "Longitude": float(row.get("Longitude", 69.2797)),
                "Harorat": round(float(row.get("Muhit_harorat (C)", 25)), 1),
                "Shamol": round(float(row.get("Shamol_tezligi (km/h)", 7)), 1),
                "Chastota": round(float(row.get("Chastota (Hz)", 50)), 2),
                "Kuchlanish": round(float(row.get("Kuchlanish (V)", 220)), 1),
                "Vibratsiya": round(float(row.get("Vibratsiya", 0.5)), 4),
                "Sim_holati": round(float(row.get("Sim_mexanik_holati (%)", 90)), 1),
                "Humidity": round(float(row.get("Atrof_muhit_humidity (%)", 50)), 1),
                "Quvvat": round(float(row.get("Quvvati (kW)", 3)), 2),
                "Fault": fault,
                "Color": "#dc3545" if fault == 2 else ("#ffc107" if fault == 1 else "#28a745")
            })

        return jsonify(result)
    except Exception as e:
        logger.error(f"Map error: {e}")
        return jsonify([]), 500

@app.route("/api/graph-data")
def get_graph_data():
    """Grafiklar uchun — barcha vaqtdan sample, vaqt bo'yicha tartiblangan"""
    try:
        if df is None or df.empty:
            return jsonify([]), 404

        sorted_df = df.sort_values("Timestamp", ascending=True)
        sample_size = min(1000, len(sorted_df))
        sample_rate = max(1, len(sorted_df) // sample_size)
        data = sorted_df.iloc[::sample_rate].head(sample_size)

        result = []
        for idx, row in data.iterrows():
            fault = int(row.get("Fault", 0))
            result.append({
                "SensorID": str(row.get("SensorID", "")),
                "District": str(row.get("District", "Unknown")),
                "Timestamp": str(row.get("Timestamp", "")),
                "Harorat": round(float(row.get("Muhit_harorat (C)", 25)), 1),
                "Shamol": round(float(row.get("Shamol_tezligi (km/h)", 7)), 1),
                "Chastota": round(float(row.get("Chastota (Hz)", 50)), 2),
                "Kuchlanish": round(float(row.get("Kuchlanish (V)", 220)), 1),
                "Vibratsiya": round(float(row.get("Vibratsiya", 0.5)), 4),
                "Sim_holati": round(float(row.get("Sim_mexanik_holati (%)", 90)), 1),
                "Humidity": round(float(row.get("Atrof_muhit_humidity (%)", 50)), 1),
                "Quvvat": round(float(row.get("Quvvati (kW)", 3)), 2),
                "Fault": fault,
                "Status": "🔴 MUAMMO" if fault == 2 else ("🟡 OGOHLANTIRISH" if fault == 1 else "🟢 HAVFSIZ")
            })

        return jsonify(result)
    except Exception as e:
        logger.error(f"Graph data error: {e}")
        return jsonify([]), 500

@app.route("/api/data")
def get_data():
    """All sensor data — pagination supported"""
    try:
        if df is None or df.empty:
            return jsonify([]), 404

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        per_page = min(per_page, 200)

        sorted_df = df.sort_values("Timestamp", ascending=False)
        total = len(sorted_df)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))

        start = (page - 1) * per_page
        data = sorted_df.iloc[start:start + per_page]

        result = []
        for idx, row in data.iterrows():
            fault = int(row.get("Fault", 0))
            result.append({
                "SensorID": str(row.get("SensorID", "")),
                "District": str(row.get("District", "Unknown")),
                "Timestamp": str(row.get("Timestamp", "")),
                "Harorat": round(float(row.get("Muhit_harorat (C)", 25)), 1),
                "Shamol": round(float(row.get("Shamol_tezligi (km/h)", 7)), 1),
                "Chastota": round(float(row.get("Chastota (Hz)", 50)), 2),
                "Kuchlanish": round(float(row.get("Kuchlanish (V)", 220)), 1),
                "Vibratsiya": round(float(row.get("Vibratsiya", 0.5)), 4),
                "Sim_holati": round(float(row.get("Sim_mexanik_holati (%)", 90)), 1),
                "Humidity": round(float(row.get("Atrof_muhit_humidity (%)", 50)), 1),
                "Quvvat": round(float(row.get("Quvvati (kW)", 3)), 2),
                "Fault": fault,
                "Status": "🔴 MUAMMO" if fault == 2 else ("🟡 OGOHLANTIRISH" if fault == 1 else "🟢 HAVFSIZ")
            })

        return jsonify({"data": result, "page": page, "per_page": per_page, "total": total, "total_pages": total_pages})
    except Exception as e:
        logger.error(f"Data error: {e}")
        return jsonify({"data": [], "page": 1, "total": 0, "total_pages": 1}), 500

# --- Sensor detail API ---
@app.route("/api/sensor/<sensor_id>")
def sensor_data_api(sensor_id):
    """Bitta sensor uchun to'liq tarixiy ma'lumot"""
    try:
        if df is None or df.empty:
            return jsonify({"error": "Ma'lumot yo'q"}), 404
        sensor_df = df[df["SensorID"] == sensor_id].sort_values("Timestamp")
        if sensor_df.empty:
            return jsonify({"error": "Sensor topilmadi"}), 404

        latest = sensor_df.iloc[-1]
        feature_cols = [
            "Muhit_harorat (C)", "Shamol_tezligi (km/h)", "Chastota (Hz)", "Kuchlanish (V)",
            "Vibratsiya", "Sim_mexanik_holati (%)", "Atrof_muhit_humidity (%)", "Quvvati (kW)"
        ]
        # So'nggi 100 o'lchov
        recent = sensor_df.tail(100)
        history = {
            "timestamps": recent["Timestamp"].astype(str).tolist(),
            "harorat": recent["Muhit_harorat (C)"].round(1).tolist(),
            "shamol": recent["Shamol_tezligi (km/h)"].round(1).tolist(),
            "chastota": recent["Chastota (Hz)"].round(2).tolist(),
            "kuchlanish": recent["Kuchlanish (V)"].round(1).tolist(),
            "vibratsiya": recent["Vibratsiya"].round(3).tolist(),
            "sim_holati": recent["Sim_mexanik_holati (%)"].round(1).tolist(),
            "humidity": recent["Atrof_muhit_humidity (%)"].round(1).tolist(),
            "quvvat": recent["Quvvati (kW)"].round(2).tolist(),
            "fault": recent["Fault"].astype(int).tolist(),
        }
        fault_counts = sensor_df["Fault"].value_counts().to_dict()
        return jsonify({
            "sensor_id": sensor_id,
            "district": str(latest.get("District", "Unknown")),
            "total_records": len(sensor_df),
            "latest": {
                "timestamp": str(latest["Timestamp"]),
                "fault": int(latest.get("Fault", 0)),
                "harorat": round(float(latest.get("Muhit_harorat (C)", 0)), 1),
                "shamol": round(float(latest.get("Shamol_tezligi (km/h)", 0)), 1),
                "chastota": round(float(latest.get("Chastota (Hz)", 50)), 2),
                "kuchlanish": round(float(latest.get("Kuchlanish (V)", 220)), 1),
                "vibratsiya": round(float(latest.get("Vibratsiya", 0)), 3),
                "sim_holati": round(float(latest.get("Sim_mexanik_holati (%)", 90)), 1),
                "humidity": round(float(latest.get("Atrof_muhit_humidity (%)", 50)), 1),
                "quvvat": round(float(latest.get("Quvvati (kW)", 3)), 2),
            },
            "fault_counts": {str(k): int(v) for k, v in fault_counts.items()},
            "history": history
        })
    except Exception as e:
        logger.error(f"Sensor detail error: {e}")
        return jsonify({"error": str(e)}), 500

# --- CSV eksport ---
@app.route("/api/export/csv")
@login_required
def export_csv():
    try:
        if df is None or df.empty:
            return "Ma'lumot yo'q", 404
        export_df = df.sort_values("Timestamp", ascending=False).head(5000)
        output = io.StringIO()
        export_df.to_csv(output, index=False)
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'sensor_data_{datetime.datetime.now().strftime("%Y%m%d_%H%M")}.csv'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- PDF hisobot ---
@app.route("/api/export/pdf")
@login_required
def export_pdf():
    try:
        if df is None or df.empty:
            return "Ma'lumot yo'q", 404
        latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
        total = len(latest)
        safe = int((latest["Fault"] == 0).sum())
        warn = int((latest["Fault"] == 1).sum())
        danger = int((latest["Fault"] == 2).sum())

        # HTML -> PDF simulated with styled HTML
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Monitoring Hisobot - {now}</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
h1 {{ color: #0f2027; border-bottom: 3px solid #2c5364; padding-bottom: 10px; }}
h2 {{ color: #203a43; margin-top: 30px; }}
table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
th {{ background: #2c5364; color: white; }}
.safe {{ color: #10b981; font-weight: bold; }}
.warn {{ color: #f59e0b; font-weight: bold; }}
.danger {{ color: #ef4444; font-weight: bold; }}
.summary {{ display: flex; gap: 20px; margin: 20px 0; }}
.stat-box {{ padding: 15px 25px; border-radius: 10px; text-align: center; flex: 1; }}
</style></head><body>
<h1>⚡ Elektr Monitoring — Haftalik Hisobot</h1>
<p><strong>Sana:</strong> {now} | <strong>Tizim:</strong> Toshkent shahar, 11 tuman</p>

<h2>📊 Umumiy holat</h2>
<table>
<tr><th>Ko'rsatkich</th><th>Qiymat</th></tr>
<tr><td>Jami sensorlar</td><td><strong>{total}</strong></td></tr>
<tr><td>Havfsiz</td><td class="safe">{safe} ({round(100*safe/total,1)}%)</td></tr>
<tr><td>Ogohlantirish</td><td class="warn">{warn} ({round(100*warn/total,1)}%)</td></tr>
<tr><td>Muammo</td><td class="danger">{danger} ({round(100*danger/total,1)}%)</td></tr>
</table>

<h2>📈 O'rtacha qiymatlar</h2>
<table>
<tr><th>Parametr</th><th>Qiymat</th><th>Normal chegara</th></tr>
<tr><td>🌡️ Harorat</td><td>{latest["Muhit_harorat (C)"].mean():.1f}°C</td><td>&lt;40°C</td></tr>
<tr><td>🌬️ Shamol</td><td>{latest["Shamol_tezligi (km/h)"].mean():.1f} km/h</td><td>&lt;15 km/h</td></tr>
<tr><td>⚡ Chastota</td><td>{latest["Chastota (Hz)"].mean():.2f} Hz</td><td>49.5-50.5 Hz</td></tr>
<tr><td>🔌 Kuchlanish</td><td>{latest["Kuchlanish (V)"].mean():.1f} V</td><td>210-230 V</td></tr>
<tr><td>📳 Vibratsiya</td><td>{latest["Vibratsiya"].mean():.3f}</td><td>&lt;1.0</td></tr>
<tr><td>🔗 Sim holati</td><td>{latest["Sim_mexanik_holati (%)"].mean():.1f}%</td><td>&gt;85%</td></tr>
<tr><td>💨 Namlik</td><td>{latest["Atrof_muhit_humidity (%)"].mean():.1f}%</td><td>35-85%</td></tr>
<tr><td>⚙️ Quvvat</td><td>{latest["Quvvati (kW)"].mean():.2f} kW</td><td>≤5.0 kW</td></tr>
</table>

<h2>🔴 Muammoli sensorlar (Top 10)</h2>
<table>
<tr><th>Sensor ID</th><th>Tuman</th><th>Kuchlanish</th><th>Chastota</th><th>Vibratsiya</th></tr>"""
        danger_sensors = latest[latest["Fault"] == 2].head(10)
        for _, r in danger_sensors.iterrows():
            html += f"""<tr><td>{r['SensorID']}</td><td>{r['District']}</td>
<td class="danger">{r['Kuchlanish (V)']:.1f}V</td>
<td>{r['Chastota (Hz)']:.2f}Hz</td>
<td>{r['Vibratsiya']:.3f}</td></tr>"""
        html += f"""</table>
<hr>
<p style="text-align:center;color:#999;">© 2026 Toshkent Elektr Transsmissiya — Avtomatik hisobot</p>
</body></html>"""
        return send_file(
            io.BytesIO(html.encode('utf-8')),
            mimetype='text/html',
            as_attachment=True,
            download_name=f'hisobot_{datetime.datetime.now().strftime("%Y%m%d_%H%M")}.html'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Telegram alert ---
@app.route("/api/telegram/test", methods=["POST"])
@login_required
def telegram_test():
    """Test Telegram xabar yuborish"""
    try:
        bot_token = request.json.get("bot_token", TELEGRAM_BOT_TOKEN)
        chat_id = request.json.get("chat_id", TELEGRAM_CHAT_ID)
        if not bot_token or not chat_id:
            return jsonify({"error": "Bot token va chat_id kerak! .env ga TELEGRAM_BOT_TOKEN va TELEGRAM_CHAT_ID qo'shing."}), 400

        # Joriy holat haqida xabar
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        if df is not None and not df.empty:
            latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
            total = len(latest)
            safe = int((latest["Fault"] == 0).sum())
            warn = int((latest["Fault"] == 1).sum())
            danger = int((latest["Fault"] == 2).sum())
            msg = (f"⚡ *Monitoring Hisobot*\n"
                   f"📅 {now}\n\n"
                   f"📊 *Umumiy holat:*\n"
                   f"• Jami sensorlar: {total}\n"
                   f"• ✅ Havfsiz: {safe}\n"
                   f"• ⚠️ Ogohlantirish: {warn}\n"
                   f"• 🔴 Muammo: {danger}\n\n"
                   f"📈 *O'rtachalar:*\n"
                   f"• Harorat: {latest['Muhit_harorat (C)'].mean():.1f}°C\n"
                   f"• Kuchlanish: {latest['Kuchlanish (V)'].mean():.1f}V\n"
                   f"• Chastota: {latest['Chastota (Hz)'].mean():.2f}Hz")
        else:
            msg = f"⚡ *Monitoring Test*\n📅 {now}\n\nTizim ishlayapti, lekin ma'lumot yo'q."

        resp = http_requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=10
        )
        if resp.status_code == 200:
            return jsonify({"success": True, "message": "Telegram xabar yuborildi!"})
        else:
            return jsonify({"error": f"Telegram xato: {resp.text}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========================
# ERROR HANDLERS
# ========================
@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", error_code=404, message="Sahifa topilmadi!"), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return render_template("error.html", error_code=500, message="Serverda xatolik!"), 500

# ========================
# MAIN
# ========================
if __name__ == "__main__":
    # Telegram botni alohida threadda ishga tushirish
    import subprocess, threading
    def run_bot():
        subprocess.Popen(
            ["python", "telegram_bot.py"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("🤖 Telegram bot ishga tushirildi")

    logger.info("🚀 Server 0.0.0.0:5000 ishga tushmmoqda")
    app.run(host="0.0.0.0", port=5000, debug=True)
