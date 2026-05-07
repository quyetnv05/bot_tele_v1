import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    ADMIN_IDS = [int(id_str) for id_str in os.getenv("ADMIN_IDS", "").split(",") if id_str]
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sales_bot.db")
    SEPAY_API_KEY = os.getenv("SEPAY_API_KEY")
    SEPAY_WEBHOOK_KEY = os.getenv("SEPAY_WEBHOOK_KEY")
    WEB_ADMIN_USERNAME = os.getenv("WEB_ADMIN_USERNAME", "quyetnguyen01")
    WEB_ADMIN_PASSWORD = os.getenv("WEB_ADMIN_PASSWORD", "Quyetdz01@")
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
    SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "phanhuy24")
    AFFILIATE_PERCENT = int(os.getenv("AFFILIATE_PERCENT", "10"))
    MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "False").lower() == "true"

config = Config()
