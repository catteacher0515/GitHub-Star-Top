import pytest
from unittest.mock import patch, MagicMock
from feishu import FeishuClient
import requests


@pytest.fixture
def client():
    return FeishuClient(
        app_id="test_app_id",
        app_secret="test_app_secret",
        bitable_app_token="test_token",
    )


def test_get_access_token(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"code": 0, "tenant_access_token": "t-abc123", "expire": 7200}
    mock_resp.raise_for_status = MagicMock()
    with patch("feishu.requests.post", return_value=mock_resp):
        token = client._get_access_token()
    assert token == "t-abc123"


def test_get_or_create_table_existing(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "code": 0,
        "data": {"items": [{"table_id": "tbl123", "name": "2026-W13"}]}
    }
    mock_resp.raise_for_status = MagicMock()
    with patch.object(client, "_get_access_token", return_value="t-abc"):
        with patch("feishu.requests.get", return_value=mock_resp):
            table_id = client.get_or_create_table("2026-W13")
    assert table_id == "tbl123"


def test_get_or_create_table_creates_table_with_expected_fields(client):
    list_resp = MagicMock()
    list_resp.ok = True
    list_resp.json.return_value = {"code": 0, "data": {"items": []}}

    create_resp = MagicMock()
    create_resp.ok = True
    create_resp.json.return_value = {"code": 0, "data": {"table_id": "tbl-new"}}

    with patch.object(client, "_get_access_token", return_value="t-abc"):
        with patch("feishu.requests.get", return_value=list_resp):
            with patch("feishu.requests.post", return_value=create_resp) as mock_post:
                table_id = client.get_or_create_table("2026-W21")

    assert table_id == "tbl-new"
    payload = mock_post.call_args.kwargs["json"]
    field_names = [field["field_name"] for field in payload["table"]["fields"]]
    assert "推荐初稿" in field_names
    assert "入池状态" in field_names
    assert "选题池记录" in field_names


def test_ensure_fields_adds_missing_pool_fields(client):
    fields_resp = MagicMock()
    fields_resp.json.return_value = {
        "code": 0,
        "data": {"items": [{"field_name": "仓库解读"}, {"field_name": "快速上手"}]},
    }
    fields_resp.raise_for_status = MagicMock()

    create_field_resp = MagicMock()
    create_field_resp.raise_for_status = MagicMock()

    with patch.object(client, "_get_access_token", return_value="t-abc"):
        with patch("feishu.requests.get", return_value=fields_resp):
            with patch("feishu.requests.post", return_value=create_field_resp) as mock_post:
                client.ensure_fields("tbl123", ["仓库解读", "快速上手", "推荐初稿", "入池状态", "选题池记录"])

    posted_field_names = [call.kwargs["json"]["field_name"] for call in mock_post.call_args_list]
    assert posted_field_names == ["推荐初稿", "入池状态", "选题池记录"]


def test_upsert_record_uses_new_status_field_for_new_records(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"code": 0, "data": {"record": {"record_id": "rec123"}}}
    mock_resp.raise_for_status = MagicMock()

    with patch.object(client, "_get_access_token", return_value="t-abc"):
        with patch("feishu.requests.post", return_value=mock_resp) as mock_post:
            client.upsert_record("tbl123", {
                "仓库名": "owner/repo",
                "Stars": 1000,
                "入池状态": "未处理",
            }, record_id=None)

    assert mock_post.call_args.kwargs["json"]["fields"]["入池状态"] == "未处理"


def test_upsert_record_new(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"code": 0, "data": {"record": {"record_id": "rec123"}}}
    mock_resp.raise_for_status = MagicMock()
    with patch.object(client, "_get_access_token", return_value="t-abc"):
        with patch("feishu.requests.post", return_value=mock_resp):
            client.upsert_record("tbl123", {
                "仓库名": "owner/repo",
                "Stars": 1000,
            }, record_id=None)


def test_upsert_record_update(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"code": 0, "data": {"record": {"record_id": "rec123"}}}
    mock_resp.raise_for_status = MagicMock()
    with patch.object(client, "_get_access_token", return_value="t-abc"):
        with patch("feishu.requests.put", return_value=mock_resp):
            client.upsert_record("tbl123", {
                "仓库名": "owner/repo",
                "Stars": 1500,
            }, record_id="rec123")


def test_get_or_create_table_raises_runtime_error_with_response_body(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.ok = False
    mock_resp.text = '{"code":1254040,"msg":"invalid app token"}'
    mock_resp.json.return_value = {"code": 1254040, "msg": "invalid app token"}

    with patch.object(client, "_get_access_token", return_value="t-abc"):
        with patch("feishu.requests.get", return_value=mock_resp):
            with pytest.raises(RuntimeError) as exc:
                client.get_or_create_table("2026-W20")

    assert "获取数据表列表失败" in str(exc.value)
    assert "invalid app token" in str(exc.value)
