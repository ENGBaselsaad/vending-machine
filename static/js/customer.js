const productsEl = document.getElementById("products");
const coinButtonsEl = document.getElementById("coin-buttons");
const balanceEl = document.getElementById("balance");
const insertedEl = document.getElementById("inserted-coins");
const statusEl = document.getElementById("status");
const cancelBtn = document.getElementById("cancel");

function render(data) {
  balanceEl.textContent = data.inserted.amount;
  insertedEl.textContent = "Coins in slot: " + formatCoins(data.inserted.coins);
  productsEl.innerHTML = data.products
    .map((p) => {
      const canBuy = p.available && Number(data.inserted.amount_cents) >= p.price_cents;
      return `
        <article class="product">
          <h3>${p.name}</h3>
          <div class="price">${p.price}</div>
          <p class="muted">${p.stock} in stock</p>
          <button ${p.available ? "" : "disabled"} data-id="${p.id}">
            ${p.available ? (canBuy ? "Buy" : "Insert more") : "Out of stock"}
          </button>
        </article>`;
    })
    .join("");

  if (!coinButtonsEl.dataset.ready) {
    coinButtonsEl.innerHTML = data.accepted_coins
      .map((c) => `<button type="button" data-coin="${c}">${c}</button>`)
      .join("");
    coinButtonsEl.dataset.ready = "1";
  }
}

async function refresh() {
  const data = await api("/api/machine/");
  render(data);
}

coinButtonsEl.addEventListener("click", async (event) => {
  const coin = event.target.dataset.coin;
  if (!coin) return;
  const data = await api("/api/machine/insert-coin/", {
    method: "POST",
    body: JSON.stringify({ coin }),
  });
  showStatus(statusEl, data);
  if (data.products) render(data);
});

productsEl.addEventListener("click", async (event) => {
  const id = event.target.dataset.id;
  if (!id) return;
  const data = await api("/api/machine/select/", {
    method: "POST",
    body: JSON.stringify({ product_id: Number(id) }),
  });
  showStatus(statusEl, data);
  if (data.products) render(data);
});

cancelBtn.addEventListener("click", async () => {
  const data = await api("/api/machine/cancel/", {
    method: "POST",
    body: JSON.stringify({}),
  });
  showStatus(statusEl, data);
  if (data.products) render(data);
});

refresh();
