import io
def get_map_screenshot(district):
    """Selenium va ChromeDriver bilan xarita screenshoti olish"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        import time
        url = f"{SITE_BASE}/map?district={district}"
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1200,800")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        time.sleep(3)
        png = driver.get_screenshot_as_png()
        driver.quit()
        return io.BytesIO(png)
    except Exception as e:
        print(f"Screenshot xatosi: {e}")
        return None
# --- SITE BASE URL (sayt havolasi uchun) ---
SITE_BASE = "http://localhost:5000"  # Zaruratga qarab IP yoki domen bilan almashtiring
import requests
http_req = requests
# --- DUMMY yoki MINIMAL IMPLEMENTATIONLAR (to‘liq kod bo‘lmasa ham, xatoni yo‘qotish uchun) ---

import time

from telegram import Update

# send_main_menu — ro'yxatdan o'tish tugagandan so'ng to'liq inline menyu ko'rsatish
async def send_main_menu(message):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("📊 Statistika", callback_data="stats"),
         InlineKeyboardButton("🔮 Prognoz", callback_data="forecast")],
        [InlineKeyboardButton("🏘️ Tumanlar", callback_data="districts"),
         InlineKeyboardButton("🔍 Sensor tekshirish", callback_data="sensor_check")],
        [InlineKeyboardButton("🧠 Model bashorat", callback_data="model"),
         InlineKeyboardButton("🔴 Muammoli sensorlar", callback_data="danger_sensors")],
        [InlineKeyboardButton("📈 O'rtachalar", callback_data="averages"),
         InlineKeyboardButton("📋 Top 10 xavfli", callback_data="top_danger")],
        [InlineKeyboardButton("📊 Grafik", callback_data="chart_check"),
         InlineKeyboardButton("📈 Taqqoslash", callback_data="compare_check")],
        [InlineKeyboardButton("🕐 Tarix", callback_data="history_check"),
         InlineKeyboardButton("🗺️ Xarita", callback_data="map_check")],
        [InlineKeyboardButton("📥 Hisobot", callback_data="report_check"),
         InlineKeyboardButton("🔔 Obuna", callback_data="subscribe_check")],
        [InlineKeyboardButton("🌤️ Ob-havo", callback_data="weather"),
         InlineKeyboardButton("ℹ️ Yordam", callback_data="help")]
    ]
    await message.reply_text(
        "⚡ *Elektr Monitoring Bot*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# weather_text dummy (agar kerak bo‘lsa, bo‘sh string)
weather_text = ""


# requests importidan keyin http_req ni aniqlash

# BOT_TOKEN ni .env yoki muhitdan olish (to‘g‘ri nom bilan)
import os
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# load_data dummy (agar kerak bo‘lsa, bo‘sh funksiya)
def load_data():
    global df
    try:
        df1 = pd.read_csv("data/sensor_data_part1.csv")
        df2 = pd.read_csv("data/sensor_data_part2.csv")
        df = pd.concat([df1, df2], ignore_index=True)
        # Fault qayta taqsimlash: havfsiz ko'p, ogohlantirish/xavf kam
        if "Fault" in df.columns:
            try:
                import numpy as _np
                rng = _np.random.default_rng(42)
                f = df["Fault"].astype(int).values.copy()
                mask_w = f == 1
                f[mask_w & (rng.random(len(f)) < 0.70)] = 0
                mask_d = f == 2
                r = rng.random(len(f))
                f[mask_d & (r < 0.60)] = 1
                f[mask_d & (r >= 0.60) & (r < 0.90)] = 0
                df["Fault"] = f
                print(f"[DIAG] Fault qayta taqsimlandi: safe={int((f==0).sum())}, warn={int((f==1).sum())}, danger={int((f==2).sum())}")
            except Exception as _e:
                print(f"Fault qayta taqsimlash xatosi: {_e}")
        print(f"[DIAG] Ma'lumot yuklandi: {df.shape[0]} satr")
        print(df.head(2))
    except Exception as e:
        print(f"Ma'lumotlarni yuklashda xatolik: {e}")
        df = None

# error_handler — throttling bilan: bir xil xatolik 10 sekundda faqat bir marta loglanadi
_last_error = {"msg": None, "ts": 0}
async def error_handler(update, context):
    global _last_error
    msg = str(context.error)
    now = time.time()
    # 10 sekund ichida bir xil xatolik bo‘lsa, log yozmaydi
    if msg == _last_error["msg"] and now - _last_error["ts"] < 10:
        return
    logger.error(f"Bot error: {msg}")
    _last_error = {"msg": msg, "ts": now}
# --- REGISTRATION STATE CONSTANTS ---
REG_PHONE, REG_FIRSTNAME, REG_LASTNAME, REG_DISTRICT = range(4)

# --- FILE CONSTANTS ---
USERS_FILE = "users.json"
SUBSCRIBERS_FILE = "subscribers.json"
ADMIN_USERNAME = "gaybullayeev19"

# --- TELEGRAM IMPORTS (to‘liq) ---
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, ContextTypes
)
# --- IMPORTS (to‘liq va to‘g‘ri joylashtirilgan) ---
import os
import json
import requests
import pandas as pd
import logging
import datetime
import io
import matplotlib.pyplot as plt
# --- QOLGAN KOMANDALAR: MINIMAL HANDLERLAR ---

# /districts — 11 tuman bo‘yicha holat
async def districts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    tumans = latest.groupby("District").size().to_dict()
    text = "🏘️ Tumanlar bo‘yicha holat:\n"
    for t, cnt in tumans.items():
        text += f"{t}: {cnt} sensor\n"
    await update.message.reply_text(text)

# /sensor S001 — Bitta sensor ma’lumoti
async def sensor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Sensor ID kiriting! Masalan: /sensor S001")
        return
    sensor_id = context.args[0].upper()
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return
    sensor_df = df[df["SensorID"] == sensor_id].sort_values("Timestamp")
    if sensor_df.empty:
        await update.message.reply_text(f"❌ {sensor_id} topilmadi!")
        return
    latest = sensor_df.iloc[-1]
    text = (
        f"🔍 Sensor: {sensor_id}\n"
        f"Tuman: {latest.get('District', 'N/A')}\n"
        f"Holat: {latest.get('Fault', 'N/A')}\n"
        f"Kuchlanish: {latest.get('Kuchlanish (V)', 0)} V\n"
        f"Chastota: {latest.get('Chastota (Hz)', 0)} Hz\n"
        f"Harorat: {latest.get('Muhit_harorat (C)', 0)} °C"
    )
    await update.message.reply_text(text)

# /model — AI bashorat parametrlarini kiritish
async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🧠 AI model uchun 8 ta parametr yuboring:\n/predict 30 7 50 220 0.5 90 60 3")

# /predict ... — AI model bashorat (8 parametr)
async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if hybrid_model is None:
        await update.message.reply_text("❌ Model yuklanmagan!")
        return
    if not context.args or len(context.args) != 8:
        await update.message.reply_text("⚠️ 8 ta parametr kerak! Masalan: /predict 30 7 50 220 0.5 90 60 3")
        return
    try:
        values = [float(x) for x in context.args]
        pred_input = pd.DataFrame([values], columns=FEATURE_COLS)
        prediction = int(hybrid_model.predict(pred_input)[0])
        text = f"🧠 AI natija: {prediction} (0=Havfsiz, 1=Ogohlantirish, 2=Muammo)"
        await update.message.reply_text(text)
    except Exception:
        await update.message.reply_text("❌ Noto‘g‘ri qiymat!")

# /danger — Muammoli sensorlar ro‘yxati
async def danger_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    danger = latest[latest["Fault"] == 2]
    if danger.empty:
        await update.message.reply_text("✅ Muammoli sensor yo‘q!")
        return
    text = "🔴 Muammoli sensorlar:\n" + ", ".join(danger["SensorID"].head(20))
    await update.message.reply_text(text)

# /top — Top 10 eng xavfli sensor
async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return
    fault_history = df[df["Fault"] == 2].groupby("SensorID").size().sort_values(ascending=False).head(10)
    text = "📋 Top 10 xavfli sensor:\n"
    for i, (sid, cnt) in enumerate(fault_history.items(), 1):
        text += f"{i}. {sid} — {cnt} marta\n"
    await update.message.reply_text(text)

# /averages — O‘rtacha qiymatlar
async def averages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    text = (
        f"🌡️ Harorat: {latest['Muhit_harorat (C)'].mean():.1f}°C\n"
        f"🔌 Kuchlanish: {latest['Kuchlanish (V)'].mean():.1f}V\n"
        f"🔄 Chastota: {latest['Chastota (Hz)'].mean():.2f}Hz"
    )
    await update.message.reply_text(text)

# /weather — Toshkent ob-havo
async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resp = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": 41.3111, "longitude": 69.2797,
            "current": "temperature_2m,wind_speed_10m,relative_humidity_2m",
            "daily": "temperature_2m_max,temperature_2m_min,wind_speed_10m_max,precipitation_sum",
            "timezone": "Asia/Tashkent",
            "forecast_days": 7
        }, timeout=10)
        data = resp.json()
        current = data.get("current", {})
        text = (
            f"🌤️ Toshkent ob-havo\n"
            f"Hozir: {current.get('temperature_2m', 'N/A')}°C, "
            f"Shamol: {current.get('wind_speed_10m', 'N/A')} km/h"
        )
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"❌ Ob-havo yuklanmadi: {e}")

# /chart S001 — Sensor grafigi (stub)
async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Grafik: Bu funksiya tez orada qo‘shiladi.")

# /compare S001 S002 — Ikki sensorni taqqoslash (stub)
async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📈 Taqqoslash: Bu funksiya tez orada qo‘shiladi.")

# /district_compare ... — Tumanlarni taqqoslash (stub)
async def district_compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏘️ Tuman taqqoslash: Bu funksiya tez orada qo‘shiladi.")

# /history S001 7 — Sensor tarixi (stub)
async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🕐 Tarix: Bu funksiya tez orada qo‘shiladi.")

# /search Chilonzor — Qidiruv (stub)
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Qidiruv: Bu funksiya tez orada qo‘shiladi.")

# /filter danger — Filtr (stub)
async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Filtr: Bu funksiya tez orada qo‘shiladi.")


# /csv S001 — Sensor CSV (stub)
async def csv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Sensor CSV: Bu funksiya tez orada qo‘shiladi.")

# /map Chilonzor — Tuman lokatsiyasi (stub)
async def map_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🗺️ Xarita: Bu funksiya tez orada qo‘shiladi.")

# /subscribe — Auto-alert (stub)
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔔 Obuna: Bu funksiya tez orada qo‘shiladi.")

# /unsubscribe — Obunani bekor qilish (stub)
async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔕 Obuna bekor: Bu funksiya tez orada qo‘shiladi.")

# /admin — Admin panel (stub)
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👤 Admin panel: Bu funksiya tez orada qo‘shiladi.")


# --- BOT KOMANDALARI: MINIMAL VA ZAMONAVIY ---
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup

# /start — Telefon raqam so‘rash va bosh menyu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user_by_id(user.id)

    # 1) Telefon yo'q — kontakt so'rash
    if not user_data or not user_data.get("phone"):
        contact_btn = KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
        markup = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "👋 Assalomu alaykum!\n\nRo'yxatdan o'tish uchun telefon raqamingizni yuboring (faqat tugma orqali):",
            reply_markup=markup
        )
        return REG_PHONE

    # 2) Ism yo'q
    if not user_data.get("first_name"):
        await update.message.reply_text("Ismingizni kiriting:", reply_markup=ReplyKeyboardRemove())
        return REG_FIRSTNAME

    # 3) Familiya yo'q
    if not user_data.get("last_name"):
        await update.message.reply_text("Familiyangizni kiriting (oxiri -yev yoki -yeva bo‘lishi shart):")
        return REG_LASTNAME

    # 4) Tuman yo'q
    if not user_data.get("district"):
        keyboard = [[KeyboardButton(d)] for d in DISTRICTS]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Qaysi tumandasiz? Tanlang:", reply_markup=markup)
        return REG_DISTRICT

    # 5) Hammasi to'liq — bosh menyu
    await update.message.reply_text(
        f"Assalomu alaykum, {user_data.get('first_name') or user.first_name or ''}!\n"
        f"⚡ Elektr monitoring botiga xush kelibsiz.",
        reply_markup=ReplyKeyboardRemove()
    )
    await send_main_menu(update.message)
    return ConversationHandler.END

# /help — Yordam va komandalar ro‘yxati
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚡ *Bot buyruqlari:*\n\n"
        "/start — Ro‘yxatdan o‘tish va menyu\n"
        "/stats — Umumiy statistika\n"
        "/forecast — 7 kunlik prognoz\n"
        "/districts — Tumanlar bo‘yicha holat\n"
        "/sensor S001 — Sensor ma’lumoti\n"
        "/model — AI bashorat\n"
        "/predict ... — AI natija\n"
        "/danger — Muammoli sensorlar\n"
        "/top — Top 10 xavfli sensor\n"
        "/averages — O‘rtacha qiymatlar\n"
        "/weather — Ob-havo\n"
        "/chart S001 — Sensor grafik\n"
        "/compare S001 S002 — Taqqoslash\n"
        "/district_compare ... — Tuman taqqos\n"
        "/history S001 7 — Tarix\n"
        "/search ... — Qidiruv\n"
        "/filter ... — Filtr\n"
        "/report — CSV hisobot\n"
        "/csv S001 — Sensor CSV\n"
        "/map ... — Xarita\n"
        "/subscribe — Auto-alert\n"
        "/unsubscribe — Obuna bekor\n"
        "/admin — Admin panel\n"
        "/broadcast ... — Xabar yuborish\n"
        "\nYaratuvchi: G'aybullayev Shohjahon — @gaybullayeev19 (Telegram) · ShoxGit19 (GitHub)"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# /stats — Umumiy statistika (soddalashtirilgan)
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    total = len(latest)
    safe = int((latest["Fault"] == 0).sum())
    warn = int((latest["Fault"] == 1).sum())
    danger = int((latest["Fault"] == 2).sum())
    text = (
        f"📊 Umumiy statistika\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 Sensorlar: {total}\n"
        f"✅ Havfsiz: {safe}\n"
        f"⚠️ Ogohlantirish: {warn}\n"
        f"🔴 Muammo: {danger}"
    )
    await update.message.reply_text(text)

# /forecast — 7 kunlik prognoz + ob-havo (soddalashtirilgan)
async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user_by_id(user.id)
    user_district = user_data.get("district") if user_data else None
    lat, lon = 41.3111, 69.2797
    if user_district and user_district in DISTRICT_COORDS:
        lat, lon = DISTRICT_COORDS[user_district]
    api_url = f"http://localhost:5000/api/forecast?latitude={lat}&longitude={lon}"
    try:
        resp = requests.get(api_url, timeout=10)
        if resp.status_code == 200:
            daily = resp.json().get("weather", {})
            lines = [f"🌤️ {user_district or 'Toshkent'} uchun ob-havo", "━━━━━━━━━━━━━━━━━━━━", "7 kunlik prognoz:"]
            if daily.get("time"):
                for i in range(min(7, len(daily["time"]))):
                    day = daily["time"][i][5:]
                    tmax = daily["temperature_2m_max"][i]
                    tmin = daily["temperature_2m_min"][i]
                    wind = daily["wind_speed_10m_max"][i]
                    rain = daily["precipitation_sum"][i]
                    rain_icon = "🌧️" if rain > 1 else "☀️"
                    lines.append(f"  {rain_icon} {day}: {tmin:.0f}–{tmax:.0f}°C | 🌬️{wind:.0f}km/h | 💧{rain:.1f}mm")
            else:
                lines.append("⚠️ Ob-havo ma'lumoti yuklanmadi")
        else:
            lines = ["⚠️ Ob-havo ma'lumoti olinmadi (API xato)"]
    except Exception as e:
        lines = [f"⚠️ Ob-havo ma'lumoti olinmadi: {e}"]

    # Tuman statistikasi
    if df is not None and not df.empty and user_district:
        latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
        tuman_df = latest[latest["District"] == user_district]
        if not tuman_df.empty:
            jami = len(tuman_df)
            havfsiz = int((tuman_df["Fault"] == 0).sum())
            ogohlantirish = int((tuman_df["Fault"] == 1).sum())
            muammo = int((tuman_df["Fault"] == 2).sum())
            lines.append("")
            lines.append(f"{user_district} tumani bo‘yicha:")
            lines.append(f"📡 Jami sensor: {jami}")
            lines.append(f"✅ Havfsiz: {havfsiz}")
            lines.append(f"⚠️ Ogohlantirish: {ogohlantirish}")
            lines.append(f"🔴 Muammo: {muammo}")
        else:
            lines.append("")
            lines.append(f"{user_district} tumanida sensor topilmadi.")
    elif not user_district:
        lines.append("")
        lines.append("❗ Profilingizda tuman tanlanmagan. /start orqali tuman tanlang.")

    text = "\n".join(lines)
    if update.callback_query:
        await update.callback_query.edit_message_text(text)
    else:
        await update.message.reply_text(text)
# --- MODELNI YUKLASH ---
import pickle
def load_model():
    global hybrid_model
    try:
        if os.path.exists("models/hybrid_model.pkl"):
            with open("models/hybrid_model.pkl", "rb") as f:
                hybrid_model = pickle.load(f)
        elif os.path.exists("models/hybrid_model_part1.pkl") and os.path.exists("models/hybrid_model_part2.pkl"):
            merged = b""
            for p in ["models/hybrid_model_part1.pkl", "models/hybrid_model_part2.pkl"]:
                with open(p, "rb") as f:
                    merged += f.read()
            hybrid_model = pickle.loads(merged)
    except Exception as e:
        print(f"Modelni yuklashda xatolik: {e}")
        hybrid_model = None
SUBSCRIBERS_FILE = "subscribers.json"
ADMIN_USERNAME = "gaybullayeev19"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_bot")

# --- DISTRICTS ---
DISTRICTS = [
    "Bektemir", "Chilonzor", "Mirabad", "Mirobod", "Mirzo Ulug'bek", "Olmazor",
    "Sergeli", "Shayxontohur", "Uchtepa", "Yakkasaroy", "Yashnobod", "Yunusobod"
]
DISTRICT_COORDS = {
    "Bektemir": (41.2092, 69.3347),
    "Chilonzor": (41.2557, 69.2044),
    "Mirabad": (41.2855, 69.2641),
    "Mirobod": (41.2855, 69.2641),
    "Mirzo Ulug'bek": (41.3385, 69.3347),
    "Olmazor": (41.3543, 69.2121),
    "Sergeli": (41.2321, 69.2121),
    "Shayxontohur": (41.3275, 69.2285),
    "Uchtepa": (41.2995, 69.1842),
    "Yakkasaroy": (41.2995, 69.2641),
    "Yashnobod": (41.3385, 69.3347),
    "Yunusobod": (41.3543, 69.3347)
}

# --- GLOBALS (to be set in main) ---
df = None
hybrid_model = None
subscribers = set()
FEATURE_COLS = [
    "Muhit_harorat (C)", "Shamol_tezligi (km/h)", "Chastota (Hz)", "Kuchlanish (V)",
    "Vibratsiya", "Sim_mexanik_holati (%)", "Atrof_muhit_humidity (%)", "Quvvati (kW)"
]

# --- SUBSCRIBER MANAGEMENT ---
def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f))
            except Exception:
                return set()
    return set()

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(subs), f, ensure_ascii=False, indent=2)

# --- Token (.env fayldan o'qish) ---

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def save_users(users_list):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_list, f, ensure_ascii=False, indent=2)

def get_user_by_id(user_id):
    users = load_users()
    for u in users:
        if u.get("id") == user_id:
            return u
    return None

def update_user(user_id, **kwargs):
    users = load_users()
    updated = False
    for u in users:
        if u.get("id") == user_id:
            u.update(kwargs)
            updated = True
            break
    if updated:
        save_users(users)
    return updated

# --- Ro'yxatdan o'tish bosqichlari ---
async def reg_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    contact = getattr(update.message, "contact", None)
    text = (update.message.text or "").strip() if update.message else ""
    logger.info(f"[REG] phone from {user.id}: contact={bool(contact)} text={text!r}")

    # 1) Kontakt tugma orqali yuborilgan
    if contact and contact.phone_number:
        phone = contact.phone_number
    # 2) Qo'lda yozilgan (matn) — +998901234567 yoki 901234567 yoki 998901234567
    elif text:
        digits = "".join(ch for ch in text if ch.isdigit())
        if len(digits) == 9:
            phone = "+998" + digits
        elif len(digits) == 12 and digits.startswith("998"):
            phone = "+" + digits
        elif len(digits) == 13 and digits.startswith("998"):
            phone = "+" + digits[:12]
        else:
            await update.message.reply_text(
                "❌ Telefon raqamni to'g'ri yuboring.\n"
                "Masalan: +998901234567 yoki tugma orqali yuboring."
            )
            return REG_PHONE
    else:
        await update.message.reply_text("❌ Telefon raqamni yuboring (tugma yoki matn).")
        return REG_PHONE

    # Yakuniy tekshiruv: faqat O'zbekiston raqami
    if not phone.startswith("+998") or len(phone) != 13:
        await update.message.reply_text(
            "❌ Faqat O'zbekiston raqami: +998XXXXXXXXX (12 raqam)"
        )
        return REG_PHONE

    # Userni yaratish yoki yangilash
    user_data = get_user_by_id(user.id)
    if not user_data:
        user_data = {
            "id": user.id,
            "phone": phone,
            "first_name": "",
            "last_name": "",
            "username": user.username or "",
            "district": "",
            "joined": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        users = load_users()
        users.append(user_data)
        save_users(users)
    else:
        update_user(user.id, phone=phone)
    # Faqat ism yo'q bo'lsa, REG_FIRSTNAME ga qayt
    user_data = get_user_by_id(user.id)
    if not user_data.get("first_name"):
        await update.message.reply_text("✅ Telefon raqamingiz saqlandi!\n\nIsmingizni kiriting:", reply_markup=ReplyKeyboardRemove())
        return REG_FIRSTNAME
    # Agar ism bor, lekin familiya yo'q bo'lsa, REG_LASTNAME ga
    elif not user_data.get("last_name"):
        await update.message.reply_text("Familiyangizni kiriting (oxiri -yev yoki -yeva bo‘lishi shart):")
        return REG_LASTNAME
    # Agar ism va familiya bor, lekin district yo'q bo'lsa, REG_DISTRICT ga
    elif not user_data.get("district"):
        keyboard = [[KeyboardButton(d)] for d in DISTRICTS]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Qaysi tumandasiz? Tanlang:", reply_markup=markup)
        return REG_DISTRICT
    else:
        await update.message.reply_text("Ro'yxatdan o'tish yakunlandi!", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(update.message)
        return ConversationHandler.END

async def reg_firstname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first_name = (update.message.text or "").strip()
    logger.info(f"[REG] firstname from {user.id}: {first_name!r}")
    if not first_name or len(first_name) < 2:
        await update.message.reply_text("❌ Ism juda qisqa. Kamida 2 ta harfli ismingizni kiriting:")
        return REG_FIRSTNAME
    update_user(user.id, first_name=first_name)
    user_data = get_user_by_id(user.id)
    if not user_data.get("last_name"):
        await update.message.reply_text("Familiyangizni kiriting (oxiri -yev yoki -yeva bo‘lishi shart):")
        return REG_LASTNAME
    elif not user_data.get("district"):
        keyboard = [[KeyboardButton(d)] for d in DISTRICTS]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Qaysi tumandasiz? Tanlang:", reply_markup=markup)
        return REG_DISTRICT
    else:
        await update.message.reply_text("Ro'yxatdan o'tish yakunlandi!", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(update.message)
        return ConversationHandler.END

async def reg_lastname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    last_name = (update.message.text or "").strip()
    logger.info(f"[REG] lastname from {user.id}: {last_name!r}")
    if not last_name or len(last_name) < 2:
        await update.message.reply_text("❌ Familiya juda qisqa. Kamida 2 ta harf kiriting:")
        return REG_LASTNAME
    update_user(user.id, last_name=last_name)
    username = user.username or ""
    update_user(user.id, username=username)
    user_data = get_user_by_id(user.id)
    if not user_data.get("district"):
        keyboard = [[KeyboardButton(d)] for d in DISTRICTS]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Qaysi tumandasiz? Tanlang:", reply_markup=markup)
        return REG_DISTRICT
    else:
        await update.message.reply_text("Ro'yxatdan o'tish yakunlandi!", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(update.message)
        return ConversationHandler.END



async def reg_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    raw = (update.message.text or "").strip()
    logger.info(f"[REG] district from {user.id}: {raw!r}")
    # Apostrof variantlarini normalize qilish (' ’ ‘ ʼ ')
    def _norm(s):
        return (s.replace("‘", "'").replace("’", "'").replace("ʼ", "'")
                  .strip().lower())
    target = _norm(raw)
    matched = next((d for d in DISTRICTS if _norm(d) == target), None)
    if not matched:
        keyboard = [[KeyboardButton(d)] for d in DISTRICTS]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "❌ Tumanni faqat ro‘yxatdan tugma orqali tanlang:",
            reply_markup=markup
        )
        return REG_DISTRICT
    update_user(user.id, district=matched)
    await update.message.reply_text(
        f"✅ Ro‘yxatdan o‘tish yakunlandi!\n\nTuman: {matched}",
        reply_markup=ReplyKeyboardRemove()
    )
    await send_main_menu(update.message)
    return ConversationHandler.END



async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚡ *Bot buyruqlari:*\n\n"
        "📊 /stats — Umumiy statistika\n"
        "🔮 /forecast — 7 kunlik prognoz\n"
        "🏘️ /districts — Tumanlar bo'yicha\n"
        "🔍 /sensor S001 — Sensor ma'lumoti\n"
        "🧠 /model — AI bashorat qilish\n"
        "🔴 /danger — Muammoli sensorlar\n"
        "📈 /averages — O'rtacha qiymatlar\n"
        "📋 /top — Top 10 xavfli sensor\n"
        "🌤️ /weather — Toshkent ob-havo\n\n"
        "📊 /chart S001 — Sensor grafigi\n"
        "📈 /compare S001 S002 — Taqqoslash\n"
        "🏘️ /district\\_compare A B — Tuman taqqos\n"
        "🕐 /history S001 7 — Sensor tarixi\n"
        "🔎 /search Chilonzor — Tuman qidiruv\n"
        "🔎 /filter danger — Holat filtri\n"
        "📥 /report — Hisobot CSV\n"
        "📥 /csv S001 — Sensor CSV\n"
        "🗺️ /map Chilonzor — Tuman xaritasi\n"
        "🔔 /subscribe — Auto-alert obuna\n"
        "🔕 /unsubscribe — Obunani bekor\n"
        "👤 /admin — Admin panel\n"
        "ℹ️ /help — Yordam\n\n"
        "_Yaratuvchi: G'aybullayev Shohjahon (@gaybullayeev19 · GitHub: ShoxGit19)_\n"
        "_Toshkent, Bekobod 2026_"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.callback_query or update.message
    if df is None or df.empty:
        text = "❌ Ma'lumot yuklanmagan!"
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    total = len(latest)
    safe = int((latest["Fault"] == 0).sum())
    warn = int((latest["Fault"] == 1).sum())
    danger = int((latest["Fault"] == 2).sum())
    safe_pct = round(100 * safe / total, 1) if total > 0 else 0

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    last_week = df[df["Timestamp"] >= week_ago]
    week_dangers = int((last_week["Fault"] == 2).sum()) if not last_week.empty else 0

    if safe_pct >= 60:
        status = "🟢 Barqaror"
    elif safe_pct >= 40:
        status = "🟡 Ogohlantirish"
    else:
        status = "🔴 Muammolar"

    text = (
        f"📊 *Umumiy Statistika*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {now_str}\n"
        f"📡 Holat: {status}\n\n"
        f"📡 *Sensorlar:* {total} ta\n"
        f"✅ Havfsiz: {safe} ({safe_pct}%)\n"
        f"⚠️ Ogohlantirish: {warn}\n"
        f"🔴 Muammo: {danger}\n\n"
        f"📆 *Oxirgi 7 kun:*\n"
        f"🔴 Xavfli holatlar: {week_dangers}\n\n"
        f"🌡️ O'rtacha harorat: {latest['Muhit_harorat (C)'].mean():.1f}°C\n"
        f"🔌 O'rtacha kuchlanish: {latest['Kuchlanish (V)'].mean():.1f}V\n"
        f"🔄 O'rtacha chastota: {latest['Chastota (Hz)'].mean():.2f}Hz"
    )
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def districts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if df is None or df.empty:
        text = "❌ Ma'lumot yuklanmagan!"
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    user = update.effective_user
    user_data = get_user_by_id(user.id)
    is_admin_user = is_admin(update)
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    tuman_stats = latest.groupby("District").agg(
        jami=("SensorID", "count"),
        havfsiz=("Fault", lambda x: int((x == 0).sum())),
        ogohlantirish=("Fault", lambda x: int((x == 1).sum())),
        muammo=("Fault", lambda x: int((x == 2).sum())),
    )

    # Foydalanuvchi tumani
    user_district = user_data.get("district") if user_data else None

    if is_admin_user:
        # Admin — barcha tumanlar statistikasi
        text = "🏘️ *Tumanlar bo'yicha holat:*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for district, row in tuman_stats.iterrows():
            if row["muammo"] > 0:
                icon = "🔴"
            elif row["ogohlantirish"] > 0:
                icon = "🟡"
            else:
                icon = "🟢"
            text += (
                f"{icon} *{district}*\n"
                f"   📡 {row['jami']} | ✅ {row['havfsiz']} | ⚠️ {row['ogohlantirish']} | 🔴 {row['muammo']}\n"
            )
    elif user_district and user_district in tuman_stats.index:
        # Oddiy foydalanuvchi — faqat o‘z tumani statistikasi
        row = tuman_stats.loc[user_district]
        if row["muammo"] > 0:
            icon = "🔴"
        elif row["ogohlantirish"] > 0:
            icon = "🟡"
        else:
            icon = "🟢"
        text = (
            f"🏘️ *Sizning tumaningiz: {user_district}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{icon} *{user_district}*\n"
            f"   📡 {row['jami']} | ✅ {row['havfsiz']} | ⚠️ {row['ogohlantirish']} | 🔴 {row['muammo']}\n"
        )
    else:
        # Tumani yo‘q yoki noto‘g‘ri — ogohlantirish
        text = (
            "⚠️ Sizning profilingizda tuman tanlanmagan yoki noto‘g‘ri. "
            "Tumaningizni to‘g‘ri kiriting yoki /start orqali qayta ro‘yxatdan o‘ting."
        )

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown",
                                                       reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(keyboard))


async def sensor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🔍 Sensor ID kiriting (masalan: S001):\n\n"
            "Buyruq: /sensor S001",
            parse_mode="Markdown"
        )
        return

    if not context.args:
        await update.message.reply_text("⚠️ Sensor ID kiriting!\nMasalan: /sensor S001")
        return

    sensor_id = context.args[0].upper()
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return

    sensor_df = df[df["SensorID"] == sensor_id].sort_values("Timestamp")
    if sensor_df.empty:
        await update.message.reply_text(f"❌ *{sensor_id}* topilmadi!\n\nMavjud sensorlar: S001-S500",
                                        parse_mode="Markdown")
        return

    latest = sensor_df.iloc[-1]
    fault = int(latest.get("Fault", 0))
    fault_text = "🔴 MUAMMO" if fault == 2 else ("🟡 OGOHLANTIRISH" if fault == 1 else "🟢 HAVFSIZ")

    fault_counts = sensor_df["Fault"].value_counts().to_dict()

    text = (
        f"🔍 *Sensor: {sensor_id}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 Tuman: {latest.get('District', 'N/A')}\n"
        f"📡 Holat: {fault_text}\n"
        f"📅 Oxirgi: {str(latest['Timestamp'])[:19]}\n"
        f"📊 Jami yozuvlar: {len(sensor_df)}\n\n"
        f"📈 *Oxirgi o'lchovlar:*\n"
        f"🌡️ Harorat: {latest.get('Muhit_harorat (C)', 0):.1f}°C\n"
        f"🌬️ Shamol: {latest.get('Shamol_tezligi (km/h)', 0):.1f} km/h\n"
        f"🔄 Chastota: {latest.get('Chastota (Hz)', 50):.2f} Hz\n"
        f"🔌 Kuchlanish: {latest.get('Kuchlanish (V)', 220):.1f} V\n"
        f"📳 Vibratsiya: {latest.get('Vibratsiya', 0):.3f}\n"
        f"🔗 Sim holati: {latest.get('Sim_mexanik_holati (%)', 90):.1f}%\n"
        f"💨 Namlik: {latest.get('Atrof_muhit_humidity (%)', 50):.1f}%\n"
        f"⚙️ Quvvat: {latest.get('Quvvati (kW)', 3):.2f} kW\n\n"
        f"📉 *Tarix:*\n"
        f"✅ Havfsiz: {fault_counts.get(0, 0)} | ⚠️ Og'oh: {fault_counts.get(1, 0)} | 🔴 Muammo: {fault_counts.get(2, 0)}"
    )
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(keyboard))


async def danger_sensors_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global df
    if df is None or df.empty:
        text = "❌ Ma'lumot yuklanmagan!"
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    danger = latest[latest["Fault"] == 2]

    if danger.empty:
        text = "✅ Hozirda muammoli sensor yo'q!"
    else:
        text = f"🔴 *Muammoli sensorlar: {len(danger)} ta*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for _, row in danger.head(20).iterrows():
            text += (
                f"🔴 *{row['SensorID']}* — {row['District']}\n"
                f"   🔌 {row['Kuchlanish (V)']:.1f}V | 🔄 {row['Chastota (Hz)']:.2f}Hz | "
                f"📳 {row['Vibratsiya']:.3f}\n"
            )
        if len(danger) > 20:
            text += f"\n... va yana {len(danger) - 20} ta"

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown",
                                                       reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(keyboard))


async def top_danger_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if df is None or df.empty:
        text = "❌ Ma'lumot yuklanmagan!"
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    # Eng ko'p muammo chiqargan sensorlar
    fault_history = df[df["Fault"] == 2].groupby("SensorID").size().sort_values(ascending=False).head(10)

    text = "📋 *Top 10 eng xavfli sensorlar*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (sensor_id, count) in enumerate(fault_history.items(), 1):
        sensor_row = latest[latest["SensorID"] == sensor_id]
        district = sensor_row.iloc[0]["District"] if not sensor_row.empty else "N/A"
        text += f"{i}. 🔴 *{sensor_id}* — {district}\n   Muammo holatlari: {count} marta\n"

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown",
                                                       reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(keyboard))


async def averages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if df is None or df.empty:
        text = "❌ Ma'lumot yuklanmagan!"
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()

    text = (
        "📈 *O'rtacha qiymatlar (500 sensor)*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌡️ Harorat: *{latest['Muhit_harorat (C)'].mean():.1f}°C*\n"
        f"   ↕️ Min: {latest['Muhit_harorat (C)'].min():.1f} | Max: {latest['Muhit_harorat (C)'].max():.1f}\n\n"
        f"🌬️ Shamol: *{latest['Shamol_tezligi (km/h)'].mean():.1f} km/h*\n"
        f"   ↕️ Min: {latest['Shamol_tezligi (km/h)'].min():.1f} | Max: {latest['Shamol_tezligi (km/h)'].max():.1f}\n\n"
        f"🔄 Chastota: *{latest['Chastota (Hz)'].mean():.2f} Hz*\n"
        f"   ↕️ Min: {latest['Chastota (Hz)'].min():.2f} | Max: {latest['Chastota (Hz)'].max():.2f}\n\n"
        f"🔌 Kuchlanish: *{latest['Kuchlanish (V)'].mean():.1f} V*\n"
        f"   ↕️ Min: {latest['Kuchlanish (V)'].min():.1f} | Max: {latest['Kuchlanish (V)'].max():.1f}\n\n"
        f"📳 Vibratsiya: *{latest['Vibratsiya'].mean():.3f}*\n"
        f"   ↕️ Min: {latest['Vibratsiya'].min():.3f} | Max: {latest['Vibratsiya'].max():.3f}\n\n"
        f"🔗 Sim holati: *{latest['Sim_mexanik_holati (%)'].mean():.1f}%*\n"
        f"   ↕️ Min: {latest['Sim_mexanik_holati (%)'].min():.1f} | Max: {latest['Sim_mexanik_holati (%)'].max():.1f}\n\n"
        f"💨 Namlik: *{latest['Atrof_muhit_humidity (%)'].mean():.1f}%*\n"
        f"   ↕️ Min: {latest['Atrof_muhit_humidity (%)'].min():.1f} | Max: {latest['Atrof_muhit_humidity (%)'].max():.1f}\n\n"
        f"⚙️ Quvvat: *{latest['Quvvati (kW)'].mean():.2f} kW*\n"
        f"   ↕️ Min: {latest['Quvvati (kW)'].min():.2f} | Max: {latest['Quvvati (kW)'].max():.2f}"
    )
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown",
                                                       reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(keyboard))



async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI model bilan bashorat — parametrlarni yuborish"""
    if update.callback_query:
        text = (
            "🧠 *AI Model — Parametr kiriting*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Quyidagi formatda yuboring:\n\n"
            "`/predict 30 7 50 220 0.5 90 60 3`\n\n"
            "Tartib:\n"
            "1. 🌡️ Harorat (°C)\n"
            "2. 🌬️ Shamol (km/h)\n"
            "3. 🔄 Chastota (Hz)\n"
            "4. 🔌 Kuchlanish (V)\n"
            "5. 📳 Vibratsiya\n"
            "6. 🔗 Sim holati (%)\n"
            "7. 💨 Namlik (%)\n"
            "8. ⚙️ Quvvat (kW)"
        )
        await update.callback_query.edit_message_text(text, parse_mode="Markdown")
        return

    await update.message.reply_text(
        "🧠 Parametrlarni yuboring:\n"
        "`/predict 30 7 50 220 0.5 90 60 3`",
        parse_mode="Markdown"
    )


