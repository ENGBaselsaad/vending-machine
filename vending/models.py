from django.db import models

from .money import cents_to_display, coin_map_total, normalize_coin_map


class Product(models.Model):
    name = models.CharField(max_length=80)
    price_cents = models.PositiveIntegerField()
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.name} ({cents_to_display(self.price_cents)})"


class CoinInventory(models.Model):
    """Physical coins sitting in the machine (not the customer's current insert)."""

    denomination_cents = models.PositiveIntegerField(unique=True)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["denomination_cents"]

    def __str__(self) -> str:
        return f"{cents_to_display(self.denomination_cents)} x {self.quantity}"


class MachineState(models.Model):
    """Singleton row: one machine, one customer inserting coins at a time."""

    inserted_coins = models.JSONField(default=dict, blank=True)

    def inserted_map(self) -> dict[int, int]:
        return normalize_coin_map(self.inserted_coins)

    def inserted_total_cents(self) -> int:
        return coin_map_total(self.inserted_map())

    @classmethod
    def load(cls) -> "MachineState":
        state, _created = cls.objects.get_or_create(pk=1)
        return state

    def __str__(self) -> str:
        return "Vending machine"
