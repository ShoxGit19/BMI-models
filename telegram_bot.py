"""
⚡ Elektr Monitoring Telegram Bot
Barcha monitoring funksiyalari: stats, sensors, forecast, model, alerts
+ Grafik, Auto-alert, Export, Qidiruv, Taqqoslash, Tarix, Admin, Xarita
Yaratuvchi: Shohjahon G'aybullayev — Toshkent, Bekobod 2026
"""
import os
import io
import json
import logging
import datetime
import pickle
import numpy as np
import pandas as pd
import requests as http_req
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# --- Logger ---
logging.basicConfig(
    format="[%(asctime)s] %(levelname)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("tg-bot")

# --- Token (.env fayldan o'qish) ---
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

load_env()
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# --- Ma'lumot va modelni yuklash ---
def load_data_and_model():
    df, model = None, None
    try:
        if os.path.exists("data/sensor_data_part1.csv") and os.path.exists("data/sensor_data_part2.csv"):
            df = pd.concat([
                pd.read_csv("data/sensor_data_part1.csv"),
                pd.read_csv("data/sensor_data_part2.csv")
            ], ignore_index=True)
            if "Timestamp" in df.columns:
                df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        if os.path.exists("models/hybrid_model_part1.pkl") and os.path.exists("models/hybrid_model_part2.pkl"):
            merged = b""
            for p in ["models/hybrid_model_part1.pkl", "models/hybrid_model_part2.pkl"]:
                with open(p, "rb") as f:
                    merged += f.read()
            model = pickle.loads(merged)
    except Exception as e:
        logger.error(f"Yuklash xatosi: {e}")
    return df, model

df, hybrid_model = load_data_and_model()
logger.info(f"CSV: {len(df) if df is not None else 0} rows | Model: {'✅' if hybrid_model else '❌'}")

FEATURE_COLS = [
    "Muhit_harorat (C)", "Shamol_tezligi (km/h)", "Chastota (Hz)", "Kuchlanish (V)",
    "Vibratsiya", "Sim_mexanik_holati (%)", "Atrof_muhit_humidity (%)", "Quvvati (kW)"
]

DISTRICTS = [
    "Bektemir", "Chilonzor", "Mirobod", "Mirzo Ulug'bek",
    "Olmazor", "Sergeli", "Shayxontohur", "Uchtepa",
    "Yakkasaroy", "Yashnobod", "Yunusobod"
]

# --- Foydalanuvchilar ---
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_users(users_list):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_list, f, ensure_ascii=False, indent=2)

def register_user(update):
    """Start bosgan foydalanuvchini users.json ga yozish"""
    user = update.effective_user
    if not user:
        return
    users_list = load_users()
    existing_ids = {u["id"] for u in users_list}
    if user.id not in existing_ids:
        users_list.append({
            "id": user.id,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "username": user.username or "",
            "phone": "",
            "language_code": user.language_code or "",
            "joined": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_users(users_list)
        logger.info(f"Yangi foydalanuvchi: {user.first_name} (@{user.username}) | Jami: {len(users_list)}")
    else:
        # Mavjud foydalanuvchining ma'lumotlarini yangilash
        changed = False
        for u in users_list:
            if u["id"] == user.id:
                if u.get("first_name") != (user.first_name or ""):
                    u["first_name"] = user.first_name or ""
                    changed = True
                if u.get("last_name") != (user.last_name or ""):
                    u["last_name"] = user.last_name or ""
                    changed = True
                if u.get("username") != (user.username or ""):
                    u["username"] = user.username or ""
                    changed = True
                break
        if changed:
            save_users(users_list)


def save_user_phone(user_id, phone):
    """Telefon raqamni saqlash"""
    users_list = load_users()
    for u in users_list:
        if u["id"] == user_id:
            u["phone"] = phone
            save_users(users_list)
            return True
    return False

# --- Obunchilar va Admin ---
SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), "subscribers.json")
ADMIN_USERNAME = "gaybullayeev19"  # Faqat shu odam admin

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(subs), f)

