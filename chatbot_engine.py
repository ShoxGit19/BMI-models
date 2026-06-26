"""
ElectroGrid AI Chatbot Engine — Professional NLU
=================================================
O'zbek / Kirill / Rus tillarida ishlaydi.
Intent detection + entity extraction + kontekstli javoblar.
"""
from __future__ import annotations
import re
import datetime
from typing import Optional

# ─── KONSTANTALAR ────────────────────────────────────────────────────────────
DISTRICTS = [
    "Bektemir", "Chilonzor", "Mirabad", "Mirobod", "Mirzo Ulug'bek",
    "Olmazor", "Sergeli", "Shayxontohur", "Uchtepa", "Yakkasaroy",
    "Yashnobod", "Yunusobod",
]

DISTRICT_ALIASES: dict[str, str] = {
    # Lotin
    "chilonzor": "Chilonzor", "chilangor": "Chilonzor",
    "yunusobod": "Yunusobod", "yunus": "Yunusobod",
    "mirabad":   "Mirabad",   "mirobod": "Mirobod",
    "mirzo":     "Mirzo Ulug'bek", "ulugbek": "Mirzo Ulug'bek",
    "olmazor":   "Olmazor",   "almazar":  "Olmazor",
    "sergeli":   "Sergeli",
    "bektemir":  "Bektemir",
    "shayxontohur": "Shayxontohur", "shayh": "Shayxontohur",
    "uchtepa":   "Uchtepa",   "uchtepa":  "Uchtepa",
    "yakkasaroy":"Yakkasaroy","yakka":    "Yakkasaroy",
    "yashnobod": "Yashnobod",
    # Kirill
    "чилонзор":  "Chilonzor", "чиланзар": "Chilonzor",
    "юнусобод":  "Yunusobod",
    "мирабад":   "Mirabad",   "миробод":  "Mirobod",
    "мирзо":     "Mirzo Ulug'bek", "улугбек": "Mirzo Ulug'bek",
    "олмазор":   "Olmazor",   "алмазар":  "Olmazor",
    "сергели":   "Sergeli",
    "бектемир":  "Bektemir",
    "шайхонтохур":"Shayxontohur",
    "учтепа":    "Uchtepa",
    "яккасарой": "Yakkasaroy",
    "яшнобод":   "Yashnobod",
}

# Normal chegaralar
LIMITS = {
    "Kuchlanish (V)":          {"ok": (210, 230), "warn": (200, 240)},
    "Chastota (Hz)":           {"ok": (49.5, 50.5), "warn": (49.0, 51.0)},
    "Muhit_harorat (C)":       {"ok": (None, 40), "warn": (None, 45)},
    "Shamol_tezligi (km/h)":   {"ok": (None, 15), "warn": (None, 25)},
    "Vibratsiya":              {"ok": (None, 1.0), "warn": (None, 1.5)},
    "Sim_mexanik_holati (%)":  {"ok": (85, None), "warn": (75, None)},
    "Atrof_muhit_humidity (%)":{"ok": (25, 85),  "warn": (15, 90)},
    "Quvvati (kW)":            {"ok": (None, 5.0), "warn": (None, 5.5)},
}

