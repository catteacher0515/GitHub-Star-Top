import json
import os
from datetime import datetime, timedelta

COOLDOWN_DAYS = 30

DEDUP_FILE = "dedup_state.json"
STAR_INCREASE_THRESHOLD = 500


class DedupState:
    def __init__(self):
        self._loaded_from_file = os.path.exists(DEDUP_FILE)
        data = self._load()
        self._weekly: dict = data.get("weekly", {})
        self._first_seen: dict = data.get("first_seen", {})
        self._last_seen: dict = data.get("last_seen", {})

    def _load(self) -> dict:
        if os.path.exists(DEDUP_FILE):
            with open(DEDUP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save(self):
        with open(DEDUP_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"weekly": self._weekly, "first_seen": self._first_seen, "last_seen": self._last_seen},
                f,
                ensure_ascii=False,
                indent=2,
            )

    @staticmethod
    def _parse_date(value: str) -> datetime | None:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except (TypeError, ValueError):
            return None

    def _is_in_cooldown(self, url: str, week: str) -> bool:
        last_seen = self._parse_date(self._last_seen.get(url))
        current_week = self._parse_date(self._week_start_date(week))
        if last_seen is None or current_week is None:
            return False
        return current_week - last_seen < timedelta(days=COOLDOWN_DAYS)

    @staticmethod
    def _week_start_date(week: str) -> str | None:
        try:
            year_str, week_str = week.split("-W")
            year = int(year_str)
            iso_week = int(week_str)
        except (ValueError, AttributeError):
            return None

        # ISO week 的周一作为该周起始日期
        return datetime.fromisocalendar(year, iso_week, 1).strftime("%Y-%m-%d")

    def check_and_update(self, url: str, stars: int, week: str) -> str:
        """
        返回值：
          "new"    — 本周首次出现
          "update" — 已存在但 star 涨幅 >= 阈值，已更新
          "skip"   — 已存在且涨幅不足，跳过
        """
        key = f"{week}:{url}"
        existing = self._weekly.get(key)

        if existing is None:
            if self._is_in_cooldown(url, week):
                return "skip"
            self._weekly[key] = {"stars": stars}
            if url not in self._first_seen:
                self._first_seen[url] = datetime.utcnow().strftime("%Y-%m-%d")
            self._last_seen[url] = self._week_start_date(week) or datetime.utcnow().strftime("%Y-%m-%d")
            return "new"

        increase = stars - existing["stars"]
        if increase >= STAR_INCREASE_THRESHOLD:
            self._weekly[key]["stars"] = stars
            self._last_seen[url] = self._week_start_date(week) or datetime.utcnow().strftime("%Y-%m-%d")
            return "update"

        return "skip"

    def get_first_seen(self, url: str) -> str:
        return self._first_seen.get(url, datetime.utcnow().strftime("%Y-%m-%d"))

    def get_stars(self, url: str, week: str) -> int:
        key = f"{week}:{url}"
        return self._weekly.get(key, {}).get("stars", 0)

    def is_loaded_from_file(self) -> bool:
        return self._loaded_from_file
