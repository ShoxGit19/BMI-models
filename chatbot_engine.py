"""Smart Chatbot Engine — Intent detection + entity extraction + rich answers.

Asosiy printsip:
- Foydalanuvchi savolini intentlarga bo'lamiz (score + keyword matching)
- Entity'larni extract qilamiz (district, sensor_id, threshold, unit)
- Har intent uchun handler funksiyasi rich JSON javob qaytaradi
- Frontend `quick_replies`, `chips`, `cards` ko'rsatadi

Foydalanish:
    from chatbot_engine import answer
    result = answer("Chilonzorda muammo bormi?", df=df)
    # result = {"text": "...", "cards": [...], "quick_replies": [...]}
"""
import re
import unicodedata
from typing import Optional

DISTRICTS = [
    "Bektemir", "Chilonzor", "Mirobod", "Mirzo Ulug'bek", "Olmazor",
    "Sergeli", "Shayxontohur", "Uchtepa", "Yakkasaroy", "Yashnobod",
    "Yunusobod", "Yangihayot",
]

# Normalizatsiya — kirill, ruscha variant, qisqartirgan
DISTRICT_ALIASES = {
    "chilonzor": "Chilonzor", "чиланзар": "Chilonzor", "чилонзор": "Chilonzor",
    "yunusobod": "Yunusobod", "юнусобод": "Yunusobod", "yunus": "Yunusobod",
    "mirobod": "Mirobod", "mirabad": "Mirobod", "мирабад": "Mirobod",
    "mirzo": "Mirzo Ulug'bek", "ulugbek": "Mirzo Ulug'bek", "улугбек": "Mirzo Ulug'bek",
    "olmazor": "Olmazor", "almazar": "Olmazor", "алмазар": "Olmazor",
    "sergeli": "Sergeli", "сергели": "Sergeli",
    "bektemir": "Bektemir", "бектемир": "Bektemir",
    "shayxontohur": "Shayxontohur", "шайхонтохур": "Shayxontohur", "shayh": "Shayxontohur",
    "uchtepa": "Uchtepa", "учтепа": "Uchtepa",
    "yakkasaroy": "Yakkasaroy", "яккасарой": "Yakkasaroy",
    "yashnobod": "Yashnobod", "яшнобод": "Yashnobod",
    "yangihayot": "Yangihayot", "янгиҳаёт": "Yangihayot", "yangi": "Yangihayot",
}

# Intentlar — har biri kalit so'zlar va ball
INTENTS = {
    "voltage_low": [
        ("kuchlanish past", 5), ("past kuchlanish", 5), ("kuchlanish kam", 4),
        ("low voltage", 5), ("kuchlanishi past", 5), ("voltage", 2),
        ("kuchlanish<", 4), ("v dan past", 3), ("v dan kam", 3),
    ],
    "voltage_high": [
        ("kuchlanish yuqori", 5), ("yuqori kuchlanish", 5), ("kuchlanish ko'p", 4),
        ("kuchlanish baland", 4), ("over voltage", 5),
    ],
    "danger_list": [
        ("muammo", 4), ("xavf", 4), ("xavfli", 5), ("danger", 4), ("nosoz", 4),
        ("buzilgan", 4), ("ishlamayotgan", 4), ("fault", 3), ("xato", 3),
        ("crit", 3), ("alert", 3),
    ],
    "warning_list": [
        ("ogohlantirish", 5), ("ogoh", 4), ("warning", 5), ("ehtiyot", 3),
    ],
    "temperature_high": [
        ("harorat yuqori", 5), ("issiq", 4), ("harorat", 3), ("temperature", 3),
        ("hot", 2), ("haroratli", 3), ("qizigan", 4),
    ],
    "frequency": [
        ("chastota", 5), ("frequency", 5), ("hz", 3), ("частота", 4),
    ],
    "sensor_info": [
        ("sensor", 2), ("датчик", 3),
    ],
    "district_info": [
        ("tuman", 3), ("район", 3), ("district", 3),
    ],
    "stats": [
        ("statistika", 5), ("stats", 5), ("umumiy", 4), ("jami", 3),
        ("nechta", 4), ("how many", 4), ("количество", 4),
    ],
    "top_danger": [
        ("eng xavfli", 5), ("top xavf", 4), ("eng yomon", 5), ("worst", 5),
        ("eng past kuchlanish", 5), ("eng yuqori harorat", 5),
    ],
    "weather": [
        ("ob-havo", 5), ("ob havo", 5), ("weather", 5), ("погода", 4),
        ("namlik", 4), ("shamol", 3),
    ],
    "help": [
        ("yordam", 5), ("help", 5), ("nima qila olasan", 5), ("buyruqlar", 4),
        ("commands", 4), ("imkoniyat", 4), ("?", 3),
    ],
    "greeting": [
        ("salom", 5), ("assalom", 5), ("hello", 5), ("hi ", 3), ("hey", 3),
        ("hayrli", 4), ("xayrli", 4), ("привет", 5),
    ],
}


