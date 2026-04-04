
# ⚡️ BMI_MODELS — Elektr Monitoring va AI Fault Prediction

![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python)
![Flask](https://img.shields.io/badge/flask-%23000?logo=flask&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

**Real-time sensor monitoring va sunʼiy intellekt asosida nosozliklarni bashoratlash tizimi**

---

## 📋 Loyiha haqida

Ushbu loyiha elektr uzatish liniyalari uchun professional monitoring va xavfsizlikni bashoratlash (AI) tizimini taqdim etadi:

- 📊 **Dashboard**: KPI va umumiy statistikalar
- 📈 **Grafiklar**: Tok, kuchlanish, harorat, vibratsiya trendlari
- 🗺️ **Xarita**: Sensorlar joylashuvi va holati
- 📋 **Jadval**: Barcha sensorlar bo‘yicha tafsilotlar
- 🤖 **AI Model**: Hybrid RandomForest + MLP

---

## 🏗️ Texnologiyalar

- **Backend**: Flask (Python)
- **Frontend**: Bootstrap 5, Plotly.js
- **ML**: Scikit-learn (RandomForest, MLP)
- **Data**: Pandas, NumPy

---

## 📁 Loyiha tuzilmasi

```
BMI model/
├── app.py                 # Flask asosiy fayl
├── config.py              # Konfiguratsiya
├── requirements.txt       # Python kutubxonalar
├── hybrid_model.pkl       # O‘qitilgan AI model
├── sensor_monitoring_1M.csv # Sensor maʼlumotlari
├── templates/             # HTML shablonlar
│   ├── index.html         # Bosh sahifa
│   ├── navbar.html        # Navigatsiya
│   ├── table.html         # Jadval
│   ├── graphs.html        # Grafiklar
│   ├── map.html           # Xarita
│   ├── model.html         # Model prognozi
│   └── error.html         # Xato sahifasi
├── static/
│   └── style.css          # UI stillar
└── venv/                  # Virtual environment
```

---

## 🚀 O‘rnatish va ishga tushirish

1. **Virtual environment yaratish**
	```bash
	python -m venv venv
	venv\Scripts\activate   # Windows
	# yoki
	source venv/bin/activate # Linux/Mac
	```
2. **Paketlarni o‘rnatish**
	```bash
	pip install -r requirements.txt
	```
3. **Dastur ishga tushirish**
	```bash
	python app.py
	```
4. Brauzerda oching: [http://localhost:5000](http://localhost:5000)

---

## 🌐 Asosiy sahifalar

| Yo‘nalish | URL | Tavsifi |
|-----------|-----|---------|
| Bosh sahifa | `/` | KPI, umumiy statistika, xarita |
| Jadval | `/table` | Sensorlar jadvali |
| Xarita | `/map` | Sensorlar joylashuvi |
| Grafiklar | `/graphs` | Trend grafiklar |
| Model | `/model` | AI prognoz va test |

---

## 🤖 AI Model haqida

**Model turi**: Hybrid Voting Classifier

- Random Forest (100 trees)
- MLP Neural Network (2 qatlam)
- Soft voting (weighted average)
- Natija: Havfsiz/Muammo (0/1)

---

## 📊 Sensor parametr limitlari

| Parametr     | Min  | Max  | Birlik |
|--------------|------|------|--------|
| Tok          | 0    | 20   | A      |
| Kuchlanish   | 210  | 230  | V      |
| Harorat      | 0    | 50   | °C     |
| Vibratsiya   | 0    | 1.5  | -      |

---

## 🛠️ API Endpoints

| Endpoint           | Metod      | Tavsifi                  |
|--------------------|------------|--------------------------|
| `/`                | GET        | Bosh sahifa              |
| `/table`           | GET        | Jadval sahifasi          |

| `/graphs`          | GET        | Grafiklar sahifasi       |
| `/map`             | GET        | Xarita sahifasi          |
| `/model`           | GET, POST  | Model sahifasi           |
| `/api/data`        | GET        | Barcha sensor maʼlumotlari|
| `/api/map-data`    | GET        | Xarita uchun maʼlumotlar |
| `/api/stats`       | GET        | Statistika               |
| `/api/forecast`    | GET        | 24 soatlik xavf prognozi |
| `/api/forecast-params` | GET    | Trend va parametrlar     |

---


## 🎨 Dizayn

- **Rang sxemasi**: Professional ko‘k (Primary: #004a9f)
- **Shrift**: Segoe UI, Tahoma, Geneva
- **Responsive**: Mobile, Tablet, Desktop
- **Animatsiyalar**: Smooth hover va transition

---

## 🐛 Troubleshooting

- **Data file not found**: `sensor_monitoring_1M.csv` fayli mavjudligini tekshiring
- **Model file not found**: `hybrid_model.pkl` birinchi ishga tushganda avtomatik yaratiladi
- **Port busy**: `app.py`da portni o‘zgartiring: `app.run(port=5001)`

---

## 📧 Hissa qo‘shish va bog‘lanish

- Pull request va issue’lar ochiq
- Taklif va savollar uchun: [GitHub Issues](https://github.com/ShoxGit19/BMI_models/issues)

---

## 📄 Litsenziya

MIT License — Erkin foydalanish

## 👤 Muallif

Ucer — 2026

---

**Izoh**: Tizim barcha maʼlumotlarni real-time yangilaydi. API xatolarida JSON formatda xabar qaytariladi.