subscribers = load_subscribers()

# Tuman koordinatalari (Toshkent)
DISTRICT_COORDS = {
    "Bektemir": (41.2142, 69.3342),
    "Chilonzor": (41.2825, 69.1903),
    "Mirobod": (41.3111, 69.2797),
    "Mirzo Ulug'bek": (41.3400, 69.3350),
    "Olmazor": (41.3330, 69.2150),
    "Sergeli": (41.2230, 69.2650),
    "Shayxontohur": (41.3280, 69.2430),
    "Uchtepa": (41.3050, 69.1700),
    "Yakkasaroy": (41.2915, 69.2700),
    "Yashnobod": (41.3380, 69.3080),
    "Yunusobod": (41.3650, 69.2850),
}

# ==================== COMMANDS ====================

async def send_main_menu(message):
    """Asosiy menuni ko'rsatish"""
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
        [InlineKeyboardButton("ℹ️ Yordam", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(
        "⚡ *Elektr Monitoring Bot*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Toshkent shahar elektr tarmog'i\n"
        "500 sensor | 11 tuman | Real-time\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update)
    user = update.effective_user
    # Telefon raqam borligini tekshirish — faqat 1 marta so'raladi
    users_list = load_users()
    user_data = next((u for u in users_list if u["id"] == user.id), None)
    if not user_data or not user_data.get("phone"):
        contact_btn = KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
        markup = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "👋 *Xush kelibsiz!*\n\n"
            "Davom etish uchun telefon raqamingizni yuboring:\n"
            "Pastdagi tugmani bosing 👇",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return
    await send_main_menu(update.message)


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi telefon raqamini qabul qilish"""
    contact = update.message.contact
    if contact:
        phone = contact.phone_number
        user_id = update.effective_user.id
        save_user_phone(user_id, phone)
        logger.info(f"📱 Telefon saqlandi: {update.effective_user.first_name} -> {phone}")
        await update.message.reply_text(
            "✅ Telefon raqamingiz saqlandi!",
            reply_markup=ReplyKeyboardRemove()
        )
        await send_main_menu(update.message)

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
        "_Yaratuvchi: Shohjahon G'aybullayev_\n"
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

    latest = df.sort_values("Timestamp").groupby("SensorID").last().reset_index()
    tuman_stats = latest.groupby("District").agg(
        jami=("SensorID", "count"),
        havfsiz=("Fault", lambda x: int((x == 0).sum())),
        ogohlantirish=("Fault", lambda x: int((x == 1).sum())),
        muammo=("Fault", lambda x: int((x == 2).sum())),
    )

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


async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if df is None or df.empty or hybrid_model is None:
        text = "❌ Ma'lumot yoki model yuklanmagan!"
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    now = datetime.datetime.now()
    week_ago = now - datetime.timedelta(days=7)
    last_week = df[df["Timestamp"] >= week_ago]

    # So'nggi 7 kun statistikasi
    if not last_week.empty:
        resampled = last_week.set_index("Timestamp")[FEATURE_COLS].resample("6h").mean().dropna()
        if not resampled.empty:
            preds = hybrid_model.predict(resampled)
            safe_6h = int((preds == 0).sum())
            warn_6h = int((preds == 1).sum())
            danger_6h = int((preds == 2).sum())
        else:
            safe_6h = warn_6h = danger_6h = 0
    else:
        safe_6h = warn_6h = danger_6h = 0

    # Real ob-havo prognozi
    weather_text = ""
    try:
        resp = http_req.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": 41.3111, "longitude": 69.2797,
            "daily": "temperature_2m_max,temperature_2m_min,wind_speed_10m_max",
            "timezone": "Asia/Tashkent",
            "forecast_days": 7
        }, timeout=10)
        wd = resp.json().get("daily", {})
        if wd.get("time"):
            weather_text = "\n🌤️ *Ob-havo prognozi (Toshkent):*\n"
            for i in range(min(7, len(wd["time"]))):
                day = wd["time"][i][5:]  # MM-DD
                tmax = wd["temperature_2m_max"][i]
                tmin = wd["temperature_2m_min"][i]
                wind = wd["wind_speed_10m_max"][i]
                weather_text += f"  {day}: {tmin:.0f}-{tmax:.0f}°C 🌬️{wind:.0f}km/h\n"
    except Exception:
        weather_text = "\n⚠️ Ob-havo ma'lumoti yuklanmadi\n"

    # Kelajak 7 kun model prognozi
    future_safe = future_warn = future_danger = 0
    if not last_week.empty:
        recent = last_week.set_index("Timestamp")[FEATURE_COLS].resample("6h").mean().dropna()
        if len(recent) >= 1:
            base = recent.iloc[-1].values.copy()
            rng = np.random.default_rng(42)
            normal = np.array([15.0, 5.0, 50.0, 220.0, 0.35, 90.0, 60.0, 3.2])
            noise_scale = np.array([1.5, 1.0, 0.15, 3.0, 0.08, 1.5, 3.0, 0.25])
            reversion = np.array([0.3, 0.3, 0.4, 0.3, 0.3, 0.15, 0.3, 0.3])
            prev = base.copy()
            for i in range(1, 29):
                noise = rng.normal(0, 1, 8) * noise_scale
                vals = prev + reversion * (normal - prev) + noise
                vals = np.clip(vals, [(-5), 0, 49.2, 205, 0.05, 70, 25, 1.5],
                               [50, 35, 50.8, 235, 1.2, 100, 95, 5.5])
                pred_input = pd.DataFrame([vals], columns=FEATURE_COLS)
                pred = int(hybrid_model.predict(pred_input)[0])
                if pred == 0:
                    future_safe += 1
                elif pred == 1:
                    future_warn += 1
                else:
                    future_danger += 1
                prev = vals.copy()

    text = (
        f"🔮 *7 kunlik prognoz*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📆 *O'tgan 7 kun (6 soatlik):*\n"
        f"✅ Havfsiz: {safe_6h} | ⚠️ Og'oh: {warn_6h} | 🔴 Xavf: {danger_6h}\n\n"
        f"🔮 *Kelajak 7 kun (prognoz):*\n"
        f"✅ Havfsiz: {future_safe} | ⚠️ Og'oh: {future_warn} | 🔴 Xavf: {future_danger}\n"
        f"{weather_text}"
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
            f"🏘️ *{district}* — {len(d_sensors)} sensor\n"
            f"✅ {safe} | ⚠️ {warn} | 🔴 {danger}\n\n"
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
        await chart_command(update, context)
    elif data == "compare_check":
        await query.edit_message_text(
            "📈 *Taqqoslash:*\n\n"
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
        await query.edit_message_text(
            "🗺️ *Xarita:*\n\nBuyruq: `/map Chilonzor`\n\n"
            f"Mavjud tumanlar:\n" + "\n".join(f"  • {d}" for d in DISTRICTS),
            parse_mode="Markdown"
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
    elif data.startswith("map_"):
        district = data[4:]
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
        await query.edit_message_text(f"🗺️ *{district}*{info}", parse_mode="Markdown")
        await context.bot.send_location(chat_id=update.effective_chat.id,
                                        latitude=coords[0], longitude=coords[1])


# ==================== MAIN ====================

def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN o'rnatilmagan!")
        logger.error("1. @BotFather dan token oling")
        logger.error("2. .env faylga TELEGRAM_BOT_TOKEN=xxx qo'shing")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands — asosiy
    app.add_handler(CommandHandler("start", start))
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

    # Yangi buyruqlar
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

    # Telefon raqam qabul qilish
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    # Callback buttons
    app.add_handler(CallbackQueryHandler(button_callback))

    # Auto-alert: har 1 soatda tekshirish
    # app.job_queue.run_repeating(alert_check, interval=3600, first=60)  # Auto-alert o'chirildi

    logger.info("🤖 Bot ishga tushdi! (8 ta yangi funksiya qo'shildi)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
