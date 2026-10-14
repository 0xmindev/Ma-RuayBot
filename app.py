import os
import re
import sqlite3
from datetime import datetime

import pytz
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# ==================== CONFIG ====================

LINE_CHANNEL_ID = os.getenv("LINE_CHANNEL_ID", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

DB_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "maruay.db"),
)

TZ = pytz.timezone("Asia/Bangkok")

# ==================== FLASK APP ====================

app = Flask(__name__)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


# ==================== LOCAL SQLITE STORAGE ====================


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS revenues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                amount REAL NOT NULL,
                note TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        conn.commit()


def record_revenue(amount: float, note: str, timestamp: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO revenues (timestamp, amount, note, status) VALUES (?, ?, ?, ?)",
            (timestamp, amount, note, "Active"),
        )
        conn.commit()


def get_active_summary():
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total "
            "FROM revenues WHERE status = 'Active'"
        ).fetchone()
    return float(row["total"]), int(row["count"])


def delete_latest():
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM revenues WHERE status = 'Active' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return False
        conn.execute(
            "UPDATE revenues SET status = 'Deleted' WHERE id = ?", (row["id"],)
        )
        conn.commit()
        return True


def close_active():
    with get_db() as conn:
        conn.execute("UPDATE revenues SET status = 'Closed' WHERE status = 'Active'")
        conn.commit()


def get_monthly_summary():
    now = now_bangkok()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT timestamp, amount FROM revenues WHERE status != 'Deleted'"
        ).fetchall()
    total = 0.0
    count = 0
    for row in rows:
        try:
            ts = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            continue
        if ts.month == now.month and ts.year == now.year:
            total += float(row["amount"])
            count += 1
    return total, count, now.strftime("%B"), now.year


def reset_data():
    with get_db() as conn:
        conn.execute("DELETE FROM revenues")
        conn.commit()


def now_bangkok():
    return datetime.now(TZ)


# Initialize storage as soon as the module is imported.
init_db()


# ==================== BOT LOGIC ====================


def handle_revenue(text: str):
    match = re.match(r"^(\d+)(?:\s+(.*))?$", text)
    if not match:
        return TextMessage(
            text='พิมพ์ตัวเลขเพื่อบันทึกรายรับ หรือพิมพ์คำสั่ง "ลบ", "สรุปยอด", "สรุปรายเดือน" คับโบร๋วว'
        )
    amount = float(match.group(1))
    note = match.group(2) if match.group(2) else "-"
    ts = now_bangkok().strftime("%Y-%m-%d %H:%M:%S")
    record_revenue(amount, note, ts)
    return TextMessage(
        text=f"✅ บันทึกรายรับ +{amount:.0f} บาท ({note}) เรียบร้อยคับโบร๋วว!\n"
        '(หากพิมพ์ผิด พิมพ์คำว่า "ลบ" เพื่อยกเลิกรายการล่าสุดได้คับโบร๋วว)'
    )


def handle_delete():
    if delete_latest():
        return TextMessage(text="↩️ ยกเลิกรายการล่าสุดให้แล้วคับโบร๋วว")
    return TextMessage(text="ไม่พบรายการล่าสุดที่สามารถลบได้คับโบร๋วว")


def handle_summary():
    total, count = get_active_summary()
    if count == 0:
        return TextMessage(text="ไม่มีรายการที่ยัง Active อยู่ในรอบนี้คับโบร๋วว")
    close_active()
    return TextMessage(
        text=f"📊 สรุปยอดประจำรอบ\n"
        f"• จำนวนรายการ: {count} รายการ\n"
        f"• ยอดรวมทั้งหมด: {total:,.2f} บาท\n"
        f"🕐 ตัดรอบบัญชีเรียบร้อยแล้วคับโบร๋วว"
    )


def handle_monthly_summary():
    total, count, month, year = get_monthly_summary()
    if count == 0:
        return TextMessage(text=f"ไม่มีรายการในเดือน {month} {year} คับโบร๋วว")
    return TextMessage(
        text=f"📈 สรุปรายเดือน {month} {year}\n"
        f"• จำนวนรายการ: {count} รายการ\n"
        f"• ยอดรวมทั้งเดือน: {total:,.2f} บาทคับโบร๋วว"
    )


def handle_reset():
    reset_data()
    return TextMessage(text="🗑️ ล้างข้อมูลทั้งหมดเรียบร้อยคับโบร๋วว")


def handle_message(text: str):
    text = text.strip()
    if text in ("ลบ", "delete"):
        return handle_delete()
    if text in ("สรุปยอด", "summary"):
        return handle_summary()
    if text in ("สรุปรายเดือน", "monthly"):
        return handle_monthly_summary()
    if text in ("รีเซ็ต", "reset", "clear"):
        return handle_reset()
    return handle_revenue(text)


# ==================== WEBHOOK ====================


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    reply = handle_message(event.message.text)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token, messages=[reply]
            )
        )


@app.route("/webhook", methods=["GET"])
def webhook_info():
    return "✅ Webhook is running! Use /callback for LINE events."


if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", "5005")), debug=False, host="0.0.0.0")