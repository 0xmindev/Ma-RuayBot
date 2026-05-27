import os
from dotenv import load_dotenv

load_dotenv()

LINE_CHANNEL_ID = "2010215865"
LINE_CHANNEL_SECRET = "01567cead4373545dfc6eaa2c13b1c43"
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv(
    "GOOGLE_SHEETS_CREDENTIALS_PATH",
    "service-account.json"
)
SHEET_NAME = "Bot_Revenue_Database"

TZ = "Asia/Bangkok"
