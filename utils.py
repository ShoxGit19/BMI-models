# ======================== UTILS ========================
# Markaziy yordamchi funksiyalar — app.py va telegram_bot.py uchun umumiy
# =========================================================

import os
import json
import math
import hashlib
import string
import secrets
import datetime
import logging

logger = logging.getLogger("bmi-utils")

# ======================== CONSTANTS ========================
USERS_FILE = "users.json"
SUBSCRIBERS_FILE = "subscribers.json"

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

# Har bir tuman uchun GPS chegaralari (min_lat, max_lat, min_lon, max_lon)
DISTRICT_BOUNDS = {
    "Bektemir":        (41.2000, 41.2500, 69.3100, 69.3950),
    "Chilonzor":       (41.2400, 41.3280, 69.1400, 69.2220),
    "Mirabad":         (41.2550, 41.2980, 69.2050, 69.2620),
    "Mirobod":         (41.2700, 41.3140, 69.2400, 69.2950),
    "Mirzo Ulug'bek":  (41.3050, 41.3950, 69.3200, 69.3950),
    "Olmazor":         (41.3300, 41.3950, 69.2150, 69.2800),
    "Sergeli":         (41.1700, 41.2600, 69.2450, 69.3380),
    "Shayxontohur":    (41.2850, 41.3350, 69.2430, 69.3020),
    "Uchtepa":         (41.2850, 41.3650, 69.1480, 69.2250),
    "Yakkasaroy":      (41.2700, 41.3100, 69.1980, 69.2420),
    "Yashnobod":       (41.2150, 41.2750, 69.2750, 69.3500),
    "Yunusobod":       (41.3180, 41.3920, 69.2880, 69.3700),
}

FEATURE_COLS = [
    "Muhit_harorat (C)", "Shamol_tezligi (km/h)", "Chastota (Hz)", "Kuchlanish (V)",
    "Vibratsiya", "Sim_mexanik_holati (%)", "Atrof_muhit_humidity (%)", "Quvvati (kW)"
]

ROLES = {"admin", "user"}


# ======================== HAVERSINE ========================
def haversine(lat1, lon1, lat2, lon2):
    """Ikki GPS koordinata orasidagi masofani km da qaytaradi."""
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ======================== SENSOR GPS (MD5 SEEDING) ========================
def generate_sensor_coords(sensor_id, district):
    """SensorID va tuman asosida MD5 seed bilan qat'iy va takrorlanmas koordinata."""
    bounds = DISTRICT_BOUNDS.get(district)
    if not bounds:
        # Fallback: Toshkent markazi atrofida
        bounds = (41.2500, 41.3500, 69.2000, 69.3500)

    min_lat, max_lat, min_lon, max_lon = bounds
    seed = hashlib.md5(f"{sensor_id}:{district}".encode()).hexdigest()

    # MD5 dan ikkita 0-1 oralig'idagi float olish
    lat_frac = int(seed[:8], 16) / 0xFFFFFFFF
    lon_frac = int(seed[8:16], 16) / 0xFFFFFFFF

    lat = min_lat + lat_frac * (max_lat - min_lat)
    lon = min_lon + lon_frac * (max_lon - min_lon)
    return round(lat, 6), round(lon, 6)


def find_nearest_sensors(user_lat, user_lon, sensor_data, n=5):
    """Foydalanuvchi GPS ga eng yaqin n ta sensorni topadi.
    sensor_data: list of dict with keys SensorID, Latitude, Longitude, ...
    """
    results = []
    for s in sensor_data:
        try:
            slat = float(s.get("Latitude", 0))
            slon = float(s.get("Longitude", 0))
            dist = haversine(user_lat, user_lon, slat, slon)
            results.append({**s, "_distance_km": round(dist, 3)})
        except (ValueError, TypeError):
            continue
    results.sort(key=lambda x: x["_distance_km"])
    return results[:n]


# ======================== USER MANAGEMENT ========================
def load_users():
    """users.json dan barcha foydalanuvchilarni o'qish."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_users(users_list):
    """users.json ga yozish."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_list, f, ensure_ascii=False, indent=2)


def get_user_by_id(user_id):
    """Telegram user_id bo'yicha foydalanuvchini topish."""
    for u in load_users():
        if u.get("id") == user_id:
            return u
    return None


def get_user_by_phone(phone):
    """Telefon raqami bo'yicha foydalanuvchini topish (login uchun)."""
    phone = phone.strip()
    for u in load_users():
        if u.get("phone", "").strip() == phone:
            return u
    return None


def update_user(user_id, **kwargs):
    """Foydalanuvchi ma'lumotlarini yangilash."""
    users = load_users()
    for u in users:
        if u.get("id") == user_id:
            u.update(kwargs)
            save_users(users)
            return True
    return False