# ─── INTENT LEKSIKONI ─────────────────────────────────────────────────────────
INTENTS: dict[str, list[tuple[str, int]]] = {
    "greeting": [
        ("salom", 9), ("assalom", 9), ("hello", 8), ("hi ", 7), ("hayrli", 8),
        ("xayrli", 8), ("привет", 9), ("хайрли", 8),
    ],
    "help": [
        ("yordam", 9), ("help", 9), ("nima qila olasan", 9), ("buyruq", 8),
        ("imkoniyat", 8), ("qanday savol", 8), ("nimani bilasan", 8),
        ("nima qilasan", 8), ("commands", 8), ("помощь", 8),
    ],
    "stats": [
        ("statistika", 9), ("umumiy holat", 9), ("jami sensor", 8),
        ("nechta sensor", 8), ("qancha sensor", 8), ("umumiy ko'rsatkich", 8),
        ("общая статистика", 8), ("sensorlar soni", 7), ("hisobot", 6),
    ],
    "danger_list": [
        ("xavfli sensor", 9), ("muammoli sensor", 9), ("nosoz sensor", 9),
        ("buzilgan sensor", 8), ("ishlamayotgan", 8), ("fault", 7),
        ("danger", 8), ("red sensor", 7), ("критические", 8),
        ("аварийные", 8), ("xavf ostida", 8), ("qizil sensor", 7),
    ],
    "warning_list": [
        ("ogohlantirish", 9), ("ogohlantirilgan", 9), ("warning", 8),
        ("sariq sensor", 7), ("ehtiyot", 6), ("предупреждение", 8),
    ],
    "safe_list": [
        ("xavfsiz sensor", 9), ("normal sensor", 8), ("yaxshi sensor", 8),
        ("barqaror sensor", 7), ("yashil sensor", 7), ("safe sensor", 7),
    ],
    "voltage_low": [
        ("kuchlanish past", 9), ("past kuchlanish", 9), ("kuchlanish kam", 8),
        ("low voltage", 9), ("kuchlanishi past", 8), ("v dan past", 8),
        ("200v", 7), ("195v", 7), ("210v", 6), ("kuchlanish tushib", 8),
        ("напряжение низкое", 8), ("низкое напряжение", 8),
    ],
    "voltage_high": [
        ("kuchlanish yuqori", 9), ("yuqori kuchlanish", 9), ("kuchlanish oshib", 8),
        ("over voltage", 8), ("230v dan yuqori", 8), ("напряжение высокое", 8),
    ],
    "voltage_info": [
        ("kuchlanish", 5), ("voltage", 5), ("напряжение", 5),
    ],
    "temperature_high": [
        ("harorat yuqori", 9), ("issiq sensor", 9), ("harorat oshdi", 8),
        ("qizigan sensor", 8), ("40 grad", 7), ("45 grad", 8),
        ("температура высокая", 8),
    ],
    "temperature_info": [
        ("harorat", 5), ("temperatura", 5), ("temperature", 5), ("температура", 5),
    ],
    "vibration_high": [
        ("vibratsiya yuqori", 9), ("kuchli vibratsiya", 9), ("tebranish", 7),
        ("vibratsiya oshib", 8), ("высокая вибрация", 8),
    ],
    "wire_low": [
        ("sim holati past", 9), ("sim yomon", 8), ("kabel holati", 7),
        ("sim mexanik", 7), ("проволока", 6), ("кабель", 6),
    ],
    "humidity_check": [
        ("namlik", 8), ("humidity", 8), ("влажность", 8),
        ("namlik yuqori", 9), ("namlik past", 9),
    ],
    "frequency_check": [
        ("chastota", 8), ("frequency", 8), ("hz", 7), ("частота", 8),
        ("chastota noto'g'ri", 9), ("chastota oshib", 8),
    ],
    "power_check": [
        ("quvvat", 7), ("power", 7), ("мощность", 7), ("quvvat oshib", 9),
    ],
    "sensor_info": [
        ("sensor holati", 8), ("sensor ma'lumot", 8), ("sensor haqida", 8),
        ("датчик", 7),
    ],
    "district_info": [
        ("tuman holati", 8), ("tuman haqida", 8), ("tuman statistika", 8),
        ("район", 7), ("district", 7), ("qaysi tuman", 8),
    ],
    "top_danger": [
        ("eng xavfli", 9), ("top xavf", 8), ("eng yomon", 9),
        ("worst", 8), ("eng muammoli", 8), ("самые опасные", 8),
    ],
    "top_voltage_low": [
        ("eng past kuchlanish", 9), ("kuchlanishi eng past", 9),
        ("minimum kuchlanish", 8),
    ],
    "top_temperature": [
        ("eng issiq", 9), ("harorati eng yuqori", 9), ("самая высокая температура", 8),
    ],
    "recent_faults": [
        ("so'nggi nosozlik", 9), ("oxirgi muammo", 9), ("yangi xavf", 8),
        ("bugungi muammo", 8), ("последние неисправности", 8),
        ("bugun qanday", 7), ("hozir nima", 7),
    ],
    "compare_districts": [
        ("taqqosla", 9), ("solishtir", 9), ("qaysi tuman yaxshi", 8),
        ("qaysi tuman yomon", 8), ("compare district", 8),
    ],
    "averages": [
        ("o'rtacha", 8), ("average", 8), ("средние", 8),
        ("o'rtacha kuchlanish", 9), ("o'rtacha harorat", 9),
    ],
    "forecast_info": [
        ("prognoz", 8), ("bashorat", 8), ("forecast", 8), ("keyingi kun", 7),
        ("prognоз", 8), ("kelajak", 7),
    ],
    "weather": [
        ("ob-havo", 9), ("ob havo", 9), ("weather", 8), ("погода", 8),
        ("havo qanday", 8), ("tashqi muhit", 6),
    ],
    "tickets_info": [
        ("buyurtma", 8), ("ticket", 8), ("ta'mirlash", 7), ("nosozlik bildirish", 9),
        ("ta'mirchi", 7), ("заявка", 8),
    ],
    "map_info": [
        ("xarita", 8), ("map", 8), ("карта", 8), ("qayerda", 7),
        ("joylashuv", 7), ("koordinata", 6),
    ],
}


# ─── YORDAMCHI FUNKSIYALAR ────────────────────────────────────────────────────

def _norm(text: str) -> str:
    """Lotin/Kirill, kichik harf, apostroflarni tozalash."""
    text = text.lower().strip()
    text = text.replace("'", "").replace("ʻ", "").replace("`", "").replace("'", "")
    return text


def detect_intent(q: str) -> tuple[str, int]:
    qn = _norm(q)
    scores: dict[str, int] = {}
    for intent, kws in INTENTS.items():
        s = sum(w for kw, w in kws if _norm(kw) in qn)
        if s > 0:
            scores[intent] = s
    if not scores:
        return "unknown", 0
    best = max(scores, key=scores.get)
    return best, scores[best]


def extract_district(q: str) -> Optional[str]:
    qn = _norm(q)
    for alias, real in DISTRICT_ALIASES.items():
        if alias in qn:
            return real
    for d in DISTRICTS:
        if _norm(d) in qn:
            return d
    return None


def extract_sensor_id(q: str) -> Optional[str]:
    """S001, S0001, S1200 formatlarini topadi va normallashtiradi."""
    m = re.search(r"\b[Ss](\d{1,5})\b", q)
    if not m:
        return None
    num = int(m.group(1))
    # 4 xonali formatga o'tkazish
    return f"S{num:04d}"


def extract_number(q: str, default: Optional[float] = None) -> Optional[float]:
    m = re.search(r"(\d+(?:[.,]\d+)?)", q)
    if m:
        return float(m.group(1).replace(",", "."))
    return default


def _fault_label(f: int) -> tuple[str, str]:
    return {0: ("🟢", "Xavfsiz"), 1: ("🟡", "Ogohlantirish"), 2: ("🔴", "Xavfli")}.get(f, ("⚪", "Noma'lum"))


