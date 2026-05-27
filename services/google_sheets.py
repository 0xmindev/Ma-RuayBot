import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
from config import GOOGLE_SHEETS_CREDENTIALS_PATH, SHEET_NAME, TZ

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def get_client():
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        GOOGLE_SHEETS_CREDENTIALS_PATH, scope
    )
    return gspread.authorize(creds)


def get_sheet():
    client = get_client()
    return client.open(SHEET_NAME).sheet1


def ensure_header(ws):
    if ws.row_count == 0 or ws.cell(1, 1).value != "Timestamp":
        header = ["Timestamp", "Amount", "Note", "Status"]
        ws.insert_row(header, 1)


def now_bangkok():
    return datetime.now(pytz.timezone(TZ))


def record_revenue(amount: float, note: str = "-"):
    ws = get_sheet()
    ensure_header(ws)
    timestamp = now_bangkok().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([timestamp, amount, note, "Active"])
    return timestamp


def delete_last_active():
    ws = get_sheet()
    ensure_header(ws)
    records = ws.get_all_values()
    if not records:
        return False
    for i in range(len(records) - 1, 0, -1):
        if len(records[i]) >= 4 and records[i][3] == "Active":
            ws.update_cell(i + 1, 4, "Deleted")
            return True
    return False


def get_active_summary():
    ws = get_sheet()
    ensure_header(ws)
    records = ws.get_all_values()
    total = 0.0
    count = 0
    for row in records[1:]:
        if len(row) >= 4 and row[3] == "Active":
            try:
                total += float(row[1])
                count += 1
            except ValueError:
                continue
    return total, count


def close_active_records():
    ws = get_sheet()
    ensure_header(ws)
    records = ws.get_all_values()
    updated = 0
    for i in range(1, len(records)):
        if len(records[i]) >= 4 and records[i][3] == "Active":
            ws.update_cell(i + 1, 4, "Closed")
            updated += 1
    return updated


def get_monthly_summary():
    ws = get_sheet()
    ensure_header(ws)
    records = ws.get_all_values()
    now = now_bangkok()
    current_month = now.month
    current_year = now.year
    total = 0.0
    count = 0
    for row in records[1:]:
        if len(row) >= 4:
            try:
                ts = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                if ts.month == current_month and ts.year == current_year:
                    total += float(row[1])
                    count += 1
            except (ValueError, IndexError):
                continue
    month_name = now.strftime("%B")
    return total, count, month_name, current_year