def _normalize(text: str) -> str:
    """Lower + remove diacritics + ' o'/u' ni 'o' ga"""
    text = text.lower().strip()
    # O'zbek apostroflarini olib tashlash
    text = text.replace("'", "").replace("ʻ", "").replace("`", "")
    return text


def detect_intent(question: str) -> tuple[str, float]:
    """Eng ko'p ball olgan intentni qaytaradi."""
    q = _normalize(question)
    scores = {}
    for intent, keywords in INTENTS.items():
        score = 0
        for kw, weight in keywords:
            if kw in q:
                score += weight
        if score > 0:
            scores[intent] = score
    if not scores:
        return ("unknown", 0)
    best = max(scores, key=scores.get)
    return (best, scores[best])


def extract_district(question: str) -> Optional[str]:
    q = _normalize(question)
    for alias, real in DISTRICT_ALIASES.items():
        if alias in q:
            return real
    for d in DISTRICTS:
        if _normalize(d) in q:
            return d
    return None


def extract_sensor_id(question: str) -> Optional[str]:
    m = re.search(r"\bs\d{3,5}\b", question, re.IGNORECASE)
    return m.group(0).upper() if m else None


def extract_number(question: str, default: Optional[float] = None) -> Optional[float]:
    """Birinchi raqamni qaytaradi (210, 220.5, 40 kabi)"""
    m = re.search(r"(\d+(?:\.\d+)?)", question)
    if m:
        return float(m.group(1))
    return default


# ================ INTENT HANDLERS ================

def _handle_voltage_low(df, q):
    threshold = extract_number(q) or 210
    district = extract_district(q)
    rows = df[df["Kuchlanish (V)"] < threshold]
    if district:
        rows = rows[rows["District"] == district]
    title = f"⚡ Kuchlanish {threshold:.0f}V dan past"
    if district:
        title += f" — {district}"
    if rows.empty:
        return {
            "text": f"✅ {title}: bunday sensor topilmadi.",
            "quick_replies": ["Muammoli sensorlar", "Statistika", "Yordam"],
        }
    cards = []
    for _, r in rows.head(8).iterrows():
        cards.append({
            "title": str(r["SensorID"]),
            "subtitle": f"{r['District']} · {r['Kuchlanish (V)']:.1f}V",
            "icon": "bolt",
            "color": "#EF4444" if r['Kuchlanish (V)'] < 190 else "#F59E0B",
            "link": f"/sensor/{r['SensorID']}",
        })
    return {
        "text": f"⚡ **{len(rows)} ta sensor** kuchlanishi {threshold:.0f}V dan past." + (f" ({district})" if district else ""),
        "cards": cards,
        "quick_replies": [f"{int(threshold)+10}V dan past", "Eng yomon 5", "Xavfli sensorlar"],
    }