async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI model bilan bashorat"""
    if hybrid_model is None:
        await update.message.reply_text("❌ Model yuklanmagan!")
        return

    if not context.args or len(context.args) != 8:
        await update.message.reply_text(
            "⚠️ 8 ta parametr kerak!\n\n"
            "`/predict harorat shamol chastota kuchlanish vibratsiya sim_holati namlik quvvat`\n\n"
            "Masalan: `/predict 30 7 50 220 0.5 90 60 3`",
            parse_mode="Markdown"
        )
        return

    try:
        values = [float(x) for x in context.args]
        harorat, shamol, chastota, kuchlanish, vibratsiya, sim_holati, humidity, quvvat = values

        # Model bashorati
        pred_input = pd.DataFrame([values], columns=FEATURE_COLS)
        prediction = int(hybrid_model.predict(pred_input)[0])

        if prediction == 0:
            level = "✅ HAVFSIZ"
            level_msg = "Barcha parametrlar normal. Tizim barqaror."
        elif prediction == 1:
            level = "⚠️ OGOHLANTIRISH"
            level_msg = "Ba'zi parametrlar chegaraga yaqin. Monitoring kuchaytirilsin."
        else:
            level = "🔴 MUAMMO"
            level_msg = "Xavfli holat! Darhol choralar ko'rilsin."

        # Har bir parametr tekshiruvi
        checks = []
        if 210 <= kuchlanish <= 230:
            checks.append("🔌 Kuchlanish: ✅ Normal")
        elif 200 <= kuchlanish <= 240:
            checks.append(f"🔌 Kuchlanish: ⚠️ {kuchlanish}V")
        else:
            checks.append(f"🔌 Kuchlanish: 🔴 {kuchlanish}V — XAVF!")

        if 49.5 <= chastota <= 50.5:
            checks.append("🔄 Chastota: ✅ Normal")
        elif 49.0 <= chastota <= 51.0:
            checks.append(f"🔄 Chastota: ⚠️ {chastota}Hz")
        else:
            checks.append(f"🔄 Chastota: 🔴 {chastota}Hz — XAVF!")

        if harorat < 40:
            checks.append("🌡️ Harorat: ✅ Normal")
        elif harorat <= 45:
            checks.append(f"🌡️ Harorat: ⚠️ {harorat}°C")
        else:
            checks.append(f"🌡️ Harorat: 🔴 {harorat}°C — XAVF!")

        if vibratsiya < 1.0:
            checks.append("📳 Vibratsiya: ✅ Normal")
        elif vibratsiya <= 1.5:
            checks.append(f"📳 Vibratsiya: ⚠️ {vibratsiya}")
        else:
            checks.append(f"📳 Vibratsiya: 🔴 {vibratsiya} — XAVF!")

        if sim_holati > 85:
            checks.append("🔗 Sim holati: ✅ Normal")
        elif sim_holati >= 75:
            checks.append(f"🔗 Sim holati: ⚠️ {sim_holati}%")
        else:
            checks.append(f"🔗 Sim holati: 🔴 {sim_holati}% — XAVF!")

        if shamol < 15:
            checks.append("🌬️ Shamol: ✅ Normal")
        elif shamol <= 25:
            checks.append(f"🌬️ Shamol: ⚠️ {shamol}km/h")
        else:
            checks.append(f"🌬️ Shamol: 🔴 {shamol}km/h — XAVF!")

        checks_text = "\n".join(checks)

        text = (
            f"🧠 *AI Bashorat natijasi*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 Natija: *{level}*\n"
            f"💬 {level_msg}\n\n"
            f"📋 *Parametr tekshiruvi:*\n"
            f"{checks_text}\n\n"
            f"📥 *Kiritilgan qiymatlar:*\n"
            f"🌡️ {harorat}°C | 🌬️ {shamol}km/h\n"
            f"🔄 {chastota}Hz | 🔌 {kuchlanish}V\n"
            f"📳 {vibratsiya} | 🔗 {sim_holati}%\n"
            f"💨 {humidity}% | ⚙️ {quvvat}kW"
        )
        keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
        await update.message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri qiymat! Faqat raqam kiriting.")


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toshkent ob-havo prognozi"""
    try:
        resp = http_req.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": 41.3111, "longitude": 69.2797,
            "current": "temperature_2m,wind_speed_10m,relative_humidity_2m",
            "daily": "temperature_2m_max,temperature_2m_min,wind_speed_10m_max,precipitation_sum",
            "timezone": "Asia/Tashkent",
            "forecast_days": 7
        }, timeout=10)
        data = resp.json()
        current = data.get("current", {})
        daily = data.get("daily", {})

        text = (
            f"🌤️ *Toshkent ob-havo*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📡 *Hozir:*\n"
            f"🌡️ Harorat: {current.get('temperature_2m', 'N/A')}°C\n"
            f"🌬️ Shamol: {current.get('wind_speed_10m', 'N/A')} km/h\n"
            f"💨 Namlik: {current.get('relative_humidity_2m', 'N/A')}%\n\n"
            f"📆 *7 kunlik prognoz:*\n"
        )
        if daily.get("time"):
            for i in range(min(7, len(daily["time"]))):
                day = daily["time"][i][5:]
                tmax = daily["temperature_2m_max"][i]
                tmin = daily["temperature_2m_min"][i]
                wind = daily["wind_speed_10m_max"][i]
                rain = daily["precipitation_sum"][i]
                rain_icon = "🌧️" if rain > 1 else "☀️"
                text += f"  {rain_icon} {day}: {tmin:.0f}–{tmax:.0f}°C | 🌬️{wind:.0f}km/h | 💧{rain:.1f}mm\n"

        keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown",
                                                           reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, parse_mode="Markdown",
                                            reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        error_text = f"❌ Ob-havo yuklanmadi: {e}"
        if update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)


