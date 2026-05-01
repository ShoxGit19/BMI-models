# ⚡ ElectroGrid Monitoring — BMI_models

> **Toshkent shahri elektr uzatish liniyalari uchun real-time monitoring, gibrid AI bashorat va Telegram bot platformasi.**

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.8-F7931E?logo=scikit-learn&logoColor=white)
![Telegram Bot](https://img.shields.io/badge/Telegram_Bot-21.3-2CA5E0?logo=telegram&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-1.9-199900?logo=leaflet&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e)
![Sensors](https://img.shields.io/badge/Sensorlar-1200-06b6d4)
![Districts](https://img.shields.io/badge/Tumanlar-12-2563EB)
![Data](https://img.shields.io/badge/Yozuvlar-1.2M-8B5CF6)

**1,200,000 yozuv · 1,200 sensor · 12 tuman · Hybrid AI · 7 kunlik prognoz · PWA · Premium UI**

[🚀 Ishga tushirish](#-ornatish-va-ishga-tushirish) ·
[🌐 Web sahifalar](#-web-sahifalar) ·
[📡 API](#-api-endpointlar) ·
[🤖 Bot](#-telegram-bot) ·
[🧠 AI](#-ai-model) ·
[🎨 UI](#-premium-ui-qatlami)

</div>

---

## 📖 Mundarija

1. [Loyiha haqida](#-loyiha-haqida)
2. [Asosiy imkoniyatlar](#-asosiy-imkoniyatlar)
3. [Texnologiyalar steki](#%EF%B8%8F-texnologiyalar-steki)
4. [Loyiha tuzilmasi](#-loyiha-tuzilmasi)
5. [O'rnatish va ishga tushirish](#-ornatish-va-ishga-tushirish)
6. [Demo kirish](#-demo-kirish)
7. [Web sahifalar](#-web-sahifalar)
8. [API endpointlar](#-api-endpointlar)
9. [AI model](#-ai-model)
10. [Sensor parametrlari va chegaralari](#-sensor-parametrlari-va-chegaralari)
11. [7 kunlik prognoz](#-7-kunlik-prognoz)
12. [Telegram bot](#-telegram-bot)
13. [Toshkent tumanlari](#-toshkent-tumanlari)
14. [Premium UI qatlami](#-premium-ui-qatlami)
15. [PWA — telefonga o'rnatish](#-pwa--telefonga-ornatish)
16. [Konfiguratsiya (`config.py`)](#%EF%B8%8F-konfiguratsiya-configpy)
17. [Konsol skriptlari (`scripts/`)](#-konsol-skriptlari-scripts)
18. [Muammolarni hal qilish](#-muammolarni-hal-qilish)
19. [Kengaytirish](#-kengaytirish)
20. [Xavfsizlik](#-xavfsizlik)
21. [Litsenziya](#-litsenziya)
22. [Muallif](#-muallif)

---

## 📋 Loyiha haqida

**ElectroGrid Monitoring** — Toshkent shahrining 12 tumanidagi **1,200 ta sensor**dan yig'ilgan **1.2 million yozuv** asosida ishlaydigan to'liq monitoring tizimi.

Tizim 8 ta elektr va atrof-muhit parametrini real vaqtda kuzatadi, har bir sensorni 3 bosqichli xavf darajasi (✅ Normal · ⚠️ Ogohlantirish · 🚨 Favqulodda) bo'yicha tasniflaydi, **gibrid AI model** (RandomForest + MLP) yordamida nosozlikni bashorat qiladi va **Open-Meteo** real ob-havo asosida 7 kunlik prognoz beradi. Barcha hodisalar Telegram bot orqali tegishli tuman foydalanuvchisiga jonli yetkaziladi.

### Loyihaning kuchli tomonlari

- ⚡ **Real-time** — har 30 sekundda yangilanish, jonli status bar
- 🧠 **Hybrid AI** — RandomForest + MLP soft-voting, ishonch foizi va matnli tahlil
- 🌦️ **Real ob-havo** — Open-Meteo API integratsiyasi (har tuman uchun GPS)
- 🤖 **Telegram bot** — 28+ buyruq, grafik PNG, auto-alert, ro'yxatdan o'tish
- 🎨 **Premium UI** — glassmorphism, animatsiyalar, command palette (Ctrl+K), toast
- 📱 **PWA** — telefon/desktopga o'rnatiladi, offline manifest
- 🌙 **Dark / Light** — qo'lda yoki avtomatik
- 🌐 **Ko'p tilli interfeys** — uz / ru / en (navbar lang switcher)
- 📊 **Eksport** — CSV, PDF (HTML hisobot), Excel-mos format

---

## ✨ Asosiy imkoniyatlar

| # | Modul | Tavsif |
|---|---|---|
| 📊 | **Real-time Dashboard** | KPI kartalar, jonli sensorlar, trend grafiklar, sparkline mini-charts |
| 🗺️ | **Interaktiv Xarita** | Leaflet, 1200 sensor, heatmap qatlami, klaster, tuman polygonlari, popup mini-grafik, GPS pin |
| 📈 | **Grafiklar** | 8 parametr trend, multi-axis, sensor taqqoslash, tarix tahlili |
| 📋 | **Jadval** | 1.2M qator, server-side pagination, sort, multi-filter, CSV eksport |
| 🧠 | **AI Model** | Hybrid VotingClassifier, ishonch %, matnli xulosa, har bir parametr uchun tavsiya |
| 🔮 | **7 kunlik Prognoz** | Real ob-havo + AI + peak-hour effekt, 28 nuqta, kunlik xulosa |
| 🆚 | **Solishtirish** | Ikki sensor / tumanni yonma-yon taqqoslash |
| 📅 | **Kalendar** | Texnik xizmat va inspeksiya rejasi |
| 🎫 | **Tiketlar** | Muammolar uchun ish hujjati (ticketing) |
| 🛠️ | **Audit jurnali** | Foydalanuvchi harakatlari log |
| 🤖 | **Telegram Bot** | 28+ buyruq, `/predict`, `/chart`, auto-alert, ro'yxatdan o'tish |
| 🔐 | **Auth + Rollar** | Session-based login, admin / operator |
| 🌙 | **Dark/Light** | Premium tema, manifest theme-color sinxron |
| 📱 | **Responsive + PWA** | Mobile/tablet/desktop, telefonga o'rnatish |
| ⌨️ | **Command Palette** | `Ctrl+K` orqali tezkor navigatsiya |
| 🔔 | **Toast bildirishnoma** | `egToast({title, msg, type})` API |
| 🎨 | **Premium SVG fon** | Toshkent elektr tarmog'i, animatsiyali energiya oqimi |

---

## 🛠️ Texnologiyalar steki

### Backend

| Kutubxona | Versiya | Vazifasi |
|---|---|---|
| **Python** | 3.10+ | Asosiy til |
| **Flask** | 3.0.0 | Web server, API |
| **Flask-SocketIO** | 5.3.6 | (ixtiyoriy) real-time push |
| **Flask-Caching** | 2.3.1 | Server javoblarini keshlash |
| **Flask-Limiter** | 4.1.1 | API rate-limit |
| **bcrypt** | 5.0.0 | Parol xeshlash |
| **pandas** | 2.x | Ma'lumotlarni qayta ishlash |
| **numpy** | 1.x / 2.x | Hisoblash |
| **pyarrow** | 24.x | CSV → Parquet konvertatsiya |
| **scikit-learn** | 1.8 | RandomForest + MLP |
| **scipy** | 1.x | Statistik funksiyalar |
| **matplotlib** | 3.x | Bot uchun PNG grafiklar |
| **plotly** | 5.18 | (ixtiyoriy) interaktiv grafik |
| **python-telegram-bot** | 21.3 | Telegram bot |
| **openpyxl** | 3.1.5 | Excel eksport |
| **requests** | 2.31 | Open-Meteo API |
| **python-dotenv** | — | `.env` fayl o'qish |

### Frontend

| Texnologiya | Versiya | Vazifasi |
|---|---|---|
| **Bootstrap** | 5.3 | UI framework, grid |
| **Leaflet.js** | 1.9.4 | Interaktiv xarita |
| **Leaflet.heat** | 0.2.0 | Heatmap qatlami |
| **Leaflet.markercluster** | 1.5.3 | Sensor klasterlash |
| **Chart.js** | 3.x | Dashboard grafiklar |
| **Font Awesome** | 6.4 | Ikonkalar |
| **Inter** | — | Premium font |
| **Custom enhance.css/js** | — | Glassmorphism, animatsiya, palette, toast |

---

## 📁 Loyiha tuzilmasi

```text
BMI_models/
├── app.py                          # Flask asosiy server, barcha API va sahifalar
├── train_model.py                  # AI modelni o'qitish skripti
├── telegram_bot.py                 # Telegram bot (28+ buyruq, auto-alert)
├── chatbot_engine.py               # Bot ichidagi NLP/qoidalar dvigateli
├── config.py                       # Sensor chegaralari, port, yo'llar
├── utils.py                        # Yordamchi funksiyalar
├── requirements.txt                # Python paketlar
├── pyrightconfig.json              # Static type config
├── bot_token.txt                   # (alternativa .env'ga)
├── users.json                      # Bot foydalanuvchilari
├── subscribers.json                # Auto-alert obunachilari
├── README.md                       # Mana shu fayl
│
├── data/
│   ├── sensor_data_part1.csv       # 600K yozuv (CSV qism 1)
│   ├── sensor_data_part2.csv       # 600K yozuv (CSV qism 2)
│   ├── alert_state.json            # Faol ogohlantirishlar
│   ├── incidents.json              # Hodisalar tarixi
│   ├── maintenance.json            # Texnik xizmat rejasi
│   ├── tickets.json                # Tiketlar
│   └── tashkent_weather_cache.json # Ob-havo keshi
│
├── models/
│   └── *.pkl                       # O'qitilgan hybrid model fayllari
│
├── logs/
│   └── audit.json                  # Foydalanuvchi harakatlari
│
├── scripts/                        # Yordamchi konsol skriptlar
│   ├── generate_data.py            # CSV ma'lumot generatsiyasi
│   ├── csv_to_parquet.py           # CSV → Parquet
│   ├── bmi_model.py                # Modelni alohida sinash
│   ├── fix_coordinates.py          # GPS koordinatalarni tekshirish
│   ├── _update_map.py              # Xarita JSON yangilash
│   ├── forecast_params_api.py      # Forecast API sinov
│   ├── gen_advanced_monitoring.py  # Kengaytirilgan monitoring data
│   └── test_pages.py               # Sahifalarni avto-test
│
├── templates/                      # Jinja2 HTML
│   ├── navbar.html                 # Umumiy navbar (har sahifaga include)
│   ├── login.html                  # Kirish sahifasi (animatsiyali fon)
│   ├── index.html                  # Bosh sahifa
│   ├── new_dashboard.html          # Yangi dashboard
│   ├── user_home.html              # Operator home
│   ├── map.html                    # Leaflet xarita
│   ├── table.html                  # Jadval
│   ├── graphs.html                 # Grafiklar
│   ├── model.html                  # AI model UI
│   ├── forecast.html               # 7 kunlik prognoz
│   ├── compare.html                # Sensor/tuman taqqoslash
│   ├── sensor_detail.html          # Sensor tafsiloti
│   ├── calendar.html               # Texnik xizmat kalendari
│   ├── tickets.html                # Tiketlar
│   ├── audit.html                  # Audit jurnali
│   └── error.html                  # 4xx/5xx
│
└── static/
    ├── style.css                   # Asosiy dizayn tizimi (tokens, kartalar)
    ├── enhance.css                 # Premium qatlam (animatsiya, glass, toast)
    ├── enhance.js                  # JS qatlam (counter, ripple, palette)
    ├── theme.js                    # Dark/Light toggle
    ├── sw.js                       # Service Worker (PWA)
    ├── manifest.json               # PWA manifest
    ├── bg-tashkent.svg             # Premium fon (elektr tarmog'i, animatsiya)
    ├── icon.svg                    # Vektor ikonka
    ├── icon-192.png                # PWA ikonka 192px
    └── icon-512.png                # PWA ikonka 512px
```

---

## 🚀 O'rnatish va ishga tushirish

### Talablar

- **Python 3.10+** (3.12 tavsiya etiladi)
- `pip` (Python bilan birga keladi)
- Internet aloqasi (Open-Meteo va Telegram uchun)
- ~2 GB bo'sh joy (CSV + model)

### Qadamlar (Windows PowerShell)

```powershell
# 1. Klonlash
git clone https://github.com/ShoxGit19/BMI_models.git
cd BMI_models

# 2. Virtual muhit yaratish va faollashtirish
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Paketlarni o'rnatish
pip install -r requirements.txt

# 4. CSV ma'lumotlarni 'data/' papkasiga joylashtiring
#    (sensor_data_part1.csv va sensor_data_part2.csv)

# 5. .env faylni yarating (BOM siz, UTF-8)
[System.IO.File]::WriteAllText("$PWD\.env", "TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN`n")

# 6. AI modelni o'qitish (bir marta, ~3-5 daqiqa)
python train_model.py

# 7. Saytni ishga tushirish (Flask + Telegram bot birga)
python app.py
```

### Qadamlar (Linux / macOS)

```bash
git clone https://github.com/ShoxGit19/BMI_models.git
cd BMI_models
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN" > .env
python train_model.py
python app.py
```

> 🌐 Brauzerda oching: **http://localhost:5000**

---

## 🔐 Demo kirish

| Foydalanuvchi | Parol | Rol |
|---|---|---|
| `admin` | `admin123` | 👑 Administrator (barcha sahifalar) |
| `operator` | `operator123` | 👤 Operator (faqat o'qish) |

> ⚠️ **Production'da** demo parollarni darhol o'zgartiring (bcrypt bilan xeshlangan parolga o'ting).

---

## 🌐 Web sahifalar

| Sahifa | URL | Tavsifi |
|---|---|---|
| Kirish | `/login` | Animatsiyali fon, glass kartalar |
| Bosh sahifa | `/` | KPI overview, eng so'nggi hodisalar |
| Dashboard | `/dashboard` | KPI kartalar, sparkline, trend, real-time |
| Xarita | `/map` | 1200 sensor, heatmap, klaster, polygon |
| Jadval | `/table` | 1.2M qator, sort, filter, CSV |
| Grafiklar | `/graphs` | 8 parametr trend, multi-axis |
| Solishtirish | `/compare` | Ikki sensor/tuman yonma-yon |
| AI Model | `/model` | 8 parametr → AI xulosa + tavsiyalar |
| Prognoz | `/forecast` | 7 kunlik AI + ob-havo bashorat |
| Sensor | `/sensor/<id>` | Sensor: grafik, tarix, holat |
| Kalendar | `/calendar` | Texnik xizmat rejasi |
| Tiketlar | `/tickets` | Muammo bilet tizimi |
| Audit | `/audit` | Foydalanuvchi harakatlari logi |

---

## 📡 API endpointlar

| Endpoint | Metod | Tavsifi |
|---|---|---|
| `/api/data` | GET | Sensor o'qishlari (`?page=&per_page=&district=`) |
| `/api/stats` | GET | Dashboard umumiy statistika |
| `/api/graph-data` | GET | Grafik uchun 1000 nuqta |
| `/api/map-data` | GET | Har sensorning so'nggi holati |
| `/api/sensor/<id>` | GET | Sensor so'nggi 100 o'qish |
| `/api/sensor-spark/<id>` | GET | Sparkline uchun 30 ta qiymat |
| `/api/forecast` | GET | 7 kunlik prognoz (`?latitude=&longitude=`) |
| `/api/forecast-params` | GET | Parametr trendi (`?param=Kuchlanish`) |
| `/api/predict` | POST | AI bashorat (JSON: 8 parametr) |
| `/api/export/csv` | GET | CSV (`?district=&only_faults=1`) |
| `/api/export/pdf` | GET | HTML hisobot |
| `/api/tickets` | GET/POST | Tiket CRUD |
| `/api/incidents` | GET | Hodisalar tarixi |

### `/api/predict` namuna so'rov

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "Harorat": 35,
    "Shamol": 12,
    "Chastota": 50.0,
    "Kuchlanish": 220,
    "Vibratsiya": 0.8,
    "Sim_holati": 88,
    "Namlik": 55,
    "Quvvat": 4.2
  }'
```

Javob:

```json
{
  "label": 0,
  "label_name": "safe",
  "confidence": 0.94,
  "issues": [],
  "recommendations": ["Barcha parametrlar normal."]
}
```

---

## 🧠 AI model

### Arxitektura

```
Kirish (8 parametr)
        │
        ▼
  StandardScaler
        │
        ▼
┌────────────────────────────────────────┐
│  RandomForestClassifier (100 daraxt)   │
│                +                       │
│  MLPClassifier (100 → 50 yashirin qatl)│
│              soft voting               │
└────────────────────────────────────────┘
        │
        ▼
  Natija: 0 / 1 / 2  +  ishonch foizi (%)
        │
        ▼
  Matnli xulosa + tavsiyalar
```

### Sinflar

| Kod | Nom | Rang | Ma'no |
|---|---|---|---|
| `0` | safe | 🟢 Yashil | Barcha parametrlar normal |
| `1` | warning | 🟡 Sariq | Bir yoki bir nechta parametr ogoh zonada |
| `2` | danger | 🔴 Qizil | Kritik chegaradan tashqarida — favqulodda |

### Modelni qayta o'qitish

```bash
python train_model.py
```

Skript `data/sensor_data_part*.csv` ni o'qib, modelni `models/` ga saqlaydi va konsol orqali metrika ko'rsatadi (Accuracy, Precision, Recall, F1).

---

## 📏 Sensor parametrlari va chegaralari

`config.py` da to'liq sozlanadigan **3 bosqichli** chegaralar:

| Parametr | Birlik | 🟢 Normal | 🟡 Ogohlantirish | 🔴 Favqulodda |
|---|---|---|---|---|
| **Kuchlanish** | V | 210–230 | 200–210 / 230–240 | < 200 yoki > 240 |
| **Chastota** | Hz | 49.5–50.5 | 49.0–49.5 / 50.5–51.0 | < 49 yoki > 51 |
| **Harorat** | °C | < 40 | 40–45 | > 45 |
| **Shamol** | km/h | < 15 | 15–25 | > 25 |
| **Vibratsiya** | — | < 1.0 | 1.0–1.5 | > 1.5 |
| **Sim holati** | % | > 85 | 75–85 | < 75 |
| **Namlik** | % | 35–85 | 30–35 / 85–90 | < 30 yoki > 90 |
| **Quvvat** | kW | ≤ 5.0 | 5.0–5.5 | > 5.5 |

---

## 🔮 7 kunlik prognoz

Algoritm:

1. **Real ob-havo** — Open-Meteo API (har tuman uchun GPS)
2. **Stoxastik simulyatsiya** — mean-reversion (Ornstein–Uhlenbeck) modeli
3. **Peak-hour effekti** — 08:00–12:00 va 18:00–22:00 yuk pastki
4. **AI bashorat** — har 6 soatlik nuqta uchun hybrid model
5. **Aggregatsiya** — kunlik xulosa: o'rtacha risk %, eng xavfli soat

**Natija**: `7 kun × 4 nuqta = 28` bashorat + 7 kunlik xulosa kartalar va risk grafigi.

---

## 🤖 Telegram bot

### Ro'yxatdan o'tish jarayoni

```
/start
  → 📱 Telefon yuborish (kontakt tugma yoki +998XXXXXXXXX qo'lda)
  → ✍️  Ism kiriting
  → ✍️  Familiya kiriting
  → 🏘️  12 tumandan birini tanlang
  → ✅  Bosh menyu (inline tugmalar)
```

### Buyruqlar (28+)

| Buyruq | Tavsifi |
|---|---|
| `/start` | Ro'yxatdan o'tish + bosh menyu |
| `/help` | Barcha buyruqlar ro'yxati |
| `/stats` | Umumiy statistika (sensorlar, holatlar) |
| `/forecast` | 7 kunlik prognoz + ob-havo |
| `/districts` | 12 tuman holati |
| `/sensor S0001` | Sensor tafsiloti |
| `/predict 30 7 50 220 0.5 90 60 3` | AI bashorat (8 parametr) |
| `/danger` | Hozirgi muammoli sensorlar |
| `/top` | Top 10 xavfli sensor |
| `/averages` | O'rtacha qiymatlar |
| `/weather` | Joriy ob-havo |
| `/chart S0001` | Sensor grafigi (PNG) |
| `/compare S0001 S0002` | Ikki sensor + grafik |
| `/district_compare A B` | Tumanlarni taqqoslash |
| `/history S0001 7` | Sensor 7 kunlik tarixi |
| `/search Chilonzor` | Tuman bo'yicha qidiruv |
| `/filter danger` | Holat bo'yicha filtr |
| `/report` | CSV hisobot fayl |
| `/csv S0001` | Bitta sensor CSV |
| `/map Chilonzor` | Tuman lokatsiya pin |
| `/subscribe` | Auto-alert obunasi |
| `/unsubscribe` | Obunani bekor qilish |
| `/admin` | Admin panel (faqat @gaybullayeev19) |
| `/broadcast matn` | Ommaviy xabar (admin) |

### Auto-alert

Foydalanuvchi `/subscribe` qilsa, **uning tumanida** sensor holati `warning` yoki `danger` ga o'tganda darhol xabar oladi. Holatlar `data/alert_state.json` da kuzatiladi (qayta yuborilmaydi).

---

## 🗺️ Toshkent tumanlari

| Tuman | Latitude | Longitude |
|---|---|---|
| Bektemir | 41.209 | 69.335 |
| Chilonzor | 41.256 | 69.204 |
| Mirobod | 41.286 | 69.264 |
| Mirzo Ulug'bek | 41.339 | 69.335 |
| Olmazor | 41.354 | 69.212 |
| Sergeli | 41.232 | 69.212 |
| Shayxontohur | 41.328 | 69.229 |
| Uchtepa | 41.300 | 69.184 |
| Yakkasaroy | 41.300 | 69.264 |
| Yashnobod | 41.339 | 69.335 |
| Yunusobod | 41.354 | 69.335 |
| Yangihayot | 41.220 | 69.240 |

---

## 🎨 Premium UI qatlami

[static/enhance.css](static/enhance.css) + [static/enhance.js](static/enhance.js) orqali butun saytga **avtomatik** qo'shilgan:

| Imkoniyat | Qayerda ishlaydi |
|---|---|
| 🌫️ **Glassmorphism navbar** | Sticky navbar — aylantirganda blur kuchayadi |
| ✨ **Sahifa fade-up animatsiya** | Har bir `main > .container` |
| 🎯 **3D tilt + lift** | `.card`, `.kpi-card`, `.stat-card` |
| 💧 **Ripple effekt** | Har bir `.btn` va `<button>` |
| 🔢 **Counter animatsiyasi** | KPI raqamlar 0 dan haqiqiy songacha |
| 🟢 **Pulse status dot** | `<span class="eg-pulse-dot"></span>` |
| 🔴 **LIVE badge** | `<span class="eg-live-badge">…</span>` |
| 🌈 **Gradient scrollbar** | Butun sayt |
| ⌨️ **Command Palette** | `Ctrl+K` — tezkor navigatsiya |
| 🔔 **Toast bildirishnoma** | `egToast({title, msg, type})` |
| 📊 **Footer status bar** | Server / DB / Bot / vaqt (jonli) |
| 💀 **Skeleton loader** | `<span class="eg-skeleton"></span>` |
| ♿ **Reduced-motion** | OS sozlamasiga hurmat |

### JavaScript API

```js
// Toast
egToast({ title: 'Saqlandi', msg: 'Sozlamalar yangilandi', type: 'success' });
egToast({ title: 'Xato', msg: 'Server javob bermadi', type: 'error' });
// type: 'info' | 'success' | 'warning' | 'error'
```

### HTML komponentlar

```html
<!-- Jonli ko'rsatkich -->
<span class="eg-live-badge"><span class="eg-pulse-dot"></span> Jonli</span>

<!-- Sensor holati -->
<span class="eg-pulse-dot"></span>          <!-- yashil (normal) -->
<span class="eg-pulse-dot warn"></span>     <!-- sariq (ogohlantirish) -->
<span class="eg-pulse-dot danger"></span>   <!-- qizil (xato) -->

<!-- Counter (avtomatik 0 dan ishga tushadi) -->
<span class="eg-counter" data-to="1247">0</span>

<!-- Skroll bilan paydo bo'luvchi blok -->
<div class="eg-reveal">…</div>

<!-- Skeleton loader -->
<span class="eg-skeleton" style="width:120px"></span>
```

---

## 📱 PWA — telefonga o'rnatish

Sayt **Progressive Web App** sifatida ishlaydi:

- `manifest.json` — ikonka, ranglar, standalone rejim
- `sw.js` — Service Worker (offline keshi)
- `icon.svg` + `icon-192.png` + `icon-512.png` — premium ikonkalar

**Telefonda o'rnatish**:
1. Chrome/Edge'da saytni oching
2. ⋮ menyusi → **"Bosh ekranga qo'shish"** / **"Install"**
3. Sayt ilova ko'rinishida ochiladi

---

## ⚙️ Konfiguratsiya (`config.py`)

```python
class Config:
    DEBUG = True
    DATA_FILES = ["data/sensor_data_part1.csv", "data/sensor_data_part2.csv"]
    MODEL_FILES = ["models/hybrid_model_part1.pkl", "models/hybrid_model_part2.pkl"]
    REFRESH_INTERVAL = 30000   # ms — front-end auto-refresh
    PORT = 5000
    HOST = "0.0.0.0"

    SENSOR_LIMITS = { ... }    # 3 bosqichli chegaralar
```

Sozlamalarni o'zgartirish uchun `Config` klassi maydonlarini tahrirlang. `DevelopmentConfig` va `ProductionConfig` orqali rejimlar ajratiladi.

---

## 🧰 Konsol skriptlari (`scripts/`)

| Skript | Vazifasi |
|---|---|
| [generate_data.py](scripts/generate_data.py) | 1.2M yozuvli realistik CSV generatsiyasi |
| [csv_to_parquet.py](scripts/csv_to_parquet.py) | CSV → Parquet (10× tezroq) |
| [bmi_model.py](scripts/bmi_model.py) | Modelni alohida sinab ko'rish |
| [fix_coordinates.py](scripts/fix_coordinates.py) | Sensor GPS koordinatalarini tekshirish |
| [_update_map.py](scripts/_update_map.py) | Xarita JSON ni yangilash |
| [forecast_params_api.py](scripts/forecast_params_api.py) | Forecast API qo'lda sinov |
| [gen_advanced_monitoring.py](scripts/gen_advanced_monitoring.py) | Kengaytirilgan monitoring data |
| [test_pages.py](scripts/test_pages.py) | Barcha sahifalarni HTTP-test |

```powershell
# Misol
python scripts\generate_data.py
python scripts\test_pages.py
```

---

## 🐛 Muammolarni hal qilish

| Muammo | Yechim |
|---|---|
| `FileNotFoundError: data/sensor_data_part1.csv` | CSV fayllarni `data/` ga qo'shing |
| `FileNotFoundError: models/...pkl` | `python train_model.py` bajaring |
| Port 5000 band | `config.py` da `PORT = 5001` |
| Bot **401 Unauthorized** | `.env` ichidagi tokenni qayta tekshiring |
| Bot **Conflict 409** | Boshqa joyda ishlayotgan bot sessiyasini to'xtating |
| `\ufeff` BOM `.env` da | `[System.IO.File]::WriteAllText(...)` ishlating |
| `__stop_running_marker` xatosi | `pip install "python-telegram-bot>=21.10"` |
| `ModuleNotFoundError` | `.venv` faollashganini tekshiring va `pip install -r requirements.txt` |
| Open-Meteo `Timeout` | Internet aloqasini tekshiring (kesh ishlatadi) |
| Brauzerda eski CSS | **Ctrl+F5** (cache tozalash) |

---

## 🔧 Kengaytirish

| Vazifa | Qaerda |
|---|---|
| Yangi API endpoint | [app.py](app.py) → `@app.route()` |
| Yangi bot buyruq | [telegram_bot.py](telegram_bot.py) → `CommandHandler` + `main()` |
| Yangi sahifa | [templates/](templates/) ga HTML + [app.py](app.py) ga route |
| Modelni qayta o'qitish | [train_model.py](train_model.py) ni o'zgartiring |
| Sensor chegaralari | [config.py](config.py) → `SENSOR_LIMITS` |
| Yangi tuman | `DISTRICTS` + `DISTRICT_COORDS` + xarita polygon |
| Yangi til | `navbar.html` lang switcher + Jinja `{% if lang == 'xx' %}` |
| Yangi UI komponent | [static/enhance.css](static/enhance.css) + [enhance.js](static/enhance.js) |

---

## 🔒 Xavfsizlik

- ✅ **Session-based auth** — Flask session cookie
- ✅ **CSRF** — POST formalarida tekshiruv (kengaytirilishi mumkin)
- ✅ **Rate-limit** — `Flask-Limiter` orqali API'larda
- ✅ **bcrypt** — parol xeshlash uchun tayyor
- ⚠️ **Demo parollar** — production'da darhol almashtiring
- ⚠️ **`.env`** — `gitignore` ichida bo'lishi shart (token sirligi)
- ✅ **OWASP Top-10** — SQL injection (DBsiz), XSS (Jinja avto-escape), open redirect tekshirilgan

---

## 📄 Litsenziya

**MIT License** — erkin foydalanish, o'zgartirish va tarqatish mumkin.

```
Copyright (c) 2024–2026 G'aybullayev Shohjahon

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction…
```

---

## 👤 Muallif

<div align="center">

### G'aybullayev Shohjahon

**🌍 Toshkent · Bekobod · 2024–2026**

**Bitiruv malakaviy ishi · Sun'iy intellekt asosida elektr tarmog'i monitoringi**

[![Telegram](https://img.shields.io/badge/Telegram-@gaybullayeev19-2CA5E0?logo=telegram&logoColor=white)](https://t.me/gaybullayeev19)
[![GitHub](https://img.shields.io/badge/GitHub-ShoxGit19-181717?logo=github&logoColor=white)](https://github.com/ShoxGit19)

</div>

---

<div align="center">

**⚡ ElectroGrid Monitoring System · v2.0 · Toshkent · 2026**

*1,200,000 sensor yozuvi · 12 tuman · Hybrid AI · Real-time monitoring · PWA · Premium UI*

⭐ **Loyiha sizga foydali bo'lsa — yulduzcha qoldiring!**

</div>
