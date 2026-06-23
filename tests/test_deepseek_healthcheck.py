from unittest.mock import MagicMock, patch

import pytest

import deepseek_healthcheck


def _mock_response(status_code=200, payload=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload or {}
    resp.text = str(payload or {})
    resp.raise_for_status = MagicMock()
    return resp


def test_check_balance_raises_when_key_missing():
    with pytest.raises(RuntimeError, match="缺少 DEEPSEEK_API_KEY"):
        deepseek_healthcheck.check_balance("")


def test_check_balance_raises_on_non_200_response():
    resp = _mock_response(
        status_code=402,
        payload={"error": {"message": "Insufficient Balance"}},
    )
    resp.raise_for_status.side_effect = Exception("402 Client Error: Payment Required")
    with patch("deepseek_healthcheck.requests.get", return_value=resp):
        with pytest.raises(RuntimeError, match="DeepSeek 余额检查失败"):
            deepseek_healthcheck.check_balance("sk-test")


def test_check_balance_raises_when_service_unavailable():
    resp = _mock_response(
        payload={
            "is_available": False,
            "balance_infos": [
                {"currency": "CNY", "total_balance": "9.92"},
            ],
        }
    )
    with patch("deepseek_healthcheck.requests.get", return_value=resp):
        with pytest.raises(RuntimeError, match="当前不可用"):
            deepseek_healthcheck.check_balance("sk-test")


def test_check_balance_raises_when_all_balances_are_zero():
    resp = _mock_response(
        payload={
            "is_available": True,
            "balance_infos": [
                {"currency": "CNY", "total_balance": "0.00"},
                {"currency": "USD", "total_balance": "0"},
            ],
        }
    )
    with patch("deepseek_healthcheck.requests.get", return_value=resp):
        with pytest.raises(RuntimeError, match="可用余额为 0"):
            deepseek_healthcheck.check_balance("sk-test")


def test_check_balance_returns_summary_when_available():
    resp = _mock_response(
        payload={
            "is_available": True,
            "balance_infos": [
                {"currency": "CNY", "total_balance": "9.92"},
                {"currency": "USD", "total_balance": "1.50"},
            ],
        }
    )
    with patch("deepseek_healthcheck.requests.get", return_value=resp):
        result = deepseek_healthcheck.check_balance("sk-test")

    assert result == {
        "is_available": True,
        "balances": [
            {"currency": "CNY", "total_balance": "9.92"},
            {"currency": "USD", "total_balance": "1.50"},
        ],
        "summary": "CNY 9.92, USD 1.50",
    }


def test_main_prints_summary_and_returns_zero():
    resp = _mock_response(
        payload={
            "is_available": True,
            "balance_infos": [
                {"currency": "CNY", "total_balance": "9.92"},
            ],
        }
    )
    with patch("deepseek_healthcheck.requests.get", return_value=resp):
        with patch.object(deepseek_healthcheck.console, "print") as mock_print:
            result = deepseek_healthcheck.main()

    assert result == 0
    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "DeepSeek 可用" in rendered
    assert "CNY 9.92" in rendered


def test_main_prints_error_and_returns_one():
    with patch("deepseek_healthcheck.check_balance", side_effect=RuntimeError("boom")):
        with patch.object(deepseek_healthcheck.console, "print") as mock_print:
            result = deepseek_healthcheck.main()

    assert result == 1
    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "boom" in rendered
