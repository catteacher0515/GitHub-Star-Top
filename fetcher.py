import re
import time

import requests
from config import GITHUB_TOKEN, GITHUB_API_BASE, get_since_date

MAX_REQUEST_RETRIES = 3
RETRY_DELAY_SECONDS = 2

EXCLUDED_REPO_KEYWORDS = (
    "aimbot",
    "triggerbot",
    "wallhack",
    "esp",
    "external overlay",
    "external-overlay",
    "helper overlay",
    "mod menu",
    "mod-menu",
    "cheat",
    "cheats",
    "hack",
    "hacks",
    "autoclicker",
    "auto clicker",
    "auto-clicker",
    "macro",
    "bypass",
    "hwid spoofer",
    "spoofer",
    "injector",
    "dll injector",
    "executor",
    "script executor",
)

EXCLUDED_HIGH_RISK_PATTERNS = (
    ("hwid", re.compile(r"(?<![a-z0-9])hwid(?![a-z0-9])")),
    ("anti-cheat", re.compile(r"(?<![a-z0-9])anti-cheat(?![a-z0-9])")),
    ("anticheat", re.compile(r"(?<![a-z0-9])anticheat(?![a-z0-9])")),
    ("vanguard", re.compile(r"(?<![a-z0-9])vanguard(?![a-z0-9])")),
    ("battleye", re.compile(r"(?<![a-z0-9])battleye(?![a-z0-9])")),
    ("battl eye", re.compile(r"(?<![a-z0-9])battl eye(?![a-z0-9])")),
    ("eac", re.compile(r"(?<![a-z0-9])eac(?![a-z0-9])")),
)

EXCLUDED_GAME_KEYWORDS = (
    "gta",
    "cs2",
    "csgo",
    "valorant",
    "fortnite",
    "roblox",
    "apex",
    "pubg",
    "warzone",
    "minecraft",
    "blooket",
    "prodigy",
)


def _headers():
    h = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _github_get(path: str, *, params: dict) -> requests.Response:
    url = f"{GITHUB_API_BASE}{path}"
    last_error = None

    for attempt in range(MAX_REQUEST_RETRIES + 1):
        try:
            return requests.get(url, headers=_headers(), params=params, timeout=15)
        except (
            requests.exceptions.SSLError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as exc:
            last_error = exc
            if attempt >= MAX_REQUEST_RETRIES:
                break
            time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(f"GitHub API 请求失败，已重试 {MAX_REQUEST_RETRIES} 次：{last_error}")


def get_exclude_reason(repo: dict) -> str | None:
    haystack = " ".join([
        repo.get("full_name", ""),
        repo.get("name", ""),
        repo.get("description") or "",
    ]).lower()

    matched_high_risk = next(
        (label for label, pattern in EXCLUDED_HIGH_RISK_PATTERNS if pattern.search(haystack)),
        None,
    )
    if matched_high_risk:
        return f"命中过滤：高风险词={matched_high_risk}"

    matched_game = next((keyword for keyword in EXCLUDED_GAME_KEYWORDS if keyword in haystack), None)
    matched_cheat = next((keyword for keyword in EXCLUDED_REPO_KEYWORDS if keyword in haystack), None)
    if matched_game and matched_cheat:
        return f"命中过滤：游戏相关词={matched_game}；外挂/作弊词={matched_cheat}"
    return None


def should_exclude_repo(repo: dict) -> bool:
    """保守过滤明显的游戏外挂/作弊工具，避免误杀创意工具类项目。"""
    return get_exclude_reason(repo) is not None


def fetch_top_repos_with_debug(top: int = 25, period: str = "weekly", lang: str = None) -> tuple[list[dict], list[dict]]:
    since = get_since_date(period)
    query = f"created:>{since}"
    if lang:
        query += f" language:{lang}"

    repos = []
    excluded = []
    page = 1
    per_page = min(max(top * 2, 30), 100)

    while len(repos) < top:
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
            "page": page,
        }
        resp = _github_get("/search/repositories", params=params)

        if resp.status_code == 403:
            remaining = resp.headers.get("X-RateLimit-Remaining", "0")
            reset = resp.headers.get("X-RateLimit-Reset", "")
            raise RuntimeError(f"Rate limit 已耗尽（剩余: {remaining}），重置时间: {reset}。请配置 GITHUB_TOKEN。")

        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break

        for item in items:
            reason = get_exclude_reason(item)
            if reason:
                excluded.append({
                    "name": item["full_name"],
                    "reason": reason,
                })
                continue
            repos.append(item)
            if len(repos) >= top:
                break

        if len(items) < per_page:
            break
        page += 1
        per_page = min(max(top - len(repos), 30), 100)

    return [_parse(i + 1, r) for i, r in enumerate(repos[:top])], excluded


def fetch_top_repos(top: int = 25, period: str = "weekly", lang: str = None) -> list[dict]:
    repos, _ = fetch_top_repos_with_debug(top=top, period=period, lang=lang)
    return repos


def _parse(rank: int, r: dict) -> dict:
    return {
        "rank": rank,
        "name": r["full_name"],
        "description": r.get("description") or "",
        "stars": r["stargazers_count"],
        "forks": r["forks_count"],
        "language": r.get("language") or "N/A",
        "url": r["html_url"],
        "created_at": r["created_at"],
    }