def _pct(n: int, total: int) -> str:
    return f"{round(100 * n / total)}%" if total > 0 else "0%"


def _latest_ts(df) -> str:
    try:
        return df["Timestamp"].max().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "—"


# ─── INTENT HANDLERLARI ───────────────────────────────────────────────────────

def _h_greeting(df, q: str) -> dict:
    hour = datetime.datetime.now().hour
    greet = "Xayrli tong" if hour < 12 else ("Xayrli kun" if hour < 18 else "Xayrli kech")
    total = len(df) if df is not None else 0
    safe  = int((df["Fault"] == 0).sum()) if df is not None else 0
    danger= int((df["Fault"] == 2).sum()) if df is not None else 0
    return {
        "text": (
            f"👋 {greet}! Men **ElectroGrid AI** yordamchisiman.\n\n"
            f"📡 Hozirda **{total:,} ta sensor** monitoring qilinmoqda:\n"
            f"🟢 {safe:,} xavfsiz · 🔴 {danger:,} xavfli\n\n"
            f"_Nima bilan yordam beray? Tabiiy tilda yozavering._"
        ),
        "quick_replies": ["Statistika", "Xavfli sensorlar", "Tumanlar holati", "Yordam"],
    }


def _h_help(df, q: str) -> dict:
    return {
        "text": (
            "🤖 **ElectroGrid AI — imkoniyatlar:**\n\n"
            "📊 **Statistika va monitoring:**\n"
            "• `Umumiy statistika` — jami holat\n"
            "• `Xavfli sensorlar` — muammoli sensorlar\n"
            "• `So'nggi nosozliklar` — bugungi xavflar\n\n"
            "⚡ **Parametrlar bo'yicha qidiruv:**\n"
            "• `Kuchlanish 210V dan past` — past kuchlanish\n"
            "• `Harorat yuqori sensorlar` — issiq sensorlar\n"
            "• `Vibratsiya yuqori` — tebranish muammosi\n\n"
            "🏘 **Tuman va sensor:**\n"
            "• `Chilonzor holati` — tuman statistikasi\n"
            "• `S0045 holati` — bitta sensor haqida\n"
            "• `Tumanlarni taqqosla` — solishtirish\n\n"
            "📈 **Tahlil:**\n"
            "• `Eng xavfli 5 sensor`\n"
            "• `Eng past kuchlanish`\n"
            "• `O'rtacha ko'rsatkichlar`"
        ),
        "quick_replies": ["Statistika", "Xavfli sensorlar", "Eng past kuchlanish", "Chilonzor"],
    }


def _h_stats(df, q: str) -> dict:
    total  = len(df)
    safe   = int((df["Fault"] == 0).sum())
    warn   = int((df["Fault"] == 1).sum())
    danger = int((df["Fault"] == 2).sum())
    avg_v  = df["Kuchlanish (V)"].mean()
    avg_t  = df["Muhit_harorat (C)"].mean()
    avg_hz = df["Chastota (Hz)"].mean()
    ts     = _latest_ts(df)
    status = "🟢 Barqaror" if safe/_max(total,1) > 0.6 else ("🟡 Ehtiyot" if danger/_max(total,1) < 0.1 else "🔴 Muammolar bor")
    return {
        "text": (
            f"📊 **Umumiy monitoring holati**\n"
            f"🕐 _Yangilangan: {ts}_\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 Jami sensorlar: **{total:,} ta**\n"
            f"🟢 Xavfsiz: **{safe:,}** ({_pct(safe, total)})\n"
            f"🟡 Ogohlantirish: **{warn:,}** ({_pct(warn, total)})\n"
            f"🔴 Xavfli: **{danger:,}** ({_pct(danger, total)})\n\n"
            f"📈 **O'rtacha qiymatlar:**\n"
            f"⚡ Kuchlanish: **{avg_v:.1f}V**\n"
            f"🌡️ Harorat: **{avg_t:.1f}°C**\n"
            f"🔄 Chastota: **{avg_hz:.3f}Hz**\n\n"
            f"📡 Holat: {status}"
        ),
        "cards": [
            {"title": "Xarita", "subtitle": "Barcha sensorlar joylashuvi", "icon": "map-location-dot", "color": "#3B82F6", "link": "/map"},
            {"title": "Grafiklar", "subtitle": "Trend va dinamika", "icon": "chart-line", "color": "#06B6D4", "link": "/graphs"},
            {"title": "Jadval", "subtitle": "Batafsil ma'lumotlar", "icon": "table", "color": "#8B5CF6", "link": "/table"},
        ],
        "quick_replies": ["Xavfli sensorlar", "Tumanlar holati", "Eng past kuchlanish"],
    }


def _max(a, b):
    return a if a > b else b


def _h_danger(df, q: str) -> dict:
    district = extract_district(q)
    rows = df[df["Fault"] == 2].copy()
    if district:
        rows = rows[rows["District"] == district]
    rows = rows.sort_values("Kuchlanish (V)")
    label = f" ({district})" if district else ""
    if rows.empty:
        return {
            "text": f"✅ Hozirda **xavfli sensor yo'q**{label}. Tizim barqaror ishlayapdi.",
            "quick_replies": ["Ogohlantirishlar", "Statistika", "Tumanlar"],
        }
    count = len(rows)
    top = rows.head(8)
    cards = [{
        "title": str(r["SensorID"]),
        "subtitle": f"{r['District']} · ⚡{r['Kuchlanish (V)']:.1f}V · 🌡️{r['Muhit_harorat (C)']:.1f}°C",
        "icon": "circle-exclamation",
        "color": "#EF4444",
        "link": f"/sensor/{r['SensorID']}",
    } for _, r in top.iterrows()]
    more = f"\n_...va yana {count - 8} ta_" if count > 8 else ""
    return {
        "text": (
            f"🔴 **{count} ta xavfli sensor**{label}\n"
            f"Zudlik bilan tekshirilishi shart!{more}"
        ),
        "cards": cards,
        "quick_replies": ["Xaritada ko'rish", "Ogohlantirishlar", "Statistika"],
    }


