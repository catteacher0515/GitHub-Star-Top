import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from config import FEISHU_BITABLE_APP_TOKEN
from feishu import FeishuClient
from llm import generate_repo_content
from readme_fetcher import fetch_readme


REQUIRED_FIELDS = [
    "仓库名",
    "描述",
    "Stars",
    "链接",
    "仓库解读",
    "快速上手",
    "推荐初稿",
]


def _load_env() -> None:
    env_path = REPO_ROOT / ".env"
    load_dotenv(env_path)


def _run_lark(args: list[str]) -> dict:
    import subprocess
    import json

    output = subprocess.check_output(["lark-cli", *args], text=True)
    data = json.loads(output)
    if data.get("ok") is False:
        raise RuntimeError(data.get("error", {}).get("message", "lark-cli failed"))
    return data


def _table_id_for_week(base_token: str, week: str) -> str:
    result = _run_lark(["base", "+table-list", "--base-token", base_token, "--format", "json"])
    for table in result["data"]["tables"]:
        if table["name"] == week:
            return table["id"]
    raise RuntimeError(f"未找到周表: {week}")


def _list_target_records(base_token: str, table_id: str) -> list[dict]:
    result = _run_lark([
        "base",
        "+record-list",
        "--base-token",
        base_token,
        "--table-id",
        table_id,
        "--limit",
        "200",
        "--format",
        "json",
        *sum([["--field-id", field] for field in REQUIRED_FIELDS], []),
    ])
    fields = result["data"]["fields"]
    record_ids = result["data"]["record_id_list"]
    rows = result["data"]["data"]
    records = []
    for index, row in enumerate(rows):
        values = dict(zip(fields, row))
        records.append({"record_id": record_ids[index], "values": values})
    return records


def _normalize_link(value):
    if isinstance(value, dict):
        return value.get("link") or value.get("text") or ""
    return value or ""


def _needs_backfill(values: dict) -> bool:
    intro = values.get("仓库解读") or ""
    guide = values.get("快速上手") or ""
    draft = values.get("推荐初稿") or ""
    if not intro and not guide and not draft:
        return True
    if intro and (not guide or not draft):
        return True
    return False


def main() -> int:
    _load_env()

    parser = argparse.ArgumentParser(description="回填飞书多维表中的 LLM 内容字段")
    parser.add_argument("--week", default="2026-W25", help="要回填的周表，默认 2026-W25")
    parser.add_argument("--dry-run", action="store_true", help="只打印待回填记录，不实际写入")
    args = parser.parse_args()

    base_token = FEISHU_BITABLE_APP_TOKEN or os.getenv("FEISHU_BITABLE_APP_TOKEN", "")
    if not base_token:
        raise RuntimeError("缺少 FEISHU_BITABLE_APP_TOKEN")

    table_id = _table_id_for_week(base_token, args.week)
    records = _list_target_records(base_token, table_id)
    targets = [record for record in records if _needs_backfill(record["values"])]

    print(f"[backfill] week={args.week} table_id={table_id} targets={len(targets)}")
    for record in targets:
        repo_name = record["values"]["仓库名"]
        print(f"[backfill] target {repo_name} ({record['record_id']})")

    if args.dry_run or not targets:
        return 0

    feishu = FeishuClient(bitable_app_token=base_token)
    for record in targets:
        values = record["values"]
        repo_name = values["仓库名"]
        repo_url = _normalize_link(values.get("链接"))
        readme = fetch_readme(repo_name)
        content = generate_repo_content(
            name=repo_name,
            description=values.get("描述") or "",
            language=values.get("语言") or "",
            readme=readme,
            stars=int(values.get("Stars") or 0),
            forks=0,
            created_at=(values.get("最后更新时间") or "")[:10],
        )
        patch = {
            "仓库解读": content["仓库解读"],
            "快速上手": content["快速上手"],
            "推荐初稿": content["推荐初稿"],
        }
        if repo_url:
            print(f"[backfill] updating {repo_name} <- {repo_url}")
        else:
            print(f"[backfill] updating {repo_name}")
        feishu.upsert_record(table_id, patch, record_id=record["record_id"])

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[backfill] error: {exc}", file=sys.stderr)
        raise
