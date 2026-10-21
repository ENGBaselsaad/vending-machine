"""Money helpers.

All vending math uses integer cents so 0.10 + 0.50 never hits floating-point
rounding. The API still talks in human amounts like "0.50" or 1.5.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

ACCEPTED_COIN_CENTS = (10, 50, 100, 200, 500, 1000)
ACCEPTED_COIN_LABELS = ("0.10", "0.50", "1.00", "2.00", "5.00", "10.00")


class InvalidAmount(ValueError):
    pass


def money_to_cents(value) -> int:
    """Convert 0.50 / "1" / "1.00" to cents. Rejects values that are not exact cents."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise InvalidAmount("Amount is not a valid number.") from exc

    cents = amount * 100
    if cents != cents.to_integral_value():
        raise InvalidAmount("Amount must have at most two decimal places.")
    as_int = int(cents.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if as_int < 0:
        raise InvalidAmount("Amount cannot be negative.")
    return as_int


def cents_to_display(cents: int) -> str:
    return f"{Decimal(cents) / Decimal(100):.2f}"


def normalize_coin_map(raw: dict | None) -> dict[int, int]:
    """JSON stores keys as strings. Convert {"10": 2} -> {10: 2}."""
    if not raw:
        return {}
    result: dict[int, int] = {}
    for key, count in raw.items():
        denom = int(key)
        qty = int(count)
        if qty:
            result[denom] = result.get(denom, 0) + qty
    return result


def coin_map_to_json(coins: dict[int, int]) -> dict[str, int]:
    return {str(denom): int(count) for denom, count in sorted(coins.items()) if count}


def coin_map_total(coins: dict[int, int]) -> int:
    return sum(denom * count for denom, count in coins.items())


def coins_for_api(coins: dict[int, int]) -> list[dict]:
    """Stable list for the frontend: denomination + how many physical coins."""
    items = []
    for denom in ACCEPTED_COIN_CENTS:
        count = int(coins.get(denom, 0))
        if count:
            items.append(
                {
                    "denomination": cents_to_display(denom),
                    "denomination_cents": denom,
                    "count": count,
                    "total": cents_to_display(denom * count),
                }
            )
    return items