def _h_warning(df, q: str) -> dict:
    district = extract_district(q)
    rows = df[df["Fault"] == 1].copy()
    if district:
        rows = rows[rows["District"] == district]
    label = f" ({district})" if district else ""
    if rows.empty:
        return {"text": f"✅ Ogohlantirish darajasida sensor yo'q{label}."}
    return {
        "text": f"🟡 **{len(rows)} ta sensor** ogohlantirish bosqichida{label}.\n_Kuzatuv kuchaytirish tavsiya etiladi._",
        "cards": [{
            "title": str(r["SensorID"]),
            "subtitle": f"{r['District']} · ⚡{r['Kuchlanish (V)']:.1f}V",
            "icon": "triangle-exclamation",
            "color": "#F59E0B",
            "link": f"/sensor/{r['SensorID']}",
        } for _, r in rows.head(6).iterrows()],
        "quick_replies": ["Xavfli sensorlar", "Statistika"],
    }


def _h_safe(df, q: str) -> dict:
    district = extract_district(q)
    rows = df[df["Fault"] == 0]
    if district:
        rows = rows[rows["District"] == district]
    label = f" ({district})" if district else ""
    pct = _pct(len(rows), len(df))
    return {
        "text": f"🟢 **{len(rows):,} ta sensor** xavfsiz holatda{label} ({pct}).\n_Tizim barqaror ishlayapdi._",
        "quick_replies": ["Statistika", "Xavfli sensorlar"],
    }


def _h_voltage(df, q: str, mode: str = "low") -> dict:
    district = extract_district(q)
    threshold = extract_number(q) or (210 if mode == "low" else 235)
    col = "Kuchlanish (V)"

    if mode == "low":
        rows = df[df[col] < threshold]
        title = f"kuchlanishi **{threshold:.0f}V dan past**"
        color = "#EF4444"
    else:
        rows = df[df[col] > threshold]
        title = f"kuchlanishi **{threshold:.0f}V dan yuqori**"
        color = "#F97316"

    if district:
        rows = rows[rows["District"] == district]

    label = f" ({district})" if district else ""
    if rows.empty:
        return {
            "text": f"✅ {title} sensor topilmadi{label}.",
            "quick_replies": ["Xavfli sensorlar", "Statistika"],
        }
    rows = rows.sort_values(col, ascending=(mode == "low"))
    cards = [{
        "title": str(r["SensorID"]),
        "subtitle": f"{r['District']} · {r[col]:.1f}V",
        "icon": "bolt",
        "color": color,
        "link": f"/sensor/{r['SensorID']}",
    } for _, r in rows.head(8).iterrows()]
    return {
        "text": f"⚡ **{len(rows)} ta sensor** {title}{label}.",
        "cards": cards,
        "quick_replies": [f"{int(threshold)-5}V dan past", "Eng past kuchlanish", "Statistika"],
    }


def _h_voltage_info(df, q: str) -> dict:
    district = extract_district(q)
    rows = df if not district else df[df["District"] == district]
    label = f" ({district})" if district else ""
    low   = int((rows["Kuchlanish (V)"] < 210).sum())
    norm  = int(((rows["Kuchlanish (V)"] >= 210) & (rows["Kuchlanish (V)"] <= 230)).sum())
    high  = int((rows["Kuchlanish (V)"] > 230).sum())
    avg   = rows["Kuchlanish (V)"].mean()
    mn    = rows["Kuchlanish (V)"].min()
    mx    = rows["Kuchlanish (V)"].max()
    return {
        "text": (
            f"⚡ **Kuchlanish holati**{label}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 O'rtacha: **{avg:.1f}V**\n"
            f"📉 Minimal: **{mn:.1f}V** · 📈 Maksimal: **{mx:.1f}V**\n\n"
            f"🔴 < 210V: **{low} ta** sensor\n"
            f"🟢 210–230V: **{norm} ta** sensor\n"
            f"🟡 > 230V: **{high} ta** sensor"
        ),
        "quick_replies": ["210V dan past sensorlar", "Xavfli sensorlar", "Statistika"],
    }


def _h_temperature(df, q: str) -> dict:
    district = extract_district(q)
    threshold = extract_number(q) or 38
    col = "Muhit_harorat (C)"
    rows = df[df[col] > threshold]
    if district:
        rows = rows[rows["District"] == district]
    label = f" ({district})" if district else ""
    if rows.empty:
        avg = df[col].mean()
        return {
            "text": f"✅ **{threshold:.0f}°C dan yuqori** sensor yo'q{label}.\nO'rtacha harorat: **{avg:.1f}°C**",
            "quick_replies": ["Statistika", "Xavfli sensorlar"],
        }
    rows = rows.sort_values(col, ascending=False)
    return {
        "text": f"🌡️ **{len(rows)} ta sensor** harorati {threshold:.0f}°C dan yuqori{label}.",
        "cards": [{
            "title": str(r["SensorID"]),
            "subtitle": f"{r['District']} · {r[col]:.1f}°C",
            "icon": "temperature-high",
            "color": "#F97316",
            "link": f"/sensor/{r['SensorID']}",
        } for _, r in rows.head(8).iterrows()],
        "quick_replies": ["Xavfli sensorlar", "Statistika"],
    }


