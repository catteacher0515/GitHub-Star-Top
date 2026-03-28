import json
import requests
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL

PROMPT_TEMPLATE = """你是一个技术分析助手。根据以下 GitHub 仓库的 README，用中文输出 JSON，格式如下：
{{"summary": "一句话介绍仓库用途（50字以内）", "quickstart": "快速上手步骤（100字以内）"}}

仓库：{full_name}
README：
{readme}

只输出 JSON，不要其他内容。"""


def analyze_repo(full_name: str, readme: str) -> dict:
    """调用 DeepSeek 分析仓库，失败重试一次，最终失败返回空字段"""
    empty = {"summary": "", "quickstart": ""}
    for _ in range(2):
        try:
            resp = requests.post(
                f"{DEEPSEEK_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(
                        full_name=full_name,
                        readme=readme[:3000],
                    )}],
                    "temperature": 0.3,
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:
            continue
    return empty
