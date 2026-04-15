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


# --- Asosiy sahifa ---
def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# --- Login ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        if USERS.get(username) == pw_hash:
            session["user"] = username
            return redirect(url_for("home"))
        return render_template("login.html", error="Noto'g'ri login yoki parol!")
    return render_template("login.html")

# --- Logout ---
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- Ob-havo (Toshkent, real vaqt) ---
def get_current_weather():
    try:
        cache_file = "data/tashkent_weather_cache.json"
        import json, time
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                cached = json.load(f)
            if time.time() - cached.get("fetched_at", 0) < 1800:
                return cached.get("weather")
        resp = http_requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": 41.2995, "longitude": 69.2401,
                    "current_weather": True, "hourly": "relativehumidity_2m",
                    "timezone": "Asia/Tashkent"},
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            cw = data.get("current_weather", {})
            weather = {
                "temperature": cw.get("temperature"),
                "windspeed": cw.get("windspeed"),
                "time": cw.get("time", "")[:16].replace("T", " "),
            }
            with open(cache_file, "w") as f:
                json.dump({"weather": weather, "fetched_at": time.time()}, f)
            return weather
    except Exception:
        pass
    return None

# --- Ob-havo API (JS uchun real-time) ---
@app.route("/api/weather")
def weather_api():
    weather = get_current_weather()
    if weather:
        return jsonify(weather)
    return jsonify({"error": "Ob-havo ma'lumoti yo'q"}), 503

# --- Bosh sahifa ---
@app.route("/")
@login_required
def home():
    return render_template("index.html")

# --- Xarita ---
@app.route("/map")
@login_required
def map_page():
    return render_template("map.html")

# --- Jadval ---
@app.route("/table")
@login_required
def table_page():
    return render_template("table.html")

# --- Grafiklar ---
@app.route("/graphs")
@login_required
def graphs_page():
    return render_template("graphs.html")

# --- Model ---
@app.route("/model", methods=["GET", "POST"])
@login_required
def model_page():
    if request.method != "POST":
        return render_template("model.html", result=None)

    def pval(name, default):
        try: return float(request.form.get(name, default))
        except: return float(default)

    harorat    = pval("harorat", 25)
    shamol     = pval("shamol", 7)
    chastota   = pval("chastota", 50)
    kuchlanish = pval("kuchlanish", 220)
    vibratsiya = pval("vibratsiya", 0.5)
    sim_holati = pval("sim_holati", 90)
    humidity   = pval("humidity", 60)
    quvvat     = pval("quvvat", 3.0)

    def check(val, normal_ok, warn_ok, name, unit, icon):
        if normal_ok(val):
            return {"status":"normal",  "icon":icon,"name":name,"value":round(val,2),"unit":unit,"msg":"Qiymat normal chegarada"}
        elif warn_ok(val):
            return {"status":"warning", "icon":icon,"name":name,"value":round(val,2),"unit":unit,"msg":"Ogohlantirishli — kuzatuv kerak"}
        else:
            return {"status":"danger",  "icon":icon,"name":name,"value":round(val,2),"unit":unit,"msg":"Xavfli! Zudlik bilan tekshiring"}

    params = [
        check(harorat,    lambda v: v<40,                lambda v: v<45,               "Muhit harorat","°C","🌡️"),
        check(shamol,     lambda v: v<15,                lambda v: v<25,               "Shamol tezligi","km/h","💨"),
        check(chastota,   lambda v: 49.5<=v<=50.5,       lambda v: 49.0<=v<=51.0,      "Chastota","Hz","〰️"),
        check(kuchlanish, lambda v: 210<=v<=230,         lambda v: 200<=v<=240,        "Kuchlanish","V","⚡"),
        check(vibratsiya, lambda v: v<1.0,               lambda v: v<1.5,              "Vibratsiya","","📳"),
        check(sim_holati, lambda v: v>85,                lambda v: v>75,               "Sim holati","%","🔗"),
        check(humidity,   lambda v: 35<=v<=85,           lambda v: 30<=v<=90,          "Namlik","%","💧"),
        check(quvvat,     lambda v: v<=5.0,              lambda v: v<=5.5,             "Quvvat","kW","⚙️"),
    ]

    d_cnt = sum(1 for p in params if p["status"]=="danger")
    w_cnt = sum(1 for p in params if p["status"]=="warning")
    n_cnt = sum(1 for p in params if p["status"]=="normal")

    if d_cnt >= 1:
        level, level_text, level_msg = "danger","🔴 Xavfli holat","Bir yoki bir nechta parametr xavfli chegarada. Zudlik bilan xizmat ko'rsatish zarur!"
    elif w_cnt >= 1:
        level, level_text, level_msg = "warning","🟡 Ogohlantirish","Ba'zi parametrlar me'yordan tashqarida. Kuzatuv kuchaytiring."
    else:
        level, level_text, level_msg = "normal","✅ Havfsiz holat","Barcha parametrlar normal chegarada. Tizim yaxshi ishlayapti."

    from types import SimpleNamespace
    values = SimpleNamespace(harorat=harorat, shamol=shamol, chastota=chastota,
                             kuchlanish=kuchlanish, vibratsiya=vibratsiya,
                             sim_holati=sim_holati, humidity=humidity, quvvat=quvvat)
    result = SimpleNamespace(level=level, level_text=level_text, level_msg=level_msg,
                             normal_count=n_cnt, warning_count=w_cnt, danger_count=d_cnt,
                             params=params, values=values)
    return render_template("model.html", result=result)