def _h_temp_info(df, q: str) -> dict:
    avg = df["Muhit_harorat (C)"].mean()
    mx  = df["Muhit_harorat (C)"].max()
    mn  = df["Muhit_harorat (C)"].min()
    hot = int((df["Muhit_harorat (C)"] > 40).sum())
    return {
        "text": (
            f"🌡️ **Harorat holati**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 O'rtacha: **{avg:.1f}°C**\n"
            f"📈 Maksimal: **{mx:.1f}°C**\n"
            f"📉 Minimal: **{mn:.1f}°C**\n"
            f"🔴 40°C dan yuqori: **{hot} ta** sensor"
        ),
        "quick_replies": ["40 graddan yuqori sensorlar", "Xavfli sensorlar", "Statistika"],
    }


def _h_vibration(df, q: str) -> dict:
    threshold = extract_number(q) or 1.0
    rows = df[df["Vibratsiya"] > threshold].sort_values("Vibratsiya", ascending=False)
    if rows.empty:
        return {"text": f"✅ Vibratsiya {threshold} dan yuqori sensor yo'q. Tizim barqaror."}
    return {
        "text": f"📳 **{len(rows)} ta sensor** vibratsiyasi {threshold} dan yuqori.\n_Mexanik tekshiruv tavsiya etiladi._",
        "cards": [{
            "title": str(r["SensorID"]),
            "subtitle": f"{r['District']} · vibratsiya: {r['Vibratsiya']:.3f}",
            "icon": "wave-square",
            "color": "#8B5CF6",
            "link": f"/sensor/{r['SensorID']}",
        } for _, r in rows.head(8).iterrows()],
        "quick_replies": ["Xavfli sensorlar", "Statistika"],
    }


def _h_wire(df, q: str) -> dict:
    threshold = extract_number(q) or 75
    col = "Sim_mexanik_holati (%)"
    rows = df[df[col] < threshold].sort_values(col)
    if rows.empty:
        avg = df[col].mean()
        return {"text": f"✅ Sim holati {threshold}% dan past sensor yo'q.\nO'rtacha sim holati: **{avg:.1f}%**"}
    return {
        "text": f"🔗 **{len(rows)} ta sensor** sim holati **{threshold}% dan past**.\n_Almashtirish rejasini tuzing._",
        "cards": [{
            "title": str(r["SensorID"]),
            "subtitle": f"{r['District']} · sim holati: {r[col]:.1f}%",
            "icon": "link-slash",
            "color": "#EF4444",
            "link": f"/sensor/{r['SensorID']}",
        } for _, r in rows.head(8).iterrows()],
        "quick_replies": ["Xavfli sensorlar", "Statistika"],
    }


def _h_humidity(df, q: str) -> dict:
    avg = df["Atrof_muhit_humidity (%)"].mean()
    high = int((df["Atrof_muhit_humidity (%)"] > 85).sum())
    low  = int((df["Atrof_muhit_humidity (%)"] < 20).sum())
    district = extract_district(q)
    rows = df if not district else df[df["District"] == district]
    label = f" ({district})" if district else ""
    return {
        "text": (
            f"💧 **Namlik holati**{label}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 O'rtacha namlik: **{rows['Atrof_muhit_humidity (%)'].mean():.1f}%**\n"
            f"🔴 > 85% (yuqori): **{high} ta** sensor\n"
            f"🔴 < 20% (past): **{low} ta** sensor\n\n"
            f"_Normal chegara: 25–85%_"
        ),
        "quick_replies": ["Xavfli sensorlar", "Statistika"],
    }


def _h_frequency(df, q: str) -> dict:
    col = "Chastota (Hz)"
    ok   = int(((df[col] >= 49.5) & (df[col] <= 50.5)).sum())
    bad  = int(((df[col] < 49.0) | (df[col] > 51.0)).sum())
    warn = int(((df[col] >= 49.0) & (df[col] < 49.5)).sum()) + int(((df[col] > 50.5) & (df[col] <= 51.0)).sum())
    avg  = df[col].mean()
    problem_rows = df[(df[col] < 49.0) | (df[col] > 51.0)].head(5)
    cards = [{
        "title": str(r["SensorID"]),
        "subtitle": f"{r['District']} · {r[col]:.3f}Hz",
        "icon": "wave-square",
        "color": "#EF4444",
        "link": f"/sensor/{r['SensorID']}",
    } for _, r in problem_rows.iterrows()]
    return {
        "text": (
            f"🔄 **Chastota holati**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 O'rtacha: **{avg:.4f}Hz**\n"
            f"🟢 Normal (49.5–50.5): **{ok:,} ta**\n"
            f"🟡 Ehtiyot (49.0–49.5 / 50.5–51.0): **{warn} ta**\n"
            f"🔴 Xavfli (< 49 / > 51): **{bad} ta**"
        ),
        "cards": cards if cards else [],
        "quick_replies": ["Xavfli sensorlar", "Statistika"],
    }


