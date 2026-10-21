"""All purchase rules live here. Views only translate HTTP to these functions."""

from django.db import transaction

from .change import make_change
from .errors import (
    EmptySession,
    InsufficientFunds,
    InvalidCoin,
    OutOfStock,
    ProductNotFound,
)
from .models import CoinInventory, MachineState, Product
from .money import (
    ACCEPTED_COIN_CENTS,
    coin_map_to_json,
    coin_map_total,
    money_to_cents,
)


def _add_maps(left: dict[int, int], right: dict[int, int]) -> dict[int, int]:
    result = dict(left)
    for denom, count in right.items():
        result[denom] = result.get(denom, 0) + count
    return result


def _inventory_map(locked_rows) -> dict[int, int]:
    return {row.denomination_cents: row.quantity for row in locked_rows}


def _save_inventory(locked_rows, new_counts: dict[int, int]) -> None:
    for row in locked_rows:
        row.quantity = int(new_counts.get(row.denomination_cents, 0))
        row.save(update_fields=["quantity"])


def _locked_state() -> MachineState:
    ensure_machine_exists()
    return MachineState.objects.select_for_update().get(pk=1)


def snapshot() -> dict:
    """Current customer-facing machine state."""
    state = MachineState.load()
    products = Product.objects.filter(is_active=True)
    coins = CoinInventory.objects.all()
    inserted = state.inserted_map()
    return {
        "accepted_coins": [f"{c / 100:.2f}" for c in ACCEPTED_COIN_CENTS],
        "inserted_cents": state.inserted_total_cents(),
        "inserted_coins": inserted,
        "products": list(products),
        "machine_coins": {row.denomination_cents: row.quantity for row in coins},
    }


@transaction.atomic
def insert_coin(coin_value) -> dict:
    cents = money_to_cents(coin_value)
    if cents not in ACCEPTED_COIN_CENTS:
        raise InvalidCoin()

    state = _locked_state()
    inserted = state.inserted_map()
    inserted[cents] = inserted.get(cents, 0) + 1
    state.inserted_coins = coin_map_to_json(inserted)
    state.save(update_fields=["inserted_coins"])
    return snapshot()


@transaction.atomic
def cancel() -> dict:
    """Return the exact coins the customer put in. Machine inventory is untouched."""
    state = _locked_state()
    inserted = state.inserted_map()
    if not inserted:
        raise EmptySession()

    refund_cents = coin_map_total(inserted)
    state.inserted_coins = {}
    state.save(update_fields=["inserted_coins"])
    return {
        "refund_cents": refund_cents,
        "refund_coins": inserted,
        **snapshot(),
    }


@transaction.atomic
def select_product(product_id: int) -> dict:
    """Vend if stock, funds, and change all work. Otherwise refund inserted coins.

    Order of checks (after locking rows):
    1. Product exists
    2. Product has stock
    3. Inserted amount >= price
    4. Change can be made from (machine coins + inserted coins)
    5. Commit: add inserted, remove change, decrement stock, clear session

    If change cannot be made we still commit: session is cleared and the
    original coins are returned. That must not be rolled back, so this path
    returns a rejected result instead of raising an exception.
    """
    state = _locked_state()
    coin_rows = list(CoinInventory.objects.select_for_update().all())

    try:
        product = Product.objects.select_for_update().get(pk=product_id, is_active=True)
    except Product.DoesNotExist as exc:
        raise ProductNotFound() from exc

    inserted = state.inserted_map()
    inserted_cents = coin_map_total(inserted)

    if product.stock <= 0:
        raise OutOfStock()

    if inserted_cents < product.price_cents:
        raise InsufficientFunds(product.price_cents, inserted_cents)

    change_needed = inserted_cents - product.price_cents
    available_after_insert = _add_maps(_inventory_map(coin_rows), inserted)
    change_coins = make_change(change_needed, available_after_insert)

    if change_coins is None:
        refund = inserted
        state.inserted_coins = {}
        state.save(update_fields=["inserted_coins"])
        return {
            "rejected": True,
            "reason": "NO_CHANGE",
            "refund_cents": coin_map_total(refund),
            "refund_coins": refund,
            **snapshot(),
        }

    # Success: inserted coins join the hopper, then change is taken out.
    new_inventory = available_after_insert
    for denom, count in change_coins.items():
        new_inventory[denom] = new_inventory.get(denom, 0) - count
        if new_inventory[denom] < 0:
            raise NoChangeAvailable()

    _save_inventory(coin_rows, new_inventory)
    product.stock -= 1
    product.save(update_fields=["stock"])
    state.inserted_coins = {}
    state.save(update_fields=["inserted_coins"])

    return {
        "rejected": False,
        "product_name": product.name,
        "price_cents": product.price_cents,
        "paid_cents": inserted_cents,
        "change_cents": change_needed,
        "change_coins": change_coins,
        **snapshot(),
    }


@transaction.atomic
def update_product(product_id: int, *, name=None, price=None, is_active=None) -> Product:
    product = Product.objects.select_for_update().get(pk=product_id)
    if name is not None:
        name = name.strip()
        if not name:
            raise ValueError("Product name cannot be empty.")
        product.name = name
    if price is not None:
        cents = money_to_cents(price)
        if cents <= 0:
            raise ValueError("Price must be greater than 0.")
        product.price_cents = cents
    if is_active is not None:
        product.is_active = bool(is_active)
    product.save()
    return product


@transaction.atomic
def restock_product(product_id: int, quantity: int) -> Product:
    if quantity <= 0:
        raise ValueError("Restock quantity must be a positive whole number.")
    product = Product.objects.select_for_update().get(pk=product_id)
    product.stock += quantity
    product.save(update_fields=["stock"])
    return product


@transaction.atomic
def create_product(*, name: str, price, stock: int = 0) -> Product:
    name = name.strip()
    if not name:
        raise ValueError("Product name cannot be empty.")
    cents = money_to_cents(price)
    if cents <= 0:
        raise ValueError("Price must be greater than 0.")
    if stock < 0:
        raise ValueError("Stock cannot be negative.")
    return Product.objects.create(name=name, price_cents=cents, stock=stock)


@transaction.atomic
def restock_coin(denomination, quantity: int) -> CoinInventory:
    if quantity <= 0:
        raise ValueError("Restock quantity must be a positive whole number.")
    cents = money_to_cents(denomination)
    if cents not in ACCEPTED_COIN_CENTS:
        raise InvalidCoin()
    row = CoinInventory.objects.select_for_update().get(denomination_cents=cents)
    row.quantity += quantity
    row.save(update_fields=["quantity"])
    return row


def admin_snapshot() -> dict:
    state = MachineState.load()
    return {
        "products": list(Product.objects.all()),
        "coins": list(CoinInventory.objects.all()),
        "inserted_coins": state.inserted_map(),
        "inserted_cents": state.inserted_total_cents(),
        "accepted_coins": list(ACCEPTED_COIN_CENTS),
    }


def ensure_machine_exists() -> None:
    MachineState.load()
    existing = set(CoinInventory.objects.values_list("denomination_cents", flat=True))
    for denom in ACCEPTED_COIN_CENTS:
        if denom not in existing:
            CoinInventory.objects.create(denomination_cents=denom, quantity=0)
