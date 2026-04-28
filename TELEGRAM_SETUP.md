# Telegram Bot Setup — Local Development Runbook

Follow these steps in order. All commands run on your Mac in Terminal.

> **Never commit `.env`** — it is already in `.gitignore`. Verify with `git status` before any push.

---

## 1. Create the bot with @BotFather

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot`.
3. When prompted for a name enter: `OH_Scanner`
4. When prompted for a username enter something unique ending in `bot`, e.g. `OHScannerBot`.
5. BotFather replies with your token — it looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`.
   **Copy it — you will not see it again without `/mybots`.**

---

## 2. Get your Telegram user ID

1. Search for **@userinfobot** on Telegram.
2. Send `/start` or any message.
3. It replies with your numeric user ID, e.g. `123456789`.
   Copy it.

---

## 3. Add credentials to .env

Open `.env` in the project root and fill in the two new lines:

```
TELEGRAM_BOT_TOKEN=<YOUR_BOT_TOKEN>
AUTHORIZED_USER_IDS=<YOUR_USER_ID>
```

To authorise multiple users, comma-separate their IDs:

```
AUTHORIZED_USER_IDS=123456789,987654321
```

---

## 4. Start uvicorn locally

```bash
# From the project root, with the virtualenv active:
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Leave this terminal running. You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 5. Start ngrok and capture the HTTPS URL

Open a second terminal tab:

```bash
ngrok http 8000
```

ngrok prints a `Forwarding` line like:
```
Forwarding  https://a1b2c3d4.ngrok-free.app -> http://localhost:8000
```

Copy the `https://...` URL — this is `<NGROK_URL>` in the commands below.

> ngrok free tier assigns a new URL every restart. Re-run step 6 whenever you restart ngrok.

---

## 6. Register the webhook with Telegram

```bash
curl -s -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "<NGROK_URL>/webhook/telegram"}'
```

A successful response looks like:
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

---

## 7. Verify the webhook is registered

```bash
curl -s "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo" | python3 -m json.tool
```

Check that `url` matches your ngrok address and `last_error_message` is absent (or empty).

---

## 8. Test by sending a real article URL to the bot

1. Open Telegram and find your bot by its username.
2. Send `/start` (optional — the bot accepts any message).
3. Paste a real news article URL, e.g.:
   ```
   https://techcrunch.com/2024/01/15/some-article/
   ```
4. The bot should reply with a structured summary within ~30 seconds (Firecrawl + OpenAI latency).

Watch the uvicorn logs for `URL processed successfully` or any errors.

---

## 9. Delete the webhook when you stop

Always clean up when shutting down so Telegram stops sending updates to the dead ngrok URL.

```bash
curl -s -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook"
```

Expected response:
```json
{"ok":true,"result":true,"description":"Webhook was deleted"}
```

Then stop uvicorn (`Ctrl+C`) and ngrok (`Ctrl+C`).

---

## Quick-reference cheat sheet

| Step | Command |
|------|---------|
| Start server | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` |
| Start tunnel | `ngrok http 8000` |
| Set webhook | `curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" -H "Content-Type: application/json" -d '{"url":"<NGROK_URL>/webhook/telegram"}'` |
| Check webhook | `curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"` |
| Delete webhook | `curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"` |
