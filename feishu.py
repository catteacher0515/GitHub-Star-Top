import time
import requests
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_BITABLE_APP_TOKEN, FEISHU_API_BASE


class FeishuClient:
    def __init__(self, app_id=None, app_secret=None, bitable_app_token=None):
        self.app_id = app_id or FEISHU_APP_ID
        self.app_secret = app_secret or FEISHU_APP_SECRET
        self.bitable_app_token = bitable_app_token or FEISHU_BITABLE_APP_TOKEN
        self._token: str = ""
        self._token_expires_at: float = 0

    def _get_access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        resp = requests.post(
            f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书获取 token 失败: {data}")
        self._token = data["tenant_access_token"]
        self._token_expires_at = time.time() + data.get("expire", 7200)
        return self._token

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def get_or_create_table(self, week_label: str) -> str:
        """获取或创建当周数据表，返回 table_id"""
        token = self._get_access_token()
        resp = requests.get(
            f"{FEISHU_API_BASE}/bitable/v1/apps/{self.bitable_app_token}/tables",
            headers=self._headers(token),
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("data", {}).get("items", [])
        for item in items:
            if item["name"] == week_label:
                return item["table_id"]

        # 不存在则创建
        resp = requests.post(
            f"{FEISHU_API_BASE}/bitable/v1/apps/{self.bitable_app_token}/tables",
            headers=self._headers(token),
            json={"table": {"name": week_label, "fields": [
                {"field_name": "仓库名", "type": 1},
                {"field_name": "描述", "type": 1},
                {"field_name": "Stars", "type": 2},
                {"field_name": "Star 涨幅", "type": 2},
                {"field_name": "语言", "type": 1},
                {"field_name": "链接", "type": 15},
                {"field_name": "首次入榜时间", "type": 1},
                {"field_name": "最后更新时间", "type": 1},
                {"field_name": "仓库解读", "type": 1},
                {"field_name": "快速上手", "type": 1},
            ]}},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书创建数据表失败: {data}")
        return data["data"]["table_id"]

    def ensure_fields(self, table_id: str, field_names: list[str]):
        """检查表字段，缺少的自动添加（文本类型）"""
        token = self._get_access_token()
        resp = requests.get(
            f"{FEISHU_API_BASE}/bitable/v1/apps/{self.bitable_app_token}/tables/{table_id}/fields",
            headers=self._headers(token),
            timeout=10,
        )
        resp.raise_for_status()
        existing = {f["field_name"] for f in resp.json().get("data", {}).get("items", [])}
        for name in field_names:
            if name not in existing:
                requests.post(
                    f"{FEISHU_API_BASE}/bitable/v1/apps/{self.bitable_app_token}/tables/{table_id}/fields",
                    headers=self._headers(token),
                    json={"field_name": name, "type": 1},
                    timeout=10,
                ).raise_for_status()
                print(f"[feishu] 已补充字段: {name}")

    def upsert_record(self, table_id: str, fields: dict, record_id: str = None):
        """新增或更新一条记录"""
        token = self._get_access_token()
        if record_id is None:
            resp = requests.post(
                f"{FEISHU_API_BASE}/bitable/v1/apps/{self.bitable_app_token}/tables/{table_id}/records",
                headers=self._headers(token),
                json={"fields": fields},
                timeout=10,
            )
        else:
            resp = requests.put(
                f"{FEISHU_API_BASE}/bitable/v1/apps/{self.bitable_app_token}/tables/{table_id}/records/{record_id}",
                headers=self._headers(token),
                json={"fields": fields},
                timeout=10,
            )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书写入记录失败: {data}")

    def find_record_id(self, table_id: str, repo_url: str) -> str | None:
        """按仓库链接查找已有记录的 record_id，找不到返回 None"""
        token = self._get_access_token()
        resp = requests.get(
            f"{FEISHU_API_BASE}/bitable/v1/apps/{self.bitable_app_token}/tables/{table_id}/records",
            headers=self._headers(token),
            params={"filter": f'CurrentValue.[链接].link = "{repo_url}"', "page_size": 1},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", {}).get("items", [])
        if items:
            return items[0]["record_id"]
        return None
