# ⚡ BMI_MODELS — Toshkent Elektr Uzatish Monitoring va AI Bashorat Tizimi

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0.0-black?logo=flask)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3.2-orange?logo=scikit-learn)
![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-2CA5E0?logo=telegram)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![Sensors](https://img.shields.io/badge/Sensorlar-1200-brightgreen)
![Districts](https://img.shields.io/badge/Tumanlar-12-blue)

**Toshkent shahri — 1200 ta sensor, 12 tuman, real-time monitoring, Telegram bot va AI bashorat**

[🌐 Demo](#-ishga-tushirish) · [🤖 Bot](#-telegram-bot) · [📊 API](#-api-endpointlar) · [🧠 AI](#-ai-model)

</div>

---

## 📋 Loyiha haqida

Ushbu tizim Toshkent shahrining 12 tumanidagi elektr uzatish liniyalari uchun **toʻliq monitoring, AI bashorat va Telegram orqali ogohlantirish** platformasidir. 1,200,000 qatorli real maʼlumot asosida qurilgan. Tizim 8 ta elektr va atrof-muhit parametrini real-time kuzatadi, 3 bosqichli xavf darajasini aniqlaydi va 7 kunlik prognoz beradi.

---

## ✨ Asosiy imkoniyatlar

| Funksiya | Tavsif |
|---|---|
| 📊 **Real-time Dashboard** | KPI kartalar, statistika, jonli sensorlar, trendlar |
| 🗺️ **Interaktiv Xarita** | 1200 sensor, heatmap, klaster, filtr, mini-grafik popup, CSV eksport |
| 📈 **Grafiklar** | 8 parametr trend, taqqoslash, tarix |
| 📋 **Jadval** | 1.2M qator, pagination, sorting, CSV eksport |
| 🧠 **AI Model** | Hybrid VotingClassifier (RandomForest + MLP), ishonch foizi, batafsil matnli xulosa |
| 🔮 **7 kunlik Prognoz** | Real ob-havo (Open-Meteo) + AI bashorat, tuman tanlov |
| 🤖 **Telegram Bot** | 28+ buyruq, grafik, auto-alert, tuman tahlili, ro'yxatdan o'tish |
| 🔐 **Autentifikatsiya** | Session-based login, admin/operator rollari |
| 🌙 **Dark/Light Mode** | Avtomatik yoki qo'lda almashtirish |
| 📱 **Responsive** | Mobile, tablet, desktop |
| 🌐 **SVG Fon** | Toshkent xaritasi + elektr tarmog'i stilizatsiyasi |

---

## 🏗️ Texnologiyalar steki

### Backend
| Kutubxona | Versiya | Vazifasi |
|---|---|---|
| **Python** | 3.12+ | Asosiy til |
| **Flask** | 3.0.0 | Web server va API |
| **Pandas** | 2.1.3 | Ma'lumot tahlili |
| **NumPy** | 1.26.2 | Matematik hisoblashlar |
| **scikit-learn** | 1.3.2 | AI model (RF + MLP) |
| **python-telegram-bot** | 22.7 | Telegram bot |
| **Matplotlib** | 3.9.2 | Bot grafiklari |
| **python-dotenv** | — | .env fayl |
| **requests** | — | Open-Meteo API |

### Frontend
| Texnologiya | Versiya | Vazifasi |
|---|---|---|
| **Bootstrap** | 5.3.0 | UI framework |
| **Leaflet.js** | 1.9.4 | Interaktiv xarita |
| **Leaflet.heat** | 0.2.0 | Heatmap qatlami |
| **Leaflet.markercluster** | 1.5.3 | Sensor klasterlash |
| **Chart.js** | 3.x | Dashboard grafiklar |
| **Font Awesome** | 6.4.0 | Ikonkalar |

---

## 📁 Loyiha tuzilmasi

```
BMI_models/
├── app.py                         # Flask asosiy server + barcha APIlar
├── train_model.py                 # AI model o'qitish skripti
├── config.py                      # Konfiguratsiya (limitlar, portlar, yo'llar)
├── telegram_bot.py                # Telegram bot (28+ buyruq)
├── users.json                     # Bot foydalanuvchilari (telefon, ism, tuman)
├── subscribers.json               # Auto-alert obunachilari
├── requirements.txt               # Python paketlar ro'yxati
├── .env                           # Telegram token (gitignore!)
├── data/
│   ├── sensor_data_part1.csv      # 600K qator (1-qism)
│   ├── sensor_data_part2.csv      # 600K qator (2-qism)
│   └── tashkent_weather_cache.json
├── models/
│   ├── hybrid_model_part1.pkl
│   └── hybrid_model_part2.pkl
├── scripts/                       # Yordamchi skriptlar
├── templates/                     # HTML sahifalar
├── static/                        # CSS, JS, SVG fon
└── logs/                          # Server loglari
```

---

## 🚀 O'rnatish va ishga tushirish

### Talablar
- Python 3.10+
- pip
- Internet (Open-Meteo API va Telegram uchun)

### Qadamlar

```bash
# 1. Klonlash
git clone https://github.com/ShoxGit19/BMI_models.git
cd BMI_models

# 2. Virtual muhit
python -m venv .venv
.\.venv\Scripts\activate        # Windows
# source .venv/bin/activate     # Linux/Mac

# 3. Paketlar
pip install -r requirements.txt

# 4. .env fayl (Windows PowerShell — BOM yo'q usul)
[System.IO.File]::WriteAllText("$PWD\.env", "TELEGRAM_BOT_TOKEN=YOUR_TOKEN`n")

# 5. Model o'qitish (bir marta)
python train_model.py

# 6. Ishga tushirish
.\.venv\Scripts\python.exe app.py
```

> **Brauzerda**: http://localhost:5000

---

## 🔐 Demo kirish ma'lumotlari

| Foydalanuvchi | Parol | Rol |
|---|---|---|
| `admin` | `admin123` | Administrator |
| `operator` | `operator123` | Operator |

---

## 🌐 Web sahifalar

| Sahifa | URL | Tavsifi |
|---|---|---|
| Kirish | `/login` | Login forma |
| Dashboard | `/` | KPI kartalar, statistika, trend grafiklar |
| Jadval | `/table` | 1.2M qator, filter, sort, CSV eksport |
| Xarita | `/map` | Leaflet xarita, heatmap, klaster, sensor qidirish |
| Grafiklar | `/graphs` | 8 parametr trend va taqqoslash |
| AI Model | `/model` | 8 parametr kiritish → AI xulosa + tavsiyalar |
| Prognoz | `/forecast` | 7 kunlik ob-havo + AI bashorat |
| Sensor | `/sensor/<id>` | Alohida sensor: grafik, tarix, holat |

---

## 📡 API Endpointlar

| Endpoint | Metod | Tavsifi |
|---|---|---|
| `/api/data` | GET | Sensor ma'lumotlari (`?page=&per_page=`) |
| `/api/stats` | GET | Dashboard statistika |
| `/api/graph-data` | GET | Grafik 1000 nuqta |
| `/api/map-data` | GET | Xarita — har sensorning so'nggi holati |
| `/api/forecast` | GET | 7 kunlik prognoz (`?latitude=&longitude=`) |
| `/api/forecast-params` | GET | Parametr trendlari (`?param=Kuchlanish`) |
| `/api/sensor/<id>` | GET | Sensor so'nggi 100 o'qish |
| `/api/sensor-spark/<id>` | GET | Sparkline uchun 30 ta qiymat |
| `/api/export/csv` | GET | CSV eksport (`?district=&only_faults=1`) |
| `/api/export/pdf` | GET | HTML hisobot |

---

## 🧠 AI Model

### Arxitektura

```
Kirish (8 parametr)
    ↓
StandardScaler
    ↓
┌──────────────────────────────────┐
│  RandomForestClassifier (100 tree)│
│  +                               │
│  MLPClassifier (100→50 qatlam)   │
└──────────────────────────────────┘
    ↓ soft voting
Natija: 0 / 1 / 2  +  ishonch foizi
```

### 8 ta kirish parametri va normal chegaralar

| Parametr | Birlik | Normal | Ogohlantirish | Xavf |
|---|---|---|---|---|
| Harorat | °C | < 48 | 48–52 | > 52 |
| Shamol | km/h | < 22 | 22–28 | > 28 |
| Chastota | Hz | 49.0–51.0 | 48.5–51.5 | tashqarida |
| Kuchlanish | V | 200–240 | 190–250 | tashqarida |
| Vibratsiya | — | < 1.4 | 1.4–1.7 | > 1.7 |
| Sim holati | % | > 75 | 65–75 | < 65 |
| Namlik | % | 25–92 | 20–95 | tashqarida |
| Quvvat | kW | ≤ 5.5 | 5.5–6.0 | > 6.0 |

### AI Xulosa paneli

Model natijasi bilan birga batafsil matnli tahlil chiqadi:
- Muammoli parametrlar aniq ko'rsatiladi
- Har bir muammo uchun alohida **tavsiya** beriladi
- AI **ishonch foizi (%)** ko'rsatiladi

---

## 📦 Dataset

| Xususiyat | Qiymat |
|---|---|
| Jami qatorlar | 1,200,000 |
| Fayllar | part1.csv (600K) + part2.csv (600K) |
| Sensorlar | 1200 ta (S0001–S1200) |
| Tumanlar | 12 ta |
| Vaqt oralig'i | 2024-01-01 – 2026-04-23 |
| Fault taqsimoti | ~77% safe · ~22% warning · ~1% danger |

> CSV fayllar GitHub 100MB limiti tufayli qo'lda `data/` papkasiga joylashtiriladi.

---

## 🔮 7 kunlik Prognoz

1. **Real ob-havo** — Open-Meteo API (har tuman uchun koordinata bo'yicha)
2. **Stoxastik simulyatsiya** — mean-reversion modeli
3. **AI bashorat** — Hybrid model har 6 soatlik nuqta uchun
4. **Peak-hour effekti** — 8–12, 18–22 soatlar

**Natija**: 28 nuqta (7 kun × 4), kunlik xulosa kartalar, risk grafigi

---

## 🤖 Telegram Bot

### Ro'yxatdan o'tish

```
/start
  → 📱 Telefon yuborish (kontakt tugma YOKI +998XXXXXXXXX qo'lda)
  → ✍️  Ism kiriting
  → ✍️  Familiya kiriting
  → 🏘️  12 tumandan birini tanlang
  → ✅  Bosh menyu
```

### Buyruqlar

| Buyruq | Tavsifi |
|---|---|
| `/start` | Ro'yxatdan o'tish + bosh menyu |
| `/help` | Barcha buyruqlar |
| `/stats` | Umumiy statistika |
| `/forecast` | 7 kunlik prognoz + ob-havo |
| `/districts` | 12 tuman holati |
| `/sensor S0001` | Sensor tafsiloti |
| `/predict 30 7 50 220 0.5 90 60 3` | AI bashorat (8 parametr) |
| `/danger` | Muammoli sensorlar |
| `/top` | Top 10 xavfli sensor |
| `/averages` | O'rtacha qiymatlar |
| `/weather` | Ob-havo |
| `/chart S0001` | Sensor grafigi (PNG) |
| `/compare S0001 S0002` | Taqqoslash + grafik |
| `/district_compare A B` | Tuman taqqoslash |
| `/history S0001 7` | Sensor tarixi |
| `/search Chilonzor` | Tuman qidiruv |
| `/filter danger` | Holat filtri |
| `/report` | CSV hisobot |
| `/csv S0001` | Sensor CSV |
| `/map Chilonzor` | Tuman lokatsiya pin |
| `/subscribe` | Auto-alert obuna |
| `/unsubscribe` | Obunani bekor |
| `/admin` | Admin panel (@gaybullayeev19) |
| `/broadcast matn` | Ommaviy xabar |

---

## 🗺️ 12 Toshkent tumani

| Tuman | Koordinata |
|---|---|
| Bektemir | 41.209, 69.335 |
| Chilonzor | 41.256, 69.204 |
| Mirabad | 41.286, 69.264 |
| Mirobod | 41.286, 69.264 |
| Mirzo Ulug'bek | 41.339, 69.335 |
| Olmazor | 41.354, 69.212 |
| Sergeli | 41.232, 69.212 |
| Shayxontohur | 41.328, 69.229 |
| Uchtepa | 41.300, 69.184 |
| Yakkasaroy | 41.300, 69.264 |
| Yashnobod | 41.339, 69.335 |
| Yunusobod | 41.354, 69.335 |

---

## 🐛 Muammolarni hal qilish

| Muammo | Yechim |
|---|---|
| CSV topilmadi | Fayllarni `data/` ga qo'ying |
| Model topilmadi | `python train_model.py` bajaring |
| Port 5000 band | `config.py` da `PORT = 5001` |
| Bot 401 Unauthorized | `.env` tokenni tekshiring |
| PTB `__stop_running_marker` xatosi | `pip install "python-telegram-bot>=21.10"` |
| `.env` token o'qilmaydi (\ufeff) | `[System.IO.File]::WriteAllText()` ishlating |
| Bot conflict 409 | Boshqa bot sessiyalarini to'xtating |
| ModuleNotFoundError | `.\.venv\Scripts\python.exe app.py` ishlating |

---

## 🔧 Kengaytirish

- **Yangi API** — `app.py` ga `@app.route()` qo'shing
- **Yangi bot buyruq** — `telegram_bot.py` da `CommandHandler` + `main()` ga qo'shing
- **Yangi sahifa** — `templates/` ga HTML, `app.py` ga route
- **AI modelni qayta o'qitish** — `train_model.py` ni o'zgartirib ishga tushiring
- **Sensor chegaralari** — `app.py` da `check()` blokini o'zgartiring
- **Yangi tuman** — `DISTRICTS`, `DISTRICT_COORDS` ga qo'shing + `map.html` polygon

---

## 📄 Litsenziya

**MIT License** — erkin foydalanish, o'zgartirish va tarqatish mumkin.

---

## 👤 Muallif

<div align="center">

### G'aybullayev Shohjahon

🌍 Toshkent, Bekobod · 2024–2026

[![Telegram](https://img.shields.io/badge/Telegram-@gaybullayeev19-2CA5E0?logo=telegram)](https://t.me/gaybullayeev19)
[![GitHub](https://img.shields.io/badge/GitHub-ShoxGit19-181717?logo=github)](https://github.com/ShoxGit19)

</div>

---

<div align="center">

**⚡ ElectroGrid Monitoring System · Toshkent · 2026**

*1,200,000 sensor yozuvi · 12 tuman · Hybrid AI · Real-time monitoring*

</div>