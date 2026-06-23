import os
from decimal import Decimal, InvalidOperation

import requests
from rich.console import Console

from config import DEEPSEEK_API_BASE, DEEPSEEK_API_KEY


console = Console()


def _parse_balance(value: str) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, TypeError):
        return Decimal("0")


def check_balance(api_key: str) -> dict:
    if not api_key:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY")

    try:
        resp = requests.get(
            f"{DEEPSEEK_API_BASE}/user/balance",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"DeepSeek 余额检查失败: {exc}") from exc

    data = resp.json()
    is_available = bool(data.get("is_available"))
    balances = []
    total = Decimal("0")
    for item in data.get("balance_infos", []):
        currency = item.get("currency") or "UNKNOWN"
        total_balance = str(item.get("total_balance") or "0")
        balances.append({"currency": currency, "total_balance": total_balance})
        total += _parse_balance(total_balance)

    if not is_available:
        raise RuntimeError("DeepSeek 当前不可用")
    if total <= 0:
        raise RuntimeError("DeepSeek 可用余额为 0")

    summary = ", ".join(
        f"{item['currency']} {item['total_balance']}" for item in balances
    ) or "unknown"
    return {
        "is_available": is_available,
        "balances": balances,
        "summary": summary,
    }


def main() -> int:
    api_key = DEEPSEEK_API_KEY or os.getenv("DEEPSEEK_API_KEY", "")
    try:
        result = check_balance(api_key)
    except RuntimeError as exc:
        console.print(f"[red]DeepSeek 预检失败：{exc}[/red]")
        return 1

    console.print(f"[green]DeepSeek 可用，余额：{result['summary']}[/green]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
