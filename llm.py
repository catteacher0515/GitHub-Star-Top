import requests
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL

PROMPT_TEMPLATE = """你是一个技术内容创作者，帮助非技术读者了解 GitHub 热门项目。

仓库信息：
- 名称：{name}
- 描述：{description}
- 语言：{language}
- README 摘要：{readme_summary}

请生成以下两段内容：

【仓库解读】
用口语化、有故事感的方式介绍这个项目：它是什么、解决什么问题、适合谁用。面向非技术读者，200字以内。

【快速上手】
结构化介绍：① 核心功能（2-3条）② 上手步骤（2-3步）。面向有一定基础的读者，300字以内。

直接输出两段内容，不要其他说明。"""


def _call_api(prompt: str) -> dict:
    resp = requests.post(
        f"{DEEPSEEK_API_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 800,
        },
        timeout=30,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    return _parse(text)


def _parse(text: str) -> dict:
    intro, guide = "", ""
    if "【仓库解读】" in text and "【快速上手】" in text:
        parts = text.split("【快速上手】")
        intro = parts[0].replace("【仓库解读】", "").strip()
        guide = parts[1].strip()
    else:
        intro = text.strip()
    return {"仓库解读": intro, "快速上手": guide}


def generate_repo_content(name: str, description: str, language: str, readme: str) -> dict:
    """生成仓库解读和快速上手内容，失败重试一次，还是失败返回空字段"""
    readme_summary = readme[:1500] if readme else description
    prompt = PROMPT_TEMPLATE.format(
        name=name,
        description=description or "暂无描述",
        language=language or "未知",
        readme_summary=readme_summary,
    )
    for attempt in range(2):
        try:
            return _call_api(prompt)
        except Exception:
            if attempt == 1:
                return {"仓库解读": "", "快速上手": ""}
    return {"仓库解读": "", "快速上手": ""}
