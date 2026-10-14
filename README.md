# MaruayBots

LINE bot for recording revenue, with daily/round summaries and monthly reports.

The old Google Apps Script storage backend and Render deployment are no longer
available, so this version stores data in a local SQLite database. That makes
the bot self-contained and runnable without Google Sheets.

## Local run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your LINE credentials
export $(grep -v '^#' .env | xargs)
python app.py
```

The health endpoint is `http://127.0.0.1:5005/webhook`.

## LINE setup

1. Create/renew the channel access token and channel secret in the LINE Developers console.
2. Deploy or expose this app with HTTPS.
3. Set the webhook URL to `https://your-domain/callback`.

## Render deploy

`render.yaml` is included. Set these environment variables in Render:

- `LINE_CHANNEL_ID`
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`
- optional: `DATABASE_PATH`

Note: Render free web services have an ephemeral filesystem. SQLite data resets
when the service restarts or redeploys. Use a paid disk or external database
for durable storage.

## Commands sent to the bot

- `<amount> [note]` records revenue
- `ลบ` deletes the latest active entry
- `สรุปยอด` shows the current round and closes it
- `สรุปรายเดือน` shows the current month
- `รีเซ็ต` clears all data
