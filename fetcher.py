import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from config import GITHUB_API_BASE, GITHUB_TOKEN, get_since_date

MAX_REQUEST_RETRIES = 3
RETRY_DELAY_SECONDS = 2
POPULAR_REPO_MIN_STARS = 3000
POPULAR_REPO_ACTIVITY_DAYS = 90
MAX_META_SKILL_REPOS = 2
SOURCE_WEIGHTS = {
    "trending": 0.6,
    "popular": 0.3,
    "new": 0.1,
}

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

EXCLUDED_GAME_PATTERNS = (
    ("gta", re.compile(r"(?<![a-z0-9])gta(?![a-z0-9])")),
    ("cs2", re.compile(r"(?<![a-z0-9])cs2(?![a-z0-9])")),
    ("csgo", re.compile(r"(?<![a-z0-9])csgo(?![a-z0-9])")),
    ("valorant", re.compile(r"(?<![a-z0-9])valorant(?![a-z0-9])")),
    ("fortnite", re.compile(r"(?<![a-z0-9])fortnite(?![a-z0-9])")),
    ("roblox", re.compile(r"(?<![a-z0-9])roblox(?![a-z0-9])")),
    ("apex", re.compile(r"(?<![a-z0-9])apex(?![a-z0-9])")),
    ("pubg", re.compile(r"(?<![a-z0-9])pubg(?![a-z0-9])")),
    ("warzone", re.compile(r"(?<![a-z0-9])warzone(?![a-z0-9])")),
    ("minecraft", re.compile(r"(?<![a-z0-9])minecraft(?![a-z0-9])")),
    ("blooket", re.compile(r"(?<![a-z0-9])blooket(?![a-z0-9])")),
    ("prodigy", re.compile(r"(?<![a-z0-9])prodigy(?![a-z0-9])")),
)

EXCLUDED_CHEAT_PATTERNS = tuple(
    (keyword, re.compile(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])"))
    for keyword in EXCLUDED_REPO_KEYWORDS
)

EXCLUDED_PIRACY_PATTERNS = (
    ("crack", re.compile(r"(?<![a-z0-9])crack(ed|ing)?(?![a-z0-9])")),
    ("pre-activated", re.compile(r"(?<![a-z0-9])pre[- ]activated(?![a-z0-9])")),
    ("keygen", re.compile(r"(?<![a-z0-9])keygen(?![a-z0-9])")),
    ("serial key", re.compile(r"(?<![a-z0-9])serial key(?![a-z0-9])")),
    ("free download", re.compile(r"(?<![a-z0-9])(free download|download free)(?![a-z0-9])")),
    ("full version", re.compile(r"(?<![a-z0-9])full version(?![a-z0-9])")),
    ("torrent", re.compile(r"(?<![a-z0-9])torrent(?![a-z0-9])")),
    ("warez", re.compile(r"(?<![a-z0-9])warez(?![a-z0-9])")),
)

EXCLUDED_EMULATOR_PATTERNS = (
    ("emulator", re.compile(r"(?<![a-z0-9])emulator(?![a-z0-9])")),
    ("rom", re.compile(r"(?<![a-z0-9])roms?(?![a-z0-9])")),
    ("yuzu", re.compile(r"(?<![a-z0-9])yuzu(?![a-z0-9])")),
    ("ryujinx", re.compile(r"(?<![a-z0-9])ryujinx(?![a-z0-9])")),
    ("mgba", re.compile(r"(?<![a-z0-9])mgba(?![a-z0-9])")),
)

LAUNCHER_PATTERN = re.compile(r"(?<![a-z0-9])launcher(?![a-z0-9])")
LAUNCHER_CONTEXT_PATTERN = re.compile(
    r"(?<![a-z0-9])(game|games|steam|epic|download|downloads|title|titles|rom|roms|emulator|torrent|pirated)(?![a-z0-9])"
)

TRENDING_REPO_PATTERN = re.compile(
    r'<h2 class="h3 lh-condensed">\s*<a[^>]+href="/([^"/]+/[^"/]+)"',
    re.IGNORECASE | re.DOTALL,
)

