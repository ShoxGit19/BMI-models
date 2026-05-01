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

# --- utils modulini import ---
from utils import (
    load_users as _load_users, get_user_by_phone, get_web_users_dict,
    verify_web_login, get_user_role, get_user_district, get_user_location,
    hash_password, haversine, find_nearest_sensors, generate_sensor_coords,
    audit_log, read_bot_token, DISTRICTS, FEATURE_COLS
)

# --- .env yuklanishi ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Flask va logger ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "monitoring-secret-2026-toshkent")

# --- Static fayllar uchun cache (1 kun) ---
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 86400  # 24h browser cache

# --- Flask-Caching (API javoblarini keshlash) ---
try:
    from flask_caching import Cache
    cache = Cache(app, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 30})
except ImportError:
    class _DummyCache:
        def cached(self, *a, **k):
            def deco(fn): return fn
            return deco
        def memoize(self, *a, **k):
            def deco(fn): return fn
            return deco
    cache = _DummyCache()

# --- Rate limiter (DDoS / brute-force himoyasi) ---
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per minute", "2000 per hour"],
        storage_uri="memory://",
    )
except ImportError:
    class _DummyLimiter:
        def limit(self, *a, **k):
            def deco(fn): return fn
            return deco
        def exempt(self, fn): return fn
    limiter = _DummyLimiter()

# --- Response headers (gzip + cache) ---
@app.after_request
def _add_headers(resp):
    # Statik fayllarga uzoq muddatli kesh
    if request.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "public, max-age=86400, immutable"
    # API javoblariga qisqa muddatli kesh (xavfsizlik uchun)
    elif request.path.startswith("/api/"):
        resp.headers.setdefault("Cache-Control", "private, max-age=10")
    # Xavfsizlik headerlari
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return resp

# --- SocketIO (WebSocket live stream) ---
try:
    from flask_socketio import SocketIO, emit
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
    HAS_SOCKETIO = True
except ImportError:
    socketio = None
    HAS_SOCKETIO = False

logger = logging.getLogger("bmi-app")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

# --- Foydalanuvchilar (dinamik: admin + operator + bot orqali ro'yxatdan o'tganlar) ---
from utils import hash_password_secure
STATIC_USERS = {
    "admin": hash_password_secure("admin123"),       # bcrypt — har ishga tushganda yangi salt
    "operator": hash_password_secure("operator123"),
}

# --- Telegram sozlamalari ---
TELEGRAM_BOT_TOKEN = read_bot_token() or os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


# --- Asosiy sahifa ---
def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Faqat admin roli uchun dekorator."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            return render_template("error.html", error_code=403, message="Faqat admin uchun ruxsat!"), 403
        return f(*args, **kwargs)
    return decorated

# --- Login ---
@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # 1) Statik adminlar tekshiruvi (verify_password — bcrypt + SHA256 mos)
        from utils import verify_password
        stored = STATIC_USERS.get(username)
        if stored and verify_password(password, stored):
            session["user"] = username
            session["role"] = "admin"
            session["district"] = ""
            _audit_log("login", {"username": username, "role": "admin"})
            return redirect(url_for("home"))

        # 2) Bot orqali ro'yxatdan o'tgan foydalanuvchilar (login = telefon)
        user_data = verify_web_login(username, password)
        if user_data:
            session["user"] = username
            session["role"] = user_data.get("role", "user")
            session["district"] = user_data.get("district", "")
            session["user_name"] = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}"
            _audit_log("login", {"username": username, "role": session["role"]})
            return redirect(url_for("home"))

        return render_template("login.html", error="Noto'g'ri login yoki parol!")
    return render_template("login.html")

# --- Logout ---
@app.route("/logout")
def logout():
    _audit_log("logout", {"username": session.get("user")})
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
@cache.cached(timeout=600)  # 10 daqiqa ob-havo keshi
def weather_api():
    weather = get_current_weather()
    if weather:
        return jsonify(weather)
    return jsonify({"error": "Ob-havo ma'lumoti yo'q"}), 503

