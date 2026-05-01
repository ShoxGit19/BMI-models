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
import re
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

# ======================== UTILS IMPORT ========================
from utils import (
    load_users, save_users, get_user_by_id, get_user_by_phone, update_user,
    is_registration_complete, create_user_credentials, generate_sensor_coords,
    find_nearest_sensors, haversine, load_subscribers, save_subscribers,
    read_bot_token, audit_log,
    DISTRICTS, DISTRICT_COORDS, FEATURE_COLS,
    load_alert_state, save_alert_state, predict_failure_probability,
    load_tickets, get_active_ticket,
    detect_fault_type, create_incident, get_incident, resolve_incident,
    get_active_incidents
)

# ======================== CONFIG ========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_bot")

# .env fayldan token o'qish
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    _env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(_env_path):
        with open(_env_path, encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())

BOT_TOKEN = read_bot_token() or os.environ.get("TELEGRAM_BOT_TOKEN", "")
SITE_BASE = os.environ.get("SITE_BASE", "http://localhost:5000")

ADMIN_USERNAME = "gaybullayeev19"

REG_PHONE, REG_FIRSTNAME, REG_LASTNAME, REG_DISTRICT, REG_LOCATION = range(5)

# ======================== GLOBALS ========================
df = None
hybrid_model = None
subscribers = set()
_last_err = {"msg": None, "ts": 0}

# ======================== DATA LOADING ========================
def load_data():
    global df
    try:
        # 1) Parquet (10× tezroq)
        if os.path.exists("data/sensor_data.parquet"):
            df = pd.read_parquet("data/sensor_data.parquet", engine="pyarrow")
            for col in ("District", "SensorID"):
                if col in df.columns and str(df[col].dtype) == "category":
                    df[col] = df[col].astype(str)
        else:
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

