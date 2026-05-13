const actionLabels = {
  approve_warning: "Approve mock warning",
  dismiss: "Dismiss",
  whitelist_sender: "Mock whitelist sender",
  blacklist_sender: "Mock blacklist sender",
};

async function getJSON(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return response.json();
}

async function postJSON(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `${path} returned ${response.status}`);
  return data;
}

function metric(label, value) {
  return `<div class="metric"><strong>${value}</strong><span>${label}</span></div>`;
}

function renderDashboard(data) {
  const counts = data.counts;
  document.querySelector("#metrics").innerHTML = [
    metric("total sample items", counts.total_review_items),
    metric("pending human review", counts.pending_review_items),
    metric("mock actions taken", counts.actioned_review_items),
    metric("audit events", counts.audit_events),
  ].join("");
}

function actionClass(action) {
  if (action === "blacklist_sender") return "danger";
  if (action === "dismiss") return "secondary";
  return "";
}

function renderQueue(items) {
  const queue = document.querySelector("#queue");
  queue.innerHTML = items.map((item) => `
    <article class="item">
      <div class="item-header">
        <div>
          <h3>${item.subject}</h3>
          <div class="meta">${item.from_name} &lt;${item.from_email}&gt; · ${item.sender_domain}</div>
        </div>
        <span class="pill ${item.status === "pending" ? "neutral" : "safe"}">${item.status}</span>
      </div>
      <p>${item.snippet}</p>
      <div class="meta">${item.classification} · confidence ${Math.round(item.confidence * 100)}% · strike ${item.sender_strike_level}</div>
      <ul class="reasons">${item.reasons.map((reason) => `<li>${reason}</li>`).join("")}</ul>
      ${item.draft_reply ? `<p class="muted"><strong>Draft:</strong> ${item.draft_reply}</p>` : ""}
      <p class="muted"><strong>Safety:</strong> ${item.safety_note}</p>
      <div class="actions">
        ${item.allowed_actions.map((action) => `<button class="${actionClass(action)}" data-item-id="${item.item_id}" data-action="${action}" ${item.status !== "pending" ? "disabled" : ""}>${actionLabels[action] || action}</button>`).join("")}
      </div>
    </article>
  `).join("");

  queue.querySelectorAll("button[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      await postJSON("/api/actions", {
        item_id: button.dataset.itemId,
        action: button.dataset.action,
        actor: "local-browser-ui",
        note: "Triggered from Phase 2 local UI skeleton",
      });
      await refresh();
    });
  });
}

function renderSenders(senders) {
  document.querySelector("#sender-history").innerHTML = senders.map((sender) => `
    <div class="sender">
      <strong>${sender.sender}</strong>
      <div class="meta">domain ${sender.sender_domain} · messages ${sender.message_count} · max strike ${sender.max_strike_level}</div>
      <div class="meta">classifications: ${sender.classifications.join(", ") || "none"}</div>
      <div class="meta">last mock action: ${sender.last_mock_action || "none"}</div>
    </div>
  `).join("");
}

function renderSettings(settings) {
  document.querySelector("#yolo-copy").textContent = settings.yolo_copy;
  document.querySelector("#safety-note").textContent = "Human approval is enabled. YOLO is visible but disabled. Provider auth is coming later.";
}

function renderAudit(events) {
  const container = document.querySelector("#audit-events");
  if (!events.length) {
    container.innerHTML = `<p class="muted">No mock actions recorded yet.</p>`;
    return;
  }
  container.innerHTML = events.map((event) => `
    <div class="event">
      <strong>${event.action}</strong> on ${event.item_id}
      <div class="meta">${event.created_at} · ${event.actor} · ${event.effect_scope}</div>
      <div class="meta">${event.safety_note}</div>
    </div>
  `).join("");
}

async function refresh() {
  const [dashboard, queue, senders, settings, audit] = await Promise.all([
    getJSON("/api/dashboard"),
    getJSON("/api/review-queue"),
    getJSON("/api/senders"),
    getJSON("/api/settings"),
    getJSON("/api/audit-events"),
  ]);
  renderDashboard(dashboard);
  renderQueue(queue.items);
  renderSenders(senders.senders);
  renderSettings(settings);
  renderAudit(audit.events);
}

refresh().catch((error) => {
  document.body.insertAdjacentHTML("afterbegin", `<pre class="panel">Failed to load local UI data: ${error.message}</pre>`);
});
