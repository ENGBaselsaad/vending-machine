from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import services
from .errors import InsufficientFunds, VendingError
from .models import CoinInventory, Product
from .money import cents_to_display
from .serializers import CoinSerializer, ProductSerializer, money_payload


def _fail(exc: Exception, status: int | None = None) -> Response:
    if isinstance(exc, VendingError):
        body = {"ok": False, "error": exc.code, "message": exc.message}
        if isinstance(exc, InsufficientFunds):
            body["needed"] = cents_to_display(exc.needed_cents)
            body["inserted"] = cents_to_display(exc.inserted_cents)
        return Response(body, status=exc.http_status)
    return Response(
        {"ok": False, "error": "BAD_REQUEST", "message": str(exc)},
        status=status or 400,
    )


def _customer_body(data: dict) -> dict:
    return {
        "accepted_coins": data["accepted_coins"],
        "inserted": money_payload(data["inserted_cents"], data["inserted_coins"]),
        "products": ProductSerializer(data["products"], many=True).data,
    }


@api_view(["GET"])
def machine_state(request):
    services.ensure_machine_exists()
    return Response({"ok": True, **_customer_body(services.snapshot())})


@api_view(["POST"])
def insert_coin(request):
    coin = request.data.get("coin")
    if coin is None:
        return _fail(ValueError("Send a coin value, for example 0.50."))
    try:
        data = services.insert_coin(coin)
    except (VendingError, ValueError) as exc:
        return _fail(exc)
    return Response({"ok": True, "message": f"Inserted {coin}.", **_customer_body(data)})


@api_view(["POST"])
def select_product(request):
    product_id = request.data.get("product_id")
    if product_id is None:
        return _fail(ValueError("Send product_id."))
    try:
        data = services.select_product(int(product_id))
    except (VendingError, ValueError, Product.DoesNotExist) as exc:
        if isinstance(exc, Product.DoesNotExist):
            return _fail(ValueError("Product was not found."), status=404)
        return _fail(exc)

    if data.get("rejected"):
        return Response(
            {
                "ok": False,
                "error": "NO_CHANGE",
                "message": (
                    "Exact change cannot be given with the coins in the machine. "
                    "Your money has been returned."
                ),
                "refund": money_payload(data["refund_cents"], data["refund_coins"]),
                **_customer_body(data),
            },
            status=400,
        )

    return Response(
        {
            "ok": True,
            "message": f"Dispensed {data['product_name']}.",
            "dispensed": data["product_name"],
            "paid": cents_to_display(data["paid_cents"]),
            "change": money_payload(data["change_cents"], data["change_coins"]),
            **_customer_body(data),
        }
    )


@api_view(["POST"])
def cancel(request):
    try:
        data = services.cancel()
    except VendingError as exc:
        return _fail(exc)
    return Response(
        {
            "ok": True,
            "message": "Transaction cancelled. Your coins were returned.",
            "refund": money_payload(data["refund_cents"], data["refund_coins"]),
            **_customer_body(data),
        }
    )


@api_view(["GET"])
def admin_state(request):
    services.ensure_machine_exists()
    data = services.admin_snapshot()
    return Response(
        {
            "ok": True,
            "products": ProductSerializer(data["products"], many=True).data,
            "coins": CoinSerializer(data["coins"], many=True).data,
            "customer_session": money_payload(data["inserted_cents"], data["inserted_coins"]),
        }
    )


@api_view(["POST"])
def admin_create_product(request):
    try:
        product = services.create_product(
            name=request.data.get("name") or "",
            price=request.data.get("price"),
            stock=int(request.data.get("stock") or 0),
        )
    except (ValueError, TypeError) as exc:
        return _fail(exc)
    return Response({"ok": True, "product": ProductSerializer(product).data}, status=201)


@api_view(["PATCH"])
def admin_update_product(request, product_id: int):
    try:
        product = services.update_product(
            product_id,
            name=request.data.get("name"),
            price=request.data.get("price"),
            is_active=request.data.get("is_active"),
        )
    except Product.DoesNotExist:
        return _fail(ValueError("Product was not found."), status=404)
    except (ValueError, TypeError) as exc:
        return _fail(exc)
    return Response({"ok": True, "product": ProductSerializer(product).data})


@api_view(["POST"])
def admin_restock_product(request, product_id: int):
    try:
        product = services.restock_product(product_id, int(request.data.get("quantity")))
    except Product.DoesNotExist:
        return _fail(ValueError("Product was not found."), status=404)
    except (ValueError, TypeError) as exc:
        return _fail(exc)
    return Response({"ok": True, "product": ProductSerializer(product).data})


@api_view(["POST"])
def admin_restock_coin(request, denomination: str):
    try:
        coin = services.restock_coin(denomination, int(request.data.get("quantity")))
    except CoinInventory.DoesNotExist:
        return _fail(ValueError("Unknown coin denomination."), status=404)
    except (VendingError, ValueError, TypeError) as exc:
        return _fail(exc)
    return Response({"ok": True, "coin": CoinSerializer(coin).data})