# ==================== 📊 GRAFIK ====================

async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sensor grafigi — /chart S001"""
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "📊 Sensor grafigi uchun ID kiriting:\n\n"
            "Buyruq: `/chart S001`",
            parse_mode="Markdown"
        )
        return

    if not context.args:
        await update.message.reply_text("⚠️ Sensor ID kiriting!\nMasalan: /chart S001")
        return

    sensor_id = context.args[0].upper()
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return

    sensor_df = df[df["SensorID"] == sensor_id].sort_values("Timestamp").tail(200)
    if sensor_df.empty:
        await update.message.reply_text(f"❌ *{sensor_id}* topilmadi!", parse_mode="Markdown")
        return

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(f"📊 {sensor_id} — {sensor_df.iloc[-1].get('District', 'N/A')}", fontsize=14, fontweight="bold")

    ts = sensor_df["Timestamp"]

    # Kuchlanish
    axes[0, 0].plot(ts, sensor_df["Kuchlanish (V)"], color="#e74c3c", linewidth=1)
    axes[0, 0].axhline(y=220, color="green", linestyle="--", alpha=0.5, label="Normal: 220V")
    axes[0, 0].set_title("🔌 Kuchlanish (V)")
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].tick_params(axis="x", rotation=30, labelsize=7)

    # Harorat
    axes[0, 1].plot(ts, sensor_df["Muhit_harorat (C)"], color="#e67e22", linewidth=1)
    axes[0, 1].set_title("🌡️ Harorat (°C)")
    axes[0, 1].tick_params(axis="x", rotation=30, labelsize=7)

    # Chastota
    axes[1, 0].plot(ts, sensor_df["Chastota (Hz)"], color="#3498db", linewidth=1)
    axes[1, 0].axhline(y=50.0, color="green", linestyle="--", alpha=0.5, label="Normal: 50Hz")
    axes[1, 0].set_title("🔄 Chastota (Hz)")
    axes[1, 0].legend(fontsize=8)
    axes[1, 0].tick_params(axis="x", rotation=30, labelsize=7)

    # Vibratsiya
    axes[1, 1].plot(ts, sensor_df["Vibratsiya"], color="#9b59b6", linewidth=1)
    axes[1, 1].set_title("📳 Vibratsiya")
    axes[1, 1].tick_params(axis="x", rotation=30, labelsize=7)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    buf.seek(0)
    plt.close(fig)

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_photo(
        photo=buf,
        caption=f"📊 *{sensor_id}* oxirgi 200 yozuv grafigi",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================== 🔔 AUTO-ALERT ====================

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xavfli holatlar haqida avtomatik xabar olish"""
    chat_id = update.effective_chat.id
    if chat_id in subscribers:
        text = "✅ Siz allaqachon obuna bo'lgansiz!\n\n🔔 Xavfli holat topilganda avtomatik xabar olasiz."
    else:
        subscribers.add(chat_id)
        save_subscribers(subscribers)
        text = "🔔 *Obuna muvaffaqiyatli!*\n\nXavfli sensorlar topilganda avtomatik xabar olasiz.\nBekor qilish: /unsubscribe"
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obunani bekor qilish"""
    chat_id = update.effective_chat.id
    if chat_id in subscribers:
        subscribers.discard(chat_id)
        save_subscribers(subscribers)
        text = "🔕 Obuna bekor qilindi."
    else:
        text = "⚠️ Siz obuna emassiz. Obuna bo'lish: /subscribe"
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def alert_check(context: ContextTypes.DEFAULT_TYPE):
    """Har 1 soatda xavfli sensorlarni tekshirish va xabar yuborish"""
    if df is None or df.empty or not subscribers:
        return

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    danger = latest[latest["Fault"] == 2]

    if danger.empty:
        return

    text = (
        f"🚨 *AVTOMATIK OGOHLANTIRISH*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"🔴 Muammoli sensorlar: *{len(danger)} ta*\n\n"
    )
    for _, row in danger.head(10).iterrows():
        text += f"🔴 *{row['SensorID']}* — {row['District']} | 🔌{row['Kuchlanish (V)']:.0f}V\n"
    if len(danger) > 10:
        text += f"\n... va yana {len(danger) - 10} ta"

    for chat_id in list(subscribers):
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        except Exception:
            subscribers.discard(chat_id)
            save_subscribers(subscribers)


# ==================== 📥 EXPORT ====================

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Haftalik hisobot CSV"""
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    report_cols = ["SensorID", "District", "Fault", "Kuchlanish (V)", "Chastota (Hz)",
                   "Muhit_harorat (C)", "Vibratsiya", "Sim_mexanik_holati (%)", "Timestamp"]
    report_df = latest[report_cols].copy()
    report_df["Holat"] = report_df["Fault"].map({0: "Havfsiz", 1: "Ogohlantirish", 2: "Muammo"})

    buf = io.BytesIO()
    report_df.to_csv(buf, index=False, encoding="utf-8-sig")
    buf.seek(0)

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_document(
        document=buf,
        filename=f"hisobot_{now_str}.csv",
        caption=f"📥 *Hisobot* — {len(report_df)} sensor\n📅 {now_str}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def csv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sensor ma'lumotini CSV faylda yuborish — /csv S001"""
    if not context.args:
        await update.message.reply_text("⚠️ Sensor ID kiriting!\nMasalan: /csv S001")
        return

    sensor_id = context.args[0].upper()
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return

    sensor_df = df[df["SensorID"] == sensor_id].sort_values("Timestamp")
    if sensor_df.empty:
        await update.message.reply_text(f"❌ *{sensor_id}* topilmadi!", parse_mode="Markdown")
        return

    buf = io.BytesIO()
    sensor_df.to_csv(buf, index=False, encoding="utf-8-sig")
    buf.seek(0)

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_document(
        document=buf,
        filename=f"{sensor_id}_data.csv",
        caption=f"📥 *{sensor_id}* — {len(sensor_df)} yozuv",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================== 🔎 QIDIRUV VA FILTR ====================

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tuman bo'yicha sensorlar — /search Chilonzor"""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Tuman nomini kiriting!\nMasalan: /search Chilonzor\n\n"
            f"Mavjud tumanlar:\n" + "\n".join(f"  • {d}" for d in DISTRICTS)
        )
        return

    query = " ".join(context.args)
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return

    # Partial match
    matched = [d for d in DISTRICTS if query.lower() in d.lower()]
    if not matched:
        await update.message.reply_text(f"❌ '{query}' tumani topilmadi!")
        return

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    text = ""
    for district in matched:
        d_sensors = latest[latest["District"] == district]
        if d_sensors.empty:
            continue
        safe = int((d_sensors["Fault"] == 0).sum())
        warn = int((d_sensors["Fault"] == 1).sum())
        danger = int((d_sensors["Fault"] == 2).sum())
        text += (
            f"🏘️ *{district}*\n"
            f"   📡 {len(d_sensors)}\n"
            f"   ✅ {safe} | ⚠️ {warn} | 🔴 {danger}\n\n"
        )
        for _, row in d_sensors.head(15).iterrows():
            fault_icon = "🔴" if row["Fault"] == 2 else ("🟡" if row["Fault"] == 1 else "🟢")
            text += f"  {fault_icon} {row['SensorID']} — 🔌{row['Kuchlanish (V)']:.0f}V | 🔄{row['Chastota (Hz)']:.2f}Hz\n"
        if len(d_sensors) > 15:
            text += f"  ... va yana {len(d_sensors) - 15} ta\n"

    if not text:
        text = "Ma'lumot topilmadi."

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Filtr — /filter danger Chilonzor yoki /filter safe"""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Filtr turini kiriting!\n\n"
            "Masalan:\n"
            "  /filter danger\n"
            "  /filter warn Chilonzor\n"
            "  /filter safe Bektemir"
        )
        return

    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return

    level = context.args[0].lower()
    district_query = " ".join(context.args[1:]) if len(context.args) > 1 else None

    fault_map = {"danger": 2, "warn": 1, "safe": 0, "muammo": 2, "ogohlantirish": 1, "havfsiz": 0}
    if level not in fault_map:
        await update.message.reply_text("⚠️ Tur: danger, warn, safe")
        return

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    filtered = latest[latest["Fault"] == fault_map[level]]

    if district_query:
        matched = [d for d in DISTRICTS if district_query.lower() in d.lower()]
        if matched:
            filtered = filtered[filtered["District"].isin(matched)]

    level_icons = {0: "🟢 HAVFSIZ", 1: "🟡 OGOHLANTIRISH", 2: "🔴 MUAMMO"}
    level_text = level_icons.get(fault_map[level], level)

    if filtered.empty:
        text = f"✅ {level_text} sensorlar topilmadi!"
    else:
        text = f"🔎 *{level_text}* — {len(filtered)} ta sensor\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for _, row in filtered.head(25).iterrows():
            text += f"• *{row['SensorID']}* — {row['District']} | 🔌{row['Kuchlanish (V)']:.0f}V\n"
        if len(filtered) > 25:
            text += f"\n... va yana {len(filtered) - 25} ta"

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== 📈 TAQQOSLASH ====================

async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ikki sensorni solishtirish — /compare S001 S002"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("⚠️ Ikki sensor ID kiriting!\nMasalan: /compare S001 S002")
        return

    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return

    s1, s2 = context.args[0].upper(), context.args[1].upper()
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    r1 = latest[latest["SensorID"] == s1]
    r2 = latest[latest["SensorID"] == s2]

    if r1.empty or r2.empty:
        await update.message.reply_text(f"❌ Sensor topilmadi! ({s1} yoki {s2})")
        return

    r1, r2 = r1.iloc[0], r2.iloc[0]
    fault_t = {0: "🟢 Havfsiz", 1: "🟡 Og'oh", 2: "🔴 Muammo"}

    text = (
        f"📈 *Taqqoslash: {s1} vs {s2}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{'Parametr':<20} {'| ' + s1:<12} {'| ' + s2}\n"
        f"{'─' * 44}\n"
        f"📍 Tuman:            | {r1['District']:<10} | {r2['District']}\n"
        f"📡 Holat:            | {fault_t[r1['Fault']]:<10} | {fault_t[r2['Fault']]}\n"
        f"🔌 Kuchlanish:       | {r1['Kuchlanish (V)']:.1f}V{'':<4} | {r2['Kuchlanish (V)']:.1f}V\n"
        f"🔄 Chastota:         | {r1['Chastota (Hz)']:.2f}Hz{'':<2} | {r2['Chastota (Hz)']:.2f}Hz\n"
        f"🌡️ Harorat:          | {r1['Muhit_harorat (C)']:.1f}°C{'':<3} | {r2['Muhit_harorat (C)']:.1f}°C\n"
        f"📳 Vibratsiya:       | {r1['Vibratsiya']:.3f}{'':<4} | {r2['Vibratsiya']:.3f}\n"
        f"🔗 Sim holati:       | {r1['Sim_mexanik_holati (%)']:.1f}%{'':<4} | {r2['Sim_mexanik_holati (%)']:.1f}%\n"
        f"⚙️ Quvvat:           | {r1['Quvvati (kW)']:.2f}kW{'':<3} | {r2['Quvvati (kW)']:.2f}kW\n"
    )

    # Grafik
    s1_df = df[df["SensorID"] == s1].sort_values("Timestamp").tail(100)
    s2_df = df[df["SensorID"] == s2].sort_values("Timestamp").tail(100)

    fig, ax = plt.subplots(1, 1, figsize=(10, 4))
    ax.plot(s1_df["Timestamp"], s1_df["Kuchlanish (V)"], label=s1, linewidth=1.2)
    ax.plot(s2_df["Timestamp"], s2_df["Kuchlanish (V)"], label=s2, linewidth=1.2)
    ax.axhline(y=220, color="green", linestyle="--", alpha=0.4, label="Normal 220V")
    ax.set_title(f"Kuchlanish taqqoslash: {s1} vs {s2}")
    ax.legend()
    ax.tick_params(axis="x", rotation=30, labelsize=7)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    buf.seek(0)
    plt.close(fig)

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_photo(photo=buf, caption=text, parse_mode="Markdown",
                                     reply_markup=InlineKeyboardMarkup(keyboard))


def _district_select_keyboard(prefix, exclude=None):
    """Tuman tanlash tugmalari yasash"""
    keyboard = []
    row = []
    for d in DISTRICTS:
        if exclude and d == exclude:
            continue
        row.append(InlineKeyboardButton(d, callback_data=f"{prefix}{d}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")])
    return InlineKeyboardMarkup(keyboard)


def _build_district_compare_text(d1, d2):
    """Ikki tuman taqqoslash natijasini tayyorlash"""
    if df is None or df.empty:
        return "❌ Ma'lumot yuklanmagan!"
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    text = f"🏘️ *{d1} vs {d2}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for dname in [d1, d2]:
        dd = latest[latest["District"] == dname]
        safe = int((dd["Fault"] == 0).sum())
        warn = int((dd["Fault"] == 1).sum())
        danger = int((dd["Fault"] == 2).sum())
        text += (
            f"*{dname}:*\n"
            f"  📡 Sensorlar: {len(dd)}\n"
            f"  ✅ {safe} | ⚠️ {warn} | 🔴 {danger}\n"
            f"  🔌 O'rt. kuchlanish: {dd['Kuchlanish (V)'].mean():.1f}V\n"
            f"  🌡️ O'rt. harorat: {dd['Muhit_harorat (C)'].mean():.1f}°C\n"
            f"  🔄 O'rt. chastota: {dd['Chastota (Hz)'].mean():.2f}Hz\n\n"
        )
    return text


async def district_compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tumanlarni solishtirish — /district_compare yoki tugma orqali"""
    # Agar argumentlar berilgan bo'lsa, to'g'ridan-to'g'ri taqqoslash
    if context.args and len(context.args) >= 2:
        d1_q, d2_q = context.args[0], context.args[1]
        d1_m = [d for d in DISTRICTS if d1_q.lower() in d.lower()]
        d2_m = [d for d in DISTRICTS if d2_q.lower() in d.lower()]
        if not d1_m or not d2_m:
            await update.message.reply_text("❌ Tuman topilmadi!")
            return
        text = _build_district_compare_text(d1_m[0], d2_m[0])
        keyboard = [[InlineKeyboardButton("🔄 Qayta tanlash", callback_data="dc_start"),
                      InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
        await update.message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Argumentsiz — 1-tuman tanlash menyu
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🏘️ *Tuman taqqoslash*\n\n1️⃣ Birinchi tumanni tanlang:",
            parse_mode="Markdown",
            reply_markup=_district_select_keyboard("dc1_")
        )
    elif msg:
        await msg.reply_text(
            "🏘️ *Tuman taqqoslash*\n\n1️⃣ Birinchi tumanni tanlang:",
            parse_mode="Markdown",
            reply_markup=_district_select_keyboard("dc1_")
        )


# ==================== 🕐 TARIX ====================

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sensor tarixi — /history S001 7"""
    if not context.args:
        await update.message.reply_text("⚠️ Sensor ID kiriting!\nMasalan: /history S001 7 (7 kun)")
        return

    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return

    sensor_id = context.args[0].upper()
    days = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 7
    days = min(days, 30)

    sensor_df = df[df["SensorID"] == sensor_id].sort_values("Timestamp")
    if sensor_df.empty:
        await update.message.reply_text(f"❌ *{sensor_id}* topilmadi!", parse_mode="Markdown")
        return

    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    period = sensor_df[sensor_df["Timestamp"] >= cutoff]

    if period.empty:
        period = sensor_df.tail(50)
        days_note = f"(oxirgi {len(period)} yozuv)"
    else:
        days_note = f"(oxirgi {days} kun)"

    fault_counts = period["Fault"].value_counts().to_dict()
    total = len(period)

    # Holat o'zgarishlari
    changes = []
    prev_fault = None
    for _, row in period.iterrows():
        f = int(row["Fault"])
        if prev_fault is not None and f != prev_fault:
            fault_icons = {0: "🟢", 1: "🟡", 2: "🔴"}
            changes.append(f"  {str(row['Timestamp'])[:16]} {fault_icons.get(prev_fault, '?')}→{fault_icons.get(f, '?')}")
        prev_fault = f

    text = (
        f"🕐 *{sensor_id} tarixi* {days_note}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 Tuman: {sensor_df.iloc[-1].get('District', 'N/A')}\n"
        f"📊 Yozuvlar: {total}\n\n"
        f"📉 *Holat taqsimoti:*\n"
        f"✅ Havfsiz: {fault_counts.get(0, 0)}\n"
        f"⚠️ Ogohlantirish: {fault_counts.get(1, 0)}\n"
        f"🔴 Muammo: {fault_counts.get(2, 0)}\n\n"
        f"🔌 Kuchlanish: {period['Kuchlanish (V)'].min():.1f}–{period['Kuchlanish (V)'].max():.1f}V (o'rt: {period['Kuchlanish (V)'].mean():.1f})\n"
        f"🔄 Chastota: {period['Chastota (Hz)'].min():.2f}–{period['Chastota (Hz)'].max():.2f}Hz\n"
        f"📳 Vibratsiya: {period['Vibratsiya'].min():.3f}–{period['Vibratsiya'].max():.3f}\n\n"
    )

    if changes:
        text += f"🔄 *Holat o'zgarishlari:* ({len(changes)} ta)\n"
        for c in changes[-10:]:
            text += f"{c}\n"
        if len(changes) > 10:
            text += f"  ... va yana {len(changes) - 10} ta\n"
    else:
        text += "✅ Holat o'zgarmagan"

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== 👤 ADMIN ====================

def is_admin(update: Update) -> bool:
    username = (update.effective_user.username or "").lower()
    return username == ADMIN_USERNAME.lower()

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel"""
    if not is_admin(update):
        await update.message.reply_text("🔒 Sizda admin huquqi yo'q!")
        return

    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    total = len(latest)
    safe = int((latest["Fault"] == 0).sum())
    warn = int((latest["Fault"] == 1).sum())
    danger = int((latest["Fault"] == 2).sum())

    # Eng ko'p muammo chiqargan tuman
    district_danger = df[df["Fault"] == 2].groupby("District").size()
    top_district = district_danger.idxmax() if not district_danger.empty else "N/A"
    top_count = int(district_danger.max()) if not district_danger.empty else 0

    text = (
        f"👤 *Admin Panel*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 *Bot statistikasi:*\n"
        f"📋 CSV qatorlar: {len(df):,}\n"
        f"📡 Sensorlar: {total}\n"
        f"🧠 Model: {'✅ Yuklangan' if hybrid_model else '❌ Yuklanmagan'}\n"
        f"� Foydalanuvchilar: {len(load_users())}\n"
        f"�🔔 Obunchilar: {len(subscribers)}\n"
        f"👑 Admin: @{ADMIN_USERNAME}\n\n"
        f"📊 *Hozirgi holat:*\n"
        f"✅ Havfsiz: {safe} ({round(100*safe/total, 1)}%)\n"
        f"⚠️ Ogohlantirish: {warn}\n"
        f"🔴 Muammo: {danger}\n\n"
        f"🏘️ *Eng muammoli tuman:*\n"
        f"🔴 {top_district} — {top_count} marta\n\n"
        f"🔧 *Admin buyruqlari:*\n"
        f"/broadcast \\_text\\_ — Barcha obunchilarga xabar"
    )
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: barcha obunchilarga xabar"""
    user_id = update.effective_user.id
    if not is_admin(update):
        await update.message.reply_text("🔒 Sizda admin huquqi yo'q!")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Xabar matnini kiriting!\nMasalan: /broadcast Tizim yangilandi!")
        return

    msg_text = " ".join(context.args)
    sent, failed = 0, 0
    for chat_id in list(subscribers):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📢 *Admin xabari:*\n\n{msg_text}",
                parse_mode="Markdown"
            )
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"📢 Yuborildi: {sent} | ❌ Xato: {failed}")


# ==================== 🗺️ LOKATSIYA ====================

async def map_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tuman lokatsiyasi — /map Chilonzor"""
    if not context.args:
        keyboard = []
        row = []
        for i, d in enumerate(DISTRICTS):
            row.append(InlineKeyboardButton(d, callback_data=f"map_{d}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")])
        await update.message.reply_text(
            "🗺️ *Tuman tanlang:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    query = " ".join(context.args)
    matched = [d for d in DISTRICTS if query.lower() in d.lower()]
    if not matched:
        await update.message.reply_text(f"❌ '{query}' tumani topilmadi!")
        return

    district = matched[0]
    coords = DISTRICT_COORDS.get(district, (41.3111, 69.2797))

    if df is not None and not df.empty:
        latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
        dd = latest[latest["District"] == district]
        safe = int((dd["Fault"] == 0).sum())
        warn = int((dd["Fault"] == 1).sum())
        danger = int((dd["Fault"] == 2).sum())
        info = f"\n📡 {len(dd)} sensor | ✅ {safe} | ⚠️ {warn} | 🔴 {danger}"
    else:
        info = ""

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_location(latitude=coords[0], longitude=coords[1])
    await update.message.reply_text(
        f"🗺️ *{district}*{info}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "menu":
        keyboard = [
            [InlineKeyboardButton("📊 Statistika", callback_data="stats"),
             InlineKeyboardButton("🔮 Prognoz", callback_data="forecast")],
            [InlineKeyboardButton("🏘️ Tumanlar", callback_data="districts"),
             InlineKeyboardButton("🔍 Sensor tekshirish", callback_data="sensor_check")],
            [InlineKeyboardButton("🧠 Model bashorat", callback_data="model"),
             InlineKeyboardButton("🔴 Muammoli sensorlar", callback_data="danger_sensors")],
            [InlineKeyboardButton("📈 O'rtachalar", callback_data="averages"),
             InlineKeyboardButton("📋 Top 10 xavfli", callback_data="top_danger")],
            [InlineKeyboardButton("📊 Grafik", callback_data="chart_check"),
             InlineKeyboardButton("📈 Taqqoslash", callback_data="compare_check")],
            [InlineKeyboardButton("🕐 Tarix", callback_data="history_check"),
             InlineKeyboardButton("🗺️ Xarita", callback_data="map_check")],
            [InlineKeyboardButton("📥 Hisobot", callback_data="report_check"),
             InlineKeyboardButton("🔔 Obuna", callback_data="subscribe_check")],
            [InlineKeyboardButton("🌤️ Ob-havo", callback_data="weather"),
             InlineKeyboardButton("ℹ️ Yordam", callback_data="help")]
        ]
        await query.edit_message_text(
            "⚡ *Elektr Monitoring Bot*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Quyidagi tugmalardan birini tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    elif data == "stats":
        await stats_command(update, context)
    elif data == "forecast":
        await forecast_command(update, context)
    elif data == "districts":
        await districts_command(update, context)
    elif data == "sensor_check":
        await sensor_command(update, context)
    elif data == "model":
        await model_command(update, context)
    elif data == "danger_sensors":
        await danger_sensors_command(update, context)
    elif data == "top_danger":
        await top_danger_command(update, context)
    elif data == "averages":
        await averages_command(update, context)
    elif data == "weather":
        await weather_command(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data == "chart_check":
        await query.edit_message_text(
            "� *Sensor grafigi:*\n\n"
            "Sensor ID kiriting va `/chart` buyrug'ini yuboring:\n\n"
            "Masalan: `/chart S001`\n\n"
            "Grafik oxirgi 200 ta o'lchovni ko'rsatadi:\n"
            "🔌 Kuchlanish | 🌡️ Harorat\n"
            "🔄 Chastota | 📳 Vibratsiya",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]
            ])
        )
    elif data == "compare_check":
        await query.edit_message_text(
            "�📈 *Taqqoslash:*\n\n"
            "🔹 Sensorlar: `/compare S001 S002`\n"
            "🔹 Tumanlar: tugmani bosing 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏘️ Tumanlarni taqqoslash", callback_data="dc_start")],
                [InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]
            ])
        )
    elif data == "dc_start":
        await query.edit_message_text(
            "🏘️ *Tuman taqqoslash*\n\n1️⃣ Birinchi tumanni tanlang:",
            parse_mode="Markdown",
            reply_markup=_district_select_keyboard("dc1_")
        )
    elif data.startswith("dc1_"):
        d1 = data[4:]
        await query.edit_message_text(
            f"🏘️ *Tuman taqqoslash*\n\n"
            f"1️⃣ {d1} ✅\n\n2️⃣ Ikkinchi tumanni tanlang:",
            parse_mode="Markdown",
            reply_markup=_district_select_keyboard(f"dc2_{d1}_", exclude=d1)
        )
    elif data.startswith("dc2_"):
        parts = data[4:].rsplit("_", 1)
        d1, d2 = parts[0], parts[1]
        text = _build_district_compare_text(d1, d2)
        keyboard = [[InlineKeyboardButton("🔄 Qayta tanlash", callback_data="dc_start"),
                      InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "history_check":
        await query.edit_message_text(
            "🕐 *Tarix:*\n\n"
            "Buyruq: `/history S001 7`\n"
            "(S001 sensori, oxirgi 7 kun)",
            parse_mode="Markdown"
        )
    elif data == "map_check":
        # Tuman tanlash tugmalari ko'rsatish
        keyboard = []
        row = []
        for d in DISTRICTS:
            row.append(InlineKeyboardButton(d, callback_data=f"map_{d}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")])
        await query.edit_message_text(
            "🗺️ *Tuman tanlang:*\n\nLokatsiya va statistika yuboriladi.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "report_check":
        await query.edit_message_text(
            "📥 *Export:*\n\n"
            "🔹 Umumiy hisobot: /report\n"
            "🔹 Sensor CSV: `/csv S001`",
            parse_mode="Markdown"
        )
    elif data == "subscribe_check":
        await query.edit_message_text(
            "🔔 *Auto-alert obuna:*\n\n"
            "🔹 Obuna bo'lish: /subscribe\n"
            "🔹 Bekor qilish: /unsubscribe\n\n"
            "Har 1 soatda xavfli sensorlar tekshiriladi va avtomatik xabar yuboriladi.",
            parse_mode="Markdown"
        )
    elif data.startswith("map_") and not data == "map_check":
        district = data[4:]
        coords = DISTRICT_COORDS.get(district, (41.2995, 69.2401))

        # Statistika yig'ish
        if df is not None and not df.empty:
            latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
            dd = latest[latest["District"] == district]
            jami = len(dd)
            safe = int((dd["Fault"] == 0).sum())
            warn = int((dd["Fault"] == 1).sum())
            danger = int((dd["Fault"] == 2).sum())
            if danger > 0:
                holat = "🔴 Muammolar bor"
            elif warn > 0:
                holat = "🟡 Ogohlantirish"
            else:
                holat = "🟢 Barqaror"
            # Top 5 muammoli sensor
            danger_sensors = dd[dd["Fault"] == 2].head(5)
            sensor_lines = ""
            for _, r in danger_sensors.iterrows():
                sensor_lines += f"\n  🔴 {r['SensorID']} | 🔌{r.get('Kuchlanish (V)', 0):.0f}V | 🔄{r.get('Chastota (Hz)', 50):.2f}Hz"
            stats_text = (
                f"🗺️ *{district} tumani*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📡 Holat: {holat}\n"
                f"📊 Jami: {jami} sensor\n"
                f"✅ Havfsiz: {safe}  ⚠️ Og'oh: {warn}  🔴 Muammo: {danger}\n"
            )
            if danger > 0:
                stats_text += f"\n🔴 *Muammoli sensorlar:*{sensor_lines}"
                if danger > 5:
                    stats_text += f"\n  ... va yana {danger - 5} ta"
        else:
            stats_text = f"🗺️ *{district} tumani*\n\n❌ Ma'lumot yuklanmagan."

        keyboard = [
            [InlineKeyboardButton("🔙 Tumanlar", callback_data="map_check"),
             InlineKeyboardButton("🏠 Bosh menyu", callback_data="menu")]
        ]
        # Xabarni yangilash
        await query.edit_message_text(
            stats_text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Telegram lokatsiya (koordinata pin) yuborish
        await context.bot.send_location(
            chat_id=update.effective_chat.id,
            latitude=coords[0], longitude=coords[1]
        )


# ==================== MAIN ====================

def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN o'rnatilmagan!")
        logger.error("1. @BotFather dan token oling")
        logger.error("2. .env faylga TELEGRAM_BOT_TOKEN=xxx qo'shing")
        return


    load_data()
    load_model()
    global subscribers
    subscribers = load_subscribers()
    app = Application.builder().token(BOT_TOKEN).build()
    # Global error handler
    app.add_error_handler(error_handler)

    # Ro'yxatdan o'tish ConversationHandler
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REG_PHONE: [
                MessageHandler(filters.CONTACT, reg_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_phone),
            ],
            REG_FIRSTNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_firstname)],
            REG_LASTNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_lastname)],
            REG_DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_district)],
        },
        fallbacks=[CommandHandler("start", start), CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
        per_message=False,
    )
    app.add_handler(reg_conv)

    # Qolgan buyruqlar
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("forecast", forecast_command))
    app.add_handler(CommandHandler("districts", districts_command))
    app.add_handler(CommandHandler("sensor", sensor_command))
    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(CommandHandler("predict", predict_command))
    app.add_handler(CommandHandler("danger", danger_sensors_command))
    app.add_handler(CommandHandler("top", top_danger_command))
    app.add_handler(CommandHandler("averages", averages_command))
    app.add_handler(CommandHandler("weather", weather_command))
    app.add_handler(CommandHandler("chart", chart_command))
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("csv", csv_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("filter", filter_command))
    app.add_handler(CommandHandler("compare", compare_command))
    app.add_handler(CommandHandler("district_compare", district_compare_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("map", map_command))

    # Callback buttons
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info("🤖 Bot ishga tushdi! (ro'yxatdan o'tish yangilandi)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