# --- Yangi dashboard ---
@app.route("/new-dashboard")
@login_required
def new_dashboard():
    return render_template("new_dashboard.html")


# --- Ma'lumot va modelni yuklash funksiyasi ---
def load_data_and_model():
    df, hybrid_model = None, None
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
        try:
            hybrid_model = pickle.loads(merged)
        except Exception as e:
            logger.error(f"Model yuklashda xato: {e}")
    return df, hybrid_model

# --- Ma'lumot va modelni global yuklash ---
df, hybrid_model = None, None
def reload_data_and_model():
    global df, hybrid_model
    df, hybrid_model = load_data_and_model()

reload_data_and_model()

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
    """Tuman (latitude, longitude) bo‘yicha 7 kunlik ob-havo prognozi"""
    try:
        import requests
        # Parametrlarni olish (query string)
        lat = request.args.get("latitude", type=float, default=41.3111)
        lon = request.args.get("longitude", type=float, default=69.2797)
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,wind_speed_10m_max,precipitation_sum",
                "timezone": "Asia/Tashkent",
                "forecast_days": 7
            },
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json().get("daily", {})
            return jsonify({"weather": data})
        else:
            return jsonify({"error": "Ob-havo ma'lumoti olinmadi"}), 503
    except Exception as e:
        logger.error(f"Forecast error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/forecast-params")
def forecast_params_api():
    if df is None or df.empty:
        return jsonify({"error": "Ma'lumot yo'q"}), 404
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
        if hybrid_model is not None:
            result["xavf"] = [int(x) for x in hybrid_model.predict(last_week[feature_cols])]
        elif "Fault" in last_week.columns:
            result["xavf"] = [int(round(x)) for x in last_week["Fault"].fillna(0).tolist()]
        else:
            result["xavf"] = [0] * len(last_week)
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
        # NaN Fault qiymatlarini 0 (xavfsiz) deb hisoblash
        latest["Fault"] = latest["Fault"].fillna(0).round().astype(int).clip(0, 2)
        safe_count   = int((latest["Fault"] == 0).sum())
        warn_count   = int((latest["Fault"] == 1).sum())
        danger_count = int((latest["Fault"] == 2).sum())
        total = safe_count + warn_count + danger_count  # mos kelishi uchun
        safe_percent = round(100 * safe_count / total, 1) if total > 0 else 0

        # So'nggi 7 kun uchun xavfli vaqtlar
        last_week = df[df["Timestamp"] >= (datetime.datetime.now() - datetime.timedelta(days=7))]
        week_dangers = int((last_week["Fault"] == 2).sum()) if not last_week.empty else 0
        week_warns = int((last_week["Fault"] == 1).sum()) if not last_week.empty else 0

        # Tumanlar bo'yicha statistika (koordinata ko'rinishidagi nomlarni chiqarib tashlash)
        def is_real_district(name):
            try:
                float(str(name))
                return False  # raqam = koordinata, o'tkazib yuborish
            except (ValueError, TypeError):
                return bool(str(name).strip())

        valid = latest[latest["District"].apply(is_real_district)]
        tuman_stats = valid.groupby("District").agg(
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

        district = request.args.get('district', None)
        latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
        if district:
            latest = latest[latest["District"] == district]

        def safe_float(val, default=0.0, ndigits=1):
            try:
                v = float(val)
                return round(v, ndigits) if v == v else default  # NaN check
            except (TypeError, ValueError):
                return default

        def safe_int(val, default=0):
            try:
                v = float(val)
                return int(v) if v == v else default
            except (TypeError, ValueError):
                return default

        result = []
        for idx, row in latest.iterrows():
            fault = safe_int(row.get("Fault", 0))
            result.append({
                "SensorID": str(row.get("SensorID", "")),
                "District": str(row.get("District", "Unknown")),
                "Latitude": safe_float(row.get("Latitude", 41.3111), 41.3111, 6),
                "Longitude": safe_float(row.get("Longitude", 69.2797), 69.2797, 6),
                "Harorat": safe_float(row.get("Muhit_harorat (C)", 25), 25),
                "Shamol": safe_float(row.get("Shamol_tezligi (km/h)", 7), 7),
                "Chastota": safe_float(row.get("Chastota (Hz)", 50), 50, 2),
                "Kuchlanish": safe_float(row.get("Kuchlanish (V)", 220), 220),
                "Vibratsiya": safe_float(row.get("Vibratsiya", 0.5), 0.5, 4),
                "Sim_holati": safe_float(row.get("Sim_mexanik_holati (%)", 90), 90),
                "Humidity": safe_float(row.get("Atrof_muhit_humidity (%)", 50), 50),
                "Quvvat": safe_float(row.get("Quvvati (kW)", 3), 3, 2),
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
