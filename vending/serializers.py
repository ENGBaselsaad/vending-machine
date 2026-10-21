from rest_framework import serializers

from .money import cents_to_display, coins_for_api
from .models import CoinInventory, Product


class ProductSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "price", "price_cents", "stock", "available", "is_active"]

    def get_price(self, obj: Product) -> str:
        return cents_to_display(obj.price_cents)

    def get_available(self, obj: Product) -> bool:
        return obj.stock > 0 and obj.is_active


class CoinSerializer(serializers.ModelSerializer):
    denomination = serializers.SerializerMethodField()

    class Meta:
        model = CoinInventory
        fields = ["denomination", "denomination_cents", "quantity"]

    def get_denomination(self, obj: CoinInventory) -> str:
        return cents_to_display(obj.denomination_cents)


def money_payload(cents: int, coins: dict[int, int]) -> dict:
    return {
        "amount": cents_to_display(cents),
        "amount_cents": cents,
        "coins": coins_for_api(coins),
    }