def is_registration_complete(user_data):
    """Ro'yxatdan to'liq o'tganligini tekshirish."""
    if not user_data:
        return False
    required = ["phone", "first_name", "last_name", "district"]
    return all(user_data.get(k) for k in required)


# ======================== PASSWORD MANAGEMENT ========================
def generate_password(length=8):
    """Tasodifiy xavfsiz parol yaratish."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_password(password):
    """Parolni SHA256 bilan hashlash (LEGACY — eski user fayllar uchun saqlanadi)."""
    return hashlib.sha256(password.encode()).hexdigest()


# === bcrypt asosli xavfsiz parol hashlash (yangi standart) ===
try:
    import bcrypt as _bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False


def hash_password_secure(password):
    """bcrypt bilan xavfsiz hash (salt + 12 round). Brute-force ga 10000× chidamli."""
    if not _HAS_BCRYPT:
        return hash_password(password)
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(rounds=12)).decode()


def verify_password(password, stored_hash):
    """Eski SHA256 va yangi bcrypt'ni qo'llab-quvvatlaydi."""
    if not stored_hash:
        return False
    # bcrypt hashlar $2b$ yoki $2a$ bilan boshlanadi
    if _HAS_BCRYPT and stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return _bcrypt.checkpw(password.encode(), stored_hash.encode())
        except Exception:
            return False
    # Eski SHA256
    return hashlib.sha256(password.encode()).hexdigest() == stored_hash


def needs_rehash(stored_hash):
    """True bo'lsa — login muvaffaqiyatli bo'lsa hash ni yangilash kerak."""
    if not _HAS_BCRYPT:
        return False
    return not stored_hash.startswith(("$2a$", "$2b$", "$2y$"))


def create_user_credentials(user_id):
    """Foydalanuvchi uchun login (telefon) va parol yaratish.
    Returns: (login, raw_password) yoki (None, None) agar foydalanuvchi topilmasa.
    """
    user = get_user_by_id(user_id)
    if not user or not user.get("phone"):
        return None, None

    raw_password = generate_password(8)
    pw_hash = hash_password(raw_password)
    login_name = user["phone"]  # Telefon = login

    update_user(user_id, web_password_hash=pw_hash, role="user")
    return login_name, raw_password


def verify_web_login(login_name, password):
    """Web login tekshirish. Login = telefon raqami.
    Returns: user dict yoki None.
    """
    pw_hash = hash_password(password)
    user = get_user_by_phone(login_name)
    if user and user.get("web_password_hash") == pw_hash:
        return user
    return None


def get_web_users_dict():
    """Flask USERS dict yaratish — {login: pw_hash} formatida.
    Admin va operator ham qo'shiladi.
    """
    users_dict = {
        "admin": hash_password("admin123"),
        "operator": hash_password("operator123"),
    }
    for u in load_users():
        phone = u.get("phone", "").strip()
        pw_hash = u.get("web_password_hash")
        if phone and pw_hash:
            users_dict[phone] = pw_hash
    return users_dict


def get_user_role(login_name):
    """Foydalanuvchi rolini aniqlash."""
    if login_name == "admin":
        return "admin"
    if login_name == "operator":
        return "admin"
    user = get_user_by_phone(login_name)
    if user:
        return user.get("role", "user")
    return "user"


def get_user_district(login_name):
    """Foydalanuvchining tumanini olish."""
    user = get_user_by_phone(login_name)
    if user:
        return user.get("district", "")
    return ""


def get_user_location(login_name):
    """Foydalanuvchining GPS koordinatalarini olish."""
    user = get_user_by_phone(login_name)
    if user:
        lat = user.get("latitude")
        lon = user.get("longitude")
        if lat and lon:
            return float(lat), float(lon)
    return None, None


# ======================== SUBSCRIBERS ========================
def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(subs), f, ensure_ascii=False, indent=2)


# ======================== AUDIT LOG ========================
AUDIT_LOG_FILE = "logs/audit.json"


def audit_log(action, user=None, ip=None, details=None):
    """Tizim jurnali — har bir muhim amalni qayd etish."""
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "user": user or "system",
        "action": action,
        "ip": ip,
        "details": details or {}
    }
    try:
        os.makedirs("logs", exist_ok=True)
        existing = []
        if os.path.exists(AUDIT_LOG_FILE):
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        existing.append(entry)
        existing = existing[-5000:]
        with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Audit log xatosi: {e}")


# ======================== TOKEN ========================
def read_bot_token(path="bot_token.txt"):
    """Bot tokenini fayldan o'qish."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


# ======================== TICKETS / MAINTENANCE ========================
TICKETS_FILE = "data/tickets.json"
ALERT_STATE_FILE = "data/alert_state.json"
INCIDENTS_FILE = "data/incidents.json"


