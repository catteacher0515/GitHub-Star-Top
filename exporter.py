import json
import csv
from datetime import datetime


def _filename(period: str, fmt: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"github_stars_{ts}_{period}.{fmt}"


def export_json(repos: list[dict], period: str) -> str:
    filename = _filename(period, "json")
    data = {
        "generated_at": datetime.utcnow().isoformat(),
        "period": period,
        "total": len(repos),
        "repos": repos,
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filename


def export_csv(repos: list[dict], period: str) -> str:
    filename = _filename(period, "csv")
    fields = ["rank", "name", "description", "stars", "forks", "language", "url", "created_at"]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(repos)
    return filename
