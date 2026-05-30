# Telegram Subscription Bot

A production-ready subscription bot that sells access to a private Telegram channel via [Lava.top](https://lava.top) payments.

## Architecture

```
User → /start → Bot shows plans → User selects plan
     → Lava.top payment page → User pays
     → Lava.top webhook → Backend activates subscription
     → Bot sends personal invite link → User joins private channel
     → Daily scheduler removes expired subscribers
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Bot framework | aiogram 3 |
| Web server | FastAPI + uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy async |
| Scheduler | APScheduler |
| Payments | Lava.top |
| Container | Docker + Docker Compose |
| Python | 3.12 |

## Project Structure

```
.
├── bot/
│   ├── config.py            # Settings via pydantic-settings
│   ├── main.py              # Entry point, webhook setup, scheduler
│   ├── database/
│   │   ├── engine.py        # SQLAlchemy engine & session factory
│   │   ├── models.py        # ORM models: User, Subscription, Payment
│   │   └── queries.py       # Async query helpers
│   ├── handlers/
│   │   ├── start.py         # /start, plan selection, payment flow
│   │   └── admin.py         # /stats /active /expired /broadcast
│   ├── keyboards/
│   │   └── inline.py        # Inline keyboard builders
│   ├── middlewares/
│   │   └── database.py      # Injects AsyncSession into handlers
│   ├── services/
│   │   ├── lava_top.py      # Invoice creation + signature verification
│   │   ├── subscription.py  # Activate / revoke subscriptions
│   │   └── scheduler.py     # Daily job to remove expired users
│   └── webhook/
│       └── server.py        # FastAPI app (Telegram + Lava webhooks)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Quick Start

### 1. Clone & configure

```bash
git clone <repo>
cd <repo>
cp .env.example .env
# Edit .env with your values
```

### 2. Required .env values

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `ADMIN_IDS` | Comma-separated Telegram user IDs |
| `CHANNEL_ID` | Target private channel/group ID (negative number) |
| `WEBHOOK_HOST` | Your public HTTPS domain, e.g. `https://bot.example.com` |
| `POSTGRES_PASSWORD` | Strong database password |
| `LAVA_SECRET_KEY` | From Lava.top merchant dashboard |
| `LAVA_SHOP_ID` | From Lava.top merchant dashboard |

### 3. Prepare the channel

1. Create a private Telegram channel or supergroup.
2. Add the bot as an **Administrator** with permissions:
   - Invite users via link
   - Ban users
3. Copy the channel ID (use [@userinfobot](https://t.me/userinfobot)) and set `CHANNEL_ID`.

### 4. Configure Lava.top

1. Register at [lava.top](https://lava.top) and create a shop.
2. Copy **Secret Key** and **Shop ID** to `.env`.
3. The webhook URL is automatically set to `WEBHOOK_HOST + LAVA_WEBHOOK_PATH` when an invoice is created.

### 5. Run

```bash
docker compose up -d --build
```

The app listens on port `8080`. Point your reverse proxy (nginx/Caddy) to it.

### 6. Set Telegram webhook

The bot sets its own webhook on startup via the Telegram API. Verify with:

```
https://api.telegram.org/bot<TOKEN>/getWebhookInfo
```

## Admin Commands

| Command | Description |
|---------|-------------|
| `/stats` | Total users, active/expired subscription counts |
| `/active` | List all active subscribers |
| `/expired` | List last 50 expired subscribers |
| `/broadcast <text>` | Send a message to all active subscribers |

Admin access is controlled by `ADMIN_IDS` in `.env`.

## Subscription Plans

Configurable via `.env`:

| Variable | Default |
|----------|---------|
| `PLAN_1_MONTH_PRICE` | 299 ₽ |
| `PLAN_3_MONTH_PRICE` | 799 ₽ |
| `PLAN_12_MONTH_PRICE` | 2499 ₽ |

## Nginx reverse proxy example

```nginx
server {
    listen 443 ssl;
    server_name bot.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Scheduler

A daily cron job runs at **03:00 UTC**:
1. Finds subscriptions where `expires_at < now` and `status = active`.
2. Kicks and unbans each user from the channel (kick + immediate unban revokes membership without permanently banning).
3. Marks subscriptions as `expired`.
4. Notifies the user with a renewal message.

## Logs

```bash
docker compose logs -f bot
```

Log level is controlled by `LOG_LEVEL` (default: `INFO`).
