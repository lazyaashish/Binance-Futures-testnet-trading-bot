"""Unit tests for the Binance Futures Testnet trading bot."""

import json
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

import requests

from bot.client import BinanceAPIError, BinanceFuturesClient, NetworkError
from bot.orders import OrderManager
from bot.validators import (
    ValidationError,
    validate_order_params,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)


class TestValidateSymbol(unittest.TestCase):
    def test_valid_symbol(self):
        self.assertEqual(validate_symbol("BTCUSDT"), "BTCUSDT")

    def test_lowercase_normalised(self):
        self.assertEqual(validate_symbol("btcusdt"), "BTCUSDT")

    def test_strips_whitespace(self):
        self.assertEqual(validate_symbol("  ETHUSDT  "), "ETHUSDT")

    def test_empty_raises(self):
        with self.assertRaises(ValidationError):
            validate_symbol("")

    def test_too_short_raises(self):
        with self.assertRaises(ValidationError):
            validate_symbol("BT")

    def test_special_chars_raises(self):
        with self.assertRaises(ValidationError):
            validate_symbol("BTC-USDT")

    def test_none_raises(self):
        with self.assertRaises(ValidationError):
            validate_symbol(None)  # type: ignore[arg-type]


class TestValidateSide(unittest.TestCase):
    def test_buy(self):
        self.assertEqual(validate_side("BUY"), "BUY")

    def test_sell(self):
        self.assertEqual(validate_side("SELL"), "SELL")

    def test_lowercase(self):
        self.assertEqual(validate_side("buy"), "BUY")

    def test_invalid_raises(self):
        with self.assertRaises(ValidationError):
            validate_side("HOLD")

    def test_empty_raises(self):
        with self.assertRaises(ValidationError):
            validate_side("")


class TestValidateOrderType(unittest.TestCase):
    def test_market(self):
        self.assertEqual(validate_order_type("MARKET"), "MARKET")

    def test_limit(self):
        self.assertEqual(validate_order_type("LIMIT"), "LIMIT")

    def test_stop_limit(self):
        self.assertEqual(validate_order_type("STOP_LIMIT"), "STOP_LIMIT")

    def test_lowercase_normalised(self):
        self.assertEqual(validate_order_type("limit"), "LIMIT")

    def test_invalid_raises(self):
        with self.assertRaises(ValidationError):
            validate_order_type("OCO")


class TestValidateQuantity(unittest.TestCase):
    def test_valid_decimal(self):
        self.assertEqual(validate_quantity("0.001"), Decimal("0.001"))

    def test_valid_int_string(self):
        self.assertEqual(validate_quantity("1"), Decimal("1"))

    def test_zero_raises(self):
        with self.assertRaises(ValidationError):
            validate_quantity("0")

    def test_negative_raises(self):
        with self.assertRaises(ValidationError):
            validate_quantity("-1")

    def test_non_numeric_raises(self):
        with self.assertRaises(ValidationError):
            validate_quantity("abc")


class TestValidatePrice(unittest.TestCase):
    def test_valid_price(self):
        self.assertEqual(validate_price("60000"), Decimal("60000"))

    def test_zero_raises(self):
        with self.assertRaises(ValidationError):
            validate_price("0")

    def test_negative_raises(self):
        with self.assertRaises(ValidationError):
            validate_price("-100")


class TestValidateOrderParams(unittest.TestCase):
    def test_market_buy(self):
        result = validate_order_params("BTCUSDT", "BUY", "MARKET", "0.001")
        self.assertEqual(result["symbol"], "BTCUSDT")
        self.assertEqual(result["side"], "BUY")
        self.assertEqual(result["order_type"], "MARKET")
        self.assertEqual(result["quantity"], Decimal("0.001"))
        self.assertIsNone(result["price"])
        self.assertIsNone(result["stop_price"])

    def test_limit_requires_price(self):
        with self.assertRaises(ValidationError):
            validate_order_params("BTCUSDT", "BUY", "LIMIT", "0.001")

    def test_stop_limit_requires_price_and_stop_price(self):
        with self.assertRaises(ValidationError):
            validate_order_params("BTCUSDT", "BUY", "STOP_LIMIT", "0.001", price="95000")

    def test_limit_order_complete(self):
        result = validate_order_params("ETHUSDT", "SELL", "LIMIT", "0.1", price="3000")
        self.assertEqual(result["price"], Decimal("3000"))
        self.assertIsNone(result["stop_price"])

    def test_stop_limit_complete(self):
        result = validate_order_params(
            "BTCUSDT",
            "BUY",
            "STOP_LIMIT",
            "0.001",
            price="95000",
            stop_price="94500",
        )
        self.assertEqual(result["price"], Decimal("95000"))
        self.assertEqual(result["stop_price"], Decimal("94500"))

    def test_market_ignores_price(self):
        result = validate_order_params("BTCUSDT", "BUY", "MARKET", "0.001", price="60000")
        self.assertIsNone(result["price"])


