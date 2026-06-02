import argparse
import sys
from datetime import datetime
from fetcher import fetch_top_repos, fetch_top_repos_with_debug
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
    parser.add_argument("--min-new", type=int, default=20, help="至少写入多少条历史未记录仓库（默认 20）")
    parser.add_argument("--period", choices=["today", "weekly", "monthly"], default="weekly")
    parser.add_argument("--lang", type=str, default=None, help="按编程语言筛选")
    parser.add_argument("--export", choices=["json", "csv"], default=None, help="同时导出本地文件")
    parser.add_argument("--dry-run", action="store_true", help="只抓取和去重，不写入飞书")
    parser.add_argument("--force-write", action="store_true", help="忽略去重，强制写入飞书，便于本地验证内容展示")
    parser.add_argument("--debug-filter", action="store_true", help="输出抓取过滤明细，便于本地调试筛选规则")
    parser.add_argument("--token", type=str, default=None, help="GitHub Token（优先级高于 .env）")
    args = parser.parse_args()

    if args.token:
        import config, fetcher
        config.GITHUB_TOKEN = args.token
        fetcher.GITHUB_TOKEN = args.token

    console.print(f"[bold]正在抓取 GitHub 热门仓库...[/bold] period=[cyan]{args.period}[/cyan] top=[cyan]{args.top}[/cyan]")

    try:
        if args.debug_filter:
            repos, excluded = fetch_top_repos_with_debug(top=args.top, period=args.period, lang=args.lang)
        else:
            repos = fetch_top_repos(top=args.top, period=args.period, lang=args.lang)
            excluded = []
    except RuntimeError as e:
        console.print(f"[red]错误：{e}[/red]")
        sys.exit(1)

    print_repos(repos, period=args.period, lang=args.lang)
    if args.debug_filter:
        console.print(f"[dim]过滤掉：{len(excluded)} 条[/dim]")
        if excluded:
            console.print("[bold yellow]过滤明细[/bold yellow]")
            for item in excluded:
                console.print(f"- {item['name']} [dim]({item['reason']})[/dim]")

    week = get_week_label()
    dedup = DedupState()
    to_write = []
    new_unseen_count = 0

    def _prepare_repo(repo: dict, action: str) -> dict:
        prepared = dict(repo)
        prepared["_dedup_action"] = action
        prepared["first_seen"] = dedup.get_first_seen(prepared["url"])
        if action == "new":
            prepared["_star_increase"] = 0
        elif action == "force_write":
            prepared["_star_increase"] = 0
        else:
            prepared["_star_increase"] = repo["stars"] - dedup.get_stars(prepared["url"], week)
        return prepared

    seen_urls = set()
    for repo in repos:
        seen_urls.add(repo["url"])
        if args.force_write:
            to_write.append(_prepare_repo(repo, "force_write"))
            continue
        was_seen_before = dedup.has_seen(repo["url"])
        action = dedup.check_and_update(repo["url"], repo["stars"], week)
        if action == "skip":
            continue
        if action == "new" and not was_seen_before:
            to_write.append(_prepare_repo(repo, action))
            new_unseen_count += 1
        elif action == "update":
            to_write.append(_prepare_repo(repo, action))

    initial_to_write_count = len(to_write)
    if not args.force_write and args.min_new > 0 and new_unseen_count < args.min_new:
        console.print(
            f"[yellow]当前只找到 {new_unseen_count} 条历史未记录仓库，开始补足到 {args.min_new} 条[/yellow]"
        )
        refill_size = max(args.top, args.min_new)
        refill_limit = refill_size
        max_refill_limit = max(refill_size * 4, args.min_new * 4)
        while new_unseen_count < args.min_new and refill_limit <= max_refill_limit:
            try:
                if args.debug_filter:
                    refill_repos, refill_excluded = fetch_top_repos_with_debug(
                        top=refill_limit, period=args.period, lang=args.lang
                    )
                else:
                    refill_repos = fetch_top_repos(top=refill_limit, period=args.period, lang=args.lang)
                    refill_excluded = []
            except RuntimeError as e:
                console.print(f"[yellow]补位抓取失败：{e}[/yellow]")
                break

            for repo in refill_repos:
                if repo["url"] in seen_urls:
                    continue
                seen_urls.add(repo["url"])
                was_seen_before = dedup.has_seen(repo["url"])
                action = dedup.preview_action(repo["url"], repo["stars"], week)
                if action != "new" or was_seen_before:
                    continue
                dedup.check_and_update(repo["url"], repo["stars"], week)
                to_write.append(_prepare_repo(repo, action))
                new_unseen_count += 1
                if new_unseen_count >= args.min_new:
                    break

            if new_unseen_count >= args.min_new:
                break
            refill_limit += refill_size

    console.print(
        f"[dim]去重后待写入：{len(to_write)} 条（初始跳过 {len(repos) - initial_to_write_count} 条）[/dim]"
    )

    if new_unseen_count < args.min_new and not args.force_write:
        console.print(
            f"[yellow]本轮仍不足 {args.min_new} 条历史未记录仓库，最终写入 {new_unseen_count} 条[/yellow]"
        )

    if not args.dry_run and to_write:
        feishu = FeishuClient()
        table_id = feishu.get_or_create_table(week)
        feishu.ensure_fields(table_id, ["仓库解读", "快速上手", "推荐初稿", "入池状态", "选题池记录"])
        today = datetime.utcnow().strftime("%Y-%m-%d")
        for repo in to_write:
            readme = fetch_readme(repo["name"])
            llm_content = generate_repo_content(
                name=repo["name"],
                description=repo["description"],
                language=repo["language"],
                readme=readme,
                stars=repo["stars"],
                forks=repo["forks"],
                created_at=repo["created_at"][:10],
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
                "推荐初稿": llm_content["推荐初稿"],
            }
            if repo["_dedup_action"] in {"new", "force_write"}:
                fields["入池状态"] = "未处理"
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
