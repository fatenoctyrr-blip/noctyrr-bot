# O'yinlar va Konkurslar Telegram Bot

Ishlaydigan MVP Telegram bot platformasi: Mafia, Bunker, Battle konkurslar, ball tizimli konkurslar, 777 Jackpot, raqamni topish, tasodifiy xabar lotereyasi, majburiy obuna va Grand Admin boshqaruvi.

## Muhim xavfsizlik eslatmasi

Bot tokeni, Grand Admin ID'si va kanal ID'si source code ichiga yozilmaydi. Ularni `.env` fayliga joylang yoki production secret manager'dan bering. `.env` fayli Git'ga kiritilmasligi uchun `.gitignore`ga qo'shilgan.

## Ishga tushirish

1. Python 3.11+ va Docker o'rnating.
2. Muhit faylini tayyorlang:

   ```bash
   cp .env.example .env
   ```

3. `.env` ichidagi qiymatlarni to'ldiring: `BOT_API_TOKEN`, `GRAND_ADMIN_ID` va `DATABASE_URL` majburiy. Docker Compose'da `DATABASE_URL` ichki PostgreSQL servisi bilan avtomatik beriladi.
4. PostgreSQL'ni ishga tushiring:

   ```bash
   docker compose up -d postgres
   ```

5. Python muhitini yaratib, paketlarni o'rnating:

   ```bash
   python -m venv .venv
   source .venv/bin/activate       # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

6. Migratsiyani bajaring:

   ```bash
   psql "$DATABASE_URL" -f migrations/001_initial.sql
   ```

   `DATABASE_URL` SQLAlchemy formatida bo'lsa, `postgresql+asyncpg://` qismini `postgresql://`ga almashtiring yoki migration SQL'ni database client orqali ishga tushiring.

7. Botni ishga tushiring:

   ```bash
   python -m app
   ```

Replit/server muhitida `BOT_API_TOKEN`ni secret/environment sifatida bering. Tokenni ZIP, Git yoki chatga yozmang.

## Birinchi sozlash

- Botni kerakli kanal/guruhga administrator qilib qo'shing.
- `GRAND_ADMIN_ID` egasining Telegram ID'si bilan `/admin` buyrug'ini yuboring.
- Kanal/guruh ichida `/connect` buyrug'i bilan kanalni ulashni boshlang.
- Kanal admini avval `/connect`, keyin `/contest` yoki `/point_contest` orqali konkurs ochadi.
- Guruhda `/game mafia`, `/game bunker`, `/game jackpot` buyruqlari ishlaydi.

## Asosiy buyruqlar

### Grand Admin

- `/admin` — inline Grand Admin paneli: statistika, kanallar va faol konkurslar
- `/override <battle:contest_id|point:contest_id> <telegram_user_id>` — g'olibni qo'lda belgilash
- `/game_config <chat_id> <target|secret|chance|gift> <value>` — faol o'yin parametrlarini o'zgartirish
- Paneldagi tugmalar orqali faol konkursni tasdiqlab yakunlash

### Kanal admini

- `/connect` — joriy chatni botga ulash
- `/contest` — sanog'iga asoslangan Battle konkursi
- `/point_contest` — ball tizimli konkurs
- `/add_boost <contest_id> <user_id> <amount>` — boost ball qo'shish
- `/stop_contest <contest_id>` — konkursni to'xtatish

### Foydalanuvchi

- `/games` — o'yinlar ro'yxati
- Konkurs postidagi `Qatnashish` tugmasi
- `/guess <number>` — raqamni top o'yinida taxmin

## Ishlaydigan buyruq formatlari

```text
/connect
/contest Kanalga obuna bo'ling | target=50 | minutes=120 | requirements=-1001,-1002
/point_contest Telefon | minutes=60 | weights=reaction:1,stars:5,boost:2,comment:1,purchased:10
/add_points 3 123456 boost 10
/stop_contest 3
/game mafia
/game bunker
/game jackpot 777
/game guess 1 100
/game lottery Sovga 0.07
/join_game
```

## Arxitektura

```text
app/
  bot.py                 Dispatcher, middleware va routerlarni yig'adi
  config.py              Pydantic Settings
  db.py                  Async SQLAlchemy engine/session
  models.py              Asosiy jadvallar
  routers/
    admin.py             Grand Admin va kanal admini callback/commandlari
    contests.py          Battle va point konkurslari
    games.py             Guruh o'yinlari
    user.py              Foydalanuvchi onboarding va yordam
  services/
    contests.py          Konkurs lifecycle, scoring va winner override
    subscriptions.py     Ko'p shartli obuna tekshiruvi
  games/
    mafia.py             Mafia state machine
    bunker.py            Bunker state machine
migrations/
  001_initial.sql        PostgreSQL schema
tests/
  test_core.py           Deterministic domain tests
```

## Nimalar to'liq ishlaydi

- Admin tekshiruvi Telegram `getChatMember` orqali.
- Battle konkursi yaratish, post qilish, tugma orqali qo'shilish va target bo'yicha yopilish.
- Ko'p kanal/guruhga majburiy obuna tekshiruvi.
- Ballik konkurs, reaction/comment eventlari, admin ball qo'shishi va reyting.
- Konkurs muddati kelganda avtomatik yakunlash.
- Mafia/Bunker sessiyalari PostgreSQL'da saqlanishi va bir nechta chatda parallel ishlashi.
- Jackpot, guess number va xabar lotereyasi.
- Grand Admin winner override va audit.

## Production checklist

- Botga kanal/guruhda zarur admin huquqlarini bering.
- Webhook yoki process supervisor (systemd/Docker) qo'llang.
- PostgreSQL backup/monitoring qo'shing.
- Telegram API rate limitlarini kuzating.
- Pullik Stars uchun Telegram payment verification'ni payment provider va biznes qoidalariga moslab ulang; adminning `purchased` ball buyrug'i allaqachon mavjud.
- Konkurs natijalarini o'zgartirish faqat Grand Admin ID orqali amalga oshadi va `admin_overrides` jadvaliga audit yozuvi tushadi.
- `POSTGRES_PASSWORD`ni production'da kuchli qiymatga almashtiring; database porti Compose orqali tashqariga ochilmaydi.
- Contest command'lari chat scope bilan himoyalangan; admin paneli esa faqat Grand Admin uchun ko'rinadi.
- Docker Compose ishlatilmasa, `DATABASE_URL` ichidagi `localhost` PostgreSQL haqiqatan ham shu serverda ishlayotganini tekshiring.