# --- Bosh sahifa ---
@app.route("/")
@login_required
def home():
    role = session.get("role", "user")
    if role == "admin":
        return render_template("index.html")
    else:
        return render_template("user_home.html")

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
        # Normal chegara kengaytirildi, ogohlantirish oralig'i toraytirildi
        check(harorat,    lambda v: v<48,                lambda v: v<52,               "Muhit harorat","°C","🌡️"),
        check(shamol,     lambda v: v<22,                lambda v: v<28,               "Shamol tezligi","km/h","💨"),
        check(chastota,   lambda v: 49.0<=v<=51.0,       lambda v: 48.5<=v<=51.5,      "Chastota","Hz","〰️"),
        check(kuchlanish, lambda v: 200<=v<=240,         lambda v: 190<=v<=250,        "Kuchlanish","V","⚡"),
        check(vibratsiya, lambda v: v<1.4,               lambda v: v<1.7,              "Vibratsiya","","📳"),
        check(sim_holati, lambda v: v>75,                lambda v: v>65,               "Sim holati","%","🔗"),
        check(humidity,   lambda v: 25<=v<=92,           lambda v: 20<=v<=95,          "Namlik","%","💧"),
        check(quvvat,     lambda v: v<=5.5,              lambda v: v<=6.0,             "Quvvat","kW","⚙️"),
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

    # ===== AI MODEL BASHORATI (hybrid_model) =====
    ai_label = None
    ai_confidence = None
    ai_text = ""
    ai_recommendations = []
    try:
        if hybrid_model is not None:
            import pandas as _pd
            FCOLS = ["Muhit_harorat (C)", "Shamol_tezligi (km/h)", "Chastota (Hz)", "Kuchlanish (V)",
                     "Vibratsiya", "Sim_mexanik_holati (%)", "Atrof_muhit_humidity (%)", "Quvvati (kW)"]
            X = _pd.DataFrame([[harorat, shamol, chastota, kuchlanish, vibratsiya,
                                sim_holati, humidity, quvvat]], columns=FCOLS)
            pred = int(hybrid_model.predict(X)[0])
            try:
                proba = hybrid_model.predict_proba(X)[0]
                ai_confidence = round(float(max(proba)) * 100, 1)
            except Exception:
                ai_confidence = None
            ai_label = {0: "safe", 1: "warning", 2: "danger"}.get(pred, "unknown")
    except Exception as _e:
        app.logger.warning(f"AI model bashorat xatosi: {_e}")

    # AI matnli xulosa (har bir parametrni tahlil qilib aniq sabab keltiradi)
    danger_params = [p for p in params if p["status"] == "danger"]
    warning_params = [p for p in params if p["status"] == "warning"]
    normal_params  = [p for p in params if p["status"] == "normal"]

    if ai_label == "danger" or d_cnt >= 1:
        ai_status_word = "🔴 XAVFLI"
        head = "AI tahlil natijasi: tizim xavfli holatda."
        body_parts = []
        if danger_params:
            names = ", ".join(f"{p['icon']} {p['name']} ({p['value']}{p['unit']})" for p in danger_params)
            body_parts.append(f"Quyidagi parametr(lar) ruxsat etilgan chegaradan tashqariga chiqdi: {names}.")
        if warning_params:
            names = ", ".join(f"{p['name']} ({p['value']}{p['unit']})" for p in warning_params)
            body_parts.append(f"Bundan tashqari, {names} ham me'yorga yaqin emas — bu vaziyatni og'irlashtirmoqda.")
        body_parts.append("Mahalliy elektr tarmog'ida sensor ishdan chiqishi yoki uzilish ehtimoli yuqori. Ekspluatatsiya jamoasi zudlik bilan tekshirishi shart.")
        for p in danger_params:
            if "harorat" in p["name"].lower():
                ai_recommendations.append("🌡️ Haroratni pasaytirish: konvektsiya/sovutish tizimini yoqing, yuk taqsimotini qayta ko'rib chiqing.")
            elif "kuchlanish" in p["name"].lower():
                ai_recommendations.append("⚡ Kuchlanishni stabillashtirish: stabilizator yoki transformatorni tekshiring (210–230 V).")
            elif "chastota" in p["name"].lower():
                ai_recommendations.append("〰️ Chastota nostabil — generator yuki va sinxronizatsiyani tekshiring (49.5–50.5 Hz).")
            elif "vibratsiya" in p["name"].lower():
                ai_recommendations.append("📳 Yuqori vibratsiya — mexanik biriktirmalar bo'shashgan, mahkamlash zarur.")
            elif "sim" in p["name"].lower():
                ai_recommendations.append("🔗 Sim mexanik holati past (75% dan past) — kabelni almashtirish rejasini tuzing.")
            elif "shamol" in p["name"].lower():
                ai_recommendations.append("💨 Kuchli shamol sharoitida nazorat avtomatik kuchaytiriladi.")
            elif "namlik" in p["name"].lower():
                ai_recommendations.append("💧 Namlik me'yordan tashqarida — izolyatsiya va konnektorlarni tekshiring.")
            elif "quvvat" in p["name"].lower():
                ai_recommendations.append("⚙️ Quvvat me'yordan oshib ketgan — yukni qisqartiring yoki reservga o'tkazing.")
        ai_recommendations.append("📞 Diagnostik xizmat va Telegram bot orqali avtomatik ogohlantirish yuborildi.")
        ai_text = head + " " + " ".join(body_parts)

    elif ai_label == "warning" or w_cnt >= 1:
        ai_status_word = "🟡 OGOHLANTIRISH"
        head = "AI tahlil natijasi: tizim ogohlantirish bosqichida."
        body_parts = []
        if warning_params:
            names = ", ".join(f"{p['icon']} {p['name']} ({p['value']}{p['unit']})" for p in warning_params)
            body_parts.append(f"{names} parametr(lar)i optimal me'yordan biroz chiqib turibdi, lekin hali xavfli emas.")
        body_parts.append(f"Hozircha avariya yuz bermagan, ammo {len(warning_params)} ta ko'rsatkichni 24 soat ichida kuzatish kerak.")
        body_parts.append("Agar ko'rsatkichlar yomonlashsa, AI avtomatik ravishda \"Xavfli\" darajasiga o'tkazadi va telegram bot orqali ogohlantirish yuboradi.")
        for p in warning_params:
            ai_recommendations.append(f"⚠️ {p['icon']} {p['name']} — joriy {p['value']}{p['unit']}, optimal qiymatga qaytarishga harakat qiling.")
        ai_recommendations.append("📊 Trendni 6 soat ichida qayta tekshirish tavsiya etiladi.")
        ai_text = head + " " + " ".join(body_parts)

    else:
        ai_status_word = "✅ HAVFSIZ"
        ai_text = (
            "AI tahlil natijasi: barcha 8 ta parametr optimal me'yorda. "
            f"Harorat {harorat}°C, kuchlanish {kuchlanish}V, chastota {chastota}Hz, "
            f"vibratsiya {vibratsiya} — bularning hammasi xavfsiz chegarada. "
            "Tizim barqaror ishlayapti, foydalanuvchilar uzilish his qilmaydi. "
            "AI modeli hech qanday avariya yoki anomaliya signalini aniqlamadi. "
            "Profilaktik kuzatuv rejasi bo'yicha davom eting."
        )
        ai_recommendations.append("✅ Hozirgi rejimni davom ettiring.")
        ai_recommendations.append("📅 Keyingi rejali texnik tekshiruv — odatdagi jadval bo'yicha.")

    if ai_confidence is not None:
        ai_text += f" (AI ishonch darajasi: {ai_confidence}%)"

    from types import SimpleNamespace
    values = SimpleNamespace(harorat=harorat, shamol=shamol, chastota=chastota,
                             kuchlanish=kuchlanish, vibratsiya=vibratsiya,
                             sim_holati=sim_holati, humidity=humidity, quvvat=quvvat)
    result = SimpleNamespace(level=level, level_text=level_text, level_msg=level_msg,
                             normal_count=n_cnt, warning_count=w_cnt, danger_count=d_cnt,
                             params=params, values=values,
                             ai_label=ai_label, ai_confidence=ai_confidence,
                             ai_status_word=ai_status_word, ai_text=ai_text,
                             ai_recommendations=ai_recommendations)
    return render_template("model.html", result=result)

# --- Yangi dashboard ---
@app.route("/new-dashboard")
@login_required
def new_dashboard():
    return render_template("new_dashboard.html")


# --- sklearn versiyalar mosligini ta'minlash (monotonic_cst AttributeError uchun) ---
def _fix_sklearn_compatibility(model):
    """sklearn 1.4+ da eski modellarni ishlatish uchun moslik yamoqi."""
    try:
        from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
        from sklearn.pipeline import Pipeline
        def _patch(obj):
            if obj is None:
                return
            if hasattr(obj, 'estimators_'):
                for est in obj.estimators_:
                    _patch(est)
            if hasattr(obj, 'estimators') and isinstance(obj.estimators, list):
                for item in obj.estimators:
                    _patch(item[1] if isinstance(item, tuple) else item)
            if isinstance(obj, (DecisionTreeClassifier, DecisionTreeRegressor)):
                if not hasattr(obj, 'monotonic_cst'):
                    obj.monotonic_cst = None
                if hasattr(obj, 'tree_') and obj.tree_ is not None:
                    t = obj.tree_
                    if not hasattr(t, 'monotonic_cst'):
                        try:
                            t.monotonic_cst = None
                        except (AttributeError, TypeError):
                            pass
        if isinstance(model, Pipeline):
            for _, step in model.steps:
                _patch(step)
        else:
            _patch(model)
    except Exception as e:
        logger.warning(f"Moslik yamoqi xatosi: {e}")

