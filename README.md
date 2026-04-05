# ⚡ BMI_MODELS — Elektr Uzatish Monitoring va AI Bashorat Tizimi

![Python](https://img.shields.io/badge/python-3.12-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0.0-black?logo=flask)
![scikit--learn](https://img.shields.io/badge/scikit--learn-1.3.2-orange?logo=scikit-learn)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

Toshkent shahri — 500 ta sensor, 11 tuman, real-time monitoring va sunʼiy intellekt asosida nosozliklarni bashoratlash

---

## 📋 Loyiha haqida

Ushbu loyiha elektr uzatish liniyalari uchun to'liq monitoring va AI-bashorat tizimini taqdim etadi. Tizim 8 ta parametrni real-time kuzatadi, 3 bosqichli xavf darajasini aniqlaydi va 7 kunlik prognoz beradi.

### Asosiy imkoniyatlar

- 📊 **Dashboard** — KPI kartalar, statistika, jonli ma'lumotlar, Toshkent xaritasi
- 📋 **Jadval** — 1M qator ma'lumot, pagination, smart sorting, CSV/PDF eksport
- 🗺️ **Xarita** — 500 ta sensor joylashuvi va real-time holati (Plotly)
- 📈 **Grafiklar** — 8 ta parametr bo'yicha trend va tahlil
- 🤖 **AI Model** — Hybrid VotingClassifier (RandomForest + MLP)
- 🔮 **7 kunlik prognoz** — Real ob-havo (Open-Meteo API) + AI bashorat
- 🔐 **Autentifikatsiya** — Session-based login, role-based access
- 🌙 **Dark mode** — To'liq qorong'u rejim
- 📱 **Responsive** — Mobile, tablet, desktop

---

## 🏗️ Texnologiyalar

| Texnologiya | Versiya | Vazifasi |
| --- | --- | --- |
| **Python** | 3.12 | Backend til |
| **Flask** | 3.0.0 | Web framework |
| **Pandas** | 2.1.3 | Data processing |
| **NumPy** | 1.26.2 | Hisoblashlar |
| **scikit-learn** | 1.3.2 | ML model (RF + MLP) |
| **Plotly** | 5.18.0 | Interaktiv grafiklar |
| **Bootstrap** | 5.3.0 | UI framework |
| **Font Awesome** | 6.4.0 | Ikonkalar |

---

## 📁 Loyiha tuzilmasi

```text
BMI_models/
├── app.py                        # Flask asosiy server
├── train_model.py                # Model o'qitish skripti
├── config.py                     # Konfiguratsiya (limitlar, portlar)
├── requirements.txt              # Python kutubxonalar
├── README.md
├── .gitignore
├── data/                         # Dataset fayllar
│   ├── sensor_data_part1.csv     # 500K qator (1-qism)
│   ├── sensor_data_part2.csv     # 500K qator (2-qism)
│   └── tashkent_weather_cache.json
├── models/                       # AI model fayllar
│   ├── hybrid_model_part1.pkl    # Model (1-qism)
│   └── hybrid_model_part2.pkl    # Model (2-qism)
├── scripts/                      # Yordamchi skriptlar
│   ├── analyze_faults.py
│   ├── check_ranges.py
│   ├── debug_model.py
│   ├── fix_csv_faults.py
│   ├── fix_fault_labels.py
│   ├── gen_advanced_monitoring.py
│   ├── regenerate_csv.py
│   ├── forecast_params_api.py
│   ├── bmi_model.py
│   └── test_pages.py
├── logs/                         # Log fayllar
│   ├── app.log
│   └── train.log
├── templates/                    # HTML sahifalar
│   ├── index.html
│   ├── navbar.html
│   ├── login.html
│   ├── table.html
│   ├── graphs.html
│   ├── map.html
│   ├── model.html
│   ├── forecast.html
│   ├── sensor_detail.html
│   └── error.html
└── static/                       # CSS, rasmlar
    ├── style.css
    └── bg-grid.png
```

---

## 🚀 O'rnatish va ishga tushirish

```bash
# 1. Repozitoriyani klonlash
git clone https://github.com/ShoxGit19/BMI_models.git
cd BMI_models

# 2. Virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 3. Paketlarni o'rnatish
pip install -r requirements.txt

# 4. Model o'qitish (birinchi marta)
python train_model.py

# 5. Serverni ishga tushirish
python app.py
```

Brauzerda oching: [http://localhost:5000](http://localhost:5000)

### Kirish ma'lumotlari

| Foydalanuvchi | Parol | Rol |
| --- | --- | --- |
| `admin` | `admin123` | Administrator |
| `operator` | `operator123` | Operator |

---

## 🌐 Sahifalar va API

### Web sahifalar

| Sahifa | URL | Tavsifi |
| --- | --- | --- |
| Kirish | `/login` | Autentifikatsiya |
| Dashboard | `/` | KPI, statistika, xarita, jonli panel |
| Jadval | `/table` | Sensor ma'lumotlar jadvali |
| Xarita | `/map` | Sensorlar joylashuvi |
| Grafiklar | `/graphs` | 8 parametr trend grafiklari |
| Model | `/model` | AI prognoz va test |
| Prognoz | `/forecast` | 7 kunlik bashorat |
| Sensor | `/sensor/<id>` | Alohida sensor tafsiloti |

### API Endpoints

| Endpoint | Metod | Tavsifi |
| --- | --- | --- |
| `/api/data` | GET | Paginated sensor data (`?page=&per_page=`) |
| `/api/graph-data` | GET | Grafiklar uchun 1000 ta nuqta |
| `/api/stats` | GET | Dashboard statistika |
| `/api/map-data` | GET | Xarita — har bir sensorning oxirgi holati |
| `/api/forecast` | GET | 7 kunlik prognoz (28 nuqta, har 6 soat) |
| `/api/forecast-params` | GET | Parametr trendlari (`?param=`) |
| `/api/sensor/<id>` | GET | Sensor oxirgi 100 o'qish + tarix |
| `/api/export/csv` | GET | CSV eksport (5000 qator) |
| `/api/export/pdf` | GET | HTML hisobot |
| `/api/telegram/test` | POST | Telegram test xabar |

---

## 🤖 AI Model

### Arxitektura

VotingClassifier (soft voting) + StandardScaler pipeline:

| Komponent | Konfiguratsiya |
| --- | --- |
| **RandomForestClassifier** | 100 trees, `n_jobs=-1` |
| **MLPClassifier** | 2 qatlam (100, 50), max_iter=300 |
| **Preprocessing** | StandardScaler |
| **Training sample** | 100,000 qator, 80/20 split |

### 8 ta kirish parametri (features)

| # | Parametr | Birlik |
| --- | --- | --- |
| 1 | Muhit harorat | °C |
| 2 | Shamol tezligi | km/h |
| 3 | Chastota | Hz |
| 4 | Kuchlanish | V |
| 5 | Vibratsiya | — |
| 6 | Sim mexanik holati | % |
| 7 | Namlik | % |
| 8 | Quvvat | kW |

### Natija — 3 bosqichli klassifikatsiya

| Kod | Holat | Rang |
| --- | --- | --- |
| 0 | ✅ Havfsiz (Normal) | Yashil |
| 1 | ⚠️ Ogohlantirish (Warning) | Sariq |
| 2 | ⛔ Muammo (Danger) | Qizil |

---

## 📊 Sensor parametr limitlari

| Parametr | Normal | Ogohlantirish | Xavfli |
| --- | --- | --- | --- |
| Kuchlanish (V) | 210–230 | 200–210 / 230–240 | <200 / >240 |
| Chastota (Hz) | 49.5–50.5 | 49.0–49.5 / 50.5–51.0 | <49 / >51 |
| Harorat (°C) | <40 | 40–45 | >45 |
| Shamol (km/h) | <15 | 15–25 | >25 |
| Vibratsiya | <1.0 | 1.0–1.5 | >1.5 |
| Sim holati (%) | >85 | 75–85 | <75 |
| Namlik (%) | 35–85 | 30–35 / 85–90 | <30 / >90 |
| Quvvat (kW) | ≤5.0 | 5.0–5.5 | >5.5 |

---

## 📦 Dataset

- **Fayllar**: `data/sensor_data_part1.csv` + `data/sensor_data_part2.csv` (GitHub 100MB limit uchun bo'lingan)
- **Qatorlar**: 1,000,000 (har bir faylda 500,000)
- **Sensorlar**: 500 ta (S001–S500)
- **Tumanlar**: 11 ta (Toshkent shahri)
- **Vaqt oralig'i**: 2024-01-01 — 2026-04-05
- **Ustunlar**: Timestamp, SensorID, District, Latitude, Longitude, 8 parametr, Fault

---

## 🔮 7 kunlik prognoz

Prognoz tizimi quyidagilarni birlashtiradi:

1. **Real ob-havo ma'lumotlari** — Open-Meteo API (Toshkent: 41.31°N, 69.28°E)
2. **Stoxastik simulyatsiya** — Elektr parametrlarning o'rtachaga qaytish modeli
3. **AI bashorat** — Har bir 6 soatlik nuqta uchun model prognozi
4. **Peak-hour effektlari** — Yuqori yuklanish soatlari (8–12, 18–22)

Natija: 28 ta prognoz nuqtasi (7 kun × 4 marta/kun), kunlik xulosa kartalari, risk grafigi va batafsil jadval.

---

## 🐛 Muammolarni hal qilish

| Muammo | Yechim |
| --- | --- |
| `data/sensor_data_part*.csv` topilmadi | Dataset fayllarini `data/` papkasiga qo'ying |
| `models/hybrid_model_part*.pkl` topilmadi | `python train_model.py` orqali model o'qiting |
| Port 5000 band | `config.py` da `PORT = 5001` qiling |
| Prognoz ob-havo xatosi | Internet aloqasini tekshiring (Open-Meteo API) |

---

## 📄 Litsenziya

MIT License — Erkin foydalanish

## 👤 Muallif

**Shohjahon G'aybullayev** — 2026
