# OHPR Media Monitor Bot

A production-style FastAPI service that receives **URLs** or **PDF files** via a Telegram bot and returns structured media-monitoring summaries.

Built as a clean, modular backend — easy to extend with WhatsApp, Slack, or any other channel later.

---

## Project structure

```
OHPR/
├── app/
│   ├── main.py                     ← FastAPI app + lifespan
│   ├── config.py                   ← Settings (loaded from .env)
│   ├── routes/
│   │   └── telegram.py             ← POST /webhook/telegram
│   ├── services/
│   │   ├── auth_service.py         ← Allowlist authorization
│   │   ├── telegram_service.py     ← Telegram API helpers
│   │   └── processor_service.py    ← process_url / process_pdf (mocked → real)
│   ├── utils/
│   │   ├── url_utils.py            ← Regex URL extractor
│   │   └── logging_utils.py        ← Logging setup
│   └── schemas/
│       └── telegram.py             ← Pydantic Telegram Update models
├── ohpr/                           ← Existing OHPR pipeline (real URL processing)
├── tmp/                            ← Downloaded PDFs (auto-cleaned after processing)
├── tests/
│   └── test_webhook.py
├── .env                            ← Local secrets (never commit)
├── .env.example                    ← Template
└── requirements.txt
```

---

## Prerequisites

- Python 3.11+
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- Your Telegram user ID (from [@userinfobot](https://t.me/userinfobot))

---

## Installation

```bash
# Clone / open the project
cd OHPR

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Minimum required values in `.env`:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
AUTHORIZED_USER_IDS=123456789,987654321
OPENAI_API_KEY=sk-...
FIRECRAWL_API_KEY=fc-...
```

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Token from @BotFather |
| `AUTHORIZED_USER_IDS` | ✅ | Comma-separated Telegram user IDs |
| `BASE_TELEGRAM_API_URL` | ❌ | Default: `https://api.telegram.org` |
| `TEMP_DIR` | ❌ | Default: `tmp` |
| `LOG_LEVEL` | ❌ | Default: `INFO` |
| `OPENAI_API_KEY` | ❌ | Needed for real URL classification |
| `FIRECRAWL_API_KEY` | ❌ | Needed for real URL scraping |

---

## Running locally

```bash
uvicorn app.main:app --reload --port 8000
```

Confirm it's running:

```bash
curl http://localhost:8000/health
# → {"status":"ok","service":"ohpr-bot"}
```

API docs available at: http://localhost:8000/docs

---

## Exposing locally with ngrok

Telegram requires a public HTTPS URL for webhooks. Use [ngrok](https://ngrok.com) to tunnel your local server:

```bash
# Install ngrok (macOS)
brew install ngrok

# Authenticate once
ngrok config add-authtoken <your-ngrok-token>

# Start tunnel on port 8000
ngrok http 8000
```

ngrok will print a URL like: `https://abc123.ngrok-free.app`

---

## Registering the Telegram webhook

After ngrok is running, register your bot webhook with Telegram:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://abc123.ngrok-free.app/webhook/telegram"}'
```

Expected response:
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

Verify it was registered:
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

Remove the webhook (e.g. when stopping):
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook"
```

---

## Authorization flow

1. User sends a message to the bot.
2. Bot extracts the `user_id` from the Telegram update.
3. `auth_service.is_authorized(user_id)` checks if it's in `AUTHORIZED_USER_IDS`.
4. **Unauthorized** → bot replies "You are not authorized" + logs the attempt. Request stops here.
5. **Authorized** → request continues to URL or PDF processing.

To find your Telegram user ID: message [@userinfobot](https://t.me/userinfobot) on Telegram.

---

## How to add real processing

### URL processing (connect the existing OHPR pipeline)

Open `app/services/processor_service.py` and replace `process_url()` with:

```python
from ohpr.pipeline import process_url as _ohpr_process_url

def process_url(url: str) -> dict:
    return _ohpr_process_url(url)
```

### PDF processing

Replace `process_pdf()` in the same file with your OCR or extraction logic.
The function receives `file_path` (absolute path to the downloaded temp file) and `file_name`.

---

## Running tests

```bash
pip install pytest
pytest tests/ -v
```

---

## End-to-end test flow

1. Start the server: `uvicorn app.main:app --reload`
2. Start ngrok: `ngrok http 8000`
3. Register the webhook (see above)
4. Open Telegram and message your bot:
   - Send a URL: `https://www.calcalistech.com/ctechnews/article/bjjnqzl2wg`
   - Send a PDF file directly
5. The bot should reply with a formatted summary

For local testing without Telegram, simulate an update with curl:

```bash
curl -X POST http://localhost:8000/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 1,
    "message": {
      "message_id": 1,
      "from": {"id": YOUR_USER_ID, "is_bot": false, "first_name": "Test"},
      "chat": {"id": YOUR_USER_ID, "type": "private"},
      "date": 1700000000,
      "text": "https://www.calcalistech.com/ctechnews/article/bjjnqzl2wg"
    }
  }'
```

Replace `YOUR_USER_ID` with your actual Telegram user ID (must be in `AUTHORIZED_USER_IDS`).

---

## Extending to other channels

To add WhatsApp (or any other channel):

1. Create `app/routes/whatsapp.py` with a new router
2. Create `app/services/whatsapp_service.py` with send/format helpers
3. Include the router in `app/main.py`
4. Reuse `processor_service.process_url()` and `process_pdf()` — they're channel-agnostic
