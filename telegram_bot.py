# ======================== IMPORTS ========================
from __future__ import annotations

import os
import io
import json
import math
import logging
import datetime
import pickle
import requests
import time as _time

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ConversationHandler, ContextTypes
)

# ======================== CONFIG ========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_bot")

# .env fayldan token o'qish
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv yo'q bo'lsa, .env ni qo'lda o'qiymiz
    _env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(_env_path):
        with open(_env_path, encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SITE_BASE = os.environ.get("SITE_BASE", "http://localhost:5000")

USERS_FILE = "users.json"
SUBSCRIBERS_FILE = "subscribers.json"
ADMIN_USERNAME = "gaybullayeev19"

REG_PHONE, REG_FIRSTNAME, REG_LASTNAME, REG_DISTRICT, REG_LOCATION = range(5)

DISTRICTS = [
    "Bektemir", "Chilonzor", "Mirabad", "Mirobod", "Mirzo Ulug'bek", "Olmazor",
    "Sergeli", "Shayxontohur", "Uchtepa", "Yakkasaroy", "Yashnobod", "Yunusobod"
]

DISTRICT_COORDS = {
    "Bektemir":        (41.2092, 69.3347),
    "Chilonzor":       (41.2557, 69.2044),
    "Mirabad":         (41.2855, 69.2641),
    "Mirobod":         (41.2855, 69.2641),
    "Mirzo Ulug'bek":  (41.3385, 69.3347),
    "Olmazor":         (41.3543, 69.2121),
    "Sergeli":         (41.2321, 69.2121),
    "Shayxontohur":    (41.3275, 69.2285),
    "Uchtepa":         (41.2995, 69.1842),
    "Yakkasaroy":      (41.2995, 69.2641),
    "Yashnobod":       (41.3385, 69.3347),
    "Yunusobod":       (41.3543, 69.3347),
}

FEATURE_COLS = [
    "Muhit_harorat (C)", "Shamol_tezligi (km/h)", "Chastota (Hz)", "Kuchlanish (V)",
    "Vibratsiya", "Sim_mexanik_holati (%)", "Atrof_muhit_humidity (%)", "Quvvati (kW)"
]

# ======================== GLOBALS ========================
df = None
hybrid_model = None
subscribers = set()
_last_err = {"msg": None, "ts": 0}

# ======================== DATA LOADING ========================
def load_data():
    global df
    try:
        df1 = pd.read_csv("data/sensor_data_part1.csv")
        df2 = pd.read_csv("data/sensor_data_part2.csv")
        df = pd.concat([df1, df2], ignore_index=True)
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
            except Exception as e:
                print(f"Fault qayta taqsimlash xatosi: {e}")
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        print(f"[DIAG] Ma'lumot yuklandi: {df.shape[0]} satr")
    except Exception as e:
        print(f"Ma'lumotlarni yuklashda xatolik: {e}")
        df = None


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

# ======================== USER MANAGEMENT ========================
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
    for u in load_users():
        if u.get("id") == user_id:
            return u
    return None

def update_user(user_id, **kwargs):
    users = load_users()
    for u in users:
        if u.get("id") == user_id:
            u.update(kwargs)
            save_users(users)
            return True
    return False

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

def is_admin(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False
    return (user.username or "").lower() == ADMIN_USERNAME.lower()

# ======================== UTILS ========================
def haversine(lat1, lon1, lat2, lon2):
    """Ikki koordinata orasidagi masofani km da qaytaradi."""
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

async def error_handler(update, context):
    msg = str(context.error)
    now = _time.time()
    if msg == _last_err["msg"] and now - _last_err["ts"] < 10:
        return
    logger.error(f"Bot error: {msg}")
    _last_err.update({"msg": msg, "ts": now})

# ======================== MAIN MENU ========================
async def send_main_menu(message):
    keyboard = [
        [InlineKeyboardButton("📊 Statistika",        callback_data="stats"),
         InlineKeyboardButton("🔮 Prognoz",           callback_data="forecast")],
        [InlineKeyboardButton("🏘️ Tumanlar",          callback_data="districts"),
         InlineKeyboardButton("🔍 Sensor tekshirish", callback_data="sensor_check")],
        [InlineKeyboardButton("🧠 Model bashorat",    callback_data="model"),
         InlineKeyboardButton("🔴 Muammoli sensorlar",callback_data="danger_sensors")],
        [InlineKeyboardButton("📈 O'rtachalar",       callback_data="averages"),
         InlineKeyboardButton("📋 Top 10 xavfli",    callback_data="top_danger")],
        [InlineKeyboardButton("📊 Grafik",            callback_data="chart_check"),
         InlineKeyboardButton("📈 Taqqoslash",        callback_data="compare_check")],
        [InlineKeyboardButton("🕐 Tarix",             callback_data="history_check"),
         InlineKeyboardButton("🗺️ Xarita",            callback_data="map_check")],
        [InlineKeyboardButton("📥 Hisobot",           callback_data="report_check"),
         InlineKeyboardButton("🔔 Obuna",             callback_data="subscribe_check")],
        [InlineKeyboardButton("📊 Dashboard",         callback_data="dashboard"),
         InlineKeyboardButton("📍 Yaqin sensorlar",  callback_data="near_sensors_info")],
        [InlineKeyboardButton("🌙 Sokin rejim",       callback_data="silent_toggle"),
         InlineKeyboardButton("🌤️ Ob-havo",           callback_data="weather")],
        [InlineKeyboardButton("ℹ️ Yordam",             callback_data="help")],
    ]
    await message.reply_text(
        "⚡ *Elektr Monitoring Bot*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ======================== REGISTRATION ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user_by_id(user.id)

    if not user_data or not user_data.get("phone"):
        btn = KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
        markup = ReplyKeyboardMarkup([[btn]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "👋 Assalomu alaykum!\n\nRo'yxatdan o'tish uchun telefon raqamingizni yuboring:",
            reply_markup=markup
        )
        return REG_PHONE

    if not user_data.get("first_name"):
        await update.message.reply_text("Ismingizni kiriting:", reply_markup=ReplyKeyboardRemove())
        return REG_FIRSTNAME

    if not user_data.get("last_name"):
        await update.message.reply_text("Familiyangizni kiriting:")
        return REG_LASTNAME

    if not user_data.get("district"):
        keyboard = [[KeyboardButton(d)] for d in DISTRICTS]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Qaysi tumandasiz?", reply_markup=markup)
        return REG_DISTRICT

    if not user_data.get("latitude"):
        loc_btn = KeyboardButton("📍 Joylashuvimni yuborish", request_location=True)
        markup = ReplyKeyboardMarkup(
            [[loc_btn], [KeyboardButton("⏭️ O'tkazib yuborish")]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await update.message.reply_text(
            "📍 *Joylashuvingizni yuboring* (ixtiyoriy)\n\n"
            "📱 *Telefonda:* tugmani bosing\n"
            "🖥 *Telegram Desktop:* koordinatani yozing:\n"
            "`41.2995 69.2641`\n\n"
            "Yoki ⏭️ O'tkazib yuborish",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return REG_LOCATION

    await update.message.reply_text(
        f"Assalomu alaykum, {user_data.get('first_name', '')}!\n⚡ Elektr monitoring botiga xush kelibsiz.",
        reply_markup=ReplyKeyboardRemove()
    )
    await send_main_menu(update.message)
    return ConversationHandler.END


async def reg_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    contact = getattr(update.message, "contact", None)
    text = (update.message.text or "").strip()

    if contact and contact.phone_number:
        phone = contact.phone_number
    elif text:
        digits = "".join(ch for ch in text if ch.isdigit())
        if len(digits) == 9:
            phone = "+998" + digits
        elif len(digits) == 12 and digits.startswith("998"):
            phone = "+" + digits
        else:
            await update.message.reply_text("❌ Noto'g'ri format. Masalan: +998901234567")
            return REG_PHONE
    else:
        await update.message.reply_text("❌ Telefon raqamni yuboring.")
        return REG_PHONE

    if not phone.startswith("+998") or len(phone) != 13:
        await update.message.reply_text("❌ Faqat O'zbekiston raqami: +998XXXXXXXXX")
        return REG_PHONE

    user_data = get_user_by_id(user.id)
    if not user_data:
        users = load_users()
        users.append({
            "id": user.id, "phone": phone,
            "first_name": "", "last_name": "",
            "username": user.username or "", "district": "",
            "latitude": None, "longitude": None,
            "silent_mode": False,
            "joined": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_users(users)
    else:
        update_user(user.id, phone=phone)

    await update.message.reply_text("✅ Telefon saqlandi!\n\nIsmingizni kiriting:", reply_markup=ReplyKeyboardRemove())
    return REG_FIRSTNAME


async def reg_firstname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = (update.message.text or "").strip()
    if len(name) < 2:
        await update.message.reply_text("❌ Kamida 2 harf kiriting:")
        return REG_FIRSTNAME
    update_user(update.effective_user.id, first_name=name)
    await update.message.reply_text("Familiyangizni kiriting:")
    return REG_LASTNAME


async def reg_lastname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = (update.message.text or "").strip()
    if len(name) < 2:
        await update.message.reply_text("❌ Kamida 2 harf kiriting:")
        return REG_LASTNAME
    update_user(user.id, last_name=name, username=user.username or "")
    keyboard = [[KeyboardButton(d)] for d in DISTRICTS]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Qaysi tumandasiz? Tanlang:", reply_markup=markup)
    return REG_DISTRICT


async def reg_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    raw = (update.message.text or "").strip()

    def _norm(s):
        return s.replace("’", "'").replace("‘", "'").replace("ʼ", "'").strip().lower()

    matched = next((d for d in DISTRICTS if _norm(d) == _norm(raw)), None)
    if not matched:
        keyboard = [[KeyboardButton(d)] for d in DISTRICTS]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("❌ Tugma orqali tanlang:", reply_markup=markup)
        return REG_DISTRICT

    update_user(user.id, district=matched)
    loc_btn = KeyboardButton("📍 Joylashuvimni yuborish", request_location=True)
    markup = ReplyKeyboardMarkup(
        [[loc_btn], [KeyboardButton("⏭️ O'tkazib yuborish")]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await update.message.reply_text(
        f"✅ Tuman saqlandi: *{matched}*\n\n"
        "📍 *Joylashuvingizni yuboring* (ixtiyoriy)\n\n"
        "📱 *Telefonda:* tugmani bosing\n"
        "🖥 *Telegram Desktop:* koordinatani yozing:\n"
        "`41.2995 69.2641`\n\n"
        "Yoki ⏭️ O'tkazib yuborish",
        parse_mode="Markdown", reply_markup=markup
    )
    return REG_LOCATION


async def reg_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    loc = getattr(update.message, "location", None)
    text = (update.message.text or "").strip()

    lat, lon = None, None

    if loc:
        # Telefon orqali joylashuv
        lat, lon = loc.latitude, loc.longitude
    elif text and text not in ("⏭️ O'tkazib yuborish", "skip", "o'tkazib"):
        # Desktop: "41.2995 69.2641" yoki "41.2995, 69.2641" formatida yozilgan
        try:
            parts = text.replace(",", " ").split()
            if len(parts) >= 2:
                lat_try = float(parts[0])
                lon_try = float(parts[1])
                # O'zbekiston koordinatalari tekshiruvi
                if 37.0 <= lat_try <= 46.0 and 56.0 <= lon_try <= 74.0:
                    lat, lon = lat_try, lon_try
                else:
                    await update.message.reply_text(
                        "❌ Noto'g'ri koordinata!\n"
                        "O'zbekiston koordinatasini kiriting:\n"
                        "`41.2995 69.2641`\n\n"
                        "Yoki ⏭️ O'tkazib yuborish deb yozing.",
                        parse_mode="Markdown"
                    )
                    return REG_LOCATION
        except (ValueError, IndexError):
            # Raqam emas — skip deb hisoblaymiz
            pass

    if lat is not None and lon is not None:
        update_user(user.id, latitude=lat, longitude=lon)
        await update.message.reply_text(
            f"✅ Joylashuv saqlandi! 📍 {lat:.4f}, {lon:.4f}",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "⏭️ Joylashuv o'tkazib yuborildi.",
            reply_markup=ReplyKeyboardRemove()
        )

    user_data = get_user_by_id(user.id)
    await update.message.reply_text(
        f"🎉 Ro'yxatdan o'tish yakunlandi!\n\n"
        f"👤 {user_data.get('first_name','')} {user_data.get('last_name','')}\n"
        f"🏘️ {user_data.get('district','')}",
        reply_markup=ReplyKeyboardRemove()
    )
    await send_main_menu(update.message)
    return ConversationHandler.END

# ======================== COMMANDS ========================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚡ *Bot buyruqlari:*\n\n"
        "📊 /stats — Umumiy statistika\n"
        "🔮 /forecast — 7 kunlik prognoz\n"
        "🏘️ /districts — Tumanlar bo'yicha\n"
        "🔍 /sensor S001 — Sensor ma'lumoti\n"
        "🧠 /model — AI bashorat\n"
        "🔴 /danger — Muammoli sensorlar\n"
        "📈 /averages — O'rtacha qiymatlar\n"
        "📋 /top — Top 10 xavfli sensor\n"
        "🌤️ /weather — Ob-havo\n\n"
        "📊 /chart S001 — Sensor grafik\n"
        "📈 /compare S001 S002 — Taqqoslash\n"
        "🏘️ /district\\_compare A B — Tuman taqqos\n"
        "🕐 /history S001 7 — Sensor tarixi\n"
        "🔎 /search Chilonzor — Tuman qidiruv\n"
        "🔎 /filter danger — Holat filtri\n"
        "📥 /report — CSV + PDF hisobot\n"
        "📥 /csv S001 — Sensor CSV\n"
        "🗺️ /map Chilonzor — Tuman xaritasi\n"
        "📊 /dashboard — Vizual panel\n"
        "📍 /near\\_sensors — Eng yaqin sensorlar\n"
        "🔔 /subscribe — Auto-alert obuna\n"
        "🔕 /unsubscribe — Obunani bekor\n"
        "🌙 /silent — Sokin rejim on/off\n"
        "👤 /admin — Admin panel\n\n"
        "_Yaratuvchi: G'aybullayev Shohjahon (@gaybullayeev19)_"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    danger_cnt = int((latest["Fault"] == 2).sum())
    safe_pct = round(100 * safe / total, 1) if total > 0 else 0
    status = "🟢 Barqaror" if safe_pct >= 60 else ("🟡 Ogohlantirish" if safe_pct >= 40 else "🔴 Muammolar")
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    text = (
        f"📊 *Umumiy Statistika*\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {now_str}\n📡 Holat: {status}\n\n"
        f"📡 *Sensorlar:* {total} ta\n"
        f"✅ Havfsiz: {safe} ({safe_pct}%)\n"
        f"⚠️ Ogohlantirish: {warn}\n"
        f"🔴 Muammo: {danger_cnt}\n\n"
        f"🌡️ O'rt. harorat: {latest['Muhit_harorat (C)'].mean():.1f}°C\n"
        f"🔌 O'rt. kuchlanish: {latest['Kuchlanish (V)'].mean():.1f}V\n"
        f"🔄 O'rt. chastota: {latest['Chastota (Hz)'].mean():.2f}Hz"
    )
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user_by_id(user.id)
    user_district = user_data.get("district") if user_data else None
    lat, lon = 41.3111, 69.2797
    if user_district and user_district in DISTRICT_COORDS:
        lat, lon = DISTRICT_COORDS[user_district]

    try:
        resp = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,wind_speed_10m,relative_humidity_2m",
            "daily": "temperature_2m_max,temperature_2m_min,wind_speed_10m_max,precipitation_sum",
            "timezone": "Asia/Tashkent", "forecast_days": 7
        }, timeout=10)
        daily = resp.json().get("daily", {})
        lines = [f"🌤️ *{user_district or 'Toshkent'} uchun ob-havo*", "━━━━━━━━━━━━━━━━━━━━", "7 kunlik prognoz:"]
        if daily.get("time"):
            for i in range(min(7, len(daily["time"]))):
                icon = "🌧️" if daily["precipitation_sum"][i] > 1 else "☀️"
                lines.append(
                    f"  {icon} {daily['time'][i][5:]}: "
                    f"{daily['temperature_2m_min'][i]:.0f}–{daily['temperature_2m_max'][i]:.0f}°C | "
                    f"🌬️{daily['wind_speed_10m_max'][i]:.0f}km/h"
                )
        else:
            lines.append("⚠️ Ob-havo ma'lumoti yuklanmadi")
    except Exception as e:
        lines = [f"⚠️ Ob-havo olinmadi: {e}"]

    if df is not None and not df.empty and user_district:
        latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
        tdf = latest[latest["District"] == user_district]
        if not tdf.empty:
            lines += [
                "",
                f"{user_district} tumani: 📡{len(tdf)} | ✅{int((tdf['Fault']==0).sum())} | "
                f"⚠️{int((tdf['Fault']==1).sum())} | 🔴{int((tdf['Fault']==2).sum())}"
            ]

    text = "\n".join(lines)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")


async def districts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if df is None or df.empty:
        text = "❌ Ma'lumot yuklanmagan!"
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    user_data = get_user_by_id(update.effective_user.id)
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    tuman_stats = latest.groupby("District").agg(
        jami=("SensorID", "count"),
        havfsiz=("Fault", lambda x: int((x == 0).sum())),
        ogohlantirish=("Fault", lambda x: int((x == 1).sum())),
        muammo=("Fault", lambda x: int((x == 2).sum())),
    )

    if is_admin(update):
        text = "🏘️ *Tumanlar bo'yicha holat:*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for district, row in tuman_stats.iterrows():
            icon = "🔴" if row["muammo"] > 0 else ("🟡" if row["ogohlantirish"] > 0 else "🟢")
            text += f"{icon} *{district}*\n   📡{row['jami']} | ✅{row['havfsiz']} | ⚠️{row['ogohlantirish']} | 🔴{row['muammo']}\n"
    else:
        user_district = user_data.get("district") if user_data else None
        if user_district and user_district in tuman_stats.index:
            row = tuman_stats.loc[user_district]
            icon = "🔴" if row["muammo"] > 0 else ("🟡" if row["ogohlantirish"] > 0 else "🟢")
            text = (
                f"🏘️ *{user_district}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{icon} *{user_district}*\n"
                f"   📡{row['jami']} | ✅{row['havfsiz']} | ⚠️{row['ogohlantirish']} | 🔴{row['muammo']}\n"
            )
        else:
            text = "⚠️ Tumaningiz tanlanmagan. /start orqali ro'yxatdan o'ting."

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def sensor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🔍 Buyruq: `/sensor S001`", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]])
        )
        return

    if not context.args:
        await update.message.reply_text("⚠️ Masalan: /sensor S001")
        return

    sensor_id = context.args[0].upper()
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return

    sensor_df = df[df["SensorID"] == sensor_id].sort_values("Timestamp")
    if sensor_df.empty:
        await update.message.reply_text(f"❌ *{sensor_id}* topilmadi!", parse_mode="Markdown")
        return

    latest = sensor_df.iloc[-1]
    fault = int(latest.get("Fault", 0))
    fault_text = "🔴 MUAMMO" if fault == 2 else ("🟡 OGOHLANTIRISH" if fault == 1 else "🟢 HAVFSIZ")
    fc = sensor_df["Fault"].value_counts().to_dict()

    text = (
        f"🔍 *Sensor: {sensor_id}*\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 Tuman: {latest.get('District','N/A')}\n"
        f"📡 Holat: {fault_text}\n"
        f"📅 Oxirgi: {str(latest['Timestamp'])[:19]}\n\n"
        f"🔌 Kuchlanish: {latest.get('Kuchlanish (V)',0):.1f}V\n"
        f"🔄 Chastota: {latest.get('Chastota (Hz)',50):.2f}Hz\n"
        f"🌡️ Harorat: {latest.get('Muhit_harorat (C)',0):.1f}°C\n"
        f"📳 Vibratsiya: {latest.get('Vibratsiya',0):.3f}\n"
        f"🔗 Sim holati: {latest.get('Sim_mexanik_holati (%)',90):.1f}%\n"
        f"💨 Namlik: {latest.get('Atrof_muhit_humidity (%)',50):.1f}%\n"
        f"⚙️ Quvvat: {latest.get('Quvvati (kW)',3):.2f}kW\n\n"
        f"📉 ✅{fc.get(0,0)} | ⚠️{fc.get(1,0)} | 🔴{fc.get(2,0)}"
    )
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🧠 *AI Model — Parametr kiriting*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "`/predict 30 7 50 220 0.5 90 60 3`\n\n"
        "Tartib: Harorat | Shamol | Chastota | Kuchlanish | Vibratsiya | Sim holati | Namlik | Quvvat"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")


async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if hybrid_model is None:
        await update.message.reply_text("❌ Model yuklanmagan!")
        return
    if not context.args or len(context.args) != 8:
        await update.message.reply_text("⚠️ 8 ta parametr: `/predict 30 7 50 220 0.5 90 60 3`", parse_mode="Markdown")
        return
    try:
        values = [float(x) for x in context.args]
        harorat, shamol, chastota, kuchlanish, vibratsiya, sim_holati, humidity, quvvat = values
        pred_input = pd.DataFrame([values], columns=FEATURE_COLS)
        prediction = int(hybrid_model.predict(pred_input)[0])
        level = {0: "✅ HAVFSIZ", 1: "⚠️ OGOHLANTIRISH", 2: "🔴 MUAMMO"}.get(prediction, "❓")
        level_msg = {
            0: "Barcha parametrlar normal. Tizim barqaror.",
            1: "Ba'zi parametrlar chegaraga yaqin. Monitoring kuchaytirilsin.",
            2: "Xavfli holat! Darhol choralar ko'rilsin."
        }.get(prediction, "")
        checks = []
        if 210 <= kuchlanish <= 230:    checks.append("🔌 Kuchlanish: ✅ Normal")
        elif 200 <= kuchlanish <= 240:  checks.append(f"🔌 Kuchlanish: ⚠️ {kuchlanish}V")
        else:                           checks.append(f"🔌 Kuchlanish: 🔴 {kuchlanish}V — XAVF!")
        if 49.5 <= chastota <= 50.5:    checks.append("🔄 Chastota: ✅ Normal")
        else:                           checks.append(f"🔄 Chastota: ⚠️ {chastota}Hz")
        if harorat < 40:                checks.append("🌡️ Harorat: ✅ Normal")
        elif harorat <= 45:             checks.append(f"🌡️ Harorat: ⚠️ {harorat}°C")
        else:                           checks.append(f"🌡️ Harorat: 🔴 {harorat}°C — XAVF!")
        if vibratsiya < 1.0:            checks.append("📳 Vibratsiya: ✅ Normal")
        elif vibratsiya <= 1.5:         checks.append(f"📳 Vibratsiya: ⚠️ {vibratsiya}")
        else:                           checks.append(f"📳 Vibratsiya: 🔴 {vibratsiya} — XAVF!")
        text = (
            f"🧠 *AI Bashorat natijasi*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 Natija: *{level}*\n💬 {level_msg}\n\n"
            f"📋 *Tekshiruv:*\n" + "\n".join(checks) + "\n\n"
            f"📥 {harorat}°C | {shamol}km/h | {chastota}Hz | {kuchlanish}V"
        )
        keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri qiymat! Faqat raqam kiriting.")


async def danger_sensors_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if df is None or df.empty:
        text = "❌ Ma'lumot yuklanmagan!"
        if update.callback_query: await update.callback_query.edit_message_text(text)
        else: await update.message.reply_text(text)
        return
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    danger = latest[latest["Fault"] == 2]
    if danger.empty:
        text = "✅ Hozirda muammoli sensor yo'q!"
    else:
        text = f"🔴 *Muammoli sensorlar: {len(danger)} ta*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for _, row in danger.head(20).iterrows():
            text += f"🔴 *{row['SensorID']}* — {row['District']}\n   🔌{row['Kuchlanish (V)']:.1f}V | 🔄{row['Chastota (Hz)']:.2f}Hz\n"
        if len(danger) > 20:
            text += f"\n... va yana {len(danger)-20} ta"
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def top_danger_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if df is None or df.empty:
        text = "❌ Ma'lumot yuklanmagan!"
        if update.callback_query: await update.callback_query.edit_message_text(text)
        else: await update.message.reply_text(text)
        return
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    fault_history = df[df["Fault"] == 2].groupby("SensorID").size().sort_values(ascending=False).head(10)
    text = "📋 *Top 10 eng xavfli sensorlar*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (sid, cnt) in enumerate(fault_history.items(), 1):
        r = latest[latest["SensorID"] == sid]
        district = r.iloc[0]["District"] if not r.empty else "N/A"
        text += f"{i}. 🔴 *{sid}* — {district} ({cnt} marta)\n"
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def averages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if df is None or df.empty:
        text = "❌ Ma'lumot yuklanmagan!"
        if update.callback_query: await update.callback_query.edit_message_text(text)
        else: await update.message.reply_text(text)
        return
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    text = (
        "📈 *O'rtacha qiymatlar*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌡️ Harorat: *{latest['Muhit_harorat (C)'].mean():.1f}°C*\n"
        f"🔌 Kuchlanish: *{latest['Kuchlanish (V)'].mean():.1f}V*\n"
        f"🔄 Chastota: *{latest['Chastota (Hz)'].mean():.2f}Hz*\n"
        f"📳 Vibratsiya: *{latest['Vibratsiya'].mean():.3f}*\n"
        f"🔗 Sim holati: *{latest['Sim_mexanik_holati (%)'].mean():.1f}%*\n"
        f"💨 Namlik: *{latest['Atrof_muhit_humidity (%)'].mean():.1f}%*\n"
        f"⚙️ Quvvat: *{latest['Quvvati (kW)'].mean():.2f}kW*"
    )
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resp = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": 41.3111, "longitude": 69.2797,
            "current": "temperature_2m,wind_speed_10m,relative_humidity_2m",
            "daily": "temperature_2m_max,temperature_2m_min,wind_speed_10m_max,precipitation_sum",
            "timezone": "Asia/Tashkent", "forecast_days": 7
        }, timeout=10)
        data = resp.json()
        current = data.get("current", {})
        daily = data.get("daily", {})
        text = (
            f"🌤️ *Toshkent ob-havo*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌡️ {current.get('temperature_2m','N/A')}°C | "
            f"🌬️ {current.get('wind_speed_10m','N/A')}km/h | "
            f"💨 {current.get('relative_humidity_2m','N/A')}%\n\n"
            f"📆 *7 kunlik prognoz:*\n"
        )
        if daily.get("time"):
            for i in range(min(7, len(daily["time"]))):
                icon = "🌧️" if daily["precipitation_sum"][i] > 1 else "☀️"
                text += (f"  {icon} {daily['time'][i][5:]}: "
                         f"{daily['temperature_2m_min'][i]:.0f}–{daily['temperature_2m_max'][i]:.0f}°C | "
                         f"🌬️{daily['wind_speed_10m_max'][i]:.0f}km/h\n")
        keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        err = f"❌ Ob-havo yuklanmadi: {e}"
        if update.callback_query: await update.callback_query.edit_message_text(err)
        else: await update.message.reply_text(err)


async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "📊 Sensor grafigi uchun:\n\n`/chart S001`", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]])
        )
        return
    if not context.args:
        await update.message.reply_text("⚠️ Masalan: /chart S001")
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
    fig.suptitle(f"📊 {sensor_id} — {sensor_df.iloc[-1].get('District','')}", fontsize=13, fontweight="bold")
    ts = sensor_df["Timestamp"]
    axes[0,0].plot(ts, sensor_df["Kuchlanish (V)"], "#e74c3c", linewidth=1)
    axes[0,0].axhline(220, color="green", linestyle="--", alpha=0.5, label="220V")
    axes[0,0].set_title("🔌 Kuchlanish (V)"); axes[0,0].legend(fontsize=8)
    axes[0,0].tick_params(axis="x", rotation=30, labelsize=7)
    axes[0,1].plot(ts, sensor_df["Muhit_harorat (C)"], "#e67e22", linewidth=1)
    axes[0,1].set_title("🌡️ Harorat (°C)")
    axes[0,1].tick_params(axis="x", rotation=30, labelsize=7)
    axes[1,0].plot(ts, sensor_df["Chastota (Hz)"], "#3498db", linewidth=1)
    axes[1,0].axhline(50, color="green", linestyle="--", alpha=0.5, label="50Hz")
    axes[1,0].set_title("🔄 Chastota (Hz)"); axes[1,0].legend(fontsize=8)
    axes[1,0].tick_params(axis="x", rotation=30, labelsize=7)
    axes[1,1].plot(ts, sensor_df["Vibratsiya"], "#9b59b6", linewidth=1)
    axes[1,1].set_title("📳 Vibratsiya")
    axes[1,1].tick_params(axis="x", rotation=30, labelsize=7)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130); buf.seek(0); plt.close(fig)
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_photo(photo=buf, caption=f"📊 *{sensor_id}* oxirgi 200 yozuv",
                                     parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("⚠️ Masalan: /compare S001 S002")
        return
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return
    s1, s2 = context.args[0].upper(), context.args[1].upper()
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    r1 = latest[latest["SensorID"] == s1]
    r2 = latest[latest["SensorID"] == s2]
    if r1.empty or r2.empty:
        await update.message.reply_text("❌ Sensor topilmadi!")
        return
    r1, r2 = r1.iloc[0], r2.iloc[0]
    ft = {0: "🟢 Havfsiz", 1: "🟡 Og'oh", 2: "🔴 Muammo"}
    text = (
        f"📈 *Taqqoslash: {s1} vs {s2}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📍 {r1['District']} / {r2['District']}\n"
        f"📡 {ft[r1['Fault']]} / {ft[r2['Fault']]}\n"
        f"🔌 {r1['Kuchlanish (V)']:.1f}V / {r2['Kuchlanish (V)']:.1f}V\n"
        f"🔄 {r1['Chastota (Hz)']:.2f}Hz / {r2['Chastota (Hz)']:.2f}Hz\n"
        f"🌡️ {r1['Muhit_harorat (C)']:.1f}°C / {r2['Muhit_harorat (C)']:.1f}°C\n"
        f"📳 {r1['Vibratsiya']:.3f} / {r2['Vibratsiya']:.3f}"
    )
    s1_df = df[df["SensorID"] == s1].sort_values("Timestamp").tail(100)
    s2_df = df[df["SensorID"] == s2].sort_values("Timestamp").tail(100)
    fig, ax = plt.subplots(1, 1, figsize=(10, 4))
    ax.plot(s1_df["Timestamp"], s1_df["Kuchlanish (V)"], label=s1, linewidth=1.2)
    ax.plot(s2_df["Timestamp"], s2_df["Kuchlanish (V)"], label=s2, linewidth=1.2)
    ax.axhline(220, color="green", linestyle="--", alpha=0.4)
    ax.set_title(f"Kuchlanish: {s1} vs {s2}"); ax.legend()
    ax.tick_params(axis="x", rotation=30, labelsize=7)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130); buf.seek(0); plt.close(fig)
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_photo(photo=buf, caption=text, parse_mode="Markdown",
                                     reply_markup=InlineKeyboardMarkup(keyboard))


def _district_select_keyboard(prefix, exclude=None):
    keyboard = []
    row = []
    for d in DISTRICTS:
        if exclude and d == exclude:
            continue
        row.append(InlineKeyboardButton(d, callback_data=f"{prefix}{d}"))
        if len(row) == 2:
            keyboard.append(row); row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")])
    return InlineKeyboardMarkup(keyboard)


def _build_district_compare_text(d1, d2):
    if df is None or df.empty:
        return "❌ Ma'lumot yuklanmagan!"
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    text = f"🏘️ *{d1} vs {d2}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for dname in [d1, d2]:
        dd = latest[latest["District"] == dname]
        text += (
            f"*{dname}:* {len(dd)} sensor\n"
            f"  ✅{int((dd['Fault']==0).sum())} | ⚠️{int((dd['Fault']==1).sum())} | 🔴{int((dd['Fault']==2).sum())}\n"
            f"  🔌{dd['Kuchlanish (V)'].mean():.1f}V | 🌡️{dd['Muhit_harorat (C)'].mean():.1f}°C\n\n"
        )
    return text


async def district_compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and len(context.args) >= 2:
        d1_m = [d for d in DISTRICTS if context.args[0].lower() in d.lower()]
        d2_m = [d for d in DISTRICTS if context.args[1].lower() in d.lower()]
        if not d1_m or not d2_m:
            await update.message.reply_text("❌ Tuman topilmadi!")
            return
        text = _build_district_compare_text(d1_m[0], d2_m[0])
        keyboard = [[InlineKeyboardButton("🔄 Qayta", callback_data="dc_start"),
                     InlineKeyboardButton("🔙 Menyu", callback_data="menu")]]
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    target = update.callback_query or update.message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🏘️ *Tuman taqqoslash*\n\n1️⃣ Birinchi tumanni tanlang:",
            parse_mode="Markdown", reply_markup=_district_select_keyboard("dc1_")
        )
    else:
        await update.message.reply_text(
            "🏘️ *Tuman taqqoslash*\n\n1️⃣ Birinchi tumanni tanlang:",
            parse_mode="Markdown", reply_markup=_district_select_keyboard("dc1_")
        )


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Masalan: /history S001 7")
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
        note = f"oxirgi {len(period)} yozuv"
    else:
        note = f"oxirgi {days} kun"
    fc = period["Fault"].value_counts().to_dict()
    changes = []
    prev = None
    for _, row in period.iterrows():
        f = int(row["Fault"])
        if prev is not None and f != prev:
            icons = {0: "🟢", 1: "🟡", 2: "🔴"}
            changes.append(f"  {str(row['Timestamp'])[:16]} {icons.get(prev,'?')}→{icons.get(f,'?')}")
        prev = f
    text = (
        f"🕐 *{sensor_id} tarixi* ({note})\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 {sensor_df.iloc[-1].get('District','N/A')}\n"
        f"✅{fc.get(0,0)} | ⚠️{fc.get(1,0)} | 🔴{fc.get(2,0)}\n"
        f"🔌 {period['Kuchlanish (V)'].min():.1f}–{period['Kuchlanish (V)'].max():.1f}V "
        f"(o'rt:{period['Kuchlanish (V)'].mean():.1f})\n"
    )
    if changes:
        text += f"\n🔄 *O'zgarishlar* ({len(changes)} ta):\n" + "\n".join(changes[-10:])
        if len(changes) > 10:
            text += f"\n  ... va yana {len(changes)-10} ta"
    else:
        text += "\n✅ Holat o'zgarmagan"
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Masalan: /search Chilonzor\n\nTumanlar:\n" + "\n".join(f"• {d}" for d in DISTRICTS)
        )
        return
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return
    query = " ".join(context.args)
    matched = [d for d in DISTRICTS if query.lower() in d.lower()]
    if not matched:
        await update.message.reply_text(f"❌ '{query}' topilmadi!")
        return
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    text = ""
    for district in matched:
        d_df = latest[latest["District"] == district]
        if d_df.empty:
            continue
        safe = int((d_df["Fault"]==0).sum()); warn = int((d_df["Fault"]==1).sum()); danger = int((d_df["Fault"]==2).sum())
        text += f"🏘️ *{district}*\n   📡{len(d_df)} | ✅{safe} | ⚠️{warn} | 🔴{danger}\n\n"
        for _, row in d_df.head(15).iterrows():
            icon = "🔴" if row["Fault"]==2 else ("🟡" if row["Fault"]==1 else "🟢")
            text += f"  {icon} {row['SensorID']} — 🔌{row['Kuchlanish (V)']:.0f}V\n"
        if len(d_df) > 15:
            text += f"  ... va yana {len(d_df)-15} ta\n"
    if not text:
        text = "Ma'lumot topilmadi."
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Masalan:\n  /filter danger\n  /filter warn Chilonzor")
        return
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return
    level = context.args[0].lower()
    fault_map = {"danger":2, "warn":1, "safe":0, "muammo":2, "ogohlantirish":1, "havfsiz":0}
    if level not in fault_map:
        await update.message.reply_text("⚠️ Tur: danger, warn, safe")
        return
    district_query = " ".join(context.args[1:]) if len(context.args) > 1 else None
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    filtered = latest[latest["Fault"] == fault_map[level]]
    if district_query:
        matched = [d for d in DISTRICTS if district_query.lower() in d.lower()]
        if matched:
            filtered = filtered[filtered["District"].isin(matched)]
    icons = {0: "🟢 HAVFSIZ", 1: "🟡 OGOHLANTIRISH", 2: "🔴 MUAMMO"}
    if filtered.empty:
        text = f"✅ {icons.get(fault_map[level], level)} sensorlar topilmadi!"
    else:
        text = f"🔎 *{icons.get(fault_map[level])}* — {len(filtered)} ta\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for _, row in filtered.head(25).iterrows():
            text += f"• *{row['SensorID']}* — {row['District']} | 🔌{row['Kuchlanish (V)']:.0f}V\n"
        if len(filtered) > 25:
            text += f"\n... va yana {len(filtered)-25} ta"
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """CSV + PDF hisobot."""
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    cols = ["SensorID", "District", "Fault", "Kuchlanish (V)", "Chastota (Hz)",
            "Muhit_harorat (C)", "Vibratsiya", "Sim_mexanik_holati (%)", "Timestamp"]
    report_df = latest[cols].copy()
    report_df["Holat"] = report_df["Fault"].map({0: "Havfsiz", 1: "Ogohlantirish", 2: "Muammo"})
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]

    # CSV
    csv_buf = io.BytesIO()
    report_df.to_csv(csv_buf, index=False, encoding="utf-8-sig")
    csv_buf.seek(0)
    await update.message.reply_document(
        document=csv_buf, filename=f"hisobot_{now_str}.csv",
        caption=f"📥 CSV Hisobot — {len(report_df)} sensor",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # PDF
    try:
        from fpdf import FPDF
        total = len(report_df)
        safe = int((report_df["Fault"] == 0).sum())
        warn = int((report_df["Fault"] == 1).sum())
        danger_cnt = int((report_df["Fault"] == 2).sum())

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Elektr Monitoring Hisoboti", ln=True, align="C")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, f"Sana: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Umumiy statistika:", ln=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, f"Jami: {total}  |  Havfsiz: {safe}  |  Ogohlantirish: {warn}  |  Muammo: {danger_cnt}", ln=True)
        pdf.ln(6)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Tumanlar bo'yicha:", ln=True)
        pdf.set_font("Helvetica", "B", 10)
        for label, w in [("Tuman", 60), ("Jami", 25), ("Havfsiz", 25), ("Ogoh.", 30), ("Muammo", 25)]:
            pdf.cell(w, 7, label, border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 10)
        district_stats = report_df.groupby("District").agg(
            jami=("SensorID", "count"),
            havfsiz=("Fault", lambda x: int((x == 0).sum())),
            ogoh=("Fault", lambda x: int((x == 1).sum())),
            muammo=("Fault", lambda x: int((x == 2).sum())),
        )
        for dist, row in district_stats.iterrows():
            pdf.cell(60, 7, str(dist), border=1)
            pdf.cell(25, 7, str(row["jami"]), border=1)
            pdf.cell(25, 7, str(row["havfsiz"]), border=1)
            pdf.cell(30, 7, str(row["ogoh"]), border=1)
            pdf.cell(25, 7, str(row["muammo"]), border=1, ln=True)

        pdf_buf = io.BytesIO(bytes(pdf.output()))
        pdf_buf.seek(0)
        await update.message.reply_document(
            document=pdf_buf, filename=f"hisobot_{now_str}.pdf",
            caption="📄 PDF Hisobot",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except ImportError:
        await update.message.reply_text("ℹ️ PDF uchun: `pip install fpdf2`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ PDF xatosi: {e}")


async def csv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Masalan: /csv S001")
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
    sensor_df.to_csv(buf, index=False, encoding="utf-8-sig"); buf.seek(0)
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_document(document=buf, filename=f"{sensor_id}_data.csv",
                                        caption=f"📥 *{sensor_id}* — {len(sensor_df)} yozuv",
                                        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== 🗺️ MAP (Matplotlib) ====================

def _generate_map_image(district):
    """Matplotlib bilan tuman sensorlari vizual xaritasi (Selenium talab etmaydi)."""
    if df is None or df.empty:
        return None
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    dd = latest[latest["District"] == district]
    if dd.empty:
        return None

    center = DISTRICT_COORDS.get(district, (41.3111, 69.2797))
    import numpy as np
    rng = np.random.default_rng(hash(district) % 2**32)
    lats = center[0] + rng.uniform(-0.018, 0.018, len(dd))
    lons = center[1] + rng.uniform(-0.018, 0.018, len(dd))
    colors = dd["Fault"].map({0: "#2ecc71", 1: "#f39c12", 2: "#e74c3c"}).fillna("#95a5a6").values

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(lons, lats, c=colors, s=55, alpha=0.85, edgecolors="white", linewidth=0.5)
    ax.scatter([center[1]], [center[0]], marker="*", c="blue", s=200, zorder=5)
    ax.set_title(f"🗺️ {district} — Sensorlar xaritasi", fontsize=12, fontweight="bold")
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.3)
    patches = [
        mpatches.Patch(color="#2ecc71", label=f"Havfsiz ({int((dd['Fault']==0).sum())})"),
        mpatches.Patch(color="#f39c12", label=f"Ogohlantirish ({int((dd['Fault']==1).sum())})"),
        mpatches.Patch(color="#e74c3c", label=f"Muammo ({int((dd['Fault']==2).sum())})"),
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=9)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130); buf.seek(0); plt.close(fig)
    return buf


async def map_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        keyboard = []
        row = []
        for d in DISTRICTS:
            row.append(InlineKeyboardButton(d, callback_data=f"map_{d}"))
            if len(row) == 2:
                keyboard.append(row); row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")])
        await update.message.reply_text("🗺️ *Tuman tanlang:*", parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
        return

    district_q = " ".join(context.args)
    matched = [d for d in DISTRICTS if district_q.lower() in d.lower()]
    if not matched:
        await update.message.reply_text(f"❌ '{district_q}' topilmadi!")
        return
    district = matched[0]
    coords = DISTRICT_COORDS.get(district, (41.3111, 69.2797))
    buf = _generate_map_image(district)
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    if buf:
        await update.message.reply_photo(photo=buf, caption=f"🗺️ *{district}*",
                                         parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.reply_location(latitude=coords[0], longitude=coords[1])


# ==================== 📊 DASHBOARD ====================

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tizim holati vizual dashboard — 4 panel."""
    if df is None or df.empty:
        text = "❌ Ma'lumot yuklanmagan!"
        if update.callback_query: await update.callback_query.edit_message_text(text)
        else: await update.message.reply_text(text)
        return

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    tuman_stats = latest.groupby("District").agg(
        havfsiz=("Fault", lambda x: int((x==0).sum())),
        ogoh=("Fault", lambda x: int((x==1).sum())),
        muammo=("Fault", lambda x: int((x==2).sum())),
    ).reset_index()

    total = len(latest)
    safe = int((latest["Fault"]==0).sum())
    warn = int((latest["Fault"]==1).sum())
    danger_cnt = int((latest["Fault"]==2).sum())

    fig, axes = plt.subplots(2, 2, figsize=(13, 10))
    fig.suptitle("⚡ Elektr Monitoring Dashboard", fontsize=14, fontweight="bold")

    axes[0,0].pie([safe, warn, danger_cnt],
                  labels=["Havfsiz", "Ogoh", "Muammo"],
                  colors=["#2ecc71","#f39c12","#e74c3c"],
                  autopct="%1.0f%%", startangle=90)
    axes[0,0].set_title("Umumiy holat")

    axes[0,1].barh(tuman_stats["District"], tuman_stats["muammo"], color="#e74c3c", alpha=0.8, label="Muammo")
    axes[0,1].barh(tuman_stats["District"], tuman_stats["ogoh"],
                   left=tuman_stats["muammo"], color="#f39c12", alpha=0.8, label="Ogoh")
    axes[0,1].set_title("Tumanlar bo'yicha holat")
    axes[0,1].legend(fontsize=8)

    axes[1,0].hist(latest["Kuchlanish (V)"].dropna(), bins=30, color="#3498db", alpha=0.8, edgecolor="white")
    axes[1,0].axvline(220, color="red", linestyle="--", label="Normal 220V")
    axes[1,0].set_title("Kuchlanish tarqalishi (V)")
    axes[1,0].legend(fontsize=9)

    axes[1,1].hist(latest["Muhit_harorat (C)"].dropna(), bins=30, color="#e67e22", alpha=0.8, edgecolor="white")
    axes[1,1].set_title("Harorat tarqalishi (°C)")

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130); buf.seek(0); plt.close(fig)

    caption = (
        f"📊 *Dashboard* — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"📡{total} sensor | ✅{safe} | ⚠️{warn} | 🔴{danger_cnt}"
    )
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    if update.callback_query:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id, photo=buf,
            caption=caption, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await update.callback_query.answer()
    else:
        await update.message.reply_photo(photo=buf, caption=caption, parse_mode="Markdown",
                                         reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== 📍 NEAR SENSORS ====================

async def near_sensors_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Haversine formulasi yordamida foydalanuvchiga eng yaqin 3 ta sensorsni topish."""
    user = update.effective_user
    user_data = get_user_by_id(user.id)

    if not user_data or not user_data.get("latitude"):
        loc_btn = KeyboardButton("📍 Joylashuvimni yuborish", request_location=True)
        markup = ReplyKeyboardMarkup([[loc_btn]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "📍 Eng yaqin sensorlarni topish uchun joylashuvingizni yuboring:",
            reply_markup=markup
        )
        context.user_data["waiting_near"] = True
        return

    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return

    user_lat = user_data["latitude"]
    user_lon = user_data["longitude"]
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()

    import numpy as np
    rows = []
    for _, row in latest.iterrows():
        district = row.get("District", "")
        coord = DISTRICT_COORDS.get(district, (41.3111, 69.2797))
        rng = np.random.default_rng(hash(row["SensorID"]) % 2**32)
        s_lat = coord[0] + rng.uniform(-0.015, 0.015)
        s_lon = coord[1] + rng.uniform(-0.015, 0.015)
        dist_km = haversine(user_lat, user_lon, s_lat, s_lon)
        rows.append((dist_km, row))

    rows.sort(key=lambda x: x[0])
    top3 = rows[:3]

    ft = {0: "🟢 Havfsiz", 1: "🟡 Ogohlantirish", 2: "🔴 Muammo"}
    text = "📍 *Sizga eng yaqin 3 ta sensor:*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (dist_km, row) in enumerate(top3, 1):
        text += (
            f"{i}. *{row['SensorID']}* — {row.get('District','N/A')}\n"
            f"   📏 {dist_km:.2f} km\n"
            f"   📡 {ft.get(int(row.get('Fault',0)),'?')}\n"
            f"   🔌{row.get('Kuchlanish (V)',0):.1f}V | 🔄{row.get('Chastota (Hz)',50):.2f}Hz\n\n"
        )

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Erkin joylashuv xabari kelganda — near_sensors uchun."""
    if not context.user_data.get("waiting_near"):
        return
    context.user_data.pop("waiting_near", None)
    loc = update.message.location
    if loc:
        update_user(update.effective_user.id, latitude=loc.latitude, longitude=loc.longitude)
        await near_sensors_command(update, context)


# ==================== 🌙 SILENT MODE ====================

async def silent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sokin rejim — tungi ogohlantirishlarni o'chirish/yoqish."""
    user_data = get_user_by_id(update.effective_user.id)
    if not user_data:
        await (update.callback_query.answer("Avval /start") if update.callback_query
               else update.message.reply_text("❌ /start orqali ro'yxatdan o'ting."))
        return
    new_val = not user_data.get("silent_mode", False)
    update_user(update.effective_user.id, silent_mode=new_val)
    text = ("🌙 *Sokin rejim yoqildi*\n\n22:00–07:00 orasida ogohlantirishlar kelmasligi o'rnatildi."
            if new_val else "🔔 *Sokin rejim o'chirildi*\n\nOgohlantirishlar qayta yoqildi.")
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown",
                                                      reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== 🔔 SUBSCRIBE ====================

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in subscribers:
        text = "✅ Allaqachon obuna bo'lgansiz!"
    else:
        subscribers.add(chat_id)
        save_subscribers(subscribers)
        text = "🔔 *Obuna muvaffaqiyatli!*\n\nXavfli holat topilganda xabar olasiz.\nBekor qilish: /unsubscribe"
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in subscribers:
        subscribers.discard(chat_id); save_subscribers(subscribers)
        text = "🔕 Obuna bekor qilindi."
    else:
        text = "⚠️ Obuna emassiz. /subscribe"
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def alert_check(context: ContextTypes.DEFAULT_TYPE):
    """Har soatda xavfli sensorlarni tekshirish; silent_mode ni hurmat qiladi."""
    if df is None or df.empty or not subscribers:
        return
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    danger = latest[latest["Fault"] == 2]
    if danger.empty:
        return

    now_hour = datetime.datetime.now().hour
    text = (
        f"🚨 *AVTOMATIK OGOHLANTIRISH*\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"🔴 Muammoli sensorlar: *{len(danger)} ta*\n\n"
    )
    for _, row in danger.head(10).iterrows():
        text += f"🔴 *{row['SensorID']}* — {row['District']} | 🔌{row['Kuchlanish (V)']:.0f}V\n"
    if len(danger) > 10:
        text += f"\n... va yana {len(danger)-10} ta"

    users_list = load_users()
    user_map = {u["id"]: u for u in users_list}

    for chat_id in list(subscribers):
        u = user_map.get(chat_id, {})
        if u.get("silent_mode") and (now_hour >= 22 or now_hour < 7):
            continue
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        except Exception:
            subscribers.discard(chat_id)
            save_subscribers(subscribers)


# ==================== 👤 ADMIN ====================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("🔒 Admin huquqi yo'q!")
        return
    if df is None or df.empty:
        await update.message.reply_text("❌ Ma'lumot yuklanmagan!")
        return
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    total = len(latest)
    safe = int((latest["Fault"]==0).sum())
    warn = int((latest["Fault"]==1).sum())
    danger_cnt = int((latest["Fault"]==2).sum())
    district_danger = df[df["Fault"]==2].groupby("District").size()
    top_d = district_danger.idxmax() if not district_danger.empty else "N/A"
    text = (
        f"👤 *Admin Panel*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Ma'lumot: {len(df):,} qator\n"
        f"📡 Sensorlar: {total}\n"
        f"🧠 Model: {'✅' if hybrid_model else '❌'}\n"
        f"👥 Foydalanuvchilar: {len(load_users())}\n"
        f"🔔 Obunchilar: {len(subscribers)}\n\n"
        f"✅{safe} | ⚠️{warn} | 🔴{danger_cnt}\n"
        f"🔴 Eng muammoli: *{top_d}*\n\n"
        f"🔧 `/broadcast <matn>` — Matn\n"
        f"🔧 Rasmga reply + `/broadcast` — Media"
    )
    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: barcha obunchilarga matn yoki media xabari (reply orqali)."""
    if not is_admin(update):
        await update.message.reply_text("🔒 Admin huquqi yo'q!")
        return

    reply = update.message.reply_to_message
    if reply:
        sent = failed = 0
        caption = " ".join(context.args) if context.args else None
        for chat_id in list(subscribers):
            try:
                if reply.photo:
                    await context.bot.send_photo(chat_id=chat_id, photo=reply.photo[-1].file_id, caption=caption)
                elif reply.video:
                    await context.bot.send_video(chat_id=chat_id, video=reply.video.file_id, caption=caption)
                elif reply.document:
                    await context.bot.send_document(chat_id=chat_id, document=reply.document.file_id, caption=caption)
                elif reply.text:
                    await context.bot.send_message(chat_id=chat_id,
                                                   text=f"📢 *Admin xabari:*\n\n{reply.text}",
                                                   parse_mode="Markdown")
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(f"📢 Yuborildi: {sent} | ❌ Xato: {failed}")
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ Ishlatish:\n• `/broadcast Matn` — matn\n• Rasmga reply qilib `/broadcast` — media",
            parse_mode="Markdown"
        )
        return

    msg_text = " ".join(context.args)
    sent = failed = 0
    for chat_id in list(subscribers):
        try:
            await context.bot.send_message(chat_id=chat_id,
                                           text=f"📢 *Admin xabari:*\n\n{msg_text}",
                                           parse_mode="Markdown")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"📢 Yuborildi: {sent} | ❌ Xato: {failed}")


# ==================== 🔘 CALLBACK ====================

_MAIN_KEYBOARD = [
    [InlineKeyboardButton("📊 Statistika",        callback_data="stats"),
     InlineKeyboardButton("🔮 Prognoz",           callback_data="forecast")],
    [InlineKeyboardButton("🏘️ Tumanlar",          callback_data="districts"),
     InlineKeyboardButton("🔍 Sensor tekshirish", callback_data="sensor_check")],
    [InlineKeyboardButton("🧠 Model bashorat",    callback_data="model"),
     InlineKeyboardButton("🔴 Muammoli sensorlar",callback_data="danger_sensors")],
    [InlineKeyboardButton("📈 O'rtachalar",       callback_data="averages"),
     InlineKeyboardButton("📋 Top 10 xavfli",    callback_data="top_danger")],
    [InlineKeyboardButton("📊 Grafik",            callback_data="chart_check"),
     InlineKeyboardButton("📈 Taqqoslash",        callback_data="compare_check")],
    [InlineKeyboardButton("🕐 Tarix",             callback_data="history_check"),
     InlineKeyboardButton("🗺️ Xarita",            callback_data="map_check")],
    [InlineKeyboardButton("📥 Hisobot",           callback_data="report_check"),
     InlineKeyboardButton("🔔 Obuna",             callback_data="subscribe_check")],
    [InlineKeyboardButton("📊 Dashboard",         callback_data="dashboard"),
     InlineKeyboardButton("📍 Yaqin sensorlar",  callback_data="near_sensors_info")],
    [InlineKeyboardButton("🌙 Sokin rejim",       callback_data="silent_toggle"),
     InlineKeyboardButton("🌤️ Ob-havo",           callback_data="weather")],
    [InlineKeyboardButton("ℹ️ Yordam",             callback_data="help")],
]

_BACK = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        await query.edit_message_text(
            "⚡ *Elektr Monitoring Bot*\n━━━━━━━━━━━━━━━━━━━━\nQuyidagi tugmalardan birini tanlang:",
            reply_markup=InlineKeyboardMarkup(_MAIN_KEYBOARD), parse_mode="Markdown"
        )
    elif data == "stats":           await stats_command(update, context)
    elif data == "forecast":        await forecast_command(update, context)
    elif data == "districts":       await districts_command(update, context)
    elif data == "model":           await model_command(update, context)
    elif data == "danger_sensors":  await danger_sensors_command(update, context)
    elif data == "top_danger":      await top_danger_command(update, context)
    elif data == "averages":        await averages_command(update, context)
    elif data == "weather":         await weather_command(update, context)
    elif data == "help":            await help_command(update, context)
    elif data == "dashboard":       await dashboard_command(update, context)
    elif data == "silent_toggle":   await silent_command(update, context)
    elif data == "sensor_check":
        await query.edit_message_text("🔍 Buyruq: `/sensor S001`", parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(_BACK))
    elif data == "chart_check":
        await query.edit_message_text(
            "📊 Sensor grafigi:\n\n`/chart S001`\n\nOxirgi 200 yozuv: Kuchlanish | Harorat | Chastota | Vibratsiya",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(_BACK))
    elif data == "compare_check":
        await query.edit_message_text(
            "📈 Taqqoslash:\n\n🔹 `/compare S001 S002`\n🔹 Tumanlar:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏘️ Tumanlarni taqqoslash", callback_data="dc_start")],
                *_BACK
            ])
        )
    elif data == "dc_start":
        await query.edit_message_text("🏘️ *Tuman taqqoslash*\n\n1️⃣ Birinchi tumanni tanlang:",
                                      parse_mode="Markdown", reply_markup=_district_select_keyboard("dc1_"))
    elif data.startswith("dc1_"):
        d1 = data[4:]
        await query.edit_message_text(f"🏘️ *Tuman taqqoslash*\n\n1️⃣ {d1} ✅\n2️⃣ Ikkinchi tumanni tanlang:",
                                      parse_mode="Markdown",
                                      reply_markup=_district_select_keyboard(f"dc2_{d1}_", exclude=d1))
    elif data.startswith("dc2_"):
        parts = data[4:].rsplit("_", 1)
        d1, d2 = parts[0], parts[1]
        text = _build_district_compare_text(d1, d2)
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup([
                                          [InlineKeyboardButton("🔄 Qayta", callback_data="dc_start"),
                                           InlineKeyboardButton("🔙 Menyu", callback_data="menu")]
                                      ]))
    elif data == "history_check":
        await query.edit_message_text("🕐 *Tarix:*\n\n`/history S001 7`", parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(_BACK))
    elif data == "map_check":
        keyboard = []
        row = []
        for d in DISTRICTS:
            row.append(InlineKeyboardButton(d, callback_data=f"map_{d}"))
            if len(row) == 2:
                keyboard.append(row); row = []
        if row:
            keyboard.append(row)
        keyboard.extend(_BACK)
        await query.edit_message_text("🗺️ *Tuman tanlang:*", parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "report_check":
        await query.edit_message_text("📥 *Export:*\n\n🔹 /report — CSV + PDF\n🔹 `/csv S001` — Sensor CSV",
                                      parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(_BACK))
    elif data == "subscribe_check":
        await query.edit_message_text("🔔 /subscribe — Obuna\n🔕 /unsubscribe — Bekor",
                                      parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(_BACK))
    elif data == "near_sensors_info":
        await query.edit_message_text(
            "📍 *Yaqin sensorlar*\n\nBuyruq: /near\\_sensors\n\n"
            "Joylashuvingiz saqlangan bo'lsa, eng yaqin 3 sensor topiladi.",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(_BACK))
    elif data.startswith("map_") and data != "map_check":
        district = data[4:]
        coords = DISTRICT_COORDS.get(district, (41.2995, 69.2401))
        if df is not None and not df.empty:
            latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
            dd = latest[latest["District"] == district]
            safe = int((dd["Fault"]==0).sum()); warn = int((dd["Fault"]==1).sum()); danger_cnt = int((dd["Fault"]==2).sum())
            holat = "🔴 Muammolar bor" if danger_cnt > 0 else ("🟡 Ogohlantirish" if warn > 0 else "🟢 Barqaror")
            stats_text = (
                f"🗺️ *{district} tumani*\n━━━━━━━━━━━━━━━━━━━━\n"
                f"📡 Holat: {holat}\n"
                f"📊 {len(dd)} sensor | ✅{safe} | ⚠️{warn} | 🔴{danger_cnt}"
            )
        else:
            stats_text = f"🗺️ *{district}*\n❌ Ma'lumot yuklanmagan."

        await query.edit_message_text(stats_text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup([
                                          [InlineKeyboardButton("🗺️ Rasmli xarita", callback_data=f"mapimg_{district}"),
                                           InlineKeyboardButton("🔙 Tumanlar", callback_data="map_check")]
                                      ]))
        await context.bot.send_location(chat_id=update.effective_chat.id,
                                        latitude=coords[0], longitude=coords[1])
    elif data.startswith("mapimg_"):
        district = data[7:]
        buf = _generate_map_image(district)
        if buf:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, photo=buf,
                caption=f"🗺️ *{district}* — Sensorlar xaritasi", parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Tumanlar", callback_data="map_check")]])
            )
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Xarita yaratilmadi.")


# ==================== MAIN ====================

def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN o'rnatilmagan! .env faylga qo'shing.")
        return

    load_data()
    load_model()
    global subscribers
    subscribers = load_subscribers()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_error_handler(error_handler)

    reg_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REG_PHONE: [
                MessageHandler(filters.CONTACT, reg_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_phone),
            ],
            REG_FIRSTNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_firstname)],
            REG_LASTNAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_lastname)],
            REG_DISTRICT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_district)],
            REG_LOCATION: [
                MessageHandler(filters.LOCATION, reg_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_location),
            ],
        },
        fallbacks=[CommandHandler("start", start),
                   CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
        per_message=False,
    )
    app.add_handler(reg_conv)

    for cmd, fn in [
        ("help",             help_command),
        ("stats",            stats_command),
        ("forecast",         forecast_command),
        ("districts",        districts_command),
        ("sensor",           sensor_command),
        ("model",            model_command),
        ("predict",          predict_command),
        ("danger",           danger_sensors_command),
        ("top",              top_danger_command),
        ("averages",         averages_command),
        ("weather",          weather_command),
        ("chart",            chart_command),
        ("compare",          compare_command),
        ("district_compare", district_compare_command),
        ("history",          history_command),
        ("search",           search_command),
        ("filter",           filter_command),
        ("report",           report_command),
        ("csv",              csv_command),
        ("map",              map_command),
        ("dashboard",        dashboard_command),
        ("near_sensors",     near_sensors_command),
        ("silent",           silent_command),
        ("subscribe",        subscribe_command),
        ("unsubscribe",      unsubscribe_command),
        ("admin",            admin_command),
        ("broadcast",        broadcast_command),
    ]:
        app.add_handler(CommandHandler(cmd, fn))

    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(CallbackQueryHandler(button_callback))

    if app.job_queue is not None:
        app.job_queue.run_repeating(alert_check, interval=3600, first=60)
        logger.info("✅ JobQueue: har soatda alert_check ishlaydi")
    else:
        logger.warning("⚠️ JobQueue yo'q. Auto-alert uchun: pip install 'python-telegram-bot[job-queue]'")

    logger.info("🤖 Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