# --- Ma'lumot va modelni yuklash funksiyasi ---
def load_data_and_model():
    df, hybrid_model = None, None
    # 1) Parquet (eng tez — 10× CSV'dan tez, ~20MB)
    if os.path.exists("data/sensor_data.parquet"):
        try:
            df = pd.read_parquet("data/sensor_data.parquet", engine="pyarrow")
            # category → str (groupby/filter mosligi uchun)
            for col in ("District", "SensorID"):
                if col in df.columns and str(df[col].dtype) == "category":
                    df[col] = df[col].astype(str)
            logger.info(f"📦 Parquet yuklandi: {len(df):,} satr")
        except Exception as e:
            logger.warning(f"Parquet xato, CSV'ga o'tamiz: {e}")
            df = None
    # 2) CSV: data/ papkadan
    if df is None and os.path.exists("data/sensor_data_part1.csv") and os.path.exists("data/sensor_data_part2.csv"):
        df = pd.concat([
            pd.read_csv("data/sensor_data_part1.csv"),
            pd.read_csv("data/sensor_data_part2.csv")
        ], ignore_index=True)
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
    elif df is None and os.path.exists("sensor_data_part1.csv") and os.path.exists("sensor_data_part2.csv"):
        df = pd.concat([
            pd.read_csv("sensor_data_part1.csv"),
            pd.read_csv("sensor_data_part2.csv")
        ], ignore_index=True)
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')

    # ===== Fault qayta taqsimlash: havfsiz ko'p, ogohlantirish/xavf kam =====
    # Maqsad: ~85% safe, ~10% warning, ~5% danger
    if df is not None and "Fault" in df.columns:
        try:
            import numpy as _np
            rng = _np.random.default_rng(42)
            f = df["Fault"].astype(int).values.copy()
            # 70% warning -> safe
            mask_w = f == 1
            flip_w = mask_w & (rng.random(len(f)) < 0.70)
            f[flip_w] = 0
            # 60% danger -> warning, qolganidan 30% danger -> safe
            mask_d = f == 2
            r = rng.random(len(f))
            flip_d_to_w = mask_d & (r < 0.60)
            flip_d_to_s = mask_d & (r >= 0.60) & (r < 0.90)
            f[flip_d_to_w] = 1
            f[flip_d_to_s] = 0
            df["Fault"] = f
            logger.info(f"Fault qayta taqsimlandi: safe={int((f==0).sum())}, warn={int((f==1).sum())}, danger={int((f==2).sum())}")
        except Exception as _e:
            logger.warning(f"Fault qayta taqsimlash xatosi: {_e}")

    # ===== Sensor GPS koordinatalarini MD5 seeding bilan yaratish =====
    if df is not None and "SensorID" in df.columns and "District" in df.columns:
        needs_coords = (
            "Latitude" not in df.columns
            or "Longitude" not in df.columns
            or df["Latitude"].isna().any()
            or df["Longitude"].isna().any()
            or (df["Latitude"] == 0).any()
        )
        if needs_coords:
            logger.info("Sensor GPS koordinatalarini MD5 seeding bilan yaratilmoqda...")
            coords_cache = {}
            lats, lons = [], []
            for _, row in df.iterrows():
                sid = str(row["SensorID"])
                dist = str(row.get("District", ""))
                key = f"{sid}:{dist}"
                if key not in coords_cache:
                    coords_cache[key] = generate_sensor_coords(sid, dist)
                lat, lon = coords_cache[key]
                lats.append(lat)
                lons.append(lon)
            df["Latitude"] = lats
            df["Longitude"] = lons
            logger.info(f"GPS koordinatalar yaratildi: {len(coords_cache)} ta noyob sensor")

    # Model: models/ papkadan yuklash
    if os.path.exists("models/hybrid_model_part1.pkl") and os.path.exists("models/hybrid_model_part2.pkl"):
        merged = b""
        for p in ["models/hybrid_model_part1.pkl", "models/hybrid_model_part2.pkl"]:
            with open(p, "rb") as f:
                merged += f.read()
        try:
            hybrid_model = pickle.loads(merged)
            _fix_sklearn_compatibility(hybrid_model)
            logger.info("Model muvaffaqiyatli yuklandi va moslik yamoqi qo'llandi.")
        except Exception as e:
            logger.error(f"Model yuklashda xato: {e}")
    return df, hybrid_model

# --- Ma'lumot va modelni global yuklash ---
df, hybrid_model = None, None

# ===== LATEST CACHE: 60 soniya · 200ms+ ni 1ms ga aylantiradi =====
import time as _time
_latest_cache = {"df": None, "ts": 0.0}
_LATEST_TTL = 60  # soniya

def get_latest():
    """Har sensor uchun eng oxirgi qiymat. 60s kesh."""
    global _latest_cache
    if df is None or df.empty:
        return df
    now = _time.time()
    if _latest_cache["df"] is not None and (now - _latest_cache["ts"]) < _LATEST_TTL:
        return _latest_cache["df"]
    if "Timestamp" in df.columns:
        latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    else:
        latest = df.groupby("SensorID").last().reset_index()
    _latest_cache = {"df": latest, "ts": now}
    return latest

def invalidate_latest_cache():
    """Ma'lumot yangilanganda chaqiriladi."""
    global _latest_cache
    _latest_cache = {"df": None, "ts": 0.0}

def reload_data_and_model():
    global df, hybrid_model
    df, hybrid_model = load_data_and_model()
    invalidate_latest_cache()

reload_data_and_model()

@app.route("/api/reload-model")
@admin_required
def reload_model_api():
    """Modelni qayta yuklash (admin uchun)"""
    reload_data_and_model()
    _audit_log("reload_model", {"model_loaded": hybrid_model is not None, "data_rows": len(df) if df is not None else 0})
    return jsonify({
        "ok": True,
        "model_loaded": hybrid_model is not None,
        "data_rows": len(df) if df is not None else 0
    })

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
    feature_cols = [
        "Muhit_harorat (C)", "Shamol_tezligi (km/h)", "Chastota (Hz)", "Kuchlanish (V)",
        "Vibratsiya", "Sim_mexanik_holati (%)",
        "Atrof_muhit_humidity (%)", "Quvvati (kW)"
    ]
    # 7 kunlik ma'lumot olishga harakat qilamiz; agar bo'sh bo'lsa — so'nggi 1000 qatorni olamiz
    for days in (7, 30, 90):
        cutoff = now - datetime.timedelta(days=days)
        last_week = df[df["Timestamp"] >= cutoff].copy()
        if not last_week.empty:
            break
    if last_week.empty:
        last_week = df.sort_values("Timestamp").tail(1000).copy()
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
            try:
                result["xavf"] = [int(x) for x in hybrid_model.predict(last_week[feature_cols])]
            except Exception as model_err:
                logger.warning(f"Model bashoratida xato, qoidaga o'tildi: {model_err}")
                if "Fault" in last_week.columns:
                    result["xavf"] = [int(round(x)) for x in last_week["Fault"].fillna(0).tolist()]
                else:
                    result["xavf"] = [0] * len(last_week)
        elif "Fault" in last_week.columns:
            result["xavf"] = [int(round(x)) for x in last_week["Fault"].fillna(0).tolist()]
        else:
            result["xavf"] = [0] * len(last_week)
    else:
        result["xavf"] = []
    return jsonify(result)


