import pytest
from unittest.mock import patch, MagicMock
from feishu import FeishuClient


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
