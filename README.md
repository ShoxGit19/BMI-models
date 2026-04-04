# 🌟 Professional Elektr Monitoring Tizimi

**Real-time sensor monitoring va AI-asosida fault prediction tizimi**

## 📋 Loyiha Haqida

Bu loyiha Toshkent elektr uzatish liniyasining real-time monitoring tizimini taqdim qiladi. Tizimda quyidagilari mavjud:

- **📊 Real-time Dashboard**: Bosh sahifa KPI kartalari bilan
- **📈 Trend Grafiklari**: Tok, kuchlanish, harorat, vibratsiya trendlari
- **🗺️ Xarita**: Toshkent xaritasida sensorlarning joylashuvi
- **📋 Jadval**: Batafsil sensor ma'lumotlari
- **🤖 AI Model**: Hybrid RandomForest + MLP fault prediction

## 🏗️ Texnologiyalar

- **Backend**: Flask (Python)
- **Frontend**: Bootstrap 5, Plotly, JavaScript
- **ML Model**: Scikit-learn (RandomForest + MLP)
- **Data**: Pandas, NumPy
- **Database**: Excel fayllar

## 📁 Loyiha Struktura

```
BMI model/
├── app.py                 # Flask asosiy faylı
├── config.py              # Konfiguratsiya
├── requirements.txt       # Python paketlar
├── hybrid_model.pkl       # Trained ML model
├── tashkent_sensors.xlsx  # Sensor ma'lumotlari
├── templates/             # HTML shablonlar
│   ├── index.html         # Bosh sahifa
│   ├── navbar.html        # Navigatsiya paneli
│   ├── table.html         # Jadval sahifasi
│   ├── graphs.html        # Grafiklar
│   ├── map.html           # Xarita
│   ├── model.html         # Model prognozi
│   └── error.html         # Xato sahifasi
├── static/
│   └── style.css          # Professional stillar
└── venv/                  # Virtual environment
```

## 🚀 O'rnatish va Ismarlash

### 1. Virtual Environment Yaratish

```bash
python -m venv venv
source venv/Scripts/activate  # Windows
# yoki
source venv/bin/activate      # Linux/Mac
```

### 2. Paketlar O'rnatish

```bash
pip install -r requirements.txt
```

### 3. Appni Ishga Tushirish

```bash
python app.py
```

Brauzer'da `http://localhost:5000` oching.

## 🌐 Sahifalar

### 1. **Bosh Sahifa** (/)
- KPI kartalari (jami sensorlar, muammolar, o'rtacha qiymatlar)
- Real-time xarita
- Joriy ma'lumotlar

### 2. **Jadval** (/table)
- Batafsil sensor ma'lumotlari
- Filtrlash va saralash

### 3. **Xarita** (/map)
- Toshkent xaritasida sensorlarning joylashuvi
- Status asosida ranglanish
- Statistika

### 4. **Grafiklar** (/graphs)
- Tok trendi
- Kuchlanish trendi
- Harorat trendi
- Vibratsiya trendi
- Manziliklar bo'yicha taqqoslash

### 5. **Model** (/model)
- Barcha sensorlardan real-time prognozlar
- Qo'lda prognoz qilish
- Model ma'lumotlari

## 🤖 AI Model

**Tür**: Hybrid Voting Classifier
- **Model 1**: Random Forest (100 trees)
- **Model 2**: MLP Neural Network (50-25 neurons)
- **Votting**: Soft voting (weighted average)
- **Natija**: Binary classification (Havfsiz/Muammo)

## 📊 Sensor Limitlari

| Parametr | Min | Max | Birlik |
|----------|-----|-----|--------|
| Tok | 0 | 20 | A |
| Kuchlanish | 210 | 230 | V |
| Harorat | 0 | 50 | °C |
| Vibratsiya | 0 | 1.5 | - |

## 🛠️ API Endpoints

| Endpoint | Metod | Tavsifi |
|----------|-------|---------|
| `/` | GET | Bosh sahifa |
| `/table` | GET | Jadval sahifasi |
| `/graphs` | GET | Grafiklar sahifasi |
| `/map` | GET | Xarita sahifasi |
| `/model` | GET, POST | Model sahifasi |
| `/api/data` | GET | Barcha sensor ma'lumotlari |
| `/api/map-data` | GET | Xarita uchun ma'lumotlar |
| `/api/stats` | GET | Statistika |

## 🎨 Dizayn

- **Rang sxemasi**: Professional ko'k (Primary: #004a9f)
- **Shrift**: Segoe UI, Tahoma, Geneva
- **Responsive**: Mobile, Tablet, Desktop
- **Animatsiyalar**: Smooth transitions va hover effects

## 📝 Qo'shimcha Amallar

### Model'ni qayta o'qitish

```python
python -c "
from app import train_or_load_model
import os
os.remove('hybrid_model.pkl')  # Eski modelni o'chirish
train_or_load_model()  # Yangi model
"
```

### Debug rejasi

`config.py` da `DEBUG = True` qilib o'rnating.

## 🐛 Troubleshooting

### 1. "Data file not found"
- `tashkent_sensors.xlsx` faylining manzilini tekshiring

### 2. "Model file not found"
- Birinchi bor ishga tushirish `hybrid_model.pkl` ni avtomatik yaratadi

### 3. Port busy
- Port o'zgartiring: `app.run(port=5001)`

## 📧 Jo'natish va Rivojlantirish

- Pull request'lar qabul qilinadi
- Issue'lar haq'ida xabar bering
- Community sug'i'yotlari kutilmoqda

## 📄 Litsenziya

MIT License - Erkin foydalanish

## 👤 Muallif

Ucer - 2026

---

**Izohlar**: Bu tizimda barcha ma'lumotlar real-time updating bo'ladi. Server xatolarida `/api` endpoints'lar JSON error dturi qaytaradi.
