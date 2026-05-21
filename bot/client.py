"""
Binance Futures Testnet REST client.

This module handles request signing, authenticated HTTP transport, structured
error wrapping, and request/response logging for Binance USDT-M Futures Testnet.
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT_SEC = 10
DEFAULT_RECV_WINDOW = 5000


class BinanceAPIError(Exception):
    """Raised when Binance returns a non-2xx response or error payload."""

    def __init__(self, message: str, code: Optional[int] = None):
        self.message = message
        self.code = code
        super().__init__(f"Binance API Error [code={code}]: {message}")


class NetworkError(Exception):
    """Raised for connection timeouts and transport-level failures."""


class BinanceFuturesClient:
    """Thin wrapper around the Binance USDT-M Futures REST API."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT_SEC,
    ):
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self.api_key})

        logger.info("BinanceFuturesClient initialised; base_url=%s", self.base_url)

    def _sign(self, payload: Dict[str, Any]) -> str:
        """Return the HMAC-SHA256 signature for a query-string payload."""
        query_string = urlencode(payload)
        return hmac.new(self.api_secret, query_string.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def _timestamp() -> int:
        return int(time.time() * 1000)

    def _attach_auth(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params["timestamp"] = self._timestamp()
        params["recvWindow"] = DEFAULT_RECV_WINDOW
        params["signature"] = self._sign(params)
        return params

    @staticmethod
    def _safe_params(params: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in params.items() if key != "signature"}

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        logger.debug("Response <- [%d] %s", response.status_code, response.text[:2000])

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            message = payload.get("msg") or response.text or "Unknown error"
            code = payload.get("code", response.status_code)
            logger.error("API error; HTTP %d code=%s msg=%s", response.status_code, code, message)
            raise BinanceAPIError(message=message, code=code) from exc

        if isinstance(payload, dict) and "code" in payload and "msg" in payload:
            logger.error("API error payload; code=%s msg=%s", payload.get("code"), payload.get("msg"))
            raise BinanceAPIError(message=payload.get("msg", "Unknown error"), code=payload.get("code"))

        return payload

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send an authenticated GET request."""
        request_params = self._attach_auth(dict(params or {}))
        url = f"{self.base_url}{endpoint}"
        logger.debug("GET -> %s | params=%s", url, json.dumps(self._safe_params(request_params)))

        try:
            response = self._session.get(url, params=request_params, timeout=self.timeout)
        except requests.ConnectionError as exc:
            logger.error("Connection error on GET %s: %s", endpoint, exc)
            raise NetworkError(f"Cannot reach Binance API: {exc}") from exc
        except requests.Timeout as exc:
            logger.error("Timeout on GET %s", endpoint)
            raise NetworkError(f"Request timed out after {self.timeout}s") from exc

        return self._handle_response(response)

    def post(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send an authenticated POST request as form-encoded data."""
        request_params = self._attach_auth(dict(params))
        url = f"{self.base_url}{endpoint}"
        logger.debug("POST -> %s | body=%s", url, json.dumps(self._safe_params(request_params)))

        try:
            response = self._session.post(url, data=request_params, timeout=self.timeout)
        except requests.ConnectionError as exc:
            logger.error("Connection error on POST %s: %s", endpoint, exc)
            raise NetworkError(f"Cannot reach Binance API: {exc}") from exc
        except requests.Timeout as exc:
            logger.error("Timeout on POST %s", endpoint)
            raise NetworkError(f"Request timed out after {self.timeout}s") from exc

        return self._handle_response(response)
