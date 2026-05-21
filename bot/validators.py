"""Input validation for order parameters."""

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{3,20}$")


class ValidationError(Exception):
    """Raised when user-supplied input fails validation."""


def validate_symbol(value: str) -> str:
    if not value or not isinstance(value, str):
        raise ValidationError("Symbol must be a non-empty string, for example BTCUSDT.")
    normalised = value.strip().upper()
    if not SYMBOL_PATTERN.match(normalised):
        raise ValidationError(
            f"Symbol '{normalised}' looks invalid. Expected 3-20 alphanumeric characters, for example BTCUSDT."
        )
    return normalised


def validate_side(value: str) -> str:
    if not value or not isinstance(value, str):
        raise ValidationError("Side must be BUY or SELL.")
    normalised = value.strip().upper()
    if normalised not in VALID_SIDES:
        raise ValidationError(f"Side '{value}' is not recognised. Choose BUY or SELL.")
    return normalised


def validate_order_type(value: str) -> str:
    if not value or not isinstance(value, str):
        raise ValidationError("Order type must be MARKET, LIMIT, or STOP_LIMIT.")
    normalised = value.strip().upper()
    if normalised not in VALID_ORDER_TYPES:
        raise ValidationError(f"Order type '{value}' is not supported. Choose MARKET, LIMIT, or STOP_LIMIT.")
    return normalised


def validate_quantity(value: Any) -> Decimal:
    try:
        quantity = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValidationError(f"Quantity '{value}' is not a valid number.") from exc
    if quantity <= 0:
        raise ValidationError(f"Quantity must be greater than 0, got {quantity}.")
    return quantity


def validate_price(value: Any, field_name: str = "Price") -> Decimal:
    try:
        price = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} '{value}' is not a valid number.") from exc
    if price <= 0:
        raise ValidationError(f"{field_name} must be greater than 0, got {price}.")
    return price


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Any,
    price: Optional[Any] = None,
    stop_price: Optional[Any] = None,
) -> Dict[str, Any]:
    validated: Dict[str, Any] = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
    }

    current_type = validated["order_type"]

    if current_type in ("LIMIT", "STOP_LIMIT"):
        if price is None:
            raise ValidationError(f"--price is required for {current_type} orders.")
        validated["price"] = validate_price(price, "Price")
    else:
        if price is not None:
            logger.warning("Price %s was provided but will be ignored for MARKET orders.", price)
        validated["price"] = None

    if current_type == "STOP_LIMIT":
        if stop_price is None:
            raise ValidationError("--stop-price is required for STOP_LIMIT orders.")
        stop = validate_price(stop_price, "Stop price")
        if validated["side"] == "BUY" and stop >= validated["price"]:
            logger.warning(
                "Stop price (%s) is greater than or equal to limit price (%s) for a BUY STOP_LIMIT order.",
                stop,
                validated["price"],
            )
        if validated["side"] == "SELL" and stop <= validated["price"]:
            logger.warning(
                "Stop price (%s) is less than or equal to limit price (%s) for a SELL STOP_LIMIT order.",
                stop,
                validated["price"],
            )
        validated["stop_price"] = stop
    else:
        validated["stop_price"] = None

    logger.debug("Validated order params: %s", validated)
    return validated