def _handle_voltage_high(df, q):
    threshold = extract_number(q) or 240
    rows = df[df["Kuchlanish (V)"] > threshold]
    if rows.empty:
        return {"text": f"✅ Kuchlanish {threshold:.0f}V dan yuqori sensor yo'q."}
    cards = [{
        "title": str(r["SensorID"]),
        "subtitle": f"{r['District']} · {r['Kuchlanish (V)']:.1f}V",
        "icon": "bolt", "color": "#EF4444",
        "link": f"/sensor/{r['SensorID']}",
    } for _, r in rows.head(8).iterrows()]
    return {
        "text": f"⚡ **{len(rows)} ta sensor** kuchlanishi {threshold:.0f}V dan yuqori.",
        "cards": cards,
    }


def _handle_danger(df, q):
    district = extract_district(q)
    rows = df[df["Fault"] == 2]
    if district:
        rows = rows[rows["District"] == district]
    if rows.empty:
        msg = f"✅ Hozirda xavfli holatdagi sensor yo'q."
        if district:
            msg = f"✅ {district} tumanida xavfli sensor yo'q."
        return {"text": msg, "quick_replies": ["Statistika", "Ogohlantirishlar"]}
    cards = [{
        "title": str(r["SensorID"]),
        "subtitle": f"{r['District']} · {r['Kuchlanish (V)']:.1f}V · {r['Chastota (Hz)']:.2f}Hz",
        "icon": "triangle-exclamation",
        "color": "#EF4444",
        "link": f"/sensor/{r['SensorID']}",
    } for _, r in rows.head(8).iterrows()]
    return {
        "text": f"🔴 **{len(rows)} ta xavfli sensor**" + (f" ({district})" if district else ""),
        "cards": cards,
        "quick_replies": ["Eng yomon 3", "Statistika", "Xaritada ko'rish"],
    }


def _handle_warning(df, q):
    rows = df[df["Fault"] == 1]
    district = extract_district(q)
    if district:
        rows = rows[rows["District"] == district]
    if rows.empty:
        return {"text": "✅ Ogohlantirilgan sensor yo'q."}
    return {
        "text": f"🟡 **{len(rows)} ta sensor** ogohlantirilgan." + (f" ({district})" if district else ""),
        "cards": [{
            "title": str(r["SensorID"]),
            "subtitle": f"{r['District']} · {r['Kuchlanish (V)']:.1f}V",
            "icon": "exclamation",
            "color": "#F59E0B",
            "link": f"/sensor/{r['SensorID']}",
        } for _, r in rows.head(6).iterrows()],
    }


def _handle_temperature(df, q):
    threshold = extract_number(q) or 40
    rows = df[df["Muhit_harorat (C)"] > threshold]
    if rows.empty:
        return {"text": f"✅ Harorat {threshold:.0f}°C dan yuqori sensor yo'q."}
    return {
        "text": f"🌡️ **{len(rows)} ta sensor** harorati {threshold:.0f}°C dan yuqori.",
        "cards": [{
            "title": str(r["SensorID"]),
            "subtitle": f"{r['District']} · {r['Muhit_harorat (C)']:.1f}°C",
            "icon": "temperature-high",
            "color": "#F97316",
            "link": f"/sensor/{r['SensorID']}",
        } for _, r in rows.head(8).iterrows()],
    }


def _handle_sensor_info(df, q):
    sid = extract_sensor_id(q)
    if not sid:
        return {
            "text": "🔍 Sensor ID kiriting (masalan: `S0001`, `S0123`)",
            "quick_replies": ["Statistika", "Xavfli sensorlar"],
        }
    s = df[df["SensorID"] == sid]
    if s.empty:
        return {"text": f"❌ `{sid}` sensor topilmadi."}
    r = s.iloc[0]
    fault = int(r.get("Fault", 0))
    status_map = {0: ("🟢", "Xavfsiz", "#10B981"), 1: ("🟡", "Ogohlantirish", "#F59E0B"), 2: ("🔴", "Xavfli", "#EF4444")}
    emoji, label, color = status_map.get(fault, ("⚪", "—", "#94A3B8"))
    return {
        "text": (
            f"{emoji} **{sid}** — {r['District']} · *{label}*\n"
            f"⚡ {r['Kuchlanish (V)']:.1f}V · 🔄 {r['Chastota (Hz)']:.2f}Hz · "
            f"🌡️ {r['Muhit_harorat (C)']:.1f}°C · 💧 {r.get('Atrof_muhit_humidity (%)', 0):.0f}%"
        ),
        "cards": [{
            "title": "Batafsil ko'rish",
            "subtitle": f"To'liq tarix · grafiklar · prognoz",
            "icon": "chart-line", "color": color,
            "link": f"/sensor/{sid}",
        }],
    }


