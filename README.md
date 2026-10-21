# Vending Machine

A small full-stack vending machine built for the Next Dynamics technical task.

There are two pages and no login:

- Customer: `/`
- Admin: `/manage/`

All purchase rules run on the backend. The frontend only calls the API and draws the result.

## How to set up and run

You need Python 3.11+ (developed with 3.13).

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py seed_machine
python manage.py runserver
```

Open:

- http://127.0.0.1:8000/ — customer
- http://127.0.0.1:8000/manage/ — admin

Run tests:

```bash
python manage.py test
```

SQLite is created automatically as `db.sqlite3`. The seed command loads sample products and fills the coin hopper if it is empty.

## Technology choices

| Choice | Why |
| --- | --- |
| **Python / Django** | I already know this stack, it is a good fit for a small API plus two pages, and the deadline favors a complete solution over a larger unfinished one. |
| **Django REST Framework** | Clear JSON endpoints without writing a separate frontend framework. |
| **SQLite** | Zero extra services to install. Enough for one machine and this task. |
| **HTML / CSS / vanilla JS** | Two pages do not need React. Same-origin pages talk to `/api/...`. |
| **Integer cents in the database** | Coin math with floats is a classic bug (`0.1 + 0.2`). Prices and coins are stored as integers (150 = 1.50). |

## How the application is structured

```
config/                 Django project settings
vending/
  models.py             Product, CoinInventory, MachineState
  money.py              Convert 1.50 <-> 150 cents
  change.py             Limited-inventory change maker
  services.py           Insert / select / cancel / restock  (the real machine)
  api.py                HTTP layer around services
  tests.py              Edge cases from the brief
templates/              Customer and admin pages
static/                 CSS and JS
```

Walk the code in this order if you want the full story:

1. `vending/models.py` — what is stored
2. `vending/change.py` — how change is computed
3. `vending/services.py` — when a sale is accepted or refunded
4. `vending/api.py` — the endpoints the UI uses
5. `static/js/customer.js` and `static/js/admin.js` — the two pages

## Data model

- **Product**: name, `price_cents`, stock.
- **CoinInventory**: one row per accepted denomination, with how many physical coins are in the hopper.
- **MachineState**: one row. JSON map of coins the current customer has inserted. Those coins are **not** in the hopper yet.

Accepted coins: `0.10`, `0.50`, `1.00`, `2.00`, `5.00`, `10.00`.

One machine, one customer at a time. That matches a physical vendor and keeps the rules obvious.

## How change calculation works

Change is **not** greedy-only.

The hopper has a limited number of each coin. Taking the largest coin first can fail even when another mix would work.

Example used in tests: the customer is owed **0.60**. The hopper has **one 0.50** and **three 0.20**. Greedy takes 0.50 and then cannot make 0.10. The working answer is three 0.20 coins.

`vending/change.py` searches from largest denomination to smallest and backtracks when a branch cannot finish the amount. There are only six coin types, so this is cheap and exact.

On a successful purchase the backend:

1. Locks the machine row, hopper rows, and product row (`select_for_update`).
2. Adds the inserted coins to the hopper *in memory*.
3. Asks `make_change` for `inserted - price` using that combined hopper.
4. If a mix exists: write the new hopper counts, decrement stock, clear the customer session, return the product and the change coins.
5. If no mix exists: **do not vend**. Clear the session and return the **same coins the customer inserted**. Hopper and stock stay unchanged.

Inserted coins are available for making change (they have physically entered the machine at vend time). If they still cannot produce exact change, the sale is rejected.

Cancel never touches the hopper. It returns the exact inserted coins.

## API

Customer:

- `GET /api/machine/`
- `POST /api/machine/insert-coin/` `{ "coin": "0.50" }`
- `POST /api/machine/select/` `{ "product_id": 1 }`
- `POST /api/machine/cancel/`

Admin:

- `GET /api/admin/`
- `POST /api/admin/products/` `{ "name", "price", "stock" }`
- `PATCH /api/admin/products/<id>/` `{ "name", "price" }`
- `POST /api/admin/products/<id>/restock/` `{ "quantity" }`
- `POST /api/admin/coins/<denomination>/restock/` `{ "quantity" }`

Errors are explicit JSON:

```json
{ "ok": false, "error": "NO_CHANGE", "message": "..." }
```

Codes: `INVALID_COIN`, `OUT_OF_STOCK`, `INSUFFICIENT_FUNDS`, `NO_CHANGE`, `PRODUCT_NOT_FOUND`, `EMPTY_SESSION`.

## Edge cases handled

| Case | Behavior |
| --- | --- |
| Invalid coin (for example 0.25) | Rejected. Session unchanged. |
| Product out of stock | Sale rejected. Coins stay inserted so the customer can pick something else or cancel. |
| Not enough money | Sale rejected. Coins stay inserted. |
| Exact change cannot be made | Sale rejected. Original coins refunded. Stock and hopper unchanged. |
| Cancel | Full refund of the inserted coins, not a substitute mix from the hopper. |
| Change of 0 | Allowed. Empty change list. |
| Concurrent requests | Row locks inside a transaction. |

## Assumptions

- Currency is unitless amounts that match the listed coins (Euro-like, not US coins).
- One customer session at a time.
- Restock **adds** to current stock / hopper counts.
- Admin has no authentication, as requested.
- Prices must be whole cents (two decimal places).
- A rejected “no change” sale refunds immediately rather than leaving money in the slot. That matches “the sale is rejected and the money is refunded.”

## What I would improve with more time

I stopped when the machine was correct and the README could explain it. With more time I would stay on this product, not jump to new tools:

- Save a history of inserts, sales, refunds, and rejected sales so an admin can see what the machine did.
- Make admin stronger: turn a product off, set stock to an exact number, and cap how many coins the hopper can hold.
- Add more tests around change-making, especially cases where the obvious “largest coin first” mix is wrong.

If this had to run for a real customer with more than one process or a shared database, I would learn the pieces that solve that problem — for example a production database instead of SQLite, and a simple way to run the app the same way on every machine. I do not use those every day yet. I would look up the options, pick one I can explain, and keep the vending rules in `services.py` so the business logic does not get mixed into the new infrastructure.

## Time spent

Approximately **6 hours** of focused work: model and rules first, then API, UI, tests, and README.
