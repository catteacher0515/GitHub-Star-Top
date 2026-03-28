from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def print_repos(repos: list[dict], period: str, lang: str = None):
    period_label = {"today": "今天", "weekly": "本周", "monthly": "本月"}.get(period, period)
    title = f"GitHub 热门仓库 — {period_label}"
    if lang:
        title += f" [{lang}]"

    table = Table(title=title, box=box.ROUNDED, show_lines=True, highlight=True)
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("仓库", style="bold cyan", min_width=30)
    table.add_column("⭐ Stars", justify="right", style="yellow")
    table.add_column("语言", justify="center", width=12)
    table.add_column("描述", max_width=50)

    for r in repos:
        table.add_row(
            str(r["rank"]),
            f"[link={r['url']}]{r['name']}[/link]",
            f"{r['stars']:,}",
            r["language"],
            r["description"],
        )

    console.print(table)
    console.print(f"[dim]共 {len(repos)} 个仓库[/dim]")
