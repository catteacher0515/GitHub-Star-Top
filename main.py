import argparse
import sys
from datetime import datetime
from fetcher import fetch_top_repos
from formatter import print_repos, console
from exporter import export_json, export_csv
from dedup import DedupState
from feishu import FeishuClient
from readme_fetcher import fetch_readme
from llm import generate_repo_content
from config import get_week_label


def main():
    parser = argparse.ArgumentParser(description="抓取 GitHub 热门仓库并写入飞书")
    parser.add_argument("--top", type=int, default=30, help="抓取前 N 个仓库（默认 30）")
    parser.add_argument("--period", choices=["today", "weekly", "monthly"], default="weekly")
    parser.add_argument("--lang", type=str, default=None, help="按编程语言筛选")
    parser.add_argument("--export", choices=["json", "csv"], default=None, help="同时导出本地文件")
    parser.add_argument("--dry-run", action="store_true", help="只抓取和去重，不写入飞书")
    parser.add_argument("--token", type=str, default=None, help="GitHub Token（优先级高于 .env）")
    args = parser.parse_args()

    if args.token:
        import config, fetcher
        config.GITHUB_TOKEN = args.token
        fetcher.GITHUB_TOKEN = args.token

    console.print(f"[bold]正在抓取 GitHub 热门仓库...[/bold] period=[cyan]{args.period}[/cyan] top=[cyan]{args.top}[/cyan]")

    try:
        repos = fetch_top_repos(top=args.top, period=args.period, lang=args.lang)
    except RuntimeError as e:
        console.print(f"[red]错误：{e}[/red]")
        sys.exit(1)

    print_repos(repos, period=args.period, lang=args.lang)

    week = get_week_label()
    dedup = DedupState()
    to_write = []

    for repo in repos:
        old_stars = dedup.get_stars(repo["url"], week)
        action = dedup.check_and_update(repo["url"], repo["stars"], week)
        if action == "skip":
            continue
        repo["_dedup_action"] = action
        repo["_star_increase"] = 0 if action == "new" else (repo["stars"] - old_stars)
        repo["first_seen"] = dedup.get_first_seen(repo["url"])
        to_write.append(repo)

    console.print(f"[dim]去重后待写入：{len(to_write)} 条（跳过 {len(repos) - len(to_write)} 条）[/dim]")

    if not args.dry_run and to_write:
        feishu = FeishuClient()
        table_id = feishu.get_or_create_table(week)
        feishu.ensure_fields(table_id, ["仓库解读", "快速上手"])
        today = datetime.utcnow().strftime("%Y-%m-%d")
        for repo in to_write:
            readme = fetch_readme(repo["name"])
            llm_content = generate_repo_content(
                name=repo["name"],
                description=repo["description"],
                language=repo["language"],
                readme=readme,
            )
            fields = {
                "仓库名": repo["name"],
                "描述": repo["description"],
                "Stars": repo["stars"],
                "Star 涨幅": repo["_star_increase"],
                "语言": repo["language"],
                "链接": {"link": repo["url"], "text": repo["name"]},
                "首次入榜时间": repo["first_seen"],
                "最后更新时间": today,
                "仓库解读": llm_content["仓库解读"],
                "快速上手": llm_content["快速上手"],
            }
            record_id = None
            if repo["_dedup_action"] == "update" and dedup.is_loaded_from_file():
                record_id = feishu.find_record_id(table_id, repo["url"])
            feishu.upsert_record(table_id, fields, record_id=record_id)
        console.print(f"[green]已写入飞书表格 {week}，共 {len(to_write)} 条[/green]")
        dedup.save()
    elif args.dry_run:
        console.print("[yellow]dry-run 模式，跳过飞书写入[/yellow]")
        dedup.save()

    if args.export == "json":
        path = export_json(repos, args.period)
        console.print(f"[green]已导出 JSON：{path}[/green]")
    elif args.export == "csv":
        path = export_csv(repos, args.period)
        console.print(f"[green]已导出 CSV：{path}[/green]")


if __name__ == "__main__":
    main()