def _h_power(df, q: str) -> dict:
    col = "Quvvati (kW)"
    high = df[df[col] > 5.5].sort_values(col, ascending=False).head(6)
    avg  = df[col].mean()
    total_mw = df[col].sum() / 1000
    if high.empty:
        return {
            "text": (
                f"⚙️ **Quvvat holati**\n"
                f"O'rtacha quvvat: **{avg:.2f}kW**\n"
                f"Jami uzatilayotgan: **{total_mw:.1f}MW**\n"
                f"✅ 5.5kW dan oshgan sensor yo'q."
            ),
        }
    return {
        "text": (
            f"⚙️ **Quvvat holati**\n"
            f"O'rtacha: **{avg:.2f}kW** · Jami: **{total_mw:.1f}MW**\n"
            f"🔴 5.5kW dan oshgan: **{len(high)} ta sensor**"
        ),
        "cards": [{
            "title": str(r["SensorID"]),
            "subtitle": f"{r['District']} · {r[col]:.2f}kW",
            "icon": "bolt",
            "color": "#F97316",
            "link": f"/sensor/{r['SensorID']}",
        } for _, r in high.iterrows()],
        "quick_replies": ["Statistika", "Xavfli sensorlar"],
    }


def _h_sensor_info(df, q: str) -> dict:
    sid = extract_sensor_id(q)
    if not sid:
        return {
            "text": "🔍 **Sensor ID** kiriting:\n_Masalan: `S0001`, `S0123`, `S1200`_",
            "quick_replies": ["Xavfli sensorlar", "Statistika"],
        }
    rows = df[df["SensorID"] == sid]
    if rows.empty:
        # Yaqin IDni qidiramiz
        try:
            num = int(re.search(r"\d+", sid).group())
            for delta in [1, -1, 2, -2, 5]:
                alt = f"S{num+delta:04d}"
                if not df[df["SensorID"] == alt].empty:
                    return {"text": f"❌ `{sid}` topilmadi. Yaqin ID: **{alt}**? \nUni ko'rish uchun yozing: `{alt} holati`"}
        except Exception:
            pass
        return {"text": f"❌ `{sid}` sensor topilmadi. ID to'g'ri ekanini tekshiring (S0001–S1200)."}
    r = rows.iloc[0]
    fault = int(r.get("Fault", 0))
    icon, lbl = _fault_label(fault)
    v    = float(r.get("Kuchlanish (V)", 0))
    hz   = float(r.get("Chastota (Hz)", 50))
    t    = float(r.get("Muhit_harorat (C)", 0))
    hum  = float(r.get("Atrof_muhit_humidity (%)", 0))
    vib  = float(r.get("Vibratsiya", 0))
    sim  = float(r.get("Sim_mexanik_holati (%)", 0))
    kw   = float(r.get("Quvvati (kW)", 0))
    ts   = str(r.get("Timestamp", ""))[:16]

    # Har bir parametrga baho
    def _v_icon(val, col_):
        lim = LIMITS.get(col_, {})
        ok, warn = lim.get("ok", (None, None)), lim.get("warn", (None, None))
        lo_ok, hi_ok = (ok[0], ok[1]) if ok else (None, None)
        lo_w, hi_w   = (warn[0], warn[1]) if warn else (None, None)
        if (lo_ok and val < lo_ok) or (hi_ok and val > hi_ok):
            if (lo_w and val < lo_w) or (hi_w and val > hi_w):
                return "🔴"
            return "🟡"
        return "🟢"

    return {
        "text": (
            f"{icon} **{sid}** — {r.get('District','?')} · _{lbl}_\n"
            f"🕐 _Oxirgi yangilanish: {ts}_\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{_v_icon(v,'Kuchlanish (V)')} Kuchlanish: **{v:.1f}V**\n"
            f"{_v_icon(hz,'Chastota (Hz)')} Chastota: **{hz:.3f}Hz**\n"
            f"{_v_icon(t,'Muhit_harorat (C)')} Harorat: **{t:.1f}°C**\n"
            f"{_v_icon(hum,'Atrof_muhit_humidity (%)')} Namlik: **{hum:.0f}%**\n"
            f"{_v_icon(vib,'Vibratsiya')} Vibratsiya: **{vib:.3f}**\n"
            f"{_v_icon(sim,'Sim_mexanik_holati (%)')} Sim holati: **{sim:.1f}%**\n"
            f"⚙️ Quvvat: **{kw:.2f}kW**"
        ),
        "cards": [{
            "title": f"{sid} — Batafsil",
            "subtitle": "Tarixiy grafik · prognoz · tahlil",
            "icon": "chart-line",
            "color": "#3B82F6",
            "link": f"/sensor/{sid}",
        }],
        "quick_replies": [f"{sid} grafigi", "Xavfli sensorlar", "Statistika"],
    }


def _h_district(df, q: str) -> dict:
    district = extract_district(q)
    if not district:
        # Barcha tumanlar ro'yxati
        rows = df.groupby("District").agg(
            jami=("SensorID", "count"),
            xavf=("Fault", lambda x: int((x == 2).sum())),
            ogoh=("Fault", lambda x: int((x == 1).sum())),
        ).reset_index().sort_values("xavf", ascending=False)
        lines = []
        for _, r in rows.iterrows():
            icon = "🔴" if r["xavf"] > 0 else ("🟡" if r["ogoh"] > 0 else "🟢")
            lines.append(f"{icon} **{r['District']}** — {r['jami']} sensor")
            if r["xavf"] > 0:
                lines[-1] += f" · 🔴{r['xavf']}"
        return {
            "text": "🏘 **Tumanlar holati:**\n\n" + "\n".join(lines),
            "quick_replies": ["Chilonzor", "Yunusobod", "Mirzo Ulug'bek", "Statistika"],
        }

    d = df[df["District"] == district]
    if d.empty:
        return {"text": f"❌ **{district}** uchun ma'lumot topilmadi."}
    total  = len(d)
    safe   = int((d["Fault"] == 0).sum())
    warn   = int((d["Fault"] == 1).sum())
    danger = int((d["Fault"] == 2).sum())
    avg_v  = d["Kuchlanish (V)"].mean()
    avg_t  = d["Muhit_harorat (C)"].mean()
    status = "🔴 Muammolar bor" if danger > 0 else ("🟡 Kuzatuv kerak" if warn > 0 else "🟢 Barqaror")
    cards = []
    if danger > 0:
        cards.append({
            "title": f"🔴 {danger} xavfli sensor",
            "subtitle": f"{district} — darhol tekshirish kerak",
            "icon": "circle-exclamation",
            "color": "#EF4444",
            "link": f"/map?district={district}",
        })
    return {
        "text": (
            f"🏘 **{district}** · {status}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 Jami: **{total}** sensor\n"
            f"🟢 Xavfsiz: **{safe}** · 🟡 Ogoh: **{warn}** · 🔴 Xavfli: **{danger}**\n\n"
            f"⚡ O'rtacha kuchlanish: **{avg_v:.1f}V**\n"
            f"🌡️ O'rtacha harorat: **{avg_t:.1f}°C**"
        ),
        "cards": cards,
        "quick_replies": [f"{district} xavflilari", "Boshqa tuman", "Statistika"],
    }


