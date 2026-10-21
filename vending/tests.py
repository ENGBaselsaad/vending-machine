from django.test import TestCase
from rest_framework.test import APIClient

from vending.change import make_change
from vending.models import CoinInventory, Product
from vending.services import ensure_machine_exists, insert_coin, select_product


class ChangeTests(TestCase):
    def test_zero_needs_no_coins(self):
        self.assertEqual(make_change(0, {100: 5}), {})

    def test_simple_change(self):
        self.assertEqual(make_change(150, {100: 2, 50: 2}), {100: 1, 50: 1})

    def test_greedy_would_fail_but_backtracking_works(self):
        # Need 0.60. Hopper has 0.50 x1 and 0.20 x3.
        # Greedy takes 0.50 then is stuck. Correct answer is three 0.20 coins.
        self.assertEqual(make_change(60, {50: 1, 20: 3}), {20: 3})

    def test_impossible_change(self):
        self.assertIsNone(make_change(30, {100: 5, 50: 2}))


class VendingApiTests(TestCase):
    def setUp(self):
        ensure_machine_exists()
        self.client = APIClient()
        self.water = Product.objects.create(name="Water", price_cents=150, stock=2)
        self.empty = Product.objects.create(name="Empty Slot", price_cents=100, stock=0)
        CoinInventory.objects.filter(denomination_cents=10).update(quantity=10)
        CoinInventory.objects.filter(denomination_cents=50).update(quantity=10)
        CoinInventory.objects.filter(denomination_cents=100).update(quantity=10)
        CoinInventory.objects.filter(denomination_cents=200).update(quantity=0)
        CoinInventory.objects.filter(denomination_cents=500).update(quantity=0)
        CoinInventory.objects.filter(denomination_cents=1000).update(quantity=0)

    def test_invalid_coin_is_rejected(self):
        response = self.client.post(
            "/api/machine/insert-coin/", {"coin": "0.25"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "INVALID_COIN")

    def test_out_of_stock(self):
        self.client.post("/api/machine/insert-coin/", {"coin": "2"}, format="json")
        response = self.client.post(
            "/api/machine/select/", {"product_id": self.empty.id}, format="json"
        )
        self.assertEqual(response.data["error"], "OUT_OF_STOCK")

    def test_insufficient_funds(self):
        self.client.post("/api/machine/insert-coin/", {"coin": "1"}, format="json")
        response = self.client.post(
            "/api/machine/select/", {"product_id": self.water.id}, format="json"
        )
        self.assertEqual(response.data["error"], "INSUFFICIENT_FUNDS")
        self.assertEqual(response.data["inserted"], "1.00")

    def test_successful_vend_returns_change(self):
        self.client.post("/api/machine/insert-coin/", {"coin": "2"}, format="json")
        response = self.client.post(
            "/api/machine/select/", {"product_id": self.water.id}, format="json"
        )
        self.assertTrue(response.data["ok"])
        self.assertEqual(response.data["dispensed"], "Water")
        self.assertEqual(response.data["change"]["amount"], "0.50")
        self.water.refresh_from_db()
        self.assertEqual(self.water.stock, 1)
        hopper_2 = CoinInventory.objects.get(denomination_cents=200)
        self.assertEqual(hopper_2.quantity, 1)

    def test_cancel_refunds_the_same_coins(self):
        self.client.post("/api/machine/insert-coin/", {"coin": "1"}, format="json")
        self.client.post("/api/machine/insert-coin/", {"coin": "0.50"}, format="json")
        response = self.client.post("/api/machine/cancel/", {}, format="json")
        self.assertTrue(response.data["ok"])
        self.assertEqual(response.data["refund"]["amount"], "1.50")
        denoms = {c["denomination"] for c in response.data["refund"]["coins"]}
        self.assertEqual(denoms, {"1.00", "0.50"})
        state = self.client.get("/api/machine/").data
        self.assertEqual(state["inserted"]["amount"], "0.00")

    def test_no_change_refunds_and_does_not_vend(self):
        CoinInventory.objects.update(quantity=0)
        Product.objects.filter(pk=self.water.pk).update(stock=2)
        insert_coin("5")
        result = select_product(self.water.id)
        self.assertTrue(result["rejected"])
        self.water.refresh_from_db()
        self.assertEqual(self.water.stock, 2)
        self.assertEqual(CoinInventory.objects.get(denomination_cents=500).quantity, 0)

        response = self.client.post("/api/machine/insert-coin/", {"coin": "5"}, format="json")
        self.assertTrue(response.data["ok"])
        response = self.client.post(
            "/api/machine/select/", {"product_id": self.water.id}, format="json"
        )
        self.assertEqual(response.data["error"], "NO_CHANGE")
        self.assertEqual(response.data["refund"]["amount"], "5.00")
        self.assertEqual(response.data["inserted"]["amount"], "0.00")
        self.water.refresh_from_db()
        self.assertEqual(self.water.stock, 2)

    def test_admin_restock_product_and_coins(self):
        before = self.water.stock
        response = self.client.post(
            f"/api/admin/products/{self.water.id}/restock/",
            {"quantity": 5},
            format="json",
        )
        self.assertTrue(response.data["ok"])
        self.water.refresh_from_db()
        self.assertEqual(self.water.stock, before + 5)

        response = self.client.post(
            "/api/admin/coins/0.10/restock/", {"quantity": 7}, format="json"
        )
        self.assertTrue(response.data["ok"])
        row = CoinInventory.objects.get(denomination_cents=10)
        self.assertEqual(row.quantity, 17)
