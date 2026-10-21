function csrfToken() {
  const input = document.querySelector("[name=csrfmiddlewaretoken]");
  return input ? input.value : "";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken(),
      ...(options.headers || {}),
    },
    ...options,
  });
  const data = await response.json();
  data.httpStatus = response.status;
  return data;
}

function showStatus(el, data) {
  el.hidden = false;
  el.className = "status " + (data.ok ? "ok" : "bad");
  if (data.ok && data.change) {
    const coins = (data.change.coins || [])
      .map((c) => `${c.count} x ${c.denomination}`)
      .join(", ") || "none";
    el.textContent = `${data.message}\nChange: ${data.change.amount} (${coins})`;
    return;
  }
  if (data.refund) {
    const coins = (data.refund.coins || [])
      .map((c) => `${c.count} x ${c.denomination}`)
      .join(", ") || "none";
    el.textContent = `${data.message}\nReturned: ${data.refund.amount} (${coins})`;
    return;
  }
  el.textContent = data.message || (data.ok ? "Done." : "Something went wrong.");
}

function formatCoins(list) {
  if (!list || !list.length) return "none";
  return list.map((c) => `${c.count} × ${c.denomination}`).join(", ");
}
