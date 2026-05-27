import re

from linebot.v3.messaging import (
    TextMessage,
    FlexMessage,
    FlexContainer,
)
from services.google_sheets import (
    record_revenue,
    delete_last_active,
    get_active_summary,
    close_active_records,
    get_monthly_summary,
)


def handle_message(text: str):
    text = text.strip()
    result = None

    if text == "ลบ":
        result = handle_delete()
    elif text == "สรุปยอด":
        result = handle_summary()
    elif text == "สรุปรายเดือน":
        result = handle_monthly_summary()
    else:
        result = handle_revenue(text)

    return result


def handle_revenue(text: str):
    match = re.match(r"^(\d+)(?:\s+(.*))?$", text)
    if not match:
        return TextMessage(text="พิมพ์ตัวเลขเพื่อบันทึกรายรับ หรือพิมพ์คำสั่ง "ลบ", "สรุปยอด", "สรุปรายเดือน" ค่ะ")
    amount = float(match.group(1))
    note = match.group(2) if match.group(2) else "-"
    timestamp = record_revenue(amount, note)
    return TextMessage(
        text=f"✅ บันทึกรายรับ +{amount:.0f} บาท ({note}) เรียบร้อยค่ะ!\n"
        "(หากพิมพ์ผิด พิมพ์คำว่า "ลบ" เพื่อยกเลิกรายการล่าสุดได้ค่ะ)"
    )


def handle_delete():
    ok = delete_last_active()
    if ok:
        return TextMessage(text="↩️ ยกเลิกรายการล่าสุดให้แล้วค่ะ")
    return TextMessage(text="ไม่พบรายการล่าสุดที่สามารถลบได้ค่ะ")


def handle_summary():
    total, count = get_active_summary()
    if count == 0:
        return TextMessage(text="ไม่มีรายการที่ยัง Active อยู่ในรอบนี้ค่ะ")
    close_active_records()
    return TextMessage(
        text=f"📊 สรุปยอดประจำรอบ\n"
        f"• จำนวนรายการ: {count} รายการ\n"
        f"• ยอดรวมทั้งหมด: {total:,.2f} บาท\n"
        f"🕐 ตัดรอบบัญชีเรียบร้อยแล้วค่ะ"
    )


def handle_monthly_summary():
    total, count, month_name, year = get_monthly_summary()
    if count == 0:
        return TextMessage(text=f"ไม่มีรายการในเดือน {month_name} {year} ค่ะ")
    return TextMessage(
        text=f"📈 สรุปรายเดือน {month_name} {year}\n"
        f"• จำนวนรายการ: {count} รายการ\n"
        f"• ยอดรวมทั้งเดือน: {total:,.2f} บาท"
    )