META_SKILL_PATTERN = re.compile(r"(?<![a-z0-9])(skill|skills|prompt|prompts)(?![a-z0-9])")
RESOURCE_LIST_PATTERN = re.compile(r"(?<![a-z0-9])(awesome|curated|list of|collections?)(?![a-z0-9])")
MARKETING_PATTERN = re.compile(
    r"(?<![a-z0-9])(earn money|passive income|赚钱|make money|side hustle|growth hack)(?![a-z0-9])"
)
PRODUCT_SIGNAL_PATTERN = re.compile(
    r"(?<![a-z0-9])(runtime|framework|compiler|sdk|platform|database|engine|browser|assistant|search|agent|toolkit|cli|editor|deployment|observability|security|workflow)(?![a-z0-9])"
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _headers():
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _retry_request(method, *args, **kwargs):
    last_error = None
    for attempt in range(MAX_REQUEST_RETRIES + 1):
        try:
            return method(*args, **kwargs)
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


def _github_get(path: str, *, params: dict | None = None) -> requests.Response:
    url = f"{GITHUB_API_BASE}{path}"
    return _retry_request(requests.get, url, headers=_headers(), params=params or {}, timeout=15)


def _web_get(url: str) -> requests.Response:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml",
    }
    return _retry_request(requests.get, url, headers=headers, timeout=15)


def _ensure_search_ok(resp: requests.Response):
    if resp.status_code == 403:
        remaining = resp.headers.get("X-RateLimit-Remaining", "0")
        reset = resp.headers.get("X-RateLimit-Reset", "")
        raise RuntimeError(f"Rate limit 已耗尽（剩余: {remaining}），重置时间: {reset}。请配置 GITHUB_TOKEN。")
    resp.raise_for_status()


def _repo_haystack(repo: dict) -> str:
    return " ".join([
        repo.get("full_name", ""),
        repo.get("name", ""),
        repo.get("description") or "",
    ]).lower()


def _match_first(haystack: str, patterns: tuple[tuple[str, re.Pattern], ...]) -> str | None:
    return next((label for label, pattern in patterns if pattern.search(haystack)), None)


def get_exclude_reason(repo: dict) -> str | None:
    haystack = _repo_haystack(repo)

    matched_high_risk = _match_first(haystack, EXCLUDED_HIGH_RISK_PATTERNS)
    if matched_high_risk:
        return f"命中过滤：高风险词={matched_high_risk}"

    matched_piracy = _match_first(haystack, EXCLUDED_PIRACY_PATTERNS)
    if matched_piracy:
        return f"命中过滤：破解/分发词={matched_piracy}"

    matched_emulator = _match_first(haystack, EXCLUDED_EMULATOR_PATTERNS)
    if matched_emulator:
        return f"命中过滤：模拟器/ROM词={matched_emulator}"

    if LAUNCHER_PATTERN.search(haystack) and LAUNCHER_CONTEXT_PATTERN.search(haystack):
        return "命中过滤：游戏/分发启动器"

    matched_game = _match_first(haystack, EXCLUDED_GAME_PATTERNS)
    matched_cheat = _match_first(haystack, EXCLUDED_CHEAT_PATTERNS)
    if matched_game and matched_cheat:
        return f"命中过滤：游戏相关词={matched_game}；外挂/作弊词={matched_cheat}"

    return None


def should_exclude_repo(repo: dict) -> bool:
    return get_exclude_reason(repo) is not None


def _search_repositories(query: str, *, limit: int, sort: str, order: str) -> list[dict]:
    if limit <= 0:
        return []

    repos = []
    page = 1
    while len(repos) < limit:
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": min(limit - len(repos), 100),
            "page": page,
        }
        resp = _github_get("/search/repositories", params=params)
        _ensure_search_ok(resp)
        items = resp.json().get("items", [])
        if not items:
            break
        repos.extend(items)
        if len(items) < params["per_page"]:
            break
        page += 1
    return repos[:limit]


def _days_ago(days: int) -> str:
    return (_now_utc() - timedelta(days=days)).strftime("%Y-%m-%d")


def _days_since(date_str: str | None) -> int | None:
    if not date_str:
        return None
    normalized = date_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, (_now_utc() - dt).days)


