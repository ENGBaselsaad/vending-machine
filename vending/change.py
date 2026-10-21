"""Limited-inventory change maker.

Greedy change (always take the largest coin) is not enough here. Example:
need 0.60, machine has one 0.50 and three 0.20. Greedy takes 0.50 then
cannot make 0.10. The real answer is three 0.20 coins.

There are only six denominations, so we search from largest coin to smallest
and backtrack when a branch fails. Memoization keeps it fast.
"""

from functools import lru_cache


def make_change(amount_cents: int, inventory: dict[int, int]) -> dict[int, int] | None:
    """Return {denomination_cents: count} that sums to amount_cents.

    Uses only coins that exist in inventory. Returns None if impossible.
    An amount of 0 returns an empty dict (no coins needed).
    """
    if amount_cents < 0:
        return None
    if amount_cents == 0:
        return {}

    denoms = tuple(sorted(inventory.keys(), reverse=True))
    available = tuple(int(inventory.get(d, 0)) for d in denoms)

    @lru_cache(maxsize=None)
    def search(remaining: int, index: int) -> tuple[int, ...] | None:
        if remaining == 0:
            return tuple(0 for _ in denoms)
        if remaining < 0 or index >= len(denoms):
            return None

        denom = denoms[index]
        max_use = min(available[index], remaining // denom)

        # Try using as many of this coin as possible first (fewest coins),
        # then step down if that path cannot finish the amount.
        for used in range(max_use, -1, -1):
            rest = search(remaining - used * denom, index + 1)
            if rest is None:
                continue
            combo = list(rest)
            combo[index] = used
            return tuple(combo)
        return None

    found = search(amount_cents, 0)
    if found is None:
        return None
    return {denoms[i]: found[i] for i in range(len(denoms)) if found[i] > 0}
