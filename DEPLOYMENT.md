# Deployment

Bu paket siz bergan sozlamalar bilan tayyorlangan:

```text
GRAND_ADMIN_ID=8126409678
DEFAULT_CHANNEL_ID=4354232618
```

## Docker server

```bash
cp .env.example .env
# .env ichida faqat BOT_API_TOKENni to'ldiring
docker compose up -d --build
docker compose logs -f bot
```

`docker-compose.yml` PostgreSQL, Redis va bot servislarini birga ishga tushiradi. Docker Compose tokenni `.env` yoki server environment'idan oladi; token bo'lmasa compose ataylab ishga tushmaydi.

## Replit/server secrets

Production serverda quyidagi secret/environment o'zgaruvchini bering:

```text
BOT_API_TOKEN=<BotFather token>
```

Qolgan qiymatlar koddagi xavfsiz defaultlar orqali berilgan, lekin production'da quyidagilarni ham environment sifatida qo'yish tavsiya etiladi:

```text
GRAND_ADMIN_ID=8126409678
DEFAULT_CHANNEL_ID=4354232618
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
```

## Telegram sozlamalari

1. Botni asosiy kanal/guruhga administrator qilib qo'shing.
2. Botga xabar yuborish, post yuborish va reaction/comment eventlarini ko'rish uchun kerakli huquqlarni bering.
3. Chat ichida `/connect` yuboring.
4. `/admin` bilan Grand Admin panelini tekshiring.

Asosiy chat ID'si Telegram'da haqiqiy kanal/guruh ID bo'lishi kerak. Supergroup va kanal ID'lari ko'pincha `-100...` ko'rinishida bo'ladi; agar berilgan `4354232618` boshqa chatga tegishli bo'lsa, `DEFAULT_CHANNEL_ID`ni o'zgartiring.