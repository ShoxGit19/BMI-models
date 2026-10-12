# ⚡ ElectroGrid Monitoring — BMI Models

> **Toshkent shahri elektr uzatish liniyalari uchun real-time monitoring, gibrid AI bashorat, nosozlik buyurtma tizimi va Telegram bot platformasi.**

<div align="center">

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.8-F7931E?logo=scikit-learn&logoColor=white)
![Telegram Bot](https://img.shields.io/badge/Telegram_Bot-21.3-2CA5E0?logo=telegram&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-1.9-199900?logo=leaflet&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e)
![Sensors](https://img.shields.io/badge/Sensorlar-1200-06b6d4)
![Districts](https://img.shields.io/badge/Tumanlar-12-2563EB)
![Data](https://img.shields.io/badge/Yozuvlar-1.3M-8B5CF6)
![Version](https://img.shields.io/badge/Version-3.0-EF4444)

**1,292,959 yozuv · 1,200 sensor · 12 tuman · Hybrid AI · 7 kunlik prognoz · Nosozlik tizimi · PWA**

[🚀 Ishga tushirish](#-ornatish-va-ishga-tushirish) ·
[🌐 Web sahifalar](#-web-sahifalar) ·
[📡 API](#-api-endpointlar) ·
[🤖 Bot](#-telegram-bot) ·
[🛠️ Buyurtma](#-nosozlik-buyurtma-tizimi) ·
[🧠 AI](#-ai-model) ·
[💬 Chatbot](#-ai-chatbot-engine)

</div>

---

## 📖 Mundarija

1. [Loyiha haqida](#-loyiha-haqida)
2. [Asosiy imkoniyatlar](#-asosiy-imkoniyatlar)
3. [Yangiliklar (v3.0)](#-yangiliklar-v30)
4. [Texnologiyalar steki](#%EF%B8%8F-texnologiyalar-steki)
5. [Loyiha tuzilmasi](#-loyiha-tuzilmasi)
6. [O'rnatish va ishga tushirish](#-ornatish-va-ishga-tushirish)
7. [Demo kirish](#-demo-kirish)
8. [Web sahifalar](#-web-sahifalar)
9. [API endpointlar](#-api-endpointlar)
10. [AI Model](#-ai-model)
11. [AI Chatbot Engine](#-ai-chatbot-engine)
12. [Sensor parametrlari va chegaralari](#-sensor-parametrlari-va-chegaralari)
13. [7 kunlik prognoz](#-7-kunlik-prognoz)
14. [Telegram bot](#-telegram-bot)
15. [Nosozlik buyurtma tizimi](#-nosozlik-buyurtma-tizimi)
16. [Toshkent tumanlari](#-toshkent-tumanlari)
17. [Premium UI qatlami](#-premium-ui-qatlami)
18. [Ko'p tilli interfeys](#-kop-tilli-interfeys)
19. [PWA — telefonga o'rnatish](#-pwa--telefonga-ornatish)
20. [Konsol skriptlari](#-konsol-skriptlari-scripts)
21. [Muammolarni hal qilish](#-muammolarni-hal-qilish)
22. [Xavfsizlik](#-xavfsizlik)
23. [Litsenziya](#-litsenziya)
24. [Muallif](#-muallif)

---

## 📋 Loyiha haqida

**ElectroGrid Monitoring** — Toshkent shahrining 12 tumanidagi **1,200 ta sensor**dan yig'ilgan **1,292,959 yozuv** asosida ishlaydigan to'liq monitoring tizimi.

Tizim 8 ta elektr va atrof-muhit parametrini real vaqtda kuzatadi, har bir sensorni 3 bosqichli xavf darajasi bo'yicha tasniflaydi, **gibrid AI model** (RandomForest + MLP) yordamida nosozlikni bashorat qiladi va **wttr.in + Open-Meteo** real ob-havo asosida 7 kunlik prognoz beradi. Foydalanuvchilar bot orqali GPS joylashuv bilan **nosozlik buyurtma** (ticket) bera oladi; buyurtmalar saytda ko'rinadi. Rejalashtirilgan xabarlarning ishlash shartlari Telegram bot bo'limida berilgan.

### Loyihaning kuchli tomonlari

| | |
|---|---|
| ⚡ **Real-time** | Har 30 sekundda yangilanish, jonli status bar |
| 🧠 **Hybrid AI** | RandomForest + MLP soft-voting, ishonch foizi va matnli tahlil |
| 🌦️ **Real ob-havo** | wttr.in + Open-Meteo ikki manba (Toshkent haqiqiy ma'lumot) |
| 🤖 **Telegram bot** | 5 bo'limli menyu, 4 asosiy command, sensor dialogi, ticket |
| 🛠️ **Ticket tizimi** | GPS + rasm + daraja bilan buyurtma, admin bildirishnoma |
| 💬 **AI Chatbot** | 24 intent, O'zbek/Kirill/Rus, professional NLU dvigateli |
| 🎨 **Premium UI** | Glassmorphism, animatsiyalar, command palette (Ctrl+K), toast |
| 📱 **PWA** | Telefon/desktopga o'rnatiladi, offline manifest |
| 🌐 **Ko'p tilli** | Lotin / Kirill (147+ so'z lug'ati, MutationObserver) |
| 📊 **Eksport** | CSV, PDF, Excel-mos format |

---

## 🆕 Yangiliklar (v3.0)

### 🛠️ Nosozlik Buyurtma Tizimi (yangi)
- Bot orqali GPS joylashuv bilan ticket berish
- Daraja tanlash: 🔴 Kritik / 🟡 O'rta / 🟢 Past
- Rasm biriktirish va saytda ko'rsatish
- GPS asosida eng yaqin sensorni avtomatik aniqlash
- Admin Telegram bildirishnomasi (joylashuv pin + rasm + tugmalar)
- `⚙️ Jarayonga o'tkazish` / `✅ Yopish` admin tugmalari botda

### 💬 AI Chatbot yangilandi
- 13 → **24 ta intent**
- Vibratsiya, namlik, sim holati, chastota, quvvat — yangi parametrlar
- O'zbek Kirill to'liq qo'llab-quvvatlash
- Kontekstli aniqlash: "Chilonzorda muammo bormi?" → district + danger
- Har parametr uchun chegara tahlili (🟢/🟡/🔴 ko'rsatkich)

### 📡 Ma'lumotlar yangilandi
- 1,200,000 → **1,292,959 yozuv** (+92,959)
- 2026-04-23 → **2026-06-26** gacha uzaytirildi
- Iyun: harorat ~32°C, namlik ~22% (Toshkent yoz) ✅

### 🌤️ Ob-havo aniqroq
- **wttr.in** asosiy manba (haqiqiy stansiya ma'lumoti)
- Open-Meteo zaxira sifatida
- Sayt widgeti uchun disk kesh 15 daqiqa, endpoint kesh 5 daqiqa
- Bot Prognoz tugmasi Open-Meteo'dan har so'rovda yangi javob oladi
- `feels_like`, `cloud`, `description` — yangi maydonlar

### 🗺️ Xarita yaxshilandi
- `fitBounds` — sensorlar avtomatik ko'rinish maydoni
- `preferCanvas` — 1200 marker tezkor render
- Markerlar yuklanib bo'lgach avtomatik zoom

### 🌐 Ko'p tilli (Lotin/Kirill)
- 80 → **147+ ta lug'at kiritma**
- Barcha sahifa sarlavhalari, oylar, parametr nomlari
- Kichik/Katta harf variantlari (`havfsiz`, `HAVFSIZ`, `Havfsiz`)
- `⏭️ O'tkazib yuborish` bilan joylashuv skip

### 🤖 Bot yangiliklari
- Bosh menyuda 5 ta bo'lim; odatiy amallar tugmalar orqali bajariladi
- `/start, /menu, /help, /cancel` — foydalanuvchi command menyusi
- Nosozlik bildirish: joylashuv, sensor, daraja, tavsif, rasm, tasdiqlash
- Noma'lum buyruq yoki matn → Bosh menyu va Yordam tugmalari
- Sensor ID normallashtirish: `S001` → `S0001` avtomatik
- Admin bildirishnoma: GPS + rasm + sensor holati + tugmalar

---

## ✨ Asosiy imkoniyatlar

| # | Modul | Tavsif |
|---|---|---|
| 📊 | **Real-time Dashboard** | KPI kartalar, jonli sensorlar, trend grafiklar, ob-havo widget |
| 🗺️ | **Interaktiv Xarita** | Leaflet, 1200 sensor, heatmap, klaster, fitBounds, popup sparkline |
| 📈 | **Grafiklar** | 8 parametr trend, multi-axis, sensor taqqoslash, tarix tahlili |
| 📋 | **Jadval** | 1.3M qator, server-side pagination, sort, multi-filter, CSV eksport |
| 🧠 | **AI Model** | Hybrid VotingClassifier, ishonch %, matnli xulosa, parametr tavsiya |
| 🔮 | **7 kunlik Prognoz** | wttr.in + Open-Meteo + AI, 28 nuqta, kunlik xulosa kartalar |
| 🆚 | **Solishtirish** | Ikki sensor / tumanni yonma-yon taqqoslash |
| 📅 | **Kalendar** | Texnik xizmat va inspeksiya rejasi |
| 🎫 | **Tiketlar** | GPS + rasm + daraja bilan nosozlik ticket tizimi |
| 💬 | **AI Chatbot** | 24 intent NLU, O'zbek/Kirill/Rus, professional javoblar |
| 🛠️ | **Audit jurnali** | Foydalanuvchi harakatlari log |
| 🤖 | **Telegram Bot** | Tugmali menyu, sensor grafiklari, ticket, ro'yxatdan o'tish |
| 🔐 | **Auth + Rollar** | Session-based login, admin / operator, bcrypt |
| 🌙 | **Dark/Light** | Premium tema, manifest theme-color sinxron |
| 📱 | **Responsive + PWA** | Mobile/tablet/desktop, telefonga o'rnatish |
| ⌨️ | **Command Palette** | `Ctrl+K` orqali tezkor navigatsiya |
| 🌐 | **Ko'p tilli** | Lotin ↔ Kirill (147+ lug'at, dinamik DOM tarjima) |

---

## 🛠️ Texnologiyalar steki

### Backend

| Kutubxona | Versiya | Vazifasi |
|---|---|---|
| **Python** | 3.14.7 (tekshirilgan) | Asosiy til |
| **Flask** | 3.0.0 | Web server, API, Jinja2 |
| **Flask-Caching** | 2.3.1 | Server javoblarini keshlash |
| **Flask-Limiter** | 4.1.1 | API rate-limit (200/min) |
| **Flask-SocketIO** | 5.3.6 | WebSocket real-time push |
| **bcrypt** | 5.0.0 | Parol xeshlash |
| **pandas** | 3.0.2 | Ma'lumotlarni qayta ishlash |
| **numpy** | 2.4.4 | Hisoblash, AR(1) simulyatsiya |
| **pyarrow** | 24.x | Parquet format (10× CSV'dan tez) |
| **scikit-learn** | 1.8 | RandomForest + MLP VotingClassifier |
| **matplotlib** | 3.x | Bot uchun PNG grafiklar |
| **python-telegram-bot** | 21.3 | Telegram bot, ConversationHandler |
| **requests** | 2.31 | wttr.in + Open-Meteo API |
| **python-dotenv** | 1.x | `.env` fayl o'qish |

### Frontend

| Texnologiya | Versiya | Vazifasi |
|---|---|---|
| **Bootstrap** | 5.3 | UI framework, grid, modal |
| **Leaflet.js** | 1.9.4 | Interaktiv xarita, GPS |
| **Leaflet.heat** | 0.2.0 | Heatmap qatlami |
| **Leaflet.markercluster** | 1.5.3 | Sensor klasterlash |
| **Plotly.js** | 2.26 | Interaktiv grafiklar |
| **Font Awesome** | 6.4 | 1500+ ikonka |
| **Inter** | — | Premium Google Font |
| **CartoDB** | — | Xarita plitka manba |

---

## 📁 Loyiha tuzilmasi

```
BMI_models/
├── run.py                          # Sayt va botni birgalikda boshqarish
├── app.py                          # Flask server, 50+ API va sahifalar
├── chatbot_engine.py               # AI Chatbot NLU (24 intent, 3 til)
├── telegram_bot.py                 # Tugmali Telegram bot, sensor va ticket dialoglari
├── config.py                       # Sensor chegaralari, port, yo'llar
├── utils.py                        # Yordamchi: ticket, alert, incident, GPS
├── train_model.py                  # AI modelni o'qitish skripti
├── requirements.txt                # Python paketlar
├── .env.example                    # Maxfiy qiymatlarsiz sozlamalar namunasi
├── tests/                          # Bot, launcher va muhit regressiya testlari
├── users.json                      # Bot foydalanuvchilari (telefon, tuman, GPS)
├── subscribers.json                # Auto-alert obunachilari
│
├── data/
│   ├── sensor_data.parquet         # 1,292,959 yozuv (asosiy, tez yuklash)
│   ├── sensor_data_part1.csv       # CSV qism 1 (zaxira)
│   ├── sensor_data_part2.csv       # CSV qism 2 (zaxira)
│   ├── tickets.json                # Nosozlik buyurtmalari
│   ├── alert_state.json            # Faol ogohlantirishlar
│   ├── incidents.json              # Hodisalar tarixi
│   ├── maintenance.json            # Texnik xizmat rejasi
│   └── tashkent_weather_cache.json # Ob-havo keshi (15 daqiqa)
│
├── models/
│   ├── hybrid_model_part1.pkl      # Hybrid AI model (qism 1)
│   └── hybrid_model_part2.pkl      # Hybrid AI model (qism 2)
│
├── logs/
│   ├── app.log                     # Server loglari
│   └── audit.json                  # Foydalanuvchi harakatlari
│
├── scripts/
│   ├── generate_data.py            # CSV ma'lumot generatsiyasi
│   ├── extend_data_to_june.py      # Ma'lumotni 2026-06-26 gacha uzaytirish
│   ├── csv_to_parquet.py           # CSV → Parquet konvertatsiya
│   ├── generate_result_image.py    # AI tahlil natijasi rasmini yaratish
│   ├── test_chatbot.py             # Chatbot engine unit test
│   ├── bmi_model.py                # Modelni alohida sinash
│   ├── fix_coordinates.py          # GPS koordinatalarni tekshirish
│   └── test_pages.py               # Barcha sahifalarni HTTP-test
│
├── templates/                      # Jinja2 HTML (16 ta sahifa)
│   ├── navbar.html                 # Navbar + til switcher + chatbot widget
│   ├── index.html                  # Bosh sahifa (harita + statistika)
│   ├── map.html                    # Leaflet xarita (klaster + heatmap)
│   ├── table.html                  # Jadval (pagination + sort + filter)
│   ├── graphs.html                 # Trend grafiklar (8 parametr)
│   ├── model.html                  # AI tahlil va prognoz
│   ├── forecast.html               # 7 kunlik kelajak prognozi
│   ├── compare.html                # Sensor/tuman solishtirish
│   ├── sensor_detail.html          # Bitta sensor tafsiloti
│   ├── tickets.html                # Nosozlik buyurtmalari (GPS + rasm)
│   ├── calendar.html               # Texnik xizmat kalendari
│   ├── audit.html                  # Audit jurnali (faqat admin)
│   ├── login.html                  # Kirish sahifasi
│   ├── user_home.html              # Operator bosh sahifasi
│   └── error.html                  # 403/404/500 xato sahifasi
│
└── static/
    ├── style.css                   # Dizayn tizimi (CSS tokens, kartalar)
    ├── enhance.css                 # Premium: glassmorphism, animatsiya
    ├── enhance.js                  # JS: counter, ripple, palette, toast
    ├── theme.js                    # Dark/Light toggle + sinxronizatsiya
    ├── sw.js                       # Service Worker (PWA offline)
    ├── manifest.json               # PWA manifest
    ├── result_preview.png          # AI tahlil natijasi namuna rasmı
    ├── ticket_photos/              # Bot orqali yuborilgan rasm fayllar
    ├── bg-tashkent.svg             # Premium animatsiyali fon
    ├── icon.svg / icon-192.png / icon-512.png  # PWA ikonkalar
    └── icons/                      # Ijtimoiy tarmoq va kontakt ikonkalari
```

---

## 🚀 O'rnatish va ishga tushirish

### Tayyor loyihani ochish

IDE'da loyiha interpreterini tanlang va **run.py → Run** bosing.
**app.py → Run** yoki **telegram_bot.py → Run** ham sayt va botni birga ochadi.

Terminalda loyiha papkasidan, kerakli Python muhiti bilan:

```powershell
python run.py
```

1. Launcher avval saytni ochadi va `/healthz` javobini kutadi.
2. Sayt tayyor bo'lgach, Telegram bot shu interpreter bilan ochiladi.
3. Brauzerda **http://localhost:5000** manzilini oching.
4. Telegram'da botga `/start` yoki `/menu` yuboring.
5. Ishga tushirgan terminalda **Ctrl+C** bosing — sayt va bot to'xtaydi.

Bir loyiha uchun bitta launcher ishlaydi. Qayta Run bosilganda
`Sayt va bot allaqachon ishga tushirilgan` xabari chiqadi va takroriy jarayon ochilmaydi.
Ikkalasidan biri to'xtasa, launcher ikkinchisini ham yopadi.
Bu tartib Python faylini bevosita ishga tushirish uchun; `flask run` umumiy launcherni chaqirmaydi.

### Talablar va sozlamalar

- Loyiha **Python 3.14.7** va **python-telegram-bot 21.3** bilan tekshirilgan.
  Botda startup sloti va event loop uchun lokal moslik tuzatishlari mavjud.
- Kutubxonalar `requirements.txt` bo'yicha o'rnatiladi.
- Telegram va ob-havo API uchun internet kerak.
- Sensor ma'lumotlari `data/`, tayyor model `models/` papkasida bo'lishi kerak.

Mavjud `.env` faylini saqlang. Yangi o'rnatishda `.env.example` nusxasidan `.env` yarating
va qiymatlarni mahalliy sozlang:

| Sozlama | Vazifasi |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather bergan bot tokeni |
| `PORT` | Sayt porti; standart qiymat `5000` |
| `HOST` | Server manzili; standart qiymat `0.0.0.0` |
| `SITE_BASE` | Bot ishlatadigan sayt URL'i |
| `TELEGRAM_ADMIN_IDS` | Bot adminlarining raqamli Telegram ID'lari, vergul bilan ajratiladi |

`SITE_BASE` berilmasa, launcher uni `http://127.0.0.1:<PORT>` qilib o'rnatadi.
Mavjud `SITE_BASE` qiymati saqlanadi. `PORT=5001` bo'lsa va `SITE_BASE` ham yozilgan bo'lsa,
uning portini ham moslang.

Sayt va bot bir loyiha papkasi hamda bir xil sozlamalar bilan ishlaydi.
Bot yuborgan ticketlar saytdagi `/tickets` bo'limiga tushadi.
`localhost` server kompyuteriga tegishli; boshqa qurilmadan sayt ochilishi uchun
yetib boriladigan sayt URL'ini `SITE_BASE` sifatida belgilang.

### Windows: yangi o'rnatish

```powershell
git clone https://github.com/ShoxGit19/BMI_models.git
cd BMI_models

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Mavjud .env ustiga yozilmaydi.
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
# .env qiymatlarini mahalliy sozlang, keyin:
python run.py
```

Windows'da `python` Microsoft Store oynasini taklif qilsa yoki topilmasa,
IDE'da ishlayotgan interpreter bilan Run qiling. Mazkur kompyuterda tekshirilgan
uv interpretori uchun:

```powershell
$projectPython = Join-Path $env:APPDATA 'uv\python\cpython-3.14.7-windows-x86_64-none\python.exe'
& $projectPython -X utf8 -B run.py
```

Bu yo'l faqat shu uv interpretori o'rnatilgan kompyuter uchun.
Tayyor model fayllari mavjud bo'lsa, qayta o'qitish talab qilinmaydi.
Model yetishmasa, `python train_model.py` ni alohida bajaring.

### Linux / macOS: yangi o'rnatish

```bash
git clone https://github.com/ShoxGit19/BMI_models.git
cd BMI_models
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
test -f .env || cp .env.example .env
# .env qiymatlarini mahalliy sozlang, keyin:
python run.py
```

### Tekshirish

Sayt holati: **http://localhost:5000/healthz**.
`status: ok` server ishlayotganini bildiradi; `data_loaded` va `model_loaded`
ma'lumot hamda model yuklanganini ko'rsatadi.

Mavjud test muhitida:

```powershell
python -m pytest tests -q -p no:cacheprovider
```

Testlar uchun `pytest` kerak. 2026-10-12 kuni Python 3.14.7 muhitida
**46 ta test va 2 ta subtest o'tgan**. Grafik shriftlari va PTB dialog sozlamalariga
oid warninglar mavjud.

---

## 🔐 Demo kirish

| Foydalanuvchi | Parol | Rol |
|---|---|---|
| `admin` | `admin123` | 👑 Administrator — barcha sahifalar |
| `operator` | `operator123` | 👤 Operator — faqat o'qish |

> ⚠️ **Production'da** demo parollarni darhol o'zgartiring.

---

## 🌐 Web sahifalar

| Sahifa | URL | Tavsifi |
|---|---|---|
| Kirish | `/login` | Animatsiyali fon, bcrypt autentifikatsiya |
| Bosh sahifa | `/` | KPI statistika, xarita, tumanlar, ob-havo |
| Xarita | `/map` | 1200 sensor, heatmap, klaster, polygon, GPS eksport |
| Jadval | `/table` | Pagination, sort, multi-filter, CSV eksport |
| Grafiklar | `/graphs` | 8 parametr trend, vaqt oralig'i filter |
| AI Model | `/model` | 8 parametr → hybrid AI xulosa + tavsiyalar |
| Prognoz | `/forecast` | 7 kunlik AI + ob-havo bashorat, 28 nuqta |
| Solishtirish | `/compare` | Ikki sensor yoki tuman yonma-yon |
| Sensor | `/sensor/<id>` | Sensor grafik, tarix, holat tahlili |
| Tiketlar | `/tickets` | Nosozlik buyurtmalari (GPS, rasm, daraja) |
| Kalendar | `/calendar` | Texnik xizmat rejasi va avariyalar |
| Audit | `/audit` | Foydalanuvchi harakatlari (faqat admin) |

---

## 📡 API endpointlar

| Endpoint | Metod | Tavsifi |
|---|---|---|
| `/api/stats` | GET | Dashboard statistika (sensor holat, o'rtacha) |
| `/api/data` | GET | Sensorlar (`?page=&per_page=&district=`) |
| `/api/graph-data` | GET | Grafik uchun 1000 nuqta |
| `/api/map-data` | GET | Har sensorning so'nggi holati + koordinata |
| `/api/sensor/<id>` | GET | Sensor oxirgi 100 o'qish + tarix |
| `/api/sensor-spark/<id>` | GET | Sparkline 30 ta kuchlanish qiymati |
| `/api/forecast` | GET | 7 kunlik ob-havo (`?latitude=&longitude=`) |
| `/api/future-forecast` | GET | AI + ob-havo 28 nuqtali kelajak prognoz |
| `/api/forecast-params` | GET | Parametr trendi (`?param=Kuchlanish (V)`) |
| `/api/weather` | GET | Hozirgi ob-havo (wttr.in + Open-Meteo) |
| `/api/tickets` | GET/POST | Ticket CRUD (bot token orqali ham) |
| `/api/tickets/<id>/update` | POST | ETA, status, izoh yangilash (admin) |
| `/api/tickets/<id>/close` | POST | Ticketni yopish (admin) |
| `/api/compare` | GET | Ikki tuman/sensor taqqoslash (`?type=&a=&b=`) |
| `/api/chatbot` | POST | AI chatbot (`{question: "..."}`) |
| `/api/export/csv` | GET | CSV eksport |
| `/api/export/map-csv` | GET | Xarita CSV (`?district=&only_faults=1`) |
| `/api/reload-model` | GET | Modelni qayta yuklash (admin) |
| `/api/set-language` | POST | Til o'zgartirish (`{lang: "uz_cyr"}`) |

### Chatbot API namunasi

```bash
curl -X POST http://localhost:5000/api/chatbot \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION" \
  -d '{"question": "Chilonzorda xavfli sensorlar bormi?"}'
```

```json
{
  "text": "🔴 **11 ta xavfli sensor** (Chilonzor)...",
  "cards": [{"title": "S0123", "subtitle": "Chilonzor · 198.2V"}],
  "quick_replies": ["Xaritada ko'rish", "Statistika"],
  "intent": "danger_list",
  "confidence": 7
}
```

---

## 🧠 AI Model

### Arxitektura

```
Kirish (8 parametr)
       │
       ▼
 StandardScaler
       │
       ▼
┌─────────────────────────────────────────┐
│  RandomForestClassifier (100 daraxt)    │
│              +                          │
│  MLPClassifier (128 → 64 yashirin qatl) │
│           soft-voting (0.4:0.6)         │
└─────────────────────────────────────────┘
       │
       ▼
 Natija: 0/1/2 + ishonch foizi (%)
       │
       ▼
 Matnli xulosa + parametr tahlili + tavsiyalar
```

### Sinf darajalari

| Kod | Nom | Rang | Ma'no |
|---|---|---|---|
| `0` | safe | 🟢 | Barcha parametrlar normal chegarada |
| `1` | warning | 🟡 | Bir yoki bir nechta parametr ogoh zonada |
| `2` | danger | 🔴 | Kritik chegaradan tashqarida — zudlik bilan tekshirish |

### Modelni qayta o'qitish

```bash
python train_model.py
# Konsol: Accuracy, Precision, Recall, F1 metrika chiqadi
# Natija: models/hybrid_model_part1.pkl + part2.pkl
```

---

## 💬 AI Chatbot Engine

`chatbot_engine.py` — professional NLU dvigateli. Saytdagi chatbot paneliga integratsiyalashgan.

### Qo'llab-quvvatlanadigan intentlar (24 ta)

| Guruh | Intentlar |
|---|---|
| **Umumiy** | greeting, help, stats, averages |
| **Holat** | danger_list, warning_list, safe_list |
| **Kuchlanish** | voltage_low, voltage_high, voltage_info |
| **Parametrlar** | temperature_high, temperature_info, vibration_high, wire_low, humidity_check, frequency_check, power_check |
| **Qidiruv** | sensor_info, district_info, compare_districts, top_danger, top_voltage_low, top_temperature |
| **Tahlil** | recent_faults, forecast_info, weather, tickets_info, map_info |

### Namuna so'rovlar

```
"Salom"                          → Salomlashish + tizim holati
"Statistika"                     → Jami sensor, holat foizlari, o'rtachalar
"Chilonzorda muammo bormi?"      → Tuman + nosozlik → 11 ta xavfli sensor
"S0045 holati"                   → Sensor barcha parametrlari (🟢/🟡/🔴)
"Kuchlanish 200V dan past"       → Filtrlanagan sensor ro'yxati + kartalar
"So'nggi nosozliklar"            → 24 soatdagi hodisalar
"Eng past kuchlanishli sensor"   → Top 5 ro'yxat
"Vibratsiya yuqori sensorlar"    → 1.0 dan oshgan sensorlar
"O'rtacha ko'rsatkichlar"        → 8 parametr o'rtachalari
"Chastota holati"                → Normal/ogohlantirish/xavf taqsimoti
```

### Til qo'llab-quvvatlash

- ✅ O'zbek Lotin (asosiy)
- ✅ O'zbek Kirill (barcha kalit so'zlar)
- ✅ Rus tili (statistika, tumanlar, parametrlar)
- ✅ Ingliz tili (voltage, sensor, danger, warning)

---

## 📏 Sensor parametrlari va chegaralari

| Parametr | Birlik | 🟢 Normal | 🟡 Ogohlantirish | 🔴 Xavfli |
|---|---|---|---|---|
| **Kuchlanish** | V | 210–230 | 200–210 / 230–240 | < 200 yoki > 240 |
| **Chastota** | Hz | 49.5–50.5 | 49.0–49.5 / 50.5–51.0 | < 49.0 yoki > 51.0 |
| **Harorat** | °C | < 40 | 40–45 | > 45 |
| **Shamol** | km/h | < 15 | 15–25 | > 25 |
| **Vibratsiya** | — | < 1.0 | 1.0–1.5 | > 1.5 |
| **Sim holati** | % | > 85 | 75–85 | < 75 |
| **Namlik** | % | 35–85 | 30–35 / 85–90 | < 30 yoki > 90 |
| **Quvvat** | kW | ≤ 5.0 | 5.0–5.5 | > 5.5 |

---

## 🔮 7 kunlik prognoz

Quyidagi AI oqimi saytdagi prognozga tegishli. Botning Prognoz tugmasi Open-Meteo ob-havosini ko'rsatadi; uning tafsilotlari Telegram bot bo'limida yozilgan.

```
1. Real ob-havo (wttr.in + Open-Meteo) → harorat, shamol, namlik
2. AR(1) trend modeli → chastota, kuchlanish, vibratsiya, sim, quvvat
3. Har 6 soatlik nuqta (28 ta jami)
4. Hybrid AI → har nuqta uchun xavf bashorat (0/1/2)
5. Kunlik xulosa → eng xavfli soat, o'rtacha risk %
```

**Natija**: 28 nuqtali grafik + 7 kunlik xulosa kartalar + timeline strip + batafsil jadval.

---

## 🤖 Telegram Bot

### Ro'yxatdan o'tish

```
/start
  → Telefon raqami
  → Ism va familiya
  → Tuman
  → Joylashuv (ixtiyoriy)
  → Web tizimi uchun login/parol
  → Bosh menyu
```

### Bosh menyu

| Bo'lim | Tugmalar orqali bajariladigan amallar |
|---|---|
| **Monitoring** | Dashboard, umumiy statistika, muammoli sensorlar |
| **Sensorlar** | ID yuborish → sensor holati → grafik yoki tarix |
| **Prognoz** | Joriy ob-havo va 7 kunlik prognoz |
| **Nosozlik bildirish** | Joylashuv, sensor, daraja, tavsif, rasm va tasdiqlash |
| **Sozlamalar va yordam** | Alert obunasi, sokin rejim, yordam |

Sensor ID uchun `S0001`, `s1` yoki `1` yuborish mumkin.
Sensor topilmasa, ID noto'g'ri bo'lsa yoki ma'lumot yuklanmagan bo'lsa, bot aniq xabar beradi.
Bo'limlardan **Bosh menyu** tugmasi bilan qaytiladi.
Dialog paytida bu tugma yoki `/menu` joriy jarayonni tugatadi;
`/cancel` ham jarayonni bekor qilib menyuni ochadi.
Noma'lum matn va commandlar uzun buyruqlar ro'yxatini chiqarmaydi.

### Foydalanuvchi commandlari

Telegram command menyusida faqat quyidagi to'rtta buyruq ko'rinadi:

| Buyruq | Vazifasi |
|---|---|
| `/start` | Ro'yxatdan o'tish yoki botni boshlash |
| `/menu` | Bosh menyu; faol dialogni tugatish |
| `/help` | Qisqa foydalanish yordami |
| `/cancel` | Joriy dialogni bekor qilish |

BotFather'da `/setcommands` uchun:

```text
start - Botni boshlash
menu - Bosh menyu
help - Yordam
cancel - Joriy jarayonni bekor qilish
```

Bot ishga tushganda commandlar `BotCommand` orqali ham o'rnatiladi.

### Bot ob-havosi

**Prognoz** tugmasi va saqlangan `/weather` commandi har so'rovda
[Open-Meteo API](https://open-meteo.com/en/docs) ga ulanadi.
Avval foydalanuvchining saqlangan koordinatasi, keyin tuman koordinatasi,
ular bo'lmasa Toshkent markazi ishlatiladi.

Ko'rsatiladigan qiymatlar: harorat (°C), nisbiy namlik (%), shamol (km/soat),
yog'ingarchilik (mm), API vaqti va 7 kunlik prognoz.
Havo quruqligi namlik asosida oddiy baholanadi:
**<30% — quruq; 30–60% — o'rtacha; >60% — nam**.
Bu botdagi baholash qoidasi.

API qiymati bo'lmasa **ma'lumot yo'q**, ulanish ishlamasa qayta urinish xabari chiqadi.
Sensor datasetidagi qiymatlar ob-havo API javobi o'rniga qo'yilmaydi.
Sayt ob-havo widgeti esa o'zining wttr.in/Open-Meteo va kesh oqimidan foydalanadi.

### Admin ruxsatlari

Botda admin huquqi foydalanuvchining saqlangan `role="admin"` qiymati
yoki `TELEGRAM_ADMIN_IDS` ro'yxatidagi Telegram ID orqali tekshiriladi.
Username admin huquqini bermaydi. Admin commandlari alohida chat scope'iga o'rnatiladi.

| Admin commandi | Vazifasi |
|---|---|
| `/admin` | Admin panel |
| `/tickets` | Ticketlar ro'yxati va boshqaruvi |
| `/broadcast <matn>` | Obunachilarga umumiy xabar |
| `/alert_test` | Alert sinovi |
| `/send_user <id> <matn>` | Foydalanuvchiga xabar |

Admin bo'lmagan foydalanuvchi bu commandlar va ticket boshqaruv callbacklarini ishlata olmaydi.

### Obuna va rejalashtirilgan xabarlar

Alert obunasi va sokin rejim **Sozlamalar va yordam** bo'limida o'zgartiriladi.
Sokin rejim qiymati saqlanadi; `alert_check` funksiyasi uni 22:00–07:00 oralig'ida tekshiradi.

Joriy startup kodi `JobQueue` mavjud bo'lsa faqat ertalabki hisobotni
**06:00, Asia/Tashkent** vaqtiga rejalashtiradi.
`alert_check` va `realtime_alert_check` mavjud, ammo startup'da rejalashtirilmagan.
`JobQueue` bo'lmasa rejalashtirilgan xabarlar ishlamaydi.
Kerak bo'lsa, faol interpreterda `python -m pip install "python-telegram-bot[job-queue]==21.3"`
orqali uni o'rnatib, loyihani qayta ishga tushiring.

<details>
<summary>Moslik uchun saqlangan eski commandlar</summary>

Bu handlerlar saqlangan, ammo oddiy foydalanuvchining Telegram command menyusida ko'rsatilmaydi.

| Buyruq | Tavsifi |
|---|---|
| `/stats` | Umumiy statistika |
| `/forecast` | 7 kunlik ob-havo prognozi |
| `/districts` | Tumanlar holati |
| `/sensor S0001` | Sensor tafsiloti + koordinata pin |
| `/chart S0001` | Sensor grafik PNG (4 parametr) |
| `/compare S0001 S0002` | Ikki sensor taqqoslash |
| `/district_compare A B` | Tumanlarni taqqoslash |
| `/history S0001 7` | Sensor tarixi (7 kun) |
| `/predict 30 7 50 220 0.5 90 60 3` | AI bashorat (8 parametr) |
| `/danger` | Muammoli sensorlar |
| `/top` | Top 10 xavfli sensor |
| `/averages` | O'rtacha qiymatlar |
| `/weather` | Hozirgi ob-havo |
| `/search Chilonzor` | Tuman qidiruv |
| `/filter danger` | Holat filtri (danger/warn/safe) |
| `/report` | PDF hisobot yuklash |
| `/map Chilonzor` | Tuman xaritasi + GPS pinlar |
| `/dashboard` | Vizual monitoring paneli |
| `/near_sensors` | GPS asosida eng yaqin sensorlar |
| `/risk` | 24 soat buzilish ehtimoli |
| `/zones` | Tumanlar xavf darajasi |
| **`/ticket`** | **🆕 Nosozlik buyurtma berish** |
| `/subscribe` | Auto-alert obunasi |
| `/unsubscribe` | Obunani bekor qilish |
| `/silent` | Sokin rejim on/off |
| `/ask <savol>` | AI chatbot (tabiiy til) |
| `/mylocation` | Saqlangan GPS joylashuvni ko'rish |

</details>

---

## 🛠️ Nosozlik Buyurtma Tizimi

Foydalanuvchilar bot orqali nosozlikni tizimga bildirishi mumkin. Jarayon:

```
"🛠️ Nosozlik bildirish" tugmasi (eski /ticket ham saqlangan)
         ↓
[1] Joylashuv yuborish yoki "GPS siz davom etish"
         ↓
[2] Sensor tanlash
    • GPS bo'lsa → 6 tagacha eng yaqin sensor ko'rinadi
    • GPS yo'q   → Tuman sensorlari ko'rinadi
    • ID bilmasa → "🤷 Sensor IDni bilmayman" → joylashuv yuboradi
                   Bot eng yaqin sensorni GPS asosida aniqlaydi
         ↓
[3] Daraja tanlash
    🔴 Kritik (zudlik bilan) / 🟡 O'rta (bugun) / 🟢 Past (reja bilan)
         ↓
[4] Muammo tavsifi yozish (min 10 belgi)
         ↓
[5] Rasm yuborish (ixtiyoriy)
    → Sayt /tickets sahifasida ko'rinadi
         ↓
[6] Tasdiqlash → Yuborish

NATIJA:
  ✅ Foydalanuvchi → "Buyurtma ID: T-20260626164800"
  📲 Admin Telegram → GPS pin + rasm + sensor holati + tugmalar:
     [⚙️ Jarayonga o'tkazish]  [✅ Yopish]
     [🗺 Google Maps]           [🧭 Yandex Maps]
  🌐 Sayt /tickets → GPS koordinata, rasm, daraja, kim/qachon
```

### Ticket maydonlari

| Maydon | Tavsifi |
|---|---|
| `sensor_id` | Sensor identifikatori (yoki UNKNOWN) |
| `priority` | `kritik` / `o'rta` / `past` |
| `issue` | Muammo tavsifi (matn) |
| `latitude`, `longitude` | GPS koordinata |
| `district` | Tuman nomi |
| `telegram_user` | Ism, telefon, username |
| `photo_url` | `/static/ticket_photos/T-xxx.jpg` |
| `source` | `bot` yoki `web` |
| `status` | `open` → `in_progress` → `closed` |

---

## 🗺️ Toshkent tumanlari

| Tuman | Lat | Lon | Sensorlar |
|---|---|---|---|
| Bektemir | 41.209 | 69.335 | 100 |
| Chilonzor | 41.256 | 69.204 | 100 |
| Mirabad | 41.276 | 69.256 | 100 |
| Mirobod | 41.286 | 69.264 | 100 |
| Mirzo Ulug'bek | 41.339 | 69.335 | 100 |
| Olmazor | 41.354 | 69.212 | 100 |
| Sergeli | 41.232 | 69.212 | 100 |
| Shayxontohur | 41.328 | 69.229 | 100 |
| Uchtepa | 41.300 | 69.184 | 100 |
| Yakkasaroy | 41.300 | 69.264 | 100 |
| Yashnobod | 41.339 | 69.335 | 100 |
| Yunusobod | 41.354 | 69.335 | 100 |

---

## 🎨 Premium UI qatlami

`enhance.css` + `enhance.js` orqali butun saytga avtomatik qo'shilgan:

| Imkoniyat | Qayerda ishlaydi |
|---|---|
| 🌫️ **Glassmorphism navbar** | Sticky, aylantirganda blur kuchayadi |
| ✨ **Fade-up animatsiya** | Har bir sahifa yuklanishida |
| 🎯 **3D tilt + lift** | `.card`, `.kpi-card`, `.stat-card` |
| 💧 **Ripple effekt** | Har bir tugma bosilganda |
| 🔢 **Counter animatsiyasi** | KPI raqamlar 0 dan haqiqiy soniga |
| 🟢 **Pulse status dot** | `<span class="eg-pulse-dot">` |
| 🔴 **LIVE badge** | Footer status bar |
| ⌨️ **Command Palette** | `Ctrl+K` — tezkor navigatsiya |
| 🔔 **Toast bildirishnoma** | `egToast({title, msg, type})` JS API |
| 📊 **Footer status bar** | Server / DB / Bot / Vaqt (jonli) |
| 💀 **Skeleton loader** | `<span class="eg-skeleton">` |

```js
// Toast API
egToast({ title: 'Saqlandi', msg: 'Buyurtma yuborildi', type: 'success' });
egToast({ title: 'Xato', msg: 'Server javob bermadi', type: 'error' });
// type: 'info' | 'success' | 'warning' | 'error'
```

---

## 🌐 Ko'p tilli interfeys

Navbar dagi `UZ | КР` tugmalari orqali Lotin ↔ Kirill almashtiriladi:

- **147+ lug'at kiritma** (barcha sahifalar, parametrlar, oylar)
- **MutationObserver** — AJAX bilan yuklanadigan kontent ham tarjima qilinadi
- **localStorage** — sahifalar o'rtasida til saqlandi
- **Regex** — uzun iboralar avval, keyin qisqaroqlari mos keladi

```js
// Tilni JavaScript dan o'zgartirish
fetch('/api/set-language', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({lang: 'uz_cyr'})
});
```

---

## 📱 PWA — telefonga o'rnatish

- `manifest.json` — ikonka, ranglar, standalone rejim
- `sw.js` — Service Worker (offline keshi)
- `icon.svg` + `icon-192.png` + `icon-512.png`

**O'rnatish (mobil):**
1. Chrome/Edge brauzerda saytni oching
2. ⋮ → **"Bosh ekranga qo'shish"** / **"Install"**
3. Sayt to'liq ekranda ilova sifatida ochiladi

---

## 🧰 Konsol skriptlari (`scripts/`)

| Skript | Vazifasi |
|---|---|
| `generate_data.py` | 1.2M yozuvli realistik CSV generatsiyasi |
| `extend_data_to_june.py` | Ma'lumotni 2026-06-26 gacha uzaytirish |
| `csv_to_parquet.py` | CSV → Parquet (10× tezroq, 21 MB) |
| `generate_result_image.py` | AI tahlil natijasi professional rasmi |
| `test_chatbot.py` | Chatbot engine 10 savol bilan test |
| `bmi_model.py` | Modelni alohida sinab ko'rish |
| `fix_coordinates.py` | Sensor GPS koordinatalarini tekshirish |
| `test_pages.py` | Barcha sahifalarni HTTP-test |

```powershell
# Ma'lumotni yangilash
python scripts\extend_data_to_june.py

# Chatbot testlash
python scripts\test_chatbot.py

# AI natijasi rasmi
python scripts\generate_result_image.py
```

---

## 🐛 Muammolarni hal qilish

| Muammo | Yechim |
|---|---|
| `FileNotFoundError: sensor_data.parquet` | `python scripts\csv_to_parquet.py` bajaring |
| `FileNotFoundError: models/*.pkl` | `python train_model.py` bajaring |
| Port 5000 band | Shu loyihaning eski jarayonini to'xtating yoki `PORT` va mavjud `SITE_BASE` portini moslang |
| Bot **401 Unauthorized** | `.env` da `TELEGRAM_BOT_TOKEN` ni tekshiring |
| Bot **Conflict 409** | Boshqa ishlayotgan bot sessiyasini to'xtating |
| Allaqachon ishga tushirilgan | Mavjud launcher ishlayapti; uning terminalida Ctrl+C bosib, keyin qayta Run qiling |
| Windows'da Python topilmayapti | IDE interpreterini tanlang yoki yuqoridagi uv interpreter buyrug'idan foydalaning |
| JobQueue yo'q | Menyu ishlaydi; rejalashtirilgan hisobot uchun JobQueue qo'shimchasini o'rnating |
| Admin commandi rad etildi | Raqamli Telegram ID yoki saqlangan admin rolini tekshiring; username yetarli emas |
| Ticket yuborilmayapti | `python run.py` bilan sayt va botni birga oching; `SITE_BASE` saytga olib borishini tekshiring |
| Xarita sensorlar burchakda | Sahifani `Ctrl+Shift+R` bilan yangilang |
| Bot ob-havosi olinmayapti | Internetni tekshirib Prognoz tugmasini qayta bosing; bot sensor qiymatlarini zaxira sifatida ishlatmaydi |
| Kirill tarjima ishlamaydi | `Ctrl+Shift+R` (cache tozalash), keyin `КР` tugmasini bosing |
| `ModuleNotFoundError` | `.venv` faol, `pip install -r requirements.txt` |
| `__stop_running_marker` | Yangilangan `telegram_bot.py` va loyiha interpreteridan foydalaning; lokal moslik tuzatishi mavjud |
| `﻿` BOM `.env` | `[System.IO.File]::WriteAllText(...)` ishlating |

---

## 🔒 Xavfsizlik

- ✅ **Session-based auth** — Flask session cookie, login required
- ✅ **bcrypt** — parol xeshlash (salt random, har sessiya yangi)
- ✅ **Rate-limit** — `Flask-Limiter`: 200/daqiqa, 2000/soat
- ✅ **Bot token** — API'ga `_bot_token` tekshiruvi
- ✅ **Admin dekorator** — `@admin_required` — 403 qaytaradi
- ✅ **XSS** — Jinja2 avto-escape, HTML sanitize JS
- ✅ **Audit log** — barcha login/logout/ticket/model harakatlar
- ⚠️ **Demo parollar** — production'da darhol o'zgartiring
- ⚠️ **`.env`** — `gitignore` ichida bo'lishi shart

---

## 📄 Litsenziya

**MIT License** — erkin foydalanish, o'zgartirish va tarqatish mumkin.

```
Copyright (c) 2024–2026 G'aybullayev Shohjahon
```

---

## 👤 Muallif

<div align="center">

### G'aybullayev Shohjahon

**🌍 Toshkent · Bekobod · 2026**

**Bitiruv malakaviy ishi — Sun'iy intellekt asosida elektr tarmog'i monitoringi**

[![Telegram](https://img.shields.io/badge/Telegram-@gaybullayeev19-2CA5E0?logo=telegram&logoColor=white)](https://t.me/gaybullayeev19)
[![GitHub](https://img.shields.io/badge/GitHub-ShoxGit19-181717?logo=github&logoColor=white)](https://github.com/ShoxGit19)
[![Instagram](https://img.shields.io/badge/Instagram-@ShoxGit19-E4405F?logo=instagram&logoColor=white)](https://instagram.com/ShoxGit19)

</div>

---

<div align="center">

**⚡ ElectroGrid Monitoring System · v3.0 · Toshkent · 2026**

*1,292,959 sensor yozuvi · 12 tuman · Hybrid AI · Ticket tizimi · Real-time · PWA*

⭐ **Loyiha sizga foydali bo'lsa — yulduzcha qoldiring!**

</div>