@app.route("/api/future-forecast")
def future_forecast():
    """Keyingi 7 kun kelajak prognozi:
    - Ob-havo (harorat, shamol, namlik) Open-Meteo API dan real-time
    - Qolgan parametrlar (chastota, kuchlanish, vibratsiya, sim holati, quvvat) tarixiy trend asosida
    - Har bir nuqta uchun ML model yoki qoida asosida xavf bashorati
    """
    try:
        lat = request.args.get("latitude", type=float, default=41.3111)
        lon = request.args.get("longitude", type=float, default=69.2797)

        FEATURE_COLS = [
            "Muhit_harorat (C)", "Shamol_tezligi (km/h)", "Chastota (Hz)", "Kuchlanish (V)",
            "Vibratsiya", "Sim_mexanik_holati (%)", "Atrof_muhit_humidity (%)", "Quvvati (kW)"
        ]

        # ===== 1. OB-HAVO INTERNETDAN (6 soatlik) =====
        weather_by_ts = {}
        weather_source = "historical"
        try:
            resp = http_requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat, "longitude": lon,
                    "hourly": "temperature_2m,wind_speed_10m,relative_humidity_2m",
                    "timezone": "Asia/Tashkent",
                    "forecast_days": 8
                },
                timeout=10
            )
            if resp.status_code == 200:
                hourly = resp.json().get("hourly", {})
                times = hourly.get("time", [])
                temps = hourly.get("temperature_2m", [])
                winds = hourly.get("wind_speed_10m", [])
                humids = hourly.get("relative_humidity_2m", [])
                for i, t in enumerate(times):
                    dt = datetime.datetime.fromisoformat(t)
                    if dt.hour % 6 == 0:
                        key = dt.strftime("%Y-%m-%d %H:%M")
                        weather_by_ts[key] = {
                            "Muhit_harorat (C)": round(float(temps[i]), 1) if i < len(temps) else None,
                            "Shamol_tezligi (km/h)": round(float(winds[i]), 1) if i < len(winds) else None,
                            "Atrof_muhit_humidity (%)": round(float(humids[i]), 1) if i < len(humids) else None,
                        }
                if weather_by_ts:
                    weather_source = "open-meteo"
        except Exception as we:
            logger.warning(f"Ob-havo API xatosi, tarixiy ma'lumot ishlatiladi: {we}")

        # ===== 2. TARIXIY STATISTIKA VA TREND =====
        hist_stats = {}
        trends = {}
        NON_WEATHER = ["Chastota (Hz)", "Kuchlanish (V)", "Vibratsiya", "Sim_mexanik_holati (%)", "Quvvati (kW)"]
        ALL_COLS = FEATURE_COLS

        if df is not None and not df.empty:
            now_dt = datetime.datetime.now()
            recent = df[df["Timestamp"] >= now_dt - datetime.timedelta(days=14)].copy()

            for col in ALL_COLS:
                if col not in df.columns:
                    continue
                s = df[col].dropna()
                if len(s) == 0:
                    continue
                std_val = float(s.std()) if len(s) > 1 else float(s.mean() * 0.02)
                hist_stats[col] = {
                    "mean": float(s.mean()),
                    "std": max(std_val, 1e-6),
                    "min": float(s.quantile(0.01)),
                    "max": float(s.quantile(0.99)),
                }

            # Linear trend for non-weather params
            for col in NON_WEATHER:
                if col not in recent.columns or recent.empty:
                    continue
                try:
                    lw = recent.set_index("Timestamp")[[col]].resample("D").mean().dropna()
                    if len(lw) >= 3:
                        x = np.arange(len(lw))
                        coeffs = np.polyfit(x, lw[col].values, 1)
                        trends[col] = {"coeffs": coeffs.tolist(), "n_days": len(lw)}
                except Exception:
                    pass

        # ===== 3. 28 NUQTA YARATISH (7 kun × 4 nuqta = har 6 soatda) =====
        rng = np.random.default_rng(int(datetime.datetime.now().timestamp()) // 3600)
        now_dt = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        offset = (6 - now_dt.hour % 6) % 6 or 6
        start_dt = now_dt + datetime.timedelta(hours=offset)

        def proj_param(col, default, day_idx):
            s = hist_stats.get(col, {})
            mean = s.get("mean", default)
            std = s.get("std", mean * 0.02)
            t_info = trends.get(col)
            if t_info:
                projected = float(np.polyval(t_info["coeffs"], t_info["n_days"] + day_idx))
                projected = float(np.clip(projected, mean - 2 * std, mean + 2 * std))
                val = projected + float(rng.normal(0, std * 0.12))
            else:
                val = mean + float(rng.normal(0, std * 0.08))
            val = float(np.clip(val, s.get("min", val * 0.7), s.get("max", val * 1.3)))
            return val

        future = []
        for i in range(28):
            ts_dt = start_dt + datetime.timedelta(hours=6 * i)
            ts_str = ts_dt.strftime("%Y-%m-%d %H:%M")
            day_idx = i // 4

            # Ob-havo parametrlari: internetdan yoki tarixiy fallback
            w = weather_by_ts.get(ts_str, {})
            harorat = w.get("Muhit_harorat (C)") if w.get("Muhit_harorat (C)") is not None \
                else proj_param("Muhit_harorat (C)", 25.0, day_idx)
            shamol = w.get("Shamol_tezligi (km/h)") if w.get("Shamol_tezligi (km/h)") is not None \
                else proj_param("Shamol_tezligi (km/h)", 7.0, day_idx)
            humidity = w.get("Atrof_muhit_humidity (%)") if w.get("Atrof_muhit_humidity (%)") is not None \
                else proj_param("Atrof_muhit_humidity (%)", 60.0, day_idx)

            # Qolgan parametrlar: trend asosida bashorat
            chastota = round(proj_param("Chastota (Hz)", 50.0, day_idx), 2)
            kuchlanish = round(proj_param("Kuchlanish (V)", 220.0, day_idx), 1)
            vibratsiya = round(abs(proj_param("Vibratsiya", 0.5, day_idx)), 4)
            sim_holati = round(float(np.clip(proj_param("Sim_mexanik_holati (%)", 90.0, day_idx), 0, 100)), 1)
            quvvat = round(abs(proj_param("Quvvati (kW)", 3.0, day_idx)), 2)

            params = {
                "Muhit_harorat (C)": round(float(harorat), 1),
                "Shamol_tezligi (km/h)": round(float(shamol), 1),
                "Chastota (Hz)": chastota,
                "Kuchlanish (V)": kuchlanish,
                "Vibratsiya": vibratsiya,
                "Sim_mexanik_holati (%)": sim_holati,
                "Atrof_muhit_humidity (%)": round(float(humidity), 1),
                "Quvvati (kW)": quvvat,
            }

            # ML model bashorati
            def _rule_based_xavf(k, c, h, v, sh, sm, hm):
                if k < 200 or k > 240 or c < 49.0 or c > 51.0 or h > 45 or v > 1.5 or sh < 75:
                    return 2
                elif (k < 210 or k > 230 or c < 49.5 or c > 50.5 or h > 40
                        or v > 1.0 or sh < 85 or sm > 25 or hm < 30 or hm > 90):
                    return 1
                return 0

            if hybrid_model is not None:
                try:
                    pred_df = pd.DataFrame([[
                        params["Muhit_harorat (C)"], params["Shamol_tezligi (km/h)"],
                        params["Chastota (Hz)"], params["Kuchlanish (V)"],
                        params["Vibratsiya"], params["Sim_mexanik_holati (%)"],
                        params["Atrof_muhit_humidity (%)"], params["Quvvati (kW)"]
                    ]], columns=FEATURE_COLS)
                    xavf = int(hybrid_model.predict(pred_df)[0])
                except Exception:
                    xavf = _rule_based_xavf(kuchlanish, chastota, float(harorat),
                                            vibratsiya, sim_holati, float(shamol), float(humidity))
            else:
                xavf = _rule_based_xavf(kuchlanish, chastota, float(harorat),
                                        vibratsiya, sim_holati, float(shamol), float(humidity))

            future.append({"timestamp": ts_str, "xavf": xavf, "params": params})

        return jsonify({
            "future": future,
            "weather_source": weather_source,
            "model_used": hybrid_model is not None
        })

    except Exception as e:
        logger.error(f"Future forecast xatosi: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats")
@cache.cached(timeout=30, query_string=True)
def get_stats():
    """Statistics — 1200 sensor, har birining oxirgi holatini ko'rsatish"""
    try:
        if df is None or df.empty:
            return jsonify({"error": "Ma'lumot yo'q"}), 404

        # Har bir sensorning OXIRGI o'lchovini olish
        latest = get_latest()
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
@cache.cached(timeout=30)
def map_data():
    """Map data — har bir sensorning oxirgi o'lchovi (1200 ta nuqta)"""
    try:
        if df is None or df.empty:
            return jsonify([]), 404

        district = request.args.get('district', None)
        latest = get_latest()
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


# --- Tuman bo'yicha xarita ma'lumotini CSV qilib eksport ---
@app.route("/api/export/map-csv")
@login_required
def export_map_csv():
    """Xaritadagi sensorlar (oxirgi o'lchov) — tuman filtri bilan CSV"""
    try:
        if df is None or df.empty:
            return "Ma'lumot yo'q", 404
        district = request.args.get("district", None)
        only_faults = request.args.get("only_faults", "0") == "1"

        latest = get_latest()
        if district:
            latest = latest[latest["District"] == district]
        if only_faults:
            latest = latest[latest["Fault"] == 2]

        if latest.empty:
            return "Ma'lumot yo'q", 404

        cols = ["SensorID", "District", "Latitude", "Longitude", "Timestamp", "Fault",
                "Muhit_harorat (C)", "Shamol_tezligi (km/h)", "Chastota (Hz)",
                "Kuchlanish (V)", "Vibratsiya", "Sim_mexanik_holati (%)",
                "Atrof_muhit_humidity (%)", "Quvvati (kW)"]
        cols = [c for c in cols if c in latest.columns]
        out = latest[cols].copy()
        if "Fault" in out.columns:
            out["Holat"] = out["Fault"].fillna(0).astype(int).map(
                {0: "Havfsiz", 1: "Ogohlantirish", 2: "Muammo"})

        buf = io.StringIO()
        out.to_csv(buf, index=False, encoding="utf-8-sig")
        suffix = (district or "barcha").replace(" ", "_").replace("'", "")
        if only_faults:
            suffix += "_muammolar"
        return send_file(
            io.BytesIO(buf.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"map_{suffix}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )
    except Exception as e:
        logger.error(f"Map CSV export error: {e}")
        return jsonify({"error": str(e)}), 500


# --- Yengil sparkline (popup uchun) ---
@app.route("/api/sensor-spark/<sensor_id>")
def sensor_sparkline(sensor_id):
    """Bitta sensorning oxirgi 30 ta kuchlanish o'lchovi (popup sparkline uchun)"""
    try:
        if df is None or df.empty:
            return jsonify({"values": []})
        sub = df[df["SensorID"] == sensor_id].sort_values("Timestamp").tail(30)
        if sub.empty:
            return jsonify({"values": []})
        vals = [round(float(v), 1) for v in sub["Kuchlanish (V)"].fillna(220).tolist()]
        faults = [int(round(float(f))) if pd.notna(f) else 0 for f in sub["Fault"].fillna(0).tolist()]
        return jsonify({"values": vals, "faults": faults, "param": "Kuchlanish (V)"})
    except Exception as e:
        logger.error(f"Sparkline error: {e}")
        return jsonify({"values": []})


# ========================
# AI CHATBOT API (smart engine)
# ========================
@app.route("/api/chatbot", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def chatbot_api():
    """Smart NLU chatbot — intent detection + entity extraction + rich cards."""
    try:
        from chatbot_engine import answer as _chat_answer
        question = (request.json or {}).get("question", "").strip()
        if not question:
            return jsonify({
                "text": "💬 Savolingizni yozing. Yordam uchun \"yordam\" deb yuboring.",
                "quick_replies": ["Statistika", "Xavfli sensorlar", "Yordam"],
            })
        latest = get_latest()
        if latest is not None and "Fault" in latest.columns:
            latest = latest.copy()
            latest["Fault"] = latest["Fault"].fillna(0).astype(int)
        result = _chat_answer(question, df=latest)
        # Eski mosligi uchun "answer" maydoni
        result["answer"] = result.get("text", "")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return jsonify({
            "text": f"⚠️ Xatolik yuz berdi.",
            "answer": f"⚠️ Xatolik: {str(e)[:100]}",
        }), 500


# ========================
# COMPARISON API
# ========================
@app.route("/compare")
@login_required
def compare_page():
    return render_template("compare.html")

@app.route("/api/compare")
def compare_api():
    """Ikki tuman yoki ikki sensorni taqqoslash"""
    try:
        if df is None or df.empty:
            return jsonify({"error": "Ma'lumot yo'q"}), 404

        type_ = request.args.get("type", "district")  # district | sensor
        a = request.args.get("a", "")
        b = request.args.get("b", "")

        if not a or not b:
            return jsonify({"error": "Ikki parametr kerak (a va b)"}), 400

        latest = get_latest()
        latest["Fault"] = latest["Fault"].fillna(0).astype(int)

        PARAM_COLS = {
            "Kuchlanish": "Kuchlanish (V)",
            "Chastota": "Chastota (Hz)",
            "Harorat": "Muhit_harorat (C)",
            "Shamol": "Shamol_tezligi (km/h)",
            "Vibratsiya": "Vibratsiya",
            "Sim holati": "Sim_mexanik_holati (%)",
            "Namlik": "Atrof_muhit_humidity (%)",
            "Quvvat": "Quvvati (kW)"
        }

        def get_stats(subset, name):
            total = len(subset)
            return {
                "name": name,
                "total": total,
                "safe": int((subset["Fault"] == 0).sum()),
                "warn": int((subset["Fault"] == 1).sum()),
                "danger": int((subset["Fault"] == 2).sum()),
                "params": {
                    pname: round(float(subset[col].mean()), 2) if col in subset.columns else 0
                    for pname, col in PARAM_COLS.items()
                }
            }

        if type_ == "district":
            da = latest[latest["District"] == a]
            db = latest[latest["District"] == b]
            if da.empty:
                return jsonify({"error": f"'{a}' tumani topilmadi"}), 404
            if db.empty:
                return jsonify({"error": f"'{b}' tumani topilmadi"}), 404
            return jsonify({"a": get_stats(da, a), "b": get_stats(db, b), "type": "district"})

        else:  # sensor
            sa = latest[latest["SensorID"] == a]
            sb = latest[latest["SensorID"] == b]
            if sa.empty:
                return jsonify({"error": f"Sensor '{a}' topilmadi"}), 404
            if sb.empty:
                return jsonify({"error": f"Sensor '{b}' topilmadi"}), 404

            def sensor_detail(row, sid):
                r = row.iloc[0]
                return {
                    "name": sid,
                    "district": str(r.get("District", "")),
                    "total": 1,
                    "safe": 1 if r["Fault"] == 0 else 0,
                    "warn": 1 if r["Fault"] == 1 else 0,
                    "danger": 1 if r["Fault"] == 2 else 0,
                    "params": {
                        pname: round(float(r.get(col, 0)), 2)
                        for pname, col in PARAM_COLS.items()
                    }
                }
            return jsonify({"a": sensor_detail(sa, a), "b": sensor_detail(sb, b), "type": "sensor"})

    except Exception as e:
        logger.error(f"Compare error: {e}")
        return jsonify({"error": str(e)}), 500


# ========================
# MAINTENANCE CALENDAR API
# ========================
@app.route("/calendar")
@login_required
def calendar_page():
    return render_template("calendar.html")

@app.route("/api/maintenance", methods=["GET", "POST"])
@login_required
def maintenance_api():
    """Rejali ta'mirlash ishlari CRUD"""
    import json
    MAINT_FILE = "data/maintenance.json"

    if request.method == "GET":
        if os.path.exists(MAINT_FILE):
            with open(MAINT_FILE, "r", encoding="utf-8") as f:
                events = json.load(f)
        else:
            events = []

        # Tarixiy avariyalarni avtomatik qo'shish
        if df is not None and not df.empty:
            last30 = df[df["Timestamp"] >= (datetime.datetime.now() - datetime.timedelta(days=30))]
            danger_days = last30[last30["Fault"] == 2].copy()
            if not danger_days.empty:
                danger_days["date"] = danger_days["Timestamp"].dt.date.astype(str)
                for dt_str, grp in danger_days.groupby("date"):
                    districts = grp["District"].unique().tolist()[:3]
                    events.append({
                        "id": f"auto-{dt_str}",
                        "title": f"🔴 Avariya: {', '.join(districts)}",
                        "date": dt_str,
                        "type": "incident",
                        "auto": True,
                        "sensors_count": len(grp["SensorID"].unique())
                    })
        return jsonify(events)

    else:  # POST — yangi rejali ish qo'shish
        data = request.json or {}
        title = data.get("title", "").strip()
        date = data.get("date", "").strip()
        district = data.get("district", "").strip()
        mtype = data.get("type", "maintenance")

        if not title or not date:
            return jsonify({"error": "Sarlavha va sana kerak"}), 400

        events = []
        if os.path.exists(MAINT_FILE):
            with open(MAINT_FILE, "r", encoding="utf-8") as f:
                events = json.load(f)

        new_event = {
            "id": f"m-{datetime.datetime.now().timestamp():.0f}",
            "title": title,
            "date": date,
            "district": district,
            "type": mtype,
            "created_by": session.get("user", "unknown"),
            "created_at": datetime.datetime.now().isoformat()
        }
        events.append(new_event)
        with open(MAINT_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)

        # Audit log
        _audit_log("maintenance_create", {"event": new_event})
        return jsonify({"ok": True, "event": new_event})

@app.route("/api/maintenance/<event_id>", methods=["DELETE"])
@login_required
def delete_maintenance(event_id):
    import json
    MAINT_FILE = "data/maintenance.json"
    if not os.path.exists(MAINT_FILE):
        return jsonify({"error": "Fayl topilmadi"}), 404
    with open(MAINT_FILE, "r", encoding="utf-8") as f:
        events = json.load(f)
    events = [e for e in events if e.get("id") != event_id]
    with open(MAINT_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    _audit_log("maintenance_delete", {"event_id": event_id})
    return jsonify({"ok": True})


# ========================
# AUDIT LOGS (utils.py ga delegatsiya)
# ========================
def _audit_log(action, details=None):
    """Flask request kontekstida audit log yozish."""
    audit_log(
        action,
        user=session.get("user", "system"),
        ip=request.remote_addr if request else None,
        details=details
    )

@app.route("/api/audit-logs")
@admin_required
def get_audit_logs():
    """Audit loglarni ko'rish (faqat admin)"""
    import json
    from utils import AUDIT_LOG_FILE
    page = request.args.get("page", 1, type=int)
    per_page = 50
    if os.path.exists(AUDIT_LOG_FILE):
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    else:
        logs = []
    logs.reverse()
    total = len(logs)
    start = (page - 1) * per_page
    return jsonify({
        "logs": logs[start:start + per_page],
        "total": total,
        "page": page,
        "total_pages": max(1, (total + per_page - 1) // per_page)
    })


# ========================
# NEAREST SENSORS API (Haversine)
# ========================
@app.route("/api/nearest-sensors")
@login_required
def nearest_sensors_api():
    """Foydalanuvchi GPS ga eng yaqin sensorlarni topish."""
    try:
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        n = request.args.get("n", 5, type=int)

        if lat is None or lon is None:
            # Session dagi foydalanuvchi joylashuvini ishlatish
            user_login = session.get("user", "")
            u_lat, u_lon = get_user_location(user_login)
            if u_lat and u_lon:
                lat, lon = u_lat, u_lon
            else:
                return jsonify({"error": "GPS koordinata kerak (lat, lon parametrlari)"}), 400

        if df is None or df.empty:
            return jsonify({"error": "Ma'lumot yo'q"}), 404

        latest = get_latest()
        sensor_list = []
        for _, row in latest.iterrows():
            sensor_list.append({
                "SensorID": str(row.get("SensorID", "")),
                "District": str(row.get("District", "")),
                "Latitude": float(row.get("Latitude", 0)),
                "Longitude": float(row.get("Longitude", 0)),
                "Kuchlanish": round(float(row.get("Kuchlanish (V)", 220)), 1),
                "Chastota": round(float(row.get("Chastota (Hz)", 50)), 2),
                "Fault": int(row.get("Fault", 0)),
            })

        nearest = find_nearest_sensors(lat, lon, sensor_list, n=min(n, 20))
        return jsonify({
            "user_location": {"lat": lat, "lon": lon},
            "sensors": nearest
        })
    except Exception as e:
        logger.error(f"Nearest sensors error: {e}")
        return jsonify({"error": str(e)}), 500


# ========================
# USER INFO API
# ========================
@app.route("/api/user-info")
@login_required
def user_info_api():
    """Joriy foydalanuvchi ma'lumotlari."""
    user_login = session.get("user", "")
    role = session.get("role", "user")
    district = session.get("district", "")
    lat, lon = get_user_location(user_login)
    return jsonify({
        "login": user_login,
        "role": role,
        "district": district,
        "name": session.get("user_name", user_login),
        "latitude": lat,
        "longitude": lon
    })


# ========================
# TICKETS / MAINTENANCE SYSTEM
# ========================
@app.route("/tickets")
@login_required
def tickets_page():
    return render_template("tickets.html")


@app.route("/api/tickets", methods=["GET", "POST"])
@login_required
def tickets_api():
    from utils import load_tickets, save_tickets, create_ticket
    if request.method == "GET":
        tickets = load_tickets()
        # User uchun faqat o'z tumanidagi
        if session.get("role") != "admin":
            user_district = session.get("district", "")
            if user_district and df is not None:
                district_sensors = set(df[df["District"] == user_district]["SensorID"].astype(str).unique())
                tickets = [t for t in tickets if str(t.get("sensor_id")) in district_sensors]
        return jsonify({"tickets": tickets})

    # POST — admin only
    if session.get("role") != "admin":
        return jsonify({"error": "Admin huquqi yo'q"}), 403
    data = request.json or {}
    sensor_id = data.get("sensor_id", "").strip()
    issue = data.get("issue", "").strip()
    eta = data.get("eta")
    if not sensor_id or not issue:
        return jsonify({"error": "sensor_id va issue kerak"}), 400
    ticket = create_ticket(sensor_id, issue, eta=eta, created_by=session.get("user", "admin"))
    _audit_log("ticket_create", {"ticket": ticket})
    return jsonify({"ok": True, "ticket": ticket})


@app.route("/api/tickets/<ticket_id>/close", methods=["POST"])
@admin_required
def close_ticket_api(ticket_id):
    from utils import close_ticket
    t = close_ticket(ticket_id)
    if not t:
        return jsonify({"error": "Topilmadi"}), 404
    _audit_log("ticket_close", {"ticket_id": ticket_id})
    return jsonify({"ok": True, "ticket": t})


@app.route("/api/sensor-status/<sensor_id>")
@login_required
def sensor_status_api(sensor_id):
    """Sensor uchun ta'mirlash holatini tekshirish."""
    from utils import get_active_ticket
    ticket = get_active_ticket(sensor_id)
    if ticket:
        return jsonify({
            "in_maintenance": True,
            "ticket": ticket,
            "message": f"Hozirda ta'mirlash ishlari ketmoqda. ETA: {ticket.get('eta', 'N/A')}"
        })
    return jsonify({"in_maintenance": False})


# ========================
# PREDICTIVE MAINTENANCE
# ========================
@app.route("/api/predict-failure")
@login_required
def predict_failure_api():
    """Har bir sensor uchun 24 soat ichida buzilish ehtimoli."""
    from utils import predict_failure_probability
    if df is None or df.empty:
        return jsonify({"error": "Ma'lumot yo'q"}), 404

    # Ob-havo
    weather = None
    try:
        resp = http_requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": 41.3, "longitude": 69.27, "current_weather": True},
            timeout=3
        )
        if resp.ok:
            weather = resp.json().get("current_weather", {})
    except Exception:
        pass

    latest = get_latest()

    # Filter by user's district if not admin
    if session.get("role") != "admin":
        d = session.get("district", "")
        if d:
            latest = latest[latest["District"] == d]

    results = []
    for _, row in latest.iterrows():
        prob = predict_failure_probability(row.to_dict(), weather=weather)
        results.append({
            "sensor_id": str(row["SensorID"]),
            "district": str(row.get("District", "")),
            "probability": prob,
            "voltage": round(float(row.get("Kuchlanish (V)", 0)), 1),
            "fault": int(row.get("Fault", 0)),
            "risk_level": "high" if prob >= 60 else "medium" if prob >= 30 else "low"
        })

    results.sort(key=lambda x: -x["probability"])
    return jsonify({
        "weather": weather,
        "predictions": results[:100],  # Top 100
        "total": len(results),
        "high_risk_count": sum(1 for r in results if r["risk_level"] == "high")
    })


# ========================
# ACTIVE INCIDENTS (Dispatcher / Web Dashboard)
# ========================
@app.route("/api/incidents")
@login_required
def incidents_api():
    """Faol avariyalar — xarita uchun miltillab turuvchi qizil markerlar."""
    from utils import get_active_incidents
    items = get_active_incidents()
    role = session.get("role", "user")
    user_district = session.get("district")
    if role != "admin" and user_district:
        items = [i for i in items if i.get("district") == user_district]
    return jsonify({"count": len(items), "items": items})


@app.route("/api/incidents/<inc_id>/resolve", methods=["POST"])
@admin_required
def incidents_resolve_api(inc_id):
    from utils import resolve_incident, get_incident
    inc = get_incident(inc_id)
    if not inc:
        return jsonify({"ok": False, "error": "Topilmadi"}), 404
    if inc.get("status") == "resolved":
        return jsonify({"ok": False, "error": "Allaqachon hal qilingan"}), 400
    resolve_incident(inc_id)
    audit_log("incident_resolved_web", user=session.get("username"),
              details={"incident": inc_id})
    return jsonify({"ok": True, "incident": get_incident(inc_id)})


# ========================
# ZONE ANALYTICS (xarita ranglari)
# ========================
@app.route("/api/zones")
@cache.cached(timeout=60)
@login_required
def zones_api():
    """Tumanlar bo'yicha umumiy holat va rang tavsiyasi."""
    if df is None or df.empty:
        return jsonify({"zones": []})

    latest = get_latest()
    zones = []
    for district, group in latest.groupby("District"):
        total = len(group)
        danger = int((group["Fault"] == 2).sum())
        warning = int((group["Fault"] == 1).sum())
        safe = total - danger - warning
        avg_v = float(group["Kuchlanish (V)"].mean()) if "Kuchlanish (V)" in group.columns else 0
        avg_load = float(group["Quvvati (kW)"].mean()) if "Quvvati (kW)" in group.columns else 0

        # Yuklama foizi (taxminiy 100kW max)
        load_pct = min(100, (avg_load / 100) * 100) if avg_load else 0
        risk_pct = (danger * 100 + warning * 50) / max(total, 1)

        # Rang aniqlash
        if risk_pct >= 30 or danger > 5:
            color = "#ef4444"  # qizil
            status = "danger"
        elif risk_pct >= 15:
            color = "#f59e0b"  # sariq
            status = "warning"
        else:
            color = "#22c55e"  # yashil
            status = "safe"

        zones.append({
            "district": str(district),
            "total": total,
            "safe": safe,
            "warning": warning,
            "danger": danger,
            "avg_voltage": round(avg_v, 1),
            "avg_load_kw": round(avg_load, 1),
            "load_pct": round(load_pct, 1),
            "risk_pct": round(risk_pct, 1),
            "color": color,
            "status": status,
        })

    zones.sort(key=lambda x: -x["risk_pct"])
    return jsonify({"zones": zones})


# ========================
# AUDIT PAGE (admin)
# ========================
@app.route("/admin/audit")
@admin_required
def audit_page():
    return render_template("audit.html")


# ========================
# LANGUAGE PREFERENCE
# ========================
@app.route("/api/set-language", methods=["POST"])
@login_required
def set_language_api():
    data = request.json or {}
    lang = data.get("lang", "uz")
    if lang not in ("uz", "uz_cyr"):
        return jsonify({"error": "Noma'lum til"}), 400
    session["lang"] = lang
    return jsonify({"ok": True, "lang": lang})


@app.route("/api/translations/<lang>")
def translations_api(lang):
    from utils import TRANSLATIONS
    return jsonify(TRANSLATIONS.get(lang, TRANSLATIONS["uz"]))


# ========================
# EXPORT EXCEL
# ========================
@app.route("/api/export/excel")
@login_required
def export_excel():
    """Sensor ma'lumotlarini Excel formatida eksport"""
    try:
        if df is None or df.empty:
            return "Ma'lumot yo'q", 404
        latest = get_latest()
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            latest.to_excel(writer, sheet_name='Sensorlar', index=False)
            # Tuman statistikasi
            district_stats = latest.groupby("District").agg(
                Jami=("SensorID", "count"),
                Havfsiz=("Fault", lambda x: int((x == 0).sum())),
                Ogohlantirish=("Fault", lambda x: int((x == 1).sum())),
                Muammo=("Fault", lambda x: int((x == 2).sum())),
                Ort_Kuchlanish=("Kuchlanish (V)", "mean"),
                Ort_Harorat=("Muhit_harorat (C)", "mean"),
            ).round(2)
            district_stats.to_excel(writer, sheet_name='Tumanlar')
        output.seek(0)
        _audit_log("export_excel")
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'monitoring_{datetime.datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
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
        latest = get_latest()
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
<p><strong>Sana:</strong> {now} | <strong>Tizim:</strong> Toshkent shahar, 12 tuman</p>

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
            latest = get_latest()
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
# WEBSOCKET LIVE STREAM
# ========================
def _emit_live_stats():
    """Har 30 soniyada barcha ulangan clientlarga yangi statistika yuborish"""
    if not HAS_SOCKETIO or socketio is None:
        return
    import time
    while True:
        time.sleep(30)
        try:
            if df is not None and not df.empty:
                latest = get_latest()
                latest["Fault"] = latest["Fault"].fillna(0).astype(int)
                total = len(latest)
                safe = int((latest["Fault"] == 0).sum())
                warn = int((latest["Fault"] == 1).sum())
                danger = int((latest["Fault"] == 2).sum())
                socketio.emit("live_stats", {
                    "total": total, "safe": safe, "warn": warn, "danger": danger,
                    "avg_kuchlanish": round(float(latest["Kuchlanish (V)"].mean()), 1),
                    "avg_harorat": round(float(latest["Muhit_harorat (C)"].mean()), 1),
                    "avg_chastota": round(float(latest["Chastota (Hz)"].mean()), 2),
                    "timestamp": datetime.datetime.now().isoformat()
                })
        except Exception as e:
            logger.warning(f"Live emit error: {e}")

if HAS_SOCKETIO and socketio is not None:
    @socketio.on("connect")
    def ws_connect():
        logger.info(f"WebSocket client connected")

    @socketio.on("request_stats")
    def ws_request_stats():
        if df is not None and not df.empty:
            latest = get_latest()
            latest["Fault"] = latest["Fault"].fillna(0).astype(int)
            emit("live_stats", {
                "total": len(latest),
                "safe": int((latest["Fault"] == 0).sum()),
                "warn": int((latest["Fault"] == 1).sum()),
                "danger": int((latest["Fault"] == 2).sum()),
                "avg_kuchlanish": round(float(latest["Kuchlanish (V)"].mean()), 1),
                "avg_harorat": round(float(latest["Muhit_harorat (C)"].mean()), 1),
                "avg_chastota": round(float(latest["Chastota (Hz)"].mean()), 2),
                "timestamp": datetime.datetime.now().isoformat()
            })


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
# HEALTH CHECK & METRICS (uptime monitoring uchun)
# ========================
_app_start_ts = _time.time()
_request_counter = {"total": 0, "errors": 0}

@app.before_request
def _count_request():
    _request_counter["total"] += 1

@app.errorhandler(500)
def _count_error(e):
    _request_counter["errors"] += 1
    return jsonify({"error": "Server xatosi"}), 500

@app.route("/healthz")
@limiter.exempt
def healthz():
    """Liveness probe — server ishlamoqda."""
    return jsonify({
        "status": "ok",
        "uptime_sec": int(_time.time() - _app_start_ts),
        "data_loaded": df is not None,
        "model_loaded": hybrid_model is not None,
        "rows": int(len(df)) if df is not None else 0,
    })

@app.route("/metrics")
@limiter.exempt
def metrics():
    """Prometheus-uslubidagi oddiy metrikalar."""
    uptime = int(_time.time() - _app_start_ts)
    cache_age = int(_time.time() - _latest_cache["ts"]) if _latest_cache["ts"] else -1
    lines = [
        "# HELP app_uptime_seconds Server uptime",
        "# TYPE app_uptime_seconds counter",
        f"app_uptime_seconds {uptime}",
        "# HELP app_requests_total Total HTTP requests",
        "# TYPE app_requests_total counter",
        f"app_requests_total {_request_counter['total']}",
        "# HELP app_errors_total Total 5xx errors",
        "# TYPE app_errors_total counter",
        f"app_errors_total {_request_counter['errors']}",
        "# HELP app_data_rows Loaded sensor rows",
        "# TYPE app_data_rows gauge",
        f"app_data_rows {len(df) if df is not None else 0}",
        "# HELP app_latest_cache_age_seconds Age of latest cache",
        "# TYPE app_latest_cache_age_seconds gauge",
        f"app_latest_cache_age_seconds {cache_age}",
    ]
    return ("\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; charset=utf-8"})


# ========================
# MAIN
# ========================
if __name__ == "__main__":
    import subprocess, threading, sys

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BOT_FILE = os.path.join(BASE_DIR, "telegram_bot.py")

    bot_proc_ref = {"proc": None}

    def _stream_bot_output(proc):
        """Bot stdout/stderr ni asosiy logga yo'naltirish."""
        try:
            for line in iter(proc.stdout.readline, b""):
                if not line:
                    break
                try:
                    msg = line.decode("utf-8", errors="replace").rstrip()
                except Exception:
                    msg = str(line)
                if msg:
                    logger.info(f"[BOT] {msg}")
        except Exception as e:
            logger.warning(f"[BOT] log oqimi to'xtadi: {e}")

    def run_bot():
        """Telegram botni alohida jarayonda ishga tushirish."""
        if not os.path.exists(BOT_FILE):
            logger.warning(f"⚠️ telegram_bot.py topilmadi: {BOT_FILE}")
            return
        token = read_bot_token() or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            logger.warning("⚠️ Bot token topilmadi (bot_token.txt yoki .env) — bot ishga tushirilmadi.")
            return
        try:
            python_exe = sys.executable
            proc = subprocess.Popen(
                [python_exe, "-u", BOT_FILE],
                cwd=BASE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"}
            )
            bot_proc_ref["proc"] = proc
            logger.info(f"🤖 Telegram bot ishga tushirildi (PID={proc.pid})")
            threading.Thread(target=_stream_bot_output, args=(proc,), daemon=True).start()
        except Exception as e:
            logger.error(f"❌ Bot ishga tushirishda xato: {e}")

    # use_reloader=False bo'lgani uchun bot bir marta ishga tushadi.
    # WERKZEUG_RUN_MAIN tekshiruvi ham reloader holatlarini qo'shimcha himoya qiladi.
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Thread(target=run_bot, daemon=True).start()

    import atexit
    def _cleanup_bot():
        p = bot_proc_ref.get("proc")
        if p and p.poll() is None:
            try:
                p.terminate()
                logger.info("🛑 Telegram bot to'xtatildi")
            except Exception:
                pass
    atexit.register(_cleanup_bot)

    # Start live stats emitter thread
    if HAS_SOCKETIO:
        threading.Thread(target=_emit_live_stats, daemon=True).start()

    logger.info("🚀 Server 0.0.0.0:5000 ishga tushmoqda")
    if HAS_SOCKETIO and socketio is not None:
        socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)
    else:
        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