def _handle_district(df, q):
    district = extract_district(q)
    if not district:
        return {
            "text": "🏘 Qaysi tuman? Tanlang:",
            "quick_replies": DISTRICTS[:6],
        }
    d = df[df["District"] == district]
    if d.empty:
        return {"text": f"❌ {district} uchun ma'lumot topilmadi."}
    safe = int((d["Fault"] == 0).sum())
    warn = int((d["Fault"] == 1).sum())
    danger = int((d["Fault"] == 2).sum())
    avg_v = d["Kuchlanish (V)"].mean()
    avg_t = d["Muhit_harorat (C)"].mean()
    return {
        "text": (
            f"🏘 **{district}** — {len(d)} sensor\n"
            f"🟢 {safe} · 🟡 {warn} · 🔴 {danger}\n"
            f"⚡ O'rtacha {avg_v:.1f}V · 🌡️ {avg_t:.1f}°C"
        ),
        "cards": ([{
            "title": "Xavfli sensorlar",
            "subtitle": f"{danger} ta sensor xavf ostida",
            "icon": "triangle-exclamation",
            "color": "#EF4444",
            "link": f"/map?district={district}",
        }] if danger > 0 else []),
        "quick_replies": [f"{district} xavflilari", "Boshqa tuman", "Statistika"],
    }


def _handle_stats(df, q):
    total = len(df)
    safe = int((df["Fault"] == 0).sum())
    warn = int((df["Fault"] == 1).sum())
    danger = int((df["Fault"] == 2).sum())
    return {
        "text": (
            f"📊 **Umumiy holat** ({total:,} sensor)\n"
            f"🟢 Xavfsiz: **{safe:,}** ({100*safe//total}%)\n"
            f"🟡 Ogohlantirish: **{warn:,}** ({100*warn//total}%)\n"
            f"🔴 Xavfli: **{danger:,}** ({100*danger//total}%)"
        ),
        "cards": [
            {"title": "Xarita", "subtitle": "Live monitoring", "icon": "map-location-dot",
             "color": "#3B82F6", "link": "/map"},
            {"title": "Grafiklar", "subtitle": "Trend va dinamika", "icon": "chart-line",
             "color": "#06B6D4", "link": "/graphs"},
        ],
        "quick_replies": ["Xavfli sensorlar", "Tumanlar", "Eng yomon 5"],
    }


def _handle_top(df, q):
    """Eng past kuchlanish / eng yuqori harorat."""
    if "harorat" in _normalize(q) or "issiq" in _normalize(q) or "qizigan" in _normalize(q):
        rows = df.nlargest(5, "Muhit_harorat (C)")
        title = "🌡️ Eng issiq 5 sensor"
        cards = [{
            "title": str(r["SensorID"]),
            "subtitle": f"{r['District']} · {r['Muhit_harorat (C)']:.1f}°C",
            "icon": "temperature-high", "color": "#F97316",
            "link": f"/sensor/{r['SensorID']}",
        } for _, r in rows.iterrows()]
    else:
        rows = df.nsmallest(5, "Kuchlanish (V)")
        title = "⚡ Eng past kuchlanishli 5 sensor"
        cards = [{
            "title": str(r["SensorID"]),
            "subtitle": f"{r['District']} · {r['Kuchlanish (V)']:.1f}V",
            "icon": "bolt", "color": "#EF4444",
            "link": f"/sensor/{r['SensorID']}",
        } for _, r in rows.iterrows()]
    return {"text": f"🏆 {title}", "cards": cards}


