import os
import re
import json
from datetime import datetime

import pytz
import requests
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

LINE_CHANNEL_ID = "2010215865"
LINE_CHANNEL_SECRET = "01567cead4373545dfc6eaa2c13b1c43"
LINE_CHANNEL_ACCESS_TOKEN = "yCkQ7/HGH47Dbnwc1+M2JQYLE2mpB8LrRSepVgjax4ImCg0CX0CwaTD0pfzXk24sN1DpEzxYYMWZNB7ovJubYXFjSbZKA0NXepU7W+dgX9itoZWCqHA5I0cLriuVSKkvk2I5ZZ3lHVoN2VBY0vq3JQdB04t89/1O/w1cDnyilFU="

GAS_WEBAPP_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbzttJTvc8olNxs5160N5rmCqHVzfxAIQ04q3OyTxl5zRWUHlijw0GZoqzuo_gj9oP25/exec"
)

TZ = pytz.timezone("Asia/Bangkok")

# ==================== FLASK APP ====================

app = Flask(__name__)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ==================== GOOGLE APPS SCRIPT (POST) ====================


def _post_gas(payload: dict) -> dict:
    resp = requests.post(
        GAS_WEBAPP_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
    return resp.json()


def now_bangkok():
    return datetime.now(TZ)


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
    _post_gas({"action": "add", "amount": amount, "note": note, "timestamp": ts})
    return TextMessage(
        text=f"✅ บันทึกรายรับ +{amount:.0f} บาท ({note}) เรียบร้อยคับโบร๋วว!\n"
        '(หากพิมพ์ผิด พิมพ์คำว่า "ลบ" เพื่อยกเลิกรายการล่าสุดได้คับโบร๋วว)'
    )


def handle_delete():
    result = _post_gas({"action": "delete"})
    if result.get("found"):
        return TextMessage(text="↩️ ยกเลิกรายการล่าสุดให้แล้วคับโบร๋วว")
    return TextMessage(text="ไม่พบรายการล่าสุดที่สามารถลบได้คับโบร๋วว")


def handle_summary():
    result = _post_gas({"action": "summary"})
    count = result.get("count", 0)
    total = result.get("total", 0)
    if count == 0:
        return TextMessage(text="ไม่มีรายการที่ยัง Active อยู่ในรอบนี้คับโบร๋วว")
    _post_gas({"action": "close"})
    return TextMessage(
        text=f"📊 สรุปยอดประจำรอบ\n"
        f"• จำนวนรายการ: {count} รายการ\n"
        f"• ยอดรวมทั้งหมด: {total:,.2f} บาท\n"
        f"🕐 ตัดรอบบัญชีเรียบร้อยแล้วคับโบร๋วว"
    )


def handle_monthly_summary():
    result = _post_gas({"action": "monthly"})
    count = result.get("count", 0)
    total = result.get("total", 0)
    month = result.get("month", now_bangkok().strftime("%B"))
    year = result.get("year", now_bangkok().year)
    if count == 0:
        return TextMessage(text=f"ไม่มีรายการในเดือน {month} {year} คับโบร๋วว")
    return TextMessage(
        text=f"📈 สรุปรายเดือน {month} {year}\n"
        f"• จำนวนรายการ: {count} รายการ\n"
        f"• ยอดรวมทั้งเดือน: {total:,.2f} บาทคับโบร๋วว"
    )


def handle_reset():
    _post_gas({"action": "reset"})
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
    app.run(port=5005, debug=False, host="0.0.0.0")