def _repo_category(repo: dict) -> str:
    haystack = _repo_haystack(repo)
    if META_SKILL_PATTERN.search(haystack):
        return "meta_skill"
    if RESOURCE_LIST_PATTERN.search(haystack):
        return "resource_list"
    return "product"


def get_quality_score(repo: dict) -> int:
    score = 0
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    haystack = _repo_haystack(repo)

    if stars >= 100000:
        score += 45
    elif stars >= 30000:
        score += 35
    elif stars >= 10000:
        score += 28
    elif stars >= 3000:
        score += 18
    elif stars >= 1000:
        score += 10

    if forks >= 5000:
        score += 10
    elif forks >= 1000:
        score += 6
    elif forks >= 100:
        score += 3

    pushed_days = _days_since(repo.get("pushed_at") or repo.get("updated_at"))
    if pushed_days is not None:
        if pushed_days <= 7:
            score += 14
        elif pushed_days <= 30:
            score += 10
        elif pushed_days <= 90:
            score += 6
        elif pushed_days <= 180:
            score += 2
        else:
            score -= 6

    license_info = repo.get("license") or {}
    if license_info.get("spdx_id") not in {None, "NOASSERTION"}:
        score += 3

    if PRODUCT_SIGNAL_PATTERN.search(haystack):
        score += 8

    if META_SKILL_PATTERN.search(haystack):
        score -= 15

    if RESOURCE_LIST_PATTERN.search(haystack):
        score -= 10

    if MARKETING_PATTERN.search(haystack):
        score -= 35

    description = repo.get("description") or ""
    if len(description.strip()) < 20:
        score -= 5

    return score


def fetch_new_repos(limit: int, period: str = "weekly", lang: str = None) -> list[dict]:
    query = f"created:>{get_since_date(period)} archived:false fork:false"
    if lang:
        query += f" language:{lang}"
    return _search_repositories(query, limit=limit, sort="stars", order="desc")


def fetch_popular_repos(limit: int, lang: str = None) -> list[dict]:
    query = (
        f"stars:>={POPULAR_REPO_MIN_STARS} "
        f"archived:false fork:false pushed:>={_days_ago(POPULAR_REPO_ACTIVITY_DAYS)}"
    )
    if lang:
        query += f" language:{lang}"
    return _search_repositories(query, limit=limit, sort="stars", order="desc")


def _trending_url(period: str, lang: str = None) -> str:
    params = {}
    if period == "weekly":
        params["since"] = "weekly"
    elif period == "monthly":
        params["since"] = "monthly"
    if lang:
        params["l"] = lang
    query = urlencode(params)
    if query:
        return f"https://github.com/trending?{query}"
    return "https://github.com/trending"


def fetch_trending_repos(limit: int, period: str = "weekly", lang: str = None) -> list[dict]:
    if limit <= 0:
        return []

    resp = _web_get(_trending_url(period, lang=lang))
    resp.raise_for_status()

    full_names = []
    seen = set()
    for match in TRENDING_REPO_PATTERN.finditer(resp.text):
        full_name = match.group(1).strip()
        if full_name in seen:
            continue
        seen.add(full_name)
        full_names.append(full_name)
        if len(full_names) >= limit:
            break

    repos = []
    for full_name in full_names:
        repo_resp = _github_get(f"/repos/{full_name}")
        _ensure_search_ok(repo_resp)
        repos.append(repo_resp.json())
    return repos


def _target_counts(top: int) -> dict[str, int]:
    raw = {
        "trending": top * SOURCE_WEIGHTS["trending"],
        "popular": top * SOURCE_WEIGHTS["popular"],
        "new": top * SOURCE_WEIGHTS["new"],
    }
    counts = {key: int(value) for key, value in raw.items()}
    remainder = top - sum(counts.values())
    while remainder > 0:
        key = max(raw, key=lambda item: (raw[item] - counts[item], SOURCE_WEIGHTS[item]))
        counts[key] += 1
        remainder -= 1
    return counts


def _collect_filtered(repos: list[dict], excluded: list[dict], seen_urls: set[str]) -> list[dict]:
    kept = []
    for repo in repos:
        url = repo["html_url"]
        if url in seen_urls:
            continue
        reason = get_exclude_reason(repo)
        if reason:
            excluded.append({"name": repo["full_name"], "reason": reason})
            continue
        seen_urls.add(url)
        repo["_quality_score"] = get_quality_score(repo)
        repo["_quality_category"] = _repo_category(repo)
        kept.append(repo)
    return kept


