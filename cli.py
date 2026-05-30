#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot CLI.

Examples:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 100000
    python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT --quantity 0.001 --price 95000 --stop-price 94500
"""

import argparse
import logging
import os
import sys
from typing import Any, Dict

from bot.client import BinanceAPIError, BinanceFuturesClient, NetworkError
from bot.logging_config import setup_logging
from bot.orders import OrderManager
from bot.validators import ValidationError, validate_order_params

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False


load_dotenv()

logger = logging.getLogger(__name__)

DIVIDER = "-" * 54
THICK = "=" * 54


def _redact(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def print_summary(params: Dict[str, Any]) -> None:
    print(f"\n{THICK}")
    print("  ORDER REQUEST SUMMARY")
    print(THICK)
    print(f"  {'Symbol':<14}: {params['symbol']}")
    print(f"  {'Side':<14}: {params['side']}")
    print(f"  {'Order Type':<14}: {params['order_type']}")
    print(f"  {'Quantity':<14}: {params['quantity']}")
    if params.get("price"):
        print(f"  {'Limit Price':<14}: {params['price']}")
    if params.get("stop_price"):
        print(f"  {'Stop Price':<14}: {params['stop_price']}")
    print(THICK)


def print_response(response: Dict[str, Any]) -> None:
    avg_price = response.get("avgPrice") or response.get("price") or "N/A"
    if avg_price in ("0", 0):
        avg_price = response.get("price", "N/A")

    print("\nSUCCESS: order placed")
    print(DIVIDER)
    print(f"  {'Order ID':<16}: {response.get('orderId')}")
    print(f"  {'Symbol':<16}: {response.get('symbol')}")
    print(f"  {'Status':<16}: {response.get('status')}")
    print(f"  {'Side':<16}: {response.get('side')}")
    print(f"  {'Type':<16}: {response.get('type')}")
    print(f"  {'Orig Qty':<16}: {response.get('origQty')}")
    print(f"  {'Executed Qty':<16}: {response.get('executedQty')}")
    print(f"  {'Avg / Limit Price':<16}: {avg_price}")
    if response.get("stopPrice") and response.get("stopPrice") != "0":
        print(f"  {'Stop Price':<16}: {response.get('stopPrice')}")
    print(f"  {'Time In Force':<16}: {response.get('timeInForce', 'N/A')}")
    print(DIVIDER)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Place orders on Binance USDT-M Futures Testnet.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    order_group = parser.add_argument_group("Order parameters")
    order_group.add_argument("--symbol", "-s", required=True, help="Trading pair, e.g. BTCUSDT")
    order_group.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        help="Order side: BUY or SELL",
    )
    order_group.add_argument(
        "--type",
        "-t",
        required=True,
        dest="order_type",
        choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
        help="Order type: MARKET, LIMIT, or STOP_LIMIT",
    )
    order_group.add_argument("--quantity", "-q", required=True, help="Order quantity, e.g. 0.001")
    order_group.add_argument("--price", "-p", default=None, help="Limit price, required for LIMIT and STOP_LIMIT")
    order_group.add_argument("--stop-price", default=None, dest="stop_price", help="Trigger price, required for STOP_LIMIT")

    auth_group = parser.add_argument_group(
        "Authentication",
        "Values fall back to BINANCE_API_KEY and BINANCE_API_SECRET environment variables.",
    )
    auth_group.add_argument("--api-key", default=None, help="Binance API key")
    auth_group.add_argument("--api-secret", default=None, help="Binance API secret")

    misc_group = parser.add_argument_group("Misc")
    misc_group.add_argument("--log-dir", default="logs", help="Directory for log files")
    misc_group.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    log_file = setup_logging(args.log_dir)
    safe_args = vars(args).copy()
    safe_args["api_key"] = _redact(safe_args.get("api_key") or os.getenv("BINANCE_API_KEY", ""))
    safe_args["api_secret"] = "***" if safe_args.get("api_secret") or os.getenv("BINANCE_API_SECRET") else ""
    logger.info("Session started; args=%s", safe_args)

    api_key = args.api_key or os.getenv("BINANCE_API_KEY", "")
    api_secret = args.api_secret or os.getenv("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        print(
            "ERROR: missing credentials.\n"
            "Set BINANCE_API_KEY and BINANCE_API_SECRET in your environment, "
            "or pass --api-key and --api-secret."
        )
        logger.error("Missing API credentials; aborting")
        sys.exit(1)

    try:
        params = validate_order_params(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValidationError as exc:
        print(f"ERROR: validation failed: {exc}")
        logger.error("Validation failed: %s", exc)
        sys.exit(1)

    print_summary(params)

    if not args.yes:
        try:
            answer = input("\n  Proceed with this order? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(0)
        if answer != "y":
            print("Order cancelled.")
            logger.info("Order cancelled by user")
            sys.exit(0)

    print("\nSending order to Binance Futures Testnet...")

    client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
    manager = OrderManager(client)

    try:
        order_type = params["order_type"]
        if order_type == "MARKET":
            response = manager.place_market_order(
                symbol=params["symbol"],
                side=params["side"],
                quantity=params["quantity"],
            )
        elif order_type == "LIMIT":
            response = manager.place_limit_order(
                symbol=params["symbol"],
                side=params["side"],
                quantity=params["quantity"],
                price=params["price"],
            )
        elif order_type == "STOP_LIMIT":
            response = manager.place_stop_limit_order(
                symbol=params["symbol"],
                side=params["side"],
                quantity=params["quantity"],
                price=params["price"],
                stop_price=params["stop_price"],
            )
        else:
            print(f"ERROR: unsupported order type: {order_type}")
            sys.exit(1)
    except BinanceAPIError as exc:
        print(f"\nERROR: Binance API error: {exc.message} (code: {exc.code})")
        logger.error("BinanceAPIError; code=%s msg=%s", exc.code, exc.message)
        print(f"Log: {log_file}")
        sys.exit(1)
    except NetworkError as exc:
        print(f"\nERROR: network error: {exc}")
        logger.error("NetworkError: %s", exc)
        print(f"Log: {log_file}")
        sys.exit(1)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"\nERROR: unexpected failure: {exc}")
        logger.exception("Unexpected exception during order placement")
        print(f"Log: {log_file}")
        sys.exit(1)

    print_response(response)
    logger.info("Order placed successfully; orderId=%s", response.get("orderId"))
    print(f"Log: {log_file}\n")


if __name__ == "__main__":
    main()