class TestBinanceFuturesClient(unittest.TestCase):
    def setUp(self):
        self.client = BinanceFuturesClient(api_key="test_api_key", api_secret="test_api_secret")

    def test_sign_returns_hex_string(self):
        signature = self.client._sign({"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.001"})
        self.assertIsInstance(signature, str)
        self.assertEqual(len(signature), 64)

    def test_sign_deterministic(self):
        payload = {"a": "1", "b": "2"}
        self.assertEqual(self.client._sign(payload), self.client._sign(payload))

    def test_attach_auth_adds_required_fields(self):
        result = self.client._attach_auth({"symbol": "BTCUSDT"})
        self.assertIn("timestamp", result)
        self.assertIn("recvWindow", result)
        self.assertIn("signature", result)

    def test_handle_response_raises_on_4xx(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = json.dumps({"code": -1102, "msg": "Bad parameter"})
        mock_resp.json.return_value = {"code": -1102, "msg": "Bad parameter"}
        mock_resp.raise_for_status.side_effect = requests.HTTPError()

        with self.assertRaises(BinanceAPIError) as ctx:
            self.client._handle_response(mock_resp)
        self.assertEqual(ctx.exception.code, -1102)

    def test_handle_response_raises_on_error_payload(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps({"code": -2015, "msg": "Invalid API-key"})
        mock_resp.json.return_value = {"code": -2015, "msg": "Invalid API-key"}
        mock_resp.raise_for_status.return_value = None

        with self.assertRaises(BinanceAPIError) as ctx:
            self.client._handle_response(mock_resp)
        self.assertEqual(ctx.exception.code, -2015)

    @patch("bot.client.requests.Session.post")
    def test_post_network_error_raises_network_error(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("Connection refused")
        with self.assertRaises(NetworkError):
            self.client.post("/fapi/v1/order", {"symbol": "BTCUSDT"})

    @patch("bot.client.requests.Session.post")
    def test_post_timeout_raises_network_error(self, mock_post):
        mock_post.side_effect = requests.Timeout()
        with self.assertRaises(NetworkError):
            self.client.post("/fapi/v1/order", {"symbol": "BTCUSDT"})

    @patch("bot.client.requests.Session.get")
    def test_get_network_error_raises_network_error(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("Connection refused")
        with self.assertRaises(NetworkError):
            self.client.get("/fapi/v1/openOrders")


class TestOrderManager(unittest.TestCase):
    def _make_manager(self):
        client = MagicMock(spec=BinanceFuturesClient)
        return OrderManager(client), client

    def test_place_market_order_calls_post_with_correct_params(self):
        manager, client = self._make_manager()
        client.post.return_value = {"orderId": 123, "status": "FILLED", "executedQty": "0.001"}

        response = manager.place_market_order("BTCUSDT", "BUY", Decimal("0.001"))

        client.post.assert_called_once()
        endpoint, params = client.post.call_args[0]
        self.assertEqual(endpoint, "/fapi/v1/order")
        self.assertEqual(params["symbol"], "BTCUSDT")
        self.assertEqual(params["side"], "BUY")
        self.assertEqual(params["type"], "MARKET")
        self.assertEqual(params["quantity"], "0.001")
        self.assertNotIn("price", params)
        self.assertEqual(response["orderId"], 123)

    def test_place_limit_order_includes_price_and_tif(self):
        manager, client = self._make_manager()
        client.post.return_value = {"orderId": 456, "status": "NEW"}

        manager.place_limit_order("BTCUSDT", "SELL", Decimal("0.001"), Decimal("60000"))

        _, params = client.post.call_args[0]
        self.assertEqual(params["type"], "LIMIT")
        self.assertEqual(params["price"], "60000")
        self.assertEqual(params["timeInForce"], "GTC")

    def test_place_stop_limit_order_uses_stop_type(self):
        manager, client = self._make_manager()
        client.post.return_value = {"orderId": 789, "status": "NEW"}

        manager.place_stop_limit_order("BTCUSDT", "BUY", Decimal("0.001"), Decimal("95000"), Decimal("94500"))

        _, params = client.post.call_args[0]
        self.assertEqual(params["type"], "STOP")
        self.assertEqual(params["stopPrice"], "94500")
        self.assertEqual(params["price"], "95000")

    def test_place_market_order_propagates_api_error(self):
        manager, client = self._make_manager()
        client.post.side_effect = BinanceAPIError("Insufficient margin", code=-2019)

        with self.assertRaises(BinanceAPIError):
            manager.place_market_order("BTCUSDT", "BUY", Decimal("0.001"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
