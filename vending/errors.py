class VendingError(Exception):
    """Raised for customer-facing vending failures."""

    def __init__(self, code: str, message: str, http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class InvalidCoin(VendingError):
    def __init__(self, message="This machine does not accept that coin."):
        super().__init__("INVALID_COIN", message)


class ProductNotFound(VendingError):
    def __init__(self):
        super().__init__("PRODUCT_NOT_FOUND", "Product was not found.", 404)


class OutOfStock(VendingError):
    def __init__(self):
        super().__init__("OUT_OF_STOCK", "That product is out of stock.")


class InsufficientFunds(VendingError):
    def __init__(self, needed_cents: int, inserted_cents: int):
        super().__init__(
            "INSUFFICIENT_FUNDS",
            "Not enough money inserted for this product.",
        )
        self.needed_cents = needed_cents
        self.inserted_cents = inserted_cents


class NoChangeAvailable(VendingError):
    def __init__(self):
        super().__init__(
            "NO_CHANGE",
            "Exact change cannot be given with the coins in the machine. "
            "Your money has been returned.",
        )


class EmptySession(VendingError):
    def __init__(self):
        super().__init__("EMPTY_SESSION", "There is nothing to refund.")