def detect_fault_type(sensor_row):
    """Sensor qiymatlariga qarab avariya turini aniqlash."""
    try:
        v = float(sensor_row.get("Kuchlanish (V)", 220))
        f = float(sensor_row.get("Chastota (Hz)", 50))
        vib = float(sensor_row.get("Vibratsiya", 0))
        sim = float(sensor_row.get("Sim_mexanik_holati (%)", 100))
        t = float(sensor_row.get("Muhit_harorat (C)", 25))
    except Exception:
        return "Noma'lum nosozlik"
    reasons = []
    if v < 170: reasons.append(f"⚡ Kuchlanish kritik past ({v:.0f}V)")
    elif v > 250: reasons.append(f"⚡ Kuchlanish kritik yuqori ({v:.0f}V)")
    elif v < 200: reasons.append(f"⚡ Kuchlanish past ({v:.0f}V)")
    elif v > 240: reasons.append(f"⚡ Kuchlanish yuqori ({v:.0f}V)")
    if f < 49.5 or f > 50.5: reasons.append(f"🔄 Chastota og'ishgan ({f:.2f}Hz)")
    if vib > 5: reasons.append(f"📳 Vibratsiya yuqori ({vib:.1f})")
    if sim < 60: reasons.append(f"🪛 Sim mexanik buzilishi ({sim:.0f}%)")
    if t < -10 or t > 45: reasons.append(f"🌡 Harorat ekstremal ({t:.0f}°C)")
    if not reasons:
        return "🔴 Avariya holati"
    return " · ".join(reasons)