def _apply_quality_ranking(repos: list[dict]) -> list[dict]:
    sorted_repos = sorted(
        repos,
        key=lambda repo: (
            repo.get("_quality_score", 0),
            repo.get("stargazers_count", 0),
            repo.get("forks_count", 0),
        ),
        reverse=True,
    )

    selected = []
    meta_skill_count = 0
    deferred_meta_skills = []

    for repo in sorted_repos:
        if repo.get("_quality_category") == "meta_skill":
            if meta_skill_count >= MAX_META_SKILL_REPOS:
                deferred_meta_skills.append(repo)
                continue
            meta_skill_count += 1
        selected.append(repo)

    selected.extend(deferred_meta_skills)
    return selected


def _take_primary_repos(repos: list[dict], limit: int) -> tuple[list[dict], list[dict], list[dict]]:
    if limit <= 0:
        return [], repos[:], []

    selected = []
    overflow = []
    deferred_meta = []
    meta_skill_count = 0

    for repo in repos:
        is_meta_skill = repo.get("_quality_category") == "meta_skill"
        if len(selected) < limit:
            if is_meta_skill and meta_skill_count >= MAX_META_SKILL_REPOS:
                deferred_meta.append(repo)
                continue
            selected.append(repo)
            if is_meta_skill:
                meta_skill_count += 1
            continue

        overflow.append(repo)

    return selected, overflow, deferred_meta


def fetch_top_repos_with_debug(top: int = 25, period: str = "weekly", lang: str = None) -> tuple[list[dict], list[dict]]:
    counts = _target_counts(top)
    excluded = []
    seen_urls = set()

    trending_repos = _collect_filtered(
        fetch_trending_repos(limit=counts["trending"], period=period, lang=lang),
        excluded,
        seen_urls,
    )
    trending_shortfall = max(0, counts["trending"] - len(trending_repos))
    popular_repos = _collect_filtered(
        fetch_popular_repos(limit=counts["popular"] + trending_shortfall, lang=lang),
        excluded,
        seen_urls,
    )
    remaining_before_new = max(0, top - len(trending_repos) - len(popular_repos))
    new_repos = _collect_filtered(
        fetch_new_repos(limit=max(counts["new"], remaining_before_new), period=period, lang=lang),
        excluded,
        seen_urls,
    )

    trending_repos = _apply_quality_ranking(trending_repos)
    popular_repos = _apply_quality_ranking(popular_repos)
    new_repos = _apply_quality_ranking(new_repos)

    trending_primary, trending_overflow, trending_deferred_meta = _take_primary_repos(trending_repos, counts["trending"])
    popular_primary, popular_overflow, popular_deferred_meta = _take_primary_repos(popular_repos, counts["popular"])
    new_primary, new_overflow, new_deferred_meta = _take_primary_repos(new_repos, counts["new"])

    ordered = []
    ordered.extend(trending_primary)
    ordered.extend(popular_primary)
    ordered.extend(new_primary)

    if len(ordered) < top:
        backfill = []
        backfill.extend(trending_overflow)
        backfill.extend(popular_overflow)
        backfill.extend(new_overflow)
        backfill.extend(trending_deferred_meta)
        backfill.extend(popular_deferred_meta)
        backfill.extend(new_deferred_meta)
        ordered.extend(backfill[: top - len(ordered)])

    return [_parse(index + 1, repo) for index, repo in enumerate(ordered[:top])], excluded


def fetch_top_repos(top: int = 25, period: str = "weekly", lang: str = None) -> list[dict]:
    repos, _ = fetch_top_repos_with_debug(top=top, period=period, lang=lang)
    return repos


def _parse(rank: int, repo: dict) -> dict:
    return {
        "rank": rank,
        "name": repo["full_name"],
        "description": repo.get("description") or "",
        "stars": repo["stargazers_count"],
        "forks": repo["forks_count"],
        "language": repo.get("language") or "N/A",
        "url": repo["html_url"],
        "created_at": repo["created_at"],
    }
