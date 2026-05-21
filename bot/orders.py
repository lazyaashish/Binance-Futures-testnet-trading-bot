"""Order placement logic for Binance USDT-M Futures Testnet."""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceFuturesClient

logger = logging.getLogger(__name__)

ORDER_ENDPOINT = "/fapi/v1/order"


class OrderManager:
    """High-level order operations built on the raw REST client."""

    def __init__(self, client: BinanceFuturesClient):
        self.client = client

    def place_market_order(self, symbol: str, side: str, quantity: Decimal) -> Dict[str, Any]:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": str(quantity),
        }
        logger.info("Placing MARKET %s order; symbol=%s qty=%s", side, symbol, quantity)
        response = self.client.post(ORDER_ENDPOINT, params)
        logger.info(
            "MARKET order accepted; orderId=%s status=%s executedQty=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("executedQty"),
        )
        return response

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "quantity": str(quantity),
            "price": str(price),
            "timeInForce": time_in_force,
        }
        logger.info(
            "Placing LIMIT %s order; symbol=%s qty=%s price=%s tif=%s",
            side,
            symbol,
            quantity,
            price,
            time_in_force,
        )
        response = self.client.post(ORDER_ENDPOINT, params)
        logger.info(
            "LIMIT order accepted; orderId=%s status=%s origQty=%s price=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("origQty"),
            response.get("price"),
        )
        return response

    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        stop_price: Decimal,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "STOP",
            "quantity": str(quantity),
            "price": str(price),
            "stopPrice": str(stop_price),
            "timeInForce": time_in_force,
        }
        logger.info(
            "Placing STOP_LIMIT %s order; symbol=%s qty=%s price=%s stopPrice=%s",
            side,
            symbol,
            quantity,
            price,
            stop_price,
        )
        response = self.client.post(ORDER_ENDPOINT, params)
        logger.info(
            "STOP_LIMIT order accepted; orderId=%s status=%s stopPrice=%s price=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("stopPrice"),
            response.get("price"),
        )
        return response

    def get_account_info(self) -> Dict[str, Any]:
        logger.debug("Fetching account info")
        return self.client.get("/fapi/v2/account")

    def get_open_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        logger.debug("Fetching open orders; symbol=%s", symbol)
        return self.client.get("/fapi/v1/openOrders", params)