def _h_compare(df, q: str) -> dict:
    return {
        "text": (
            "📊 **Tumanlarni taqqoslash:**\n\n"
            "Quyidagi sahifada ikki tumanni side-by-side solishtiring:"
        ),
        "cards": [{
            "title": "Taqqoslash paneli",
            "subtitle": "Ikki tuman yoki sensorno solishtiring",
            "icon": "code-compare",
            "color": "#3B82F6",
            "link": "/compare",
        }],
        "quick_replies": DISTRICTS[:4],
    }


def _h_top(df, q: str) -> dict:
    qn = _norm(q)
    if "harorat" in qn or "issiq" in qn:
        rows = df.nlargest(5, "Muhit_harorat (C)")
        title, col, unit, icon = "🌡️ Eng issiq 5 sensor", "Muhit_harorat (C)", "°C", "temperature-high"
    elif "vibratsiya" in qn or "tebranish" in qn:
        rows = df.nlargest(5, "Vibratsiya")
        title, col, unit, icon = "📳 Eng yuqori vibratsiya", "Vibratsiya", "", "wave-square"
    elif "namlik" in qn:
        rows = df.nlargest(5, "Atrof_muhit_humidity (%)")
        title, col, unit, icon = "💧 Eng yuqori namlik", "Atrof_muhit_humidity (%)", "%", "droplet"
    else:
        rows = df.nsmallest(5, "Kuchlanish (V)")
        title, col, unit, icon = "⚡ Eng past kuchlanishli 5 sensor", "Kuchlanish (V)", "V", "bolt"

    return {
        "text": f"🏆 **{title}**",
        "cards": [{
            "title": str(r["SensorID"]),
            "subtitle": f"{r['District']} · {r[col]:.2f}{unit}",
            "icon": icon,
            "color": "#EF4444",
            "link": f"/sensor/{r['SensorID']}",
        } for _, r in rows.iterrows()],
        "quick_replies": ["Eng issiq sensorlar", "Eng past kuchlanish", "Xavfli sensorlar"],
    }


def _h_recent(df, q: str) -> dict:
    """So'nggi 24 soatdagi nosozliklar."""
    try:
        cutoff = df["Timestamp"].max() - __import__("pandas").Timedelta(hours=24)
        recent = df[df["Timestamp"] >= cutoff]
        danger = recent[recent["Fault"] == 2]
        warn   = recent[recent["Fault"] == 1]
        ts     = df["Timestamp"].max().strftime("%Y-%m-%d %H:%M")
        text = (
            f"🕐 **So'nggi 24 soat**\n"
            f"_Yangigi ma'lumot: {ts}_\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 Tekshirilgan: **{len(recent):,} ta yozuv**\n"
            f"🔴 Xavfli hodisalar: **{len(danger)} ta**\n"
            f"🟡 Ogohlantirishlar: **{len(warn)} ta**"
        )
        cards = [{
            "title": str(r["SensorID"]),
            "subtitle": f"{r['District']} · {str(r['Timestamp'])[:16]}",
            "icon": "circle-exclamation",
            "color": "#EF4444",
            "link": f"/sensor/{r['SensorID']}",
        } for _, r in danger.head(5).iterrows()]
        return {
            "text": text,
            "cards": cards,
            "quick_replies": ["Xavfli sensorlar", "Statistika", "Xaritada ko'rish"],
        }
    except Exception:
        return _h_stats(df, q)


def _h_averages(df, q: str) -> dict:
    district = extract_district(q)
    rows = df if not district else df[df["District"] == district]
    label = f" ({district})" if district else ""
    return {
        "text": (
            f"📈 **O'rtacha ko'rsatkichlar**{label}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Kuchlanish: **{rows['Kuchlanish (V)'].mean():.1f}V**\n"
            f"🔄 Chastota: **{rows['Chastota (Hz)'].mean():.4f}Hz**\n"
            f"🌡️ Harorat: **{rows['Muhit_harorat (C)'].mean():.1f}°C**\n"
            f"📳 Vibratsiya: **{rows['Vibratsiya'].mean():.3f}**\n"
            f"🔗 Sim holati: **{rows['Sim_mexanik_holati (%)'].mean():.1f}%**\n"
            f"💧 Namlik: **{rows['Atrof_muhit_humidity (%)'].mean():.1f}%**\n"
            f"⚙️ Quvvat: **{rows['Quvvati (kW)'].mean():.2f}kW**"
        ),
        "quick_replies": ["Xavfli sensorlar", "Statistika", "Tumanlar holati"],
    }


