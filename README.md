# 🚀 Telegram Video Bot v2 — Production Ready

> **Aiogram 3 + PostgreSQL + Redis** asosida yozilgan professional bot

---

## 📁 Loyiha strukturasi

```
bot_v2/
├── main.py                  ← Entry point (polling / webhook)
├── config.py                ← Barcha konfiguratsiyalar
├── database.py              ← PostgreSQL (asyncpg)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml       ← Local dev (PG + Redis + Bot)
├── .env.example
│
├── handlers/
│   ├── user.py              ← /start, video kodi, like/dislike, referral
│   └── admin.py             ← Admin panel (inline), broadcast, ban, chart
│
├── keyboards/
│   └── inline.py            ← Barcha inline klaviaturalar
│
├── middlewares/
│   ├── anti_spam.py         ← Sliding-window rate limiter
│   └── user_tracker.py      ← User DB ga yozish + ban tekshirish
│
└── services/
    ├── cache.py             ← Redis cache (sub, ban, video, broadcast)
    ├── subscription.py      ← Kanal obuna tekshirish (cache-first)
    ├── broadcast.py         ← Mass xabar yuborish (live progress)
    └── charts.py            ← Matplotlib grafik generatsiya
```

---

## ⚡ Ishga tushirish

### 1. Docker Compose (tavsiya etiladi)

```bash
git clone <repo> && cd bot_v2
cp .env.example .env
# .env ni to'ldiring (BOT_TOKEN, ADMIN_IDS, REQUIRED_CHANNELS)
docker-compose up -d
```

### 2. Manual (local)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # to'ldiring
python main.py
```

---

## 🤖 Funksiyalar

### Foydalanuvchi
| Amal | Tavsif |
|------|--------|
| `/start` | Botni boshlash, referral link olish |
| `/start ref_ID` | Referral orqali kirish |
| Raqam yozish | Video olish (ko'rishlar hisoblanadi) |
| 👍 / 👎 | Like/dislike (1 marta, o'zgartirish mumkin) |

### Admin (faqat ADMIN_IDS uchun)
| Buyruq / Tugma | Tavsif |
|----------------|--------|
| `/admin` | Inline admin panel |
| 📹 Video qo'sh | FSM orqali video qo'shish |
| 📊 Statistika | To'liq bot statistikasi |
| 📈 Grafik | 7 kunlik matplotlib grafik |
| 📋 Video ro'yxat | Barcha videolar (ko'rish, like, dislike) |
| 📨 Broadcast | Mass xabar (preview + tasdiqlash) |
| 🚫 Ban | Foydalanuvchi ban qilish |
| ✅ Unban | Banni ochish |
| 🏆 Top referrallar | Top 10 referrer |

---

## 🛡️ Xavfsizlik

- **Majburiy obuna** — 3 ta kanal, Redis cache (60s TTL)
- **Ban tizimi** — DB + Redis cache, real-vaqt blok
- **Anti-spam** — sliding window (5 xabar / 10 soniya)
- **Admin guard** — barcha admin amallarda tekshiruv
- **Referral fraud** — o'z havolasidan foydalanib bo'lmaydi

---

## 🗄️ Database schema

```sql
users        — user_id, username, full_name, is_banned, referrer_id, ref_count
videos       — code, file_id, title, like/dislike/view_count, added_by
reactions    — user_id, video_id, reaction (UNIQUE constraint)
daily_stats  — date, new_users, messages (kunlik hisobot)
```

---

## 🚀 Deployment

### Railway
1. New project → Deploy from GitHub
2. Add PostgreSQL va Redis services
3. Environment Variables qo'shing (`.env.example` ga qarang)
4. `USE_WEBHOOK=true`, `WEBHOOK_URL=https://xxx.up.railway.app`

### Render
1. New Web Service → Connect repo
2. Build: `pip install -r requirements.txt`
3. Start: `python main.py`
4. Add PostgreSQL va Redis (Render dashboard)

### VPS (systemd)
```ini
[Unit]
Description=Telegram Bot v2
After=network.target

[Service]
WorkingDirectory=/opt/bot_v2
EnvironmentFile=/opt/bot_v2/.env
ExecStart=/opt/bot_v2/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## ⚠️ Muhim

1. Bot 3 ta kanalda **admin** bo'lishi shart (obuna tekshirish uchun)
2. `ADMIN_IDS` — Telegram raqamli ID ([@userinfobot](https://t.me/userinfobot) orqali topish)
3. PostgreSQL va Redis **ikkalasi ham** kerak
4. `matplotlib` o'rnatilmasa grafik ishlamaydi (ixtiyoriy)
