from django.core.management.base import BaseCommand

from vending.models import CoinInventory, Product
from vending.services import ensure_machine_exists


class Command(BaseCommand):
    help = "Load sample products and coin hopper amounts."

    def handle(self, *args, **options):
        ensure_machine_exists()

        products = [
            ("Still Water", 150, 8),
            ("Cola", 200, 6),
            ("Chips", 100, 10),
            ("Chocolate", 50, 12),
            ("Iced Coffee", 250, 4),
        ]
        if Product.objects.exists():
            self.stdout.write("Products already exist — leaving them unchanged.")
        else:
            for name, price, stock in products:
                Product.objects.create(name=name, price_cents=price, stock=stock)
            self.stdout.write(self.style.SUCCESS("Created sample products."))

        starter_coins = {10: 25, 50: 20, 100: 20, 200: 10, 500: 8, 1000: 4}
        for row in CoinInventory.objects.all():
            if row.quantity == 0:
                row.quantity = starter_coins.get(row.denomination_cents, 0)
                row.save(update_fields=["quantity"])
        self.stdout.write(self.style.SUCCESS("Coin hopper is ready."))
