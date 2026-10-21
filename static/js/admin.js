const productsEl = document.getElementById("products");
const coinsEl = document.getElementById("coins");
const sessionEl = document.getElementById("session");
const statusEl = document.getElementById("status");
const createForm = document.getElementById("create-product");

function render(data) {
  sessionEl.textContent = `Inserted now: ${data.customer_session.amount} (${formatCoins(data.customer_session.coins)})`;
  productsEl.innerHTML = data.products
    .map(
      (p) => `
      <form class="card row" data-id="${p.id}">
        <label>Name <input name="name" value="${p.name}"></label>
        <label>Price <input name="price" value="${p.price}"></label>
        <label>Add stock <input name="quantity" type="number" min="1" value="1"></label>
        <button type="submit">Save</button>
        <button type="button" class="ghost restock">Restock</button>
        <p class="muted">Current stock: ${p.stock}</p>
      </form>`
    )
    .join("");

  coinsEl.innerHTML = data.coins
    .map(
      (c) => `
      <form class="card hopper" data-denom="${c.denomination}">
        <div>
          <strong>${c.denomination}</strong>
          <div class="muted">${c.quantity} coins in hopper</div>
        </div>
        <input name="quantity" type="number" min="1" value="5">
        <button type="submit">Add coins</button>
      </form>`
    )
    .join("");
}

async function refresh() {
  const data = await api("/api/admin/");
  render(data);
}

productsEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const id = form.dataset.id;
  const body = {
    name: form.name.value,
    price: form.price.value,
  };
  const data = await api(`/api/admin/products/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  showStatus(statusEl, data);
  refresh();
});

productsEl.addEventListener("click", async (event) => {
  if (!event.target.classList.contains("restock")) return;
  const form = event.target.closest("form");
  const data = await api(`/api/admin/products/${form.dataset.id}/restock/`, {
    method: "POST",
    body: JSON.stringify({ quantity: Number(form.quantity.value) }),
  });
  showStatus(statusEl, data);
  refresh();
});

coinsEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const data = await api(`/api/admin/coins/${form.dataset.denom}/restock/`, {
    method: "POST",
    body: JSON.stringify({ quantity: Number(form.quantity.value) }),
  });
  showStatus(statusEl, data);
  refresh();
});

createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = await api("/api/admin/products/", {
    method: "POST",
    body: JSON.stringify({
      name: createForm.name.value,
      price: createForm.price.value,
      stock: Number(createForm.stock.value || 0),
    }),
  });
  showStatus(statusEl, data);
  createForm.reset();
  refresh();
});

refresh();
