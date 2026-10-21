from django.contrib import admin

from .models import CoinInventory, MachineState, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price_cents", "stock", "is_active")


@admin.register(CoinInventory)
class CoinInventoryAdmin(admin.ModelAdmin):
    list_display = ("denomination_cents", "quantity")


@admin.register(MachineState)
class MachineStateAdmin(admin.ModelAdmin):
    list_display = ("id", "inserted_coins")
