import requests
from config import GITHUB_TOKEN, GITHUB_API_BASE, get_since_date


def _headers():
    h = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def fetch_top_repos(top: int = 25, period: str = "weekly", lang: str = None) -> list[dict]:
    since = get_since_date(period)
    query = f"created:>{since}"
    if lang:
        query += f" language:{lang}"

    repos = []
    page = 1
    per_page = min(top, 100)

    while len(repos) < top:
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
            "page": page,
        }
        resp = requests.get(f"{GITHUB_API_BASE}/search/repositories", headers=_headers(), params=params, timeout=15)

        if resp.status_code == 403:
            remaining = resp.headers.get("X-RateLimit-Remaining", "0")
            reset = resp.headers.get("X-RateLimit-Reset", "")
            raise RuntimeError(f"Rate limit 已耗尽（剩余: {remaining}），重置时间: {reset}。请配置 GITHUB_TOKEN。")

        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break

        repos.extend(items)
        if len(items) < per_page:
            break
        page += 1
        per_page = min(top - len(repos), 100)

    return [_parse(i + 1, r) for i, r in enumerate(repos[:top])]


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