def _handle_weather(df, q):
    return {
        "text": "🌤 Ob-havo ma'lumotlari uchun bosh sahifaga kiring.",
        "cards": [{
            "title": "Ob-havo paneli",
            "subtitle": "Toshkent · real vaqt",
            "icon": "cloud-sun", "color": "#3B82F6",
            "link": "/",
        }],
    }


def _handle_help(df, q):
    return {
        "text": (
            "🤖 **Men nima qila olaman:**\n"
            "• Kuchlanish past sensorlar (210V, 200V…)\n"
            "• Tuman ma'lumotlari (Chilonzor, Yunusobod…)\n"
            "• Sensor holati (S0123, S1500…)\n"
            "• Eng xavfli / eng issiq sensorlar\n"
            "• Umumiy statistika\n\n"
            "Tabiiy tilda yozavering — tushunaman!"
        ),
        "quick_replies": [
            "Statistika", "Xavfli sensorlar", "Chilonzor", "Eng past kuchlanish",
        ],
    }


def _handle_greeting(df, q):
    import datetime as _dt
    hour = _dt.datetime.now().hour
    if hour < 12:
        greet = "Xayrli tong"
    elif hour < 17:
        greet = "Xayrli kun"
    else:
        greet = "Xayrli kech"
    total = len(df) if df is not None else 0
    return {
        "text": (
            f"👋 {greet}! Men **ElectroGrid AI** yordamchisiman.\n"
            f"Hozirda {total:,} ta sensor monitoring qilinmoqda.\n\n"
            f"_Nima bilan yordam beray?_"
        ),
        "quick_replies": ["Statistika", "Xavfli sensorlar", "Tuman tanlash", "Yordam"],
    }


def _handle_unknown(df, q):
    return {
        "text": (
            "🤔 Tushunmadim. Quyidagilardan birini tanlang yoki boshqacha so'rang:"
        ),
        "quick_replies": [
            "Statistika", "Xavfli sensorlar", "Yordam", "Eng yomon 5",
        ],
    }


HANDLERS = {
    "voltage_low": _handle_voltage_low,
    "voltage_high": _handle_voltage_high,
    "danger_list": _handle_danger,
    "warning_list": _handle_warning,
    "temperature_high": _handle_temperature,
    "frequency": _handle_voltage_low,  # umumiy
    "sensor_info": _handle_sensor_info,
    "district_info": _handle_district,
    "stats": _handle_stats,
    "top_danger": _handle_top,
    "weather": _handle_weather,
    "help": _handle_help,
    "greeting": _handle_greeting,
    "unknown": _handle_unknown,
}


def answer(question: str, df=None) -> dict:
    """Asosiy entry point — chatbot javobi.

    Returns:
        {
          "text": str,            # asosiy javob (markdown)
          "cards": [...],         # ixtiyoriy: kartochkalar
          "quick_replies": [...], # ixtiyoriy: tezkor javob tugmalari
          "intent": str,          # debug uchun
          "confidence": float,
        }
    """
    if df is None or len(df) == 0:
        return {
            "text": "⚠️ Ma'lumotlar yuklanmagan. Iltimos, keyinroq urinib ko'ring.",
            "intent": "no_data", "confidence": 0,
        }

    intent, score = detect_intent(question)

    # Sensor ID yoki tuman aniq topilsa — intentni override qilish
    if not intent or intent == "unknown":
        if extract_sensor_id(question):
            intent = "sensor_info"
        elif extract_district(question):
            intent = "district_info"

    handler = HANDLERS.get(intent, _handle_unknown)
    try:
        result = handler(df, question)
    except Exception as e:
        result = {"text": f"⚠️ Xatolik: {e}"}

    result["intent"] = intent
    result["confidence"] = score
    return result