def _h_forecast(df, q: str) -> dict:
    return {
        "text": "📊 **7 kunlik kelajak prognozi** sahifasiga o'ting:",
        "cards": [{
            "title": "Kelajak Prognozi",
            "subtitle": "Keyingi 7 kun xavf va parametrlar bashorati",
            "icon": "chart-area",
            "color": "#06B6D4",
            "link": "/forecast",
        }],
        "quick_replies": ["Statistika", "Xavfli sensorlar"],
    }


def _h_weather(df, q: str) -> dict:
    return {
        "text": "🌤️ **Ob-havo ma'lumoti** bosh sahifada (yuqori o'ng burchak) ko'rsatiladi.\nHozirgi Toshkent ob-havosi real vaqtda yangilanadi.",
        "cards": [{"title": "Bosh sahifa", "subtitle": "Real vaqt ob-havo widget", "icon": "cloud-sun", "color": "#3B82F6", "link": "/"}],
        "quick_replies": ["Statistika", "Prognoz"],
    }


def _h_tickets(df, q: str) -> dict:
    return {
        "text": "🛠️ **Ta'mirlash buyurtmalari:**",
        "cards": [{
            "title": "Buyurtmalar sahifasi",
            "subtitle": "Faol, jarayondagi va yopilgan buyurtmalar",
            "icon": "tools",
            "color": "#F59E0B",
            "link": "/tickets",
        }],
        "quick_replies": ["Xavfli sensorlar", "Statistika"],
    }


def _h_map(df, q: str) -> dict:
    district = extract_district(q)
    link = f"/map?district={district}" if district else "/map"
    return {
        "text": f"🗺️ **Sensorlar xaritasi**{' — '+district if district else ''}",
        "cards": [{
            "title": "Xarita",
            "subtitle": "1200 sensor · rang kodlangan holat",
            "icon": "map-location-dot",
            "color": "#10B981",
            "link": link,
        }],
        "quick_replies": ["Xavfli sensorlar", "Statistika"],
    }


def _h_unknown(df, q: str) -> dict:
    # Sensor ID yoki tuman bor-yo'qligini oxirgi marta tekshiramiz
    sid = extract_sensor_id(q)
    if sid:
        return _h_sensor_info(df, q)
    district = extract_district(q)
    if district:
        return _h_district(df, q)
    return {
        "text": (
            "🤔 Savolingizni tushunmadim. Quyidagilardan birini sinab ko'ring:"
        ),
        "quick_replies": ["Statistika", "Xavfli sensorlar", "Tumanlar holati", "Yordam"],
    }


# ─── DISPATCHER ───────────────────────────────────────────────────────────────

_HANDLERS = {
    "greeting":         _h_greeting,
    "help":             _h_help,
    "stats":            _h_stats,
    "danger_list":      _h_danger,
    "warning_list":     _h_warning,
    "safe_list":        _h_safe,
    "voltage_low":      lambda df, q: _h_voltage(df, q, "low"),
    "voltage_high":     lambda df, q: _h_voltage(df, q, "high"),
    "voltage_info":     _h_voltage_info,
    "temperature_high": _h_temperature,
    "temperature_info": _h_temp_info,
    "vibration_high":   _h_vibration,
    "wire_low":         _h_wire,
    "humidity_check":   _h_humidity,
    "frequency_check":  _h_frequency,
    "power_check":      _h_power,
    "sensor_info":      _h_sensor_info,
    "district_info":    _h_district,
    "compare_districts":_h_compare,
    "top_danger":       _h_top,
    "top_voltage_low":  _h_top,
    "top_temperature":  _h_top,
    "recent_faults":    _h_recent,
    "averages":         _h_averages,
    "forecast_info":    _h_forecast,
    "weather":          _h_weather,
    "tickets_info":     _h_tickets,
    "map_info":         _h_map,
    "unknown":          _h_unknown,
}


def answer(question: str, df=None) -> dict:
    """
    Asosiy entry point.
    Returns: {"text", "cards"?, "quick_replies"?, "intent", "confidence"}
    """
    if df is None or len(df) == 0:
        return {
            "text": "⚠️ Ma'lumotlar yuklanmagan. Iltimos, keyinroq urinib ko'ring.",
            "intent": "no_data",
            "confidence": 0,
        }

    intent, score = detect_intent(question)
    qn = _norm(question)

    # ── District + muammo/xavf → danger_list ──
    has_district = bool(extract_district(question))
    if has_district:
        danger_kw = ("muammo", "xavf", "nosoz", "buzil", "fault", "danger", "yomon")
        warn_kw   = ("ogohlantirish", "ogoh", "warning", "ehtiyot")
        if any(k in qn for k in danger_kw):
            intent = "danger_list"
        elif any(k in qn for k in warn_kw):
            intent = "warning_list"
        elif intent in ("greeting", "unknown") or score < 5:
            intent = "district_info"

    # ── Sensor ID aniq topilsa ──
    if extract_sensor_id(question):
        if intent in ("greeting", "unknown") or score < 5:
            intent = "sensor_info"

    handler = _HANDLERS.get(intent, _h_unknown)
    try:
        result = handler(df, question)
    except Exception as e:
        result = {
            "text": f"⚠️ Xatolik yuz berdi. Savol boshqacha berib ko'ring.",
            "quick_replies": ["Statistika", "Yordam"],
        }

    result["intent"]     = intent
    result["confidence"] = score
    return result