def load_incidents():
    if os.path.exists(INCIDENTS_FILE):
        try:
            with open(INCIDENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_incidents(items):
    os.makedirs("data", exist_ok=True)
    with open(INCIDENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def create_incident(sensor_id, district, fault_type, lat, lon, voltage, notified_users=None):
    """Yangi avariya yozuvini saqlash. Web dashboard va resolve uchun."""
    items = load_incidents()
    inc_id = f"INC-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    inc = {
        "id": inc_id,
        "sensor_id": str(sensor_id),
        "district": district,
        "fault_type": fault_type,
        "lat": lat,
        "lon": lon,
        "voltage": voltage,
        "status": "active",
        "created_at": datetime.datetime.now().isoformat(),
        "resolved_at": None,
        "notified_users": notified_users or []
    }
    items.append(inc)
    save_incidents(items)
    return inc


def get_incident(inc_id):
    for inc in load_incidents():
        if inc.get("id") == inc_id:
            return inc
    return None


def resolve_incident(inc_id):
    items = load_incidents()
    for inc in items:
        if inc.get("id") == inc_id and inc.get("status") == "active":
            inc["status"] = "resolved"
            inc["resolved_at"] = datetime.datetime.now().isoformat()
            save_incidents(items)
            return inc
    return None


def get_active_incidents():
    return [i for i in load_incidents() if i.get("status") == "active"]


def load_tickets():
    if os.path.exists(TICKETS_FILE):
        try:
            with open(TICKETS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_tickets(tickets):
    os.makedirs("data", exist_ok=True)
    with open(TICKETS_FILE, "w", encoding="utf-8") as f:
        json.dump(tickets, f, ensure_ascii=False, indent=2, default=str)


def get_active_ticket(sensor_id):
    """Sensor uchun ochiq ticket bor-yo'qligini tekshirish."""
    sensor_id = str(sensor_id)
    for t in load_tickets():
        if str(t.get("sensor_id")) == sensor_id and t.get("status") in ("open", "in_progress"):
            return t
    return None


def create_ticket(sensor_id, issue, eta=None, created_by="admin"):
    """Yangi ta'mirlash buyurtmasi yaratish."""
    tickets = load_tickets()
    ticket = {
        "id": f"T-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "sensor_id": str(sensor_id),
        "issue": issue,
        "status": "in_progress",
        "eta": eta,
        "created_at": datetime.datetime.now().isoformat(),
        "created_by": created_by,
        "closed_at": None
    }
    tickets.append(ticket)
    save_tickets(tickets)
    return ticket


def close_ticket(ticket_id):
    tickets = load_tickets()
    for t in tickets:
        if t.get("id") == ticket_id:
            t["status"] = "closed"
            t["closed_at"] = datetime.datetime.now().isoformat()
            save_tickets(tickets)
            return t
    return None


# ======================== ALERT STATE (per-user dedup) ========================
def load_alert_state():
    if os.path.exists(ALERT_STATE_FILE):
        try:
            with open(ALERT_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_alert_state(state):
    os.makedirs("data", exist_ok=True)
    with open(ALERT_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ======================== PREDICTIVE MAINTENANCE ========================
def predict_failure_probability(sensor_row, weather=None):
    """24 soat ichida ishdan chiqish ehtimoli (0-100%).
    Ob-havo, kuchlanish, vibratsiya va sim holatiga asoslanadi."""
    try:
        v = float(sensor_row.get("Kuchlanish (V)", 220))
        f = float(sensor_row.get("Chastota (Hz)", 50))
        t = float(sensor_row.get("Muhit_harorat (C)", 25))
        vib = float(sensor_row.get("Vibratsiya", 0))
        sim = float(sensor_row.get("Sim_mexanik_holati (%)", 100))
        fault = int(sensor_row.get("Fault", 0))

        score = 0.0
        # Kuchlanish chetlashishi
        if v < 200 or v > 240: score += 25
        elif v < 210 or v > 230: score += 12
        # Chastota
        if f < 49.5 or f > 50.5: score += 20
        elif f < 49.8 or f > 50.2: score += 8
        # Vibratsiya
        if vib > 5: score += 18
        elif vib > 3: score += 8
        # Sim holati
        if sim < 60: score += 22
        elif sim < 80: score += 10
        # Mavjud fault holati
        if fault == 2: score += 35
        elif fault == 1: score += 15
        # Harorat (ekstremal)
        if t < -10 or t > 40: score += 8

        # Ob-havo qo'shimcha
        if weather:
            wind = float(weather.get("windspeed", 0))
            if wind > 50: score += 15
            elif wind > 30: score += 7

        return min(round(score, 1), 99.0)
    except Exception:
        return 0.0


# ======================== I18N ========================
TRANSLATIONS = {
    "uz": {
        "welcome": "Xush kelibsiz",
        "login": "Kirish",
        "logout": "Chiqish",
        "home": "Asosiy",
        "map": "Xarita",
        "table": "Jadval",
        "graphs": "Grafiklar",
        "forecast": "Prognoz",
        "model": "AI Model",
        "compare": "Taqqoslash",
        "calendar": "Kalendar",
        "tickets": "Buyurtmalar",
        "alerts": "Ogohlantirishlar",
        "language": "Til",
        "dark_mode": "Qorong'i rejim",
        "user_role": "Foydalanuvchi",
        "admin_role": "Administrator",
        "safe": "Xavfsiz",
        "warning": "Ogohlantirish",
        "danger": "Xavfli",
        "voltage": "Kuchlanish",
        "frequency": "Chastota",
        "temperature": "Harorat",
        "near_sensors": "Yaqin sensorlar",
        "weather": "Ob-havo",
        "maintenance": "Ta'mirlashda",
        "fail_prob": "Buzilish ehtimoli",
        "no_data": "Ma'lumot yo'q",
    },
    "uz_cyr": {
        "welcome": "Хуш келибсиз",
        "login": "Кириш",
        "logout": "Чиқиш",
        "home": "Асосий",
        "map": "Харита",
        "table": "Жадвал",
        "graphs": "Графиклар",
        "forecast": "Прогноз",
        "model": "AI Модел",
        "compare": "Таққослаш",
        "calendar": "Календар",
        "tickets": "Буюртмалар",
        "alerts": "Огоҳлантиришлар",
        "language": "Тил",
        "dark_mode": "Қоронғи режим",
        "user_role": "Фойдаланувчи",
        "admin_role": "Администратор",
        "safe": "Хавфсиз",
        "warning": "Огоҳлантириш",
        "danger": "Хавфли",
        "voltage": "Кучланиш",
        "frequency": "Частота",
        "temperature": "Ҳарорат",
        "near_sensors": "Яқин сенсорлар",
        "weather": "Об-ҳаво",
        "maintenance": "Таъмирлашда",
        "fail_prob": "Бузилиш эҳтимоли",
        "no_data": "Маълумот йўқ",
    },
    "ru": {
        "welcome": "Добро пожаловать",
        "login": "Вход",
        "logout": "Выход",
        "home": "Главная",
        "map": "Карта",
        "table": "Таблица",
        "graphs": "Графики",
        "forecast": "Прогноз",
        "model": "AI Модель",
        "compare": "Сравнение",
        "calendar": "Календарь",
        "tickets": "Заявки",
        "alerts": "Оповещения",
        "language": "Язык",
        "dark_mode": "Темный режим",
        "user_role": "Пользователь",
        "admin_role": "Администратор",
        "safe": "Безопасно",
        "warning": "Предупреждение",
        "danger": "Опасно",
        "voltage": "Напряжение",
        "frequency": "Частота",
        "temperature": "Температура",
        "near_sensors": "Ближайшие датчики",
        "weather": "Погода",
        "maintenance": "На ремонте",
        "fail_prob": "Вероятность отказа",
        "no_data": "Нет данных",
    }
}


def t(key, lang="uz"):
    """Tarjima funksiyasi."""
    return TRANSLATIONS.get(lang, TRANSLATIONS["uz"]).get(key, key)

