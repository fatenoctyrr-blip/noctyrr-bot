# Deployment

Bu paket siz bergan sozlamalar bilan tayyorlangan:

```text
GRAND_ADMIN_ID=<your Telegram user ID>
DEFAULT_CHANNEL_ID=<optional -100... chat ID>
```

## Docker server

```bash
cp .env.example .env
# .env ichida BOT_API_TOKEN, GRAND_ADMIN_ID va POSTGRES_PASSWORDni to'ldiring
docker compose up -d --build
docker compose logs -f bot
```

`docker-compose.yml` PostgreSQL va bot servislarini ishga tushiradi. Bot PostgreSQL healthcheck o'tgandan keyin boshlanadi. Token yoki Grand Admin ID bo'lmasa Compose ataylab ishga tushmaydi.

## Replit/server secrets

Production serverda quyidagi secret/environment o'zgaruvchini bering:

```text
BOT_API_TOKEN=<BotFather token>
GRAND_ADMIN_ID=<your Telegram user ID>
POSTGRES_PASSWORD=<strong database password>
DATABASE_URL=postgresql+asyncpg://postgres:<password>@<postgres-host>:5432/oyunlar
DB_CONNECT_RETRIES=12
DB_RETRY_SECONDS=5
```

Qolgan qiymatlar koddagi xavfsiz defaultlar orqali berilgan, lekin production'da quyidagilarni ham environment sifatida qo'yish tavsiya etiladi:

```text
DEFAULT_CHANNEL_ID=-100...
```

`docker compose up` bilan ishga tushirilganda `DATABASE_URL` Compose tomonidan
ichki PostgreSQL servis nomiga almashtiriladi: host `postgres`. Agar faqat bot
image'i yoki oddiy Python process ishga tushirilsa, `localhost:5432` faqat
PostgreSQL aynan shu serverda ishlayotgan bo'lsa to'g'ri bo'ladi.
Alohida database serveri uchun `DATABASE_URL`da o'sha serverning haqiqiy hostini yozing.

Bot database ishga tushishini `DB_CONNECT_RETRIES` va `DB_RETRY_SECONDS` orqali kutadi.
Ulanish bo'lmasa logda `DATABASE_URL` hostini tekshirish kerakligi aniq ko'rsatiladi.

## Telegram sozlamalari

1. Botni asosiy kanal/guruhga administrator qilib qo'shing.
2. Botga xabar yuborish, post yuborish va reaction/comment eventlarini ko'rish uchun kerakli huquqlarni bering.
3. Chat ichida `/connect` yuboring.
4. `/admin` bilan inline Grand Admin panelini tekshiring.
5. Paneldagi `🎯 Konkurslar` bo'limidan faol konkursni ko'ring va yakunlashni tasdiqlang.

Asosiy chat ID'si Telegram'da haqiqiy kanal/guruh ID bo'lishi kerak. Supergroup va kanal ID'lari ko'pincha `-100...` ko'rinishida bo'ladi.