def is_admin(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False
    return (user.username or "").lower() == ADMIN_USERNAME.lower()

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

    # ===== AUTO-PAROL: Web login uchun parol yaratish =====
    login_name, raw_password = create_user_credentials(user.id)
    if login_name and raw_password:
        await update.message.reply_text(
            f"🔐 *Web tizimga kirish maʼlumotlaringiz:*\n\n"
            f"👤 Login: `{login_name}`\n"
            f"🔑 Parol: `{raw_password}`\n\n"
            f"🌐 Sayt: {SITE_BASE}\n\n"
            f"⚠️ Parolni xavfsiz joyda saqlang!",
            parse_mode="Markdown"
        )
        audit_log("user_registered", user=str(user.id), details={
            "phone": login_name,
            "district": user_data.get("district", "")
        })

    await update.message.reply_text(
        f"🎉 Ro'yxatdan o'tish yakunlandi!\n\n"
        f"👤 {user_data.get('first_name','')} {user_data.get('last_name','')}\n"
        f"🏘️ {user_data.get('district','')}",
        reply_markup=ReplyKeyboardRemove()
    )
    await send_main_menu(update.message)
    return ConversationHandler.END

# ======================== COMMANDS ========================
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🤖 AI chatbot — tabiiy tilda savol berib, sensor ma'lumotlari haqida javob olish."""
    try:
        from chatbot_engine import answer as _ai_answer
    except Exception as e:
        await update.message.reply_text(f"⚠️ AI engine yuklanmadi: {e}")
        return

    if not context.args:
        await update.message.reply_text(
            "🤖 *AI yordamchi*\n\n"
            "Savolingizni yozing:\n"
            "`/ask Chilonzorda muammo bormi?`\n"
            "`/ask S0123 holati`\n"
            "`/ask eng past kuchlanish`\n"
            "`/ask 200V dan past sensorlar`",
            parse_mode="Markdown",
        )
        return

    question = " ".join(context.args)
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index() if df is not None else None
    if latest is not None and "Fault" in latest.columns:
        latest = latest.copy()
        latest["Fault"] = latest["Fault"].fillna(0).astype(int)

    try:
        result = _ai_answer(question, df=latest)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Xatolik: {e}")
        return

    text = result.get("text", "Javob yo'q")
    # Telegram Markdown sanitization (`_` va `*` ga ehtiyot)
    text_md = text.replace("_", "\\_")

    # Cards'larni inline buttons sifatida qo'shamiz
    keyboard_rows = []
    for c in (result.get("cards") or [])[:6]:
        title = c.get("title", "")
        link = c.get("link", "")
        if link.startswith("/"):
            # Sensor sahifasi → bot komandasiga aylantirish
            sensor_match = re.search(r"/sensor/(S\d+)", link)
            if sensor_match:
                keyboard_rows.append([InlineKeyboardButton(
                    f"🔍 {title}",
                    callback_data=f"sensor_{sensor_match.group(1)}"
                )])
                continue
        keyboard_rows.append([InlineKeyboardButton(f"➡️ {title}", callback_data="noop")])

    # Quick replies — instructions sifatida
    if result.get("quick_replies"):
        text_md += "\n\n💡 _Tezkor savollar:_\n"
        for q in result["quick_replies"][:4]:
            text_md += f"`/ask {q}`\n"

    reply_markup = InlineKeyboardMarkup(keyboard_rows) if keyboard_rows else None
    try:
        await update.message.reply_text(text_md, parse_mode="Markdown", reply_markup=reply_markup, disable_web_page_preview=True)
    except Exception:
        # Markdown xatosi bo'lsa, plain text yuborish
        await update.message.reply_text(text, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚡ *Bot buyruqlari:*\n\n"
        "🤖 /ask <savol> — AI yordamchi (tabiiy til)\n"
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
        "� /report — PDF hisobot\n"
        "� /report — PDF hisobot\n"
        "🗺️ /map Chilonzor — Tuman xaritasi\n"
        "📊 /dashboard — Vizual panel\n"
        "📍 /near\\_sensors — Eng yaqin sensorlar\n"
        "� /risk — 24h buzilish ehtimoli (yaqin)\n"
        "🗺 /zones — Tumanlar xavf darajasi\n"
        "🛠 /tickets — Faol ta'mirlash buyurtmalari\n"
        "📍 /mylocation — GPS-ni yangilash\n"
        "🔔 /subscribe — Auto-alert obuna\n"
        "🔕 /unsubscribe — Obunani bekor\n"
        "🌙 /silent — Sokin rejim on/off\n"
        "🧪 /alert\\_test — (admin) alert testi\n"
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

    # Sensor koordinatasi — navigatsiya tugmalari
    s_lat = float(latest.get("Latitude", 0))
    s_lon = float(latest.get("Longitude", 0))
    nav_kb = []
    if s_lat and s_lon:
        text += f"\n📌 *Koordinata:* `{s_lat:.5f}, {s_lon:.5f}`"
        nav_kb.append([
            InlineKeyboardButton("🗺 Google Maps",
                                  url=f"https://www.google.com/maps?q={s_lat},{s_lon}"),
            InlineKeyboardButton("🧭 Yandex Maps",
                                  url=f"https://yandex.com/maps/?pt={s_lon},{s_lat}&z=17&l=map"),
        ])
    nav_kb.append([InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")])
    await update.message.reply_text(text, parse_mode="Markdown",
                                     reply_markup=InlineKeyboardMarkup(nav_kb))

    # Telegram-ning native location pin'ini ham yuboramiz
    if s_lat and s_lon:
        try:
            await update.message.reply_location(latitude=s_lat, longitude=s_lon)
        except Exception as e:
            logger.warning(f"Sensor location yuborilmadi: {e}")


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
    """PDF hisobot (CSV bot orqali berilmaydi)."""
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

    # PDF (CSV bot orqali berilmaydi — ma'lumot xavfsizligi uchun)
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
    """CSV eksport — BOT ORQALI O'CHIRILGAN (ma'lumot xavfsizligi).
    Foydalanuvchilar veb dashboarddan PDF/Excel oladi."""
    keyboard = [[InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"),
                 InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
    await update.message.reply_text(
        "🚫 *CSV eksport bot orqali yopilgan*\n\n"
        "Ma'lumot xavfsizligi uchun bot orqali xom CSV fayllar berilmaydi.\n"
        "Buning o'rniga:\n"
        "📋 /report — PDF hisobot\n"
        "📊 /dashboard — vizual dashboard\n"
        "🌐 Veb saytda — to'liq Excel/CSV eksport",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================== 🗺️ MAP (Matplotlib) ====================

def _generate_map_image(district, user_lat=None, user_lon=None, highlight_ids=None):
    """Matplotlib bilan tuman sensorlari vizual xaritasi (REAL koordinatalar bilan).
    Agar user_lat/lon berilsa — foydalanuvchi nuqtasi ham chiziladi."""
    if df is None or df.empty:
        return None
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    dd = latest[latest["District"] == district].copy()
    if dd.empty:
        return None

    # REAL koordinatalardan foydalanish
    lats = dd["Latitude"].astype(float).values
    lons = dd["Longitude"].astype(float).values
    faults = dd["Fault"].astype(int).values
    sids = dd["SensorID"].astype(str).values
    color_map = {0: "#10B981", 1: "#F59E0B", 2: "#EF4444"}

    fig, ax = plt.subplots(figsize=(9, 8), dpi=120)
    # Sensor markerlar
    for lat, lon, f, sid in zip(lats, lons, faults, sids):
        size = 220 if f == 2 else (150 if f == 1 else 90)
        ax.scatter([lon], [lat], c=color_map.get(f, "#94A3B8"), s=size,
                   alpha=0.88, edgecolors="white", linewidths=1.3, zorder=3)
        # Faqat eng yaqin/muammoli sensorlarning nomini chizish (chig'anoq bo'lmasligi uchun)
        if highlight_ids and sid in highlight_ids:
            ax.annotate(sid, (lon, lat),
                        textcoords="offset points", xytext=(7, 7),
                        fontsize=8, fontweight="bold", color="#1F2937")
        elif f == 2:
            ax.annotate(sid, (lon, lat),
                        textcoords="offset points", xytext=(6, 6),
                        fontsize=7, color="#7F1D1D", alpha=0.9)

    # Foydalanuvchi joylashuvi
    if user_lat is not None and user_lon is not None:
        ax.scatter([user_lon], [user_lat], marker="*", c="#0EA5E9", s=420,
                   edgecolors="white", linewidths=2.5, zorder=6, label="Siz")
        # 1, 2, 5 km radius doiralari
        for r_km in [1, 2, 5]:
            r_deg = r_km / 111.0
            circle = plt.Circle((user_lon, user_lat), r_deg,
                                fill=False, color="#0EA5E9",
                                linestyle=":", linewidth=1.0, alpha=0.55)
            ax.add_patch(circle)
            ax.annotate(f"{r_km}km",
                        (user_lon + r_deg * 0.7, user_lat + r_deg * 0.7),
                        fontsize=7, color="#0EA5E9", alpha=0.75)

    ax.set_title(f"🗺 {district} — Sensorlar xaritasi ({len(dd)} ta)",
                 fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.set_facecolor("#F8FAFC")
    ax.set_aspect("equal")
    legend_handles = [
        mpatches.Patch(color="#10B981",
                        label=f"Havfsiz ({int((faults==0).sum())})"),
        mpatches.Patch(color="#F59E0B",
                        label=f"Ogohlantirish ({int((faults==1).sum())})"),
        mpatches.Patch(color="#EF4444",
                        label=f"Muammo ({int((faults==2).sum())})"),
    ]
    if user_lat is not None:
        legend_handles.insert(0, mpatches.Patch(color="#0EA5E9", label="Siz (★)"))
    ax.legend(handles=legend_handles, loc="lower right",
              fontsize=9, framealpha=0.95)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    buf.seek(0)
    plt.close(fig)
    return buf


async def map_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi tumanini avtomatik aniqlaydi va shu tuman xaritasini yuboradi."""
    user_data = get_user_by_id(update.effective_user.id) or {}
    user_district = user_data.get("district")
    user_lat = user_data.get("latitude")
    user_lon = user_data.get("longitude")

    # 1) Argument bilan: /map Chilonzor
    if context.args:
        district_q = " ".join(context.args)
        matched = [d for d in DISTRICTS if district_q.lower() in d.lower()]
        if not matched:
            await update.message.reply_text(f"❌ '{district_q}' tuman topilmadi!")
            return
        district = matched[0]
    # 2) Foydalanuvchi tumani avtomatik
    elif user_district and user_district in DISTRICTS:
        district = user_district
    # 3) Tuman tanlash menyusi
    else:
        keyboard = []
        row = []
        for d in DISTRICTS:
            row.append(InlineKeyboardButton(d, callback_data=f"map_{d}"))
            if len(row) == 2:
                keyboard.append(row); row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")])
        await update.message.reply_text(
            "🗺 *Qaysi tuman xaritasini ko'rsatay?*\n"
            "_(Profilingizda tuman ko'rsatilmagan)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Eng yaqin sensorlarni ajratib ko'rsatish (agar foydalanuvchi GPS bersa)
    highlight = None
    nearest_info = ""
    if user_lat and user_lon and df is not None:
        latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
        dd = latest[latest["District"] == district].copy()
        if not dd.empty:
            dists = []
            for _, r in dd.iterrows():
                try:
                    d_km = haversine(float(user_lat), float(user_lon),
                                      float(r["Latitude"]), float(r["Longitude"]))
                    dists.append((d_km, str(r["SensorID"])))
                except Exception:
                    pass
            dists.sort(key=lambda x: x[0])
            top = dists[:5]
            highlight = {sid for _, sid in top}
            nearest_info = "\n\n📏 *Sizga eng yaqin 5 ta:*\n" + "\n".join(
                [f"  {i+1}. `{sid}` — {dk:.2f} km" for i, (dk, sid) in enumerate(top)]
            )

    coords = DISTRICT_COORDS.get(district, (41.3111, 69.2797))
    buf = _generate_map_image(district,
                               user_lat=float(user_lat) if user_lat else None,
                               user_lon=float(user_lon) if user_lon else None,
                               highlight_ids=highlight)
    caption = f"🗺 *{district}* tuman xaritasi{nearest_info}"
    keyboard = [[InlineKeyboardButton("📍 Yaqin sensorlar", callback_data="near_sensors"),
                 InlineKeyboardButton("🔙 Menyu", callback_data="menu")]]
    if buf:
        await update.message.reply_photo(photo=buf, caption=caption,
                                         parse_mode="Markdown",
                                         reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(caption, parse_mode="Markdown",
                                         reply_markup=InlineKeyboardMarkup(keyboard))

    # === KETMA-KET koordinata pin'lari (har bir yaqin sensor uchun) ===
    if user_lat and user_lon and df is not None:
        latest2 = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
        dd2 = latest2[latest2["District"] == district].copy()
        seq = []
        for _, r in dd2.iterrows():
            try:
                d_km = haversine(float(user_lat), float(user_lon),
                                  float(r["Latitude"]), float(r["Longitude"]))
                seq.append((d_km, r))
            except Exception:
                pass
        seq.sort(key=lambda x: x[0])
        ft_emoji = {0: "🟢", 1: "🟡", 2: "🔴"}
        # Avval foydalanuvchi joylashuvini, keyin har bir yaqin sensorni yuboramiz
        try:
            await update.message.reply_location(latitude=float(user_lat), longitude=float(user_lon))
        except Exception:
            pass
        for i, (d_km, r) in enumerate(seq[:5], 1):
            try:
                s_lat = float(r["Latitude"]); s_lon = float(r["Longitude"])
                sid = str(r["SensorID"])
                fault = int(r.get("Fault", 0))
                emoji = ft_emoji.get(fault, "⚪")
                cap = (
                    f"{i}. {emoji} *{sid}*\n"
                    f"📏 {d_km:.2f} km · 📍 `{s_lat:.5f}, {s_lon:.5f}`\n"
                    f"🔌 {r.get('Kuchlanish (V)',0):.1f}V · 🔄 {r.get('Chastota (Hz)',50):.2f}Hz"
                )
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🗺 Google", url=f"https://www.google.com/maps?q={s_lat},{s_lon}"),
                    InlineKeyboardButton("🧭 Yandex", url=f"https://yandex.com/maps/?pt={s_lon},{s_lat}&z=17&l=map"),
                ]])
                await update.message.reply_location(latitude=s_lat, longitude=s_lon)
                await update.message.reply_text(cap, parse_mode="Markdown", reply_markup=kb)
            except Exception as e:
                logger.warning(f"map seq pin xato {sid}: {e}")
    else:
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

    user_lat = float(user_data["latitude"])
    user_lon = float(user_data["longitude"])
    user_district = user_data.get("district")
    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()

    # Foydalanuvchi tumani bo'lsa — faqat shu tuman ichidan
    if user_district and user_district in DISTRICTS:
        scope = latest[latest["District"] == user_district].copy()
        scope_label = f"📍 *{user_district}* tumani ichidan"
    else:
        scope = latest
        scope_label = "📍 Barcha tumanlardan"

    # Real koordinatalar bilan masofa hisoblash
    rows = []
    for _, row in scope.iterrows():
        try:
            s_lat = float(row.get("Latitude", 0))
            s_lon = float(row.get("Longitude", 0))
            if not s_lat or not s_lon:
                continue
            dist_km = haversine(user_lat, user_lon, s_lat, s_lon)
            rows.append((dist_km, row, s_lat, s_lon))
        except Exception:
            continue

    rows.sort(key=lambda x: x[0])
    top5 = rows[:5]

    if not top5:
        await update.message.reply_text("❌ Atrofda sensor topilmadi.")
        return

    ft = {0: "🟢 Havfsiz", 1: "🟡 Ogohlantirish", 2: "🔴 Muammo"}
    text = f"{scope_label}\n*Eng yaqin 5 ta sensor:*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (dist_km, row, s_lat, s_lon) in enumerate(top5, 1):
        text += (
            f"{i}. *{row['SensorID']}* — {row.get('District','N/A')}\n"
            f"   📏 {dist_km:.2f} km · 📡 {ft.get(int(row.get('Fault',0)),'?')}\n"
            f"   🔌{row.get('Kuchlanish (V)',0):.1f}V · 🔄{row.get('Chastota (Hz)',50):.2f}Hz\n\n"
        )

    # === Static xarita rasmi (REAL koordinatalar) ===
    try:
        # Foydalanuvchi tumani ichidagi BARCHA sensorlarni rasmda ko'rsatamiz
        if user_district and user_district in DISTRICTS:
            highlight = {str(r[1]["SensorID"]) for r in top5}
            buf = _generate_map_image(user_district,
                                       user_lat=user_lat, user_lon=user_lon,
                                       highlight_ids=highlight)
        else:
            # Tuman yo'q — top5 ni ko'rsatamiz
            buf = None
        nearest = top5[0]
        keyboard = [
            [InlineKeyboardButton(f"🗺 {nearest[1]['SensorID']} — Google Maps",
                                   url=f"https://www.google.com/maps?q={nearest[2]},{nearest[3]}")],
            [InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]
        ]
        if buf:
            await update.message.reply_photo(
                photo=buf, caption=text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(text, parse_mode="Markdown",
                                             reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.warning(f"near_sensors map rendering xato: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")]]
        await update.message.reply_text(text, parse_mode="Markdown",
                                         reply_markup=InlineKeyboardMarkup(keyboard))

    # Eng yaqin sensorning native location pin'i
    try:
        await update.message.reply_location(latitude=top5[0][2], longitude=top5[0][3])
    except Exception:
        pass


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


# ==================== 🛰 SMART GEOFENCING ALERT ====================
ALERT_RADIUS_KM = 2.0          # Foydalanuvchini ogohlantirish radiusi (1-2 km)
ADMIN_DEDUP_SEC = 1800          # 30 daqiqa — bir xil sensor qayta xabar bermasin
USER_DEDUP_SEC = 3600           # 1 soat — foydalanuvchi qayta xabar bermasin


def _maps_keyboard(lat, lon, sensor_id, inc_id=None, include_resolve=False):
    """Google Maps + Yandex Maps + (ixtiyoriy) Resolve tugmalari."""
    g_url = f"https://www.google.com/maps?q={lat},{lon}"
    y_url = f"https://yandex.com/maps/?pt={lon},{lat}&z=16&l=map"
    rows = [[
        InlineKeyboardButton("🗺 Google Maps", url=g_url),
        InlineKeyboardButton("🧭 Yandex Maps", url=y_url),
    ]]
    if include_resolve and inc_id:
        rows.append([InlineKeyboardButton("✅ Muammo hal qilindi", callback_data=f"resolve:{inc_id}")])
    return InlineKeyboardMarkup(rows)


async def realtime_alert_check(context: ContextTypes.DEFAULT_TYPE):
    """Geofencing: avariya sensoridan 1-2 km radiusdagi foydalanuvchilarni ogohlantirish.
    + Admin uchun batafsil dispatcher xabari (Google/Yandex Maps tugmalari bilan)."""
    global df
    if df is None or df.empty:
        return

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    state = load_alert_state()
    now = datetime.datetime.now()
    now_iso = now.isoformat()

    users_list = load_users()
    admins = [u for u in users_list if u.get("role") == "admin"
              or (u.get("username") or "").lower() == ADMIN_USERNAME.lower()]

    critical_rows = []
    for _, row in latest.iterrows():
        try:
            v = float(row.get("Kuchlanish (V)", 220))
            fault = int(row.get("Fault", 0))
            if fault == 2 or v < 170 or v > 250:
                critical_rows.append(row)
        except Exception:
            continue

    if not critical_rows:
        return

    for row in critical_rows:
        sid = str(row["SensorID"])
        sensor_lat = float(row.get("Latitude", 0))
        sensor_lon = float(row.get("Longitude", 0))
        district = row.get("District", "?")
        v = float(row.get("Kuchlanish (V)", 220))
        fault_type = detect_fault_type(row.to_dict())

        admin_key = f"admin:sensor:{sid}"
        last_admin = state.get(admin_key)
        admin_should_send = True
        if last_admin:
            try:
                if (now - datetime.datetime.fromisoformat(last_admin)).total_seconds() < ADMIN_DEDUP_SEC:
                    admin_should_send = False
            except Exception:
                pass

        nearby_users = []
        for u in users_list:
            if u.get("role") == "admin":
                continue
            lat = u.get("latitude")
            lon = u.get("longitude")
            chat_id = u.get("id")
            if not chat_id or lat is None or lon is None:
                continue
            try:
                d = haversine(float(lat), float(lon), sensor_lat, sensor_lon)
            except Exception:
                continue
            if d > ALERT_RADIUS_KM:
                continue
            user_key = f"{chat_id}:{sid}"
            last = state.get(user_key)
            if last:
                try:
                    if (now - datetime.datetime.fromisoformat(last)).total_seconds() < USER_DEDUP_SEC:
                        continue
                except Exception:
                    pass
            nearby_users.append((chat_id, d))

        if not nearby_users and not admin_should_send:
            continue

        notified_ids = [cid for cid, _ in nearby_users]
        incident = create_incident(
            sensor_id=sid, district=district, fault_type=fault_type,
            lat=sensor_lat, lon=sensor_lon, voltage=v,
            notified_users=notified_ids
        )
        inc_id = incident["id"]

        for chat_id, dist in nearby_users:
            user_text = (
                f"⚠️ *Diqqat! Hududingizdagi {sid} sensori muammo aniqladi.*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 Tuman: {district}\n"
                f"📏 Sizdan masofa: *{dist:.2f} km*\n"
                f"⚡ Kuchlanish: *{v:.0f}V*\n"
                f"🔧 Holat: {fault_type}\n\n"
                f"_Tez orada bartaraf etiladi. Iltimos, xavfsizlik qoidalariga rioya qiling._"
            )
            try:
                await context.bot.send_message(
                    chat_id=chat_id, text=user_text, parse_mode="Markdown",
                    reply_markup=_maps_keyboard(sensor_lat, sensor_lon, sid)
                )
                state[f"{chat_id}:{sid}"] = now_iso
                audit_log("geofence_alert", user=str(chat_id),
                          details={"sensor": sid, "dist_km": round(dist, 2), "incident": inc_id})
            except Exception as e:
                logger.warning(f"Geofence alert {chat_id} ga yuborilmadi: {e}")

        if admin_should_send and admins:
            admin_text = (
                f"🚨 *AVARIYA — DISPATCHER XABARI*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 Incident: `{inc_id}`\n"
                f"📡 Sensor: `{sid}`\n"
                f"🏘 Tuman: *{district}*\n"
                f"📍 Koordinata: `{sensor_lat:.5f}, {sensor_lon:.5f}`\n\n"
                f"🔴 *Avariya turi:*\n{fault_type}\n\n"
                f"⚡ Kuchlanish: *{v:.0f}V*\n"
                f"👥 Ogohlantirilgan foydalanuvchilar: *{len(nearby_users)}*\n"
                f"📅 Vaqt: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"_Joyiga borib bartaraf etgach, \"✅ Muammo hal qilindi\" tugmasini bosing._"
            )
            for adm in admins:
                try:
                    await context.bot.send_message(
                        chat_id=adm["id"], text=admin_text, parse_mode="Markdown",
                        reply_markup=_maps_keyboard(sensor_lat, sensor_lon, sid,
                                                     inc_id=inc_id, include_resolve=True)
                    )
                except Exception as e:
                    logger.warning(f"Admin dispatcher xabari yuborilmadi {adm.get('id')}: {e}")
            state[admin_key] = now_iso
            audit_log("dispatcher_alert", user="system",
                      details={"sensor": sid, "incident": inc_id, "admins": len(admins)})

    save_alert_state(state)


# ==================== 👮 ADMIN GROUP ALERT ====================
async def admin_district_alert(context: ContextTypes.DEFAULT_TYPE):
    """Agar butun bir tuman fault holatga tushsa — admin uchun xabar."""
    global df
    if df is None or df.empty:
        return

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    state = load_alert_state()
    now_iso = datetime.datetime.now().isoformat()
    alerts = []

    for district, group in latest.groupby("District"):
        total = len(group)
        danger = int((group["Fault"] == 2).sum())
        if total >= 5 and danger / total >= 0.5:
            key = f"admin:district:{district}"
            last = state.get(key)
            if last:
                try:
                    if (datetime.datetime.now() - datetime.datetime.fromisoformat(last)).total_seconds() < 7200:
                        continue
                except Exception:
                    pass
            alerts.append((district, danger, total))
            state[key] = now_iso

    if not alerts:
        return

    save_alert_state(state)
    text = "🚨 *ADMIN OGOHLANTIRISH — YIRIK AVARIYA*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for d, dn, t in alerts:
        text += f"🏘️ *{d}*: {dn}/{t} sensor avariya holatda ({dn*100//t}%)\n"
    text += f"\n📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Adminlarga yuborish
    for u in load_users():
        if u.get("role") == "admin" or (u.get("username") or "").lower() == ADMIN_USERNAME.lower():
            try:
                await context.bot.send_message(chat_id=u["id"], text=text, parse_mode="Markdown")
            except Exception:
                pass


# ==================== 🆕 RISK / ZONES / TICKETS / LOCATION ====================

async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """24 soat ichida buzilish ehtimoli yuqori bo'lgan eng yaqin sensorlar."""
    user = update.effective_user
    user_data = get_user_by_id(user.id)
    if not user_data or not user_data.get("latitude"):
        await update.message.reply_text(
            "📍 Avval joylashuvingizni yuboring: /near_sensors yoki /mylocation"
        )
        return
    lat = float(user_data["latitude"])
    lon = float(user_data["longitude"])
    df = data_loader.df
    if df is None or df.empty:
        await update.message.reply_text("❌ Maʼlumot yo'q.")
        return
    latest = df.sort_values("Timestamp").groupby("SensorID", as_index=False).tail(1)
    rows = []
    for _, r in latest.iterrows():
        try:
            d_km = haversine(lat, lon, float(r.get("Latitude", 0)), float(r.get("Longitude", 0)))
            if d_km > 5:
                continue
            prob = predict_failure_probability(r.to_dict())
            rows.append((prob, d_km, r))
        except Exception:
            continue
    rows.sort(key=lambda x: -x[0])
    rows = rows[:10]
    if not rows:
        await update.message.reply_text("✅ 5 km radiusda xavfli sensor topilmadi.")
        return
    lines = ["🔮 *24 soat ichida buzilish ehtimoli (Top 10)*\n"]
    for prob, d_km, r in rows:
        emoji = "🔴" if prob >= 60 else ("🟡" if prob >= 30 else "🟢")
        lines.append(f"{emoji} `{r['SensorID']}` — *{prob}%* · {d_km:.2f} km · {r.get('District','?')}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def zones_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha tumanlar bo'yicha xavf darajasi."""
    df = data_loader.df
    if df is None or df.empty:
        await update.message.reply_text("❌ Maʼlumot yo'q.")
        return
    latest = df.sort_values("Timestamp").groupby("SensorID", as_index=False).tail(1)
    lines = ["🗺 *Tumanlar bo'yicha xavf darajasi*\n"]
    rows = []
    for district, g in latest.groupby("District"):
        total = len(g)
        if total == 0:
            continue
        danger = int((g["Fault"] == 2).sum())
        warn = int((g["Fault"] == 1).sum())
        risk_pct = round((danger / total) * 100, 1)
        rows.append((risk_pct, district, total, danger, warn))
    rows.sort(key=lambda x: -x[0])
    for risk_pct, district, total, danger, warn in rows:
        if risk_pct >= 30:
            emoji = "🔴"
        elif risk_pct >= 15:
            emoji = "🟡"
        else:
            emoji = "🟢"
        lines.append(f"{emoji} *{district}* — {risk_pct}% xavf · {danger}🔴 {warn}🟡 / {total}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def tickets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Faol ta'mirlash buyurtmalari."""
    tickets = load_tickets()
    active = [t for t in tickets if t.get("status") != "closed"]
    if not active:
        await update.message.reply_text("✅ Hozirda faol ta'mirlash buyurtmasi yo'q.")
        return
    lines = [f"🛠 *Faol buyurtmalar: {len(active)}*\n"]
    for t in active[:20]:
        status_emoji = "🟡" if t.get("status") == "in_progress" else "🔴"
        eta = t.get("eta") or "—"
        lines.append(
            f"{status_emoji} `#{t['id']}` · `{t.get('sensor_id','?')}`\n"
            f"   📝 {t.get('issue','—')[:80]}\n"
            f"   ⏱ ETA: {eta}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def mylocation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi GPS-ini yangilash."""
    loc_btn = KeyboardButton("📍 Joylashuvimni yuborish", request_location=True)
    markup = ReplyKeyboardMarkup([[loc_btn]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "📍 Joriy joylashuvingizni yuboring (real-time alertlar shu bo'yicha keladi):",
        reply_markup=markup
    )


async def alert_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: real-time alert tizimini sinash (dedup tozalash)."""
    if not is_admin(update):
        await update.message.reply_text("🔒 Faqat admin uchun.")
        return
    user_data = get_user_by_id(update.effective_user.id)
    if not user_data or not user_data.get("latitude"):
        await update.message.reply_text("📍 Avval joylashuvingizni yuboring: /mylocation")
        return
    state = load_alert_state()
    chat_key = str(update.effective_chat.id)
    cleared = len([k for k in state if chat_key in k])
    state = {k: v for k, v in state.items() if chat_key not in k}
    save_alert_state(state)
    await update.message.reply_text(
        f"🧪 *Alert testi*\n\n"
        f"• Tozalandi: *{cleared}* ta dedup yozuv\n"
        f"• Keyingi tekshiruv: ≤5 daqiqa ichida\n"
        f"• Radius: 3 km\n"
        f"• Sizning GPS: `{user_data['latitude']:.4f}, {user_data['longitude']:.4f}`",
        parse_mode="Markdown"
    )


# ==================== �👤 ADMIN ====================

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

    # ---- Resolve incident (admin tugmasi) ----
    if data.startswith("resolve:"):
        inc_id = data.split(":", 1)[1]
        if not is_admin(update):
            await query.answer("🔒 Faqat admin", show_alert=True)
            return
        inc = get_incident(inc_id)
        if not inc:
            await query.edit_message_text("❌ Incident topilmadi.")
            return
        if inc.get("status") == "resolved":
            await query.answer("Bu avariya allaqachon hal qilingan.", show_alert=True)
            return
        resolve_incident(inc_id)
        # Yaqin atrofdagi foydalanuvchilarga "tiklandi" xabari
        sent_ok = 0
        for chat_id in inc.get("notified_users", []):
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"✅ *Sizning hududingizda elektr ta'minoti tiklandi.*\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📡 Sensor: `{inc['sensor_id']}`\n"
                        f"🏘 Tuman: {inc.get('district','')}\n\n"
                        f"_Xizmatimizdan foydalanganingiz uchun rahmat!_"
                    ),
                    parse_mode="Markdown"
                )
                sent_ok += 1
            except Exception:
                pass
        audit_log("incident_resolved", user=str(update.effective_user.id),
                  details={"incident": inc_id, "notified_back": sent_ok})
        try:
            await query.edit_message_text(
                query.message.text + f"\n\n✅ *HAL QILINDI* ({sent_ok} ta foydalanuvchiga xabar yuborildi)",
                parse_mode="Markdown"
            )
        except Exception:
            await query.message.reply_text(f"✅ Hal qilindi. {sent_ok} ta foydalanuvchiga xabar yuborildi.")
        return

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
        await query.edit_message_text("📥 *Export:*\n\n🔹 /report — PDF hisobot\n🔹 /dashboard — vizual dashboard",
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


# ==================== MORNING REPORT ====================
async def morning_report(context: ContextTypes.DEFAULT_TYPE):
    """Har kuni ertalab 06:00 da barcha subscriberlarga hisobot yuborish."""
    global df, subscribers
    if df is None or df.empty:
        return

    try:
        total = df["SensorID"].nunique()
        latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()

        danger_count = int((latest["Fault"] == 2).sum()) if "Fault" in latest.columns else 0
        warning_count = int((latest["Fault"] == 1).sum()) if "Fault" in latest.columns else 0
        safe_count = total - danger_count - warning_count

        avg_v = latest["Kuchlanish (V)"].mean() if "Kuchlanish (V)" in latest.columns else 0
        avg_hz = latest["Chastota (Hz)"].mean() if "Chastota (Hz)" in latest.columns else 0
        avg_t = latest["Muhit_harorat (C)"].mean() if "Muhit_harorat (C)" in latest.columns else 0

        # Ob-havo
        weather_text = ""
        try:
            resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={"latitude": 41.3, "longitude": 69.27, "current_weather": True},
                timeout=5
            )
            if resp.ok:
                cw = resp.json().get("current_weather", {})
                weather_text = (
                    f"\n🌤️ *Ob-havo (Toshkent):*\n"
                    f"🌡️ {cw.get('temperature', '?')}°C | 💨 {cw.get('windspeed', '?')} km/h\n"
                )
        except Exception:
            pass

        text = (
            f"☀️ *Ertalabki hisobot — {datetime.datetime.now().strftime('%d.%m.%Y')}*\n\n"
            f"📊 *Jami sensorlar:* {total}\n"
            f"✅ Xavfsiz: {safe_count}\n"
            f"⚠️ Ogohlantirish: {warning_count}\n"
            f"🔴 Xavfli: {danger_count}\n\n"
            f"⚡ O'rtacha kuchlanish: {avg_v:.1f} V\n"
            f"📡 O'rtacha chastota: {avg_hz:.2f} Hz\n"
            f"🌡️ O'rtacha harorat: {avg_t:.1f}°C\n"
            f"{weather_text}\n"
            f"🌐 Dashboard: {SITE_BASE}"
        )

        sent = 0
        for chat_id in subscribers:
            try:
                # Foydalanuvchi tumani bo'yicha shaxsiy ogohlantirish
                u = get_user_by_id(chat_id) or {}
                u_district = u.get("district")
                personal = ""
                danger_rows = []
                if u_district and u_district in DISTRICTS:
                    dd = latest[(latest["District"] == u_district) & (latest["Fault"] == 2)]
                    if not dd.empty:
                        personal = (
                            f"\n\n⚠️ *Sizning tumaningizda ({u_district}) "
                            f"{len(dd)} ta xavfli sensor!*\n"
                        )
                        danger_rows = dd.head(5).to_dict("records")

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text + personal,
                    parse_mode="Markdown"
                )

                # Har bir xavfli sensor uchun KOORDINATA pin'i + tafsilot
                for r in danger_rows:
                    try:
                        s_lat = float(r.get("Latitude", 0))
                        s_lon = float(r.get("Longitude", 0))
                        if not s_lat or not s_lon:
                            continue
                        sid = str(r.get("SensorID", "?"))
                        cap = (
                            f"🔴 *{sid}* — xavfli holat\n"
                            f"📍 `{s_lat:.5f}, {s_lon:.5f}`\n"
                            f"🔌 {float(r.get('Kuchlanish (V)',0)):.1f}V · "
                            f"🔄 {float(r.get('Chastota (Hz)',50)):.2f}Hz"
                        )
                        kb = InlineKeyboardMarkup([[
                            InlineKeyboardButton("🗺 Google", url=f"https://www.google.com/maps?q={s_lat},{s_lon}"),
                            InlineKeyboardButton("🧭 Yandex", url=f"https://yandex.com/maps/?pt={s_lon},{s_lat}&z=17&l=map"),
                        ]])
                        await context.bot.send_location(chat_id=chat_id, latitude=s_lat, longitude=s_lon)
                        await context.bot.send_message(chat_id=chat_id, text=cap, parse_mode="Markdown", reply_markup=kb)
                    except Exception as e:
                        logger.warning(f"morning pin xato: {e}")
                sent += 1
            except Exception:
                pass
        logger.info(f"Morning report yuborildi: {sent}/{len(subscribers)} subscriber")

    except Exception as e:
        logger.error(f"Morning report xatosi: {e}")


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
        ("ask",              ask_command),
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
        ("map",              map_command),
        ("dashboard",        dashboard_command),
        ("near_sensors",     near_sensors_command),
        ("risk",             risk_command),
        ("zones",            zones_command),
        ("tickets",          tickets_command),
        ("mylocation",       mylocation_command),
        ("alert_test",       alert_test_command),
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
        # Faqat ertalabki hisobot — har kuni 06:00 Toshkent vaqti (UTC+5)
        try:
            import zoneinfo
            tz_tashkent = zoneinfo.ZoneInfo("Asia/Tashkent")
        except Exception:
            tz_tashkent = datetime.timezone(datetime.timedelta(hours=5))
        morning_time = datetime.time(hour=6, minute=0, tzinfo=tz_tashkent)
        app.job_queue.run_daily(morning_report, time=morning_time, name="morning_report")
        logger.info("✅ JobQueue: morning_report (06:00 Asia/Tashkent)")
    else:
        logger.warning("⚠️ JobQueue yo'q. Auto-alert uchun: pip install 'python-telegram-bot[job-queue]'")

    logger.info("🤖 Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
