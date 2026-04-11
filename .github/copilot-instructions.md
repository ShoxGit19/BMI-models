# 🧑‍💻 Copilot Ishchi Ko‘rsatmalari — BMI_models

## Maqsad
Ushbu workspace — Toshkent elektr uzatish liniyalari uchun real vaqt monitoring va sunʼiy intellekt asosida bashorat qilish tizimi. Loyihada zamonaviy dashboardlar, gibrid AI modeli va Telegram bot orqali ogohlantirishlar va tahlil mavjud.

## Asosiy Qoidalar
- **Flask** — asosiy web server (`app.py`).
- **AI modeli** — VotingClassifier (RandomForest + MLP), `train_model.py` orqali o‘qitiladi va web hamda Telegram botda ishlatiladi.
- **Maʼlumotlar** — GitHub cheklovi sababli `data/` papkasida ikkita katta CSV faylga bo‘lingan.
- **scripts/** — Maʼlumot generatsiyasi, tozalash, tahlil va modelni tekshirish uchun yordamchi skriptlar.
- **templates/** va **static/** — Flask uchun HTML va CSS fayllar.
- **config.py** — Barcha konfiguratsiya (chegaralar, fayl yo‘llari va boshqalar) shu faylda.
- **Demo login/parollar** — Test uchun kodda qattiq yozilgan (README-ga qarang).
- **Maxfiy sozlamalar**: `.env` faylida (masalan, Telegram bot tokeni).

## O‘rnatish va Ishga Tushirish
- **O‘rnatish**: `pip install -r requirements.txt`
- **Modelni o‘qitish**: `python train_model.py` (birinchi ishga tushirishdan oldin)
- **Serverni ishga tushirish**: `python app.py` (Flask va Telegram bot birga)
- **Bot**: Telegram bot server bilan birga ishga tushadi.
- **Maʼlumotlar**: `sensor_data_part1.csv` va `sensor_data_part2.csv` fayllarini `data/` papkasiga joylashtiring.

## Loyiha Tuzilmasi
- `app.py` — Flask server, API va web yo‘llar
- `train_model.py` — Modelni o‘qitish
- `telegram_bot.py` — Telegram bot logikasi
- `config.py` — Markaziy konfiguratsiya
- `scripts/` — Maʼlumot va model uchun yordamchi skriptlar
- `models/` — O‘qitilgan model fayllari (pkl)
- `templates/` — HTML (Jinja2)
- `static/` — CSS/rasmlar

## Ko‘p Uchraydigan Muammolar
- **Maʼlumot/model fayllari yo‘q**: README-dagi troubleshooting bo‘limiga qarang
- **Port band**: `config.py` da `PORT` ni o‘zgartiring
- **Bot ishlamayapti**: `.env` faylini va faqat bitta bot ishlayotganini tekshiring
- **Katta CSV fayllar**: Git orqali kuzatilmaydi, qo‘lda joylashtirish kerak

## Qanday Kengaytirish Mumkin
- `scripts/` papkasiga yangi tahlil yoki monitoring funksiyasi qo‘shish
- `train_model.py` ni o‘zgartirib, modelni qayta o‘qitish
- `app.py` ga yangi API endpointlar qo‘shish
- Yangi web sahifa uchun template va route qo‘shish

## Qo‘shimcha Maʼlumot
- [README.md](README.md) — To‘liq loyiha tavsifi, o‘rnatish va foydalanish

---

### Namuna So‘rovlar
- "AI modelini yangi maʼlumot bilan qanday qayta o‘qitaman?"
- "Dashboardga yangi sensor parametrini qanday qo‘shaman?"
- "Har bir sensor uchun to‘g‘ri qiymatlar oraliqlari qanday?"
- "Bir tumandagi barcha sensor maʼlumotini qanday eksport qilaman?"

---

### Keyingi: Agent Sozlamalari
- **/create-instruction**: Data science skriptlar uchun maxsus ko‘rsatmalar (masalan, faqat `scripts/` uchun)
- **/create-agent**: Modelni tekshirish yoki maʼlumot tozalash uchun maxsus agent
- **/create-prompt**: Tez-tez uchraydigan muammolar yoki kengaytirish uchun namuna so‘rovlar

Bu sozlamalar workspace uchun tez va samarali ish jarayonini taʼminlaydi.
