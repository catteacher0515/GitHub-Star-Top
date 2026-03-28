import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_BASE = "https://api.github.com"

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_BITABLE_APP_TOKEN = os.getenv("FEISHU_BITABLE_APP_TOKEN", "")
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

TIME_RANGES = {
    "today": 1,
    "weekly": 7,
    "monthly": 30,
}

def get_since_date(period: str) -> str:
    days = TIME_RANGES.get(period, 7)
    since = datetime.utcnow() - timedelta(days=days)
    return since.strftime("%Y-%m-%d")

def get_week_label() -> str:
    """返回当前周标签，格式 YYYY-WXX，如 2026-W13"""
    iso = datetime.utcnow().isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"
