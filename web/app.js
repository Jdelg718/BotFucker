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

function clear(element) {
  element.replaceChildren();
}

function el(tagName, options = {}, ...children) {
  const element = document.createElement(tagName);
  if (options.className) element.className = options.className;
  if (options.dataset) {
    Object.entries(options.dataset).forEach(([key, value]) => {
      element.dataset[key] = String(value);
    });
  }
  if (options.disabled) element.disabled = true;
  children.forEach((child) => appendTextOrNode(element, child));
  return element;
}

function appendTextOrNode(parent, child) {
  if (child === null || child === undefined || child === false) return;
  if (child instanceof Node) {
    parent.appendChild(child);
    return;
  }
  parent.appendChild(document.createTextNode(String(child)));
}

function appendLabeledText(parent, label, value) {
  const strong = el("strong");
  strong.textContent = label;
  parent.appendChild(strong);
  parent.appendChild(document.createTextNode(value));
}

function metric(label, value) {
  const strong = el("strong");
  strong.textContent = value;
  const span = el("span");
  span.textContent = label;
  return el("div", { className: "metric" }, strong, span);
}

function renderDashboard(data) {
  const counts = data.counts;
  const metrics = document.querySelector("#metrics");
  clear(metrics);
  metrics.append(
    metric("total sample items", counts.total_review_items),
    metric("pending human review", counts.pending_review_items),
    metric("mock actions taken", counts.actioned_review_items),
    metric("audit events", counts.audit_events),
  );
}

function actionClass(action) {
  if (action === "blacklist_sender") return "danger";
  if (action === "dismiss") return "secondary";
  return "";
}

function renderQueue(items) {
  const queue = document.querySelector("#queue");
  clear(queue);

  items.forEach((item) => {
    const title = el("h3");
    title.textContent = item.subject;

    const senderMeta = el("div", { className: "meta" });
    senderMeta.textContent = `${item.from_name} <${item.from_email}> · ${item.sender_domain}`;

    const heading = el("div", {}, title, senderMeta);
    const statusClass = item.status === "pending" ? "neutral" : "safe";
    const status = el("span", { className: `pill ${statusClass}` });
    status.textContent = item.status;

    const snippet = el("p");
    snippet.textContent = item.snippet;

    const classification = el("div", { className: "meta" });
    classification.textContent = `${item.classification} · confidence ${Math.round(item.confidence * 100)}% · strike ${item.sender_strike_level}`;

    const reasons = el("ul", { className: "reasons" });
    item.reasons.forEach((reason) => {
      const row = el("li");
      row.textContent = reason;
      reasons.appendChild(row);
    });

    const article = el(
      "article",
      { className: "item" },
      el("div", { className: "item-header" }, heading, status),
      snippet,
      classification,
      reasons,
    );

    if (item.draft_reply) {
      const draft = el("p", { className: "muted" });
      appendLabeledText(draft, "Draft:", ` ${item.draft_reply}`);
      article.appendChild(draft);
    }

    const safety = el("p", { className: "muted" });
    appendLabeledText(safety, "Safety:", ` ${item.safety_note}`);
    article.appendChild(safety);

    const actions = el("div", { className: "actions" });
    item.allowed_actions.forEach((action) => {
      const button = el("button", {
        className: actionClass(action),
        dataset: { itemId: item.item_id, action },
        disabled: item.status !== "pending",
      });
      button.textContent = actionLabels[action] || action;
      actions.appendChild(button);
    });
    article.appendChild(actions);
    queue.appendChild(article);
  });

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
  const container = document.querySelector("#sender-history");
  clear(container);
  senders.forEach((sender) => {
    const name = el("strong");
    name.textContent = sender.sender;

    const summary = el("div", { className: "meta" });
    summary.textContent = `domain ${sender.sender_domain} · messages ${sender.message_count} · max strike ${sender.max_strike_level}`;

    const classifications = el("div", { className: "meta" });
    classifications.textContent = `classifications: ${sender.classifications.join(", ") || "none"}`;

    const lastAction = el("div", { className: "meta" });
    lastAction.textContent = `last mock action: ${sender.last_mock_action || "none"}`;

    container.appendChild(el("div", { className: "sender" }, name, summary, classifications, lastAction));
  });
}

function renderSettings(settings) {
  document.querySelector("#yolo-copy").textContent = settings.yolo_copy;
  document.querySelector("#safety-note").textContent = "Human approval is enabled. YOLO is visible but disabled. Provider auth is coming later.";
}

function renderAudit(events) {
  const container = document.querySelector("#audit-events");
  clear(container);
  if (!events.length) {
    const empty = el("p", { className: "muted" });
    empty.textContent = "No mock actions recorded yet.";
    container.appendChild(empty);
    return;
  }

  events.forEach((event) => {
    const action = el("strong");
    action.textContent = event.action;

    const title = el("div", {}, action, ` on ${event.item_id}`);
    const meta = el("div", { className: "meta" });
    meta.textContent = `${event.created_at} · ${event.actor} · ${event.effect_scope}`;

    const safety = el("div", { className: "meta" });
    safety.textContent = event.safety_note;

    if (event.note) {
      const note = el("div", { className: "meta" });
      note.textContent = event.note;
      container.appendChild(el("div", { className: "event" }, title, meta, safety, note));
      return;
    }
    container.appendChild(el("div", { className: "event" }, title, meta, safety));
  });
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
  const panel = el("pre", { className: "panel" });
  panel.textContent = `Failed to load local UI data: ${error.message}`;
  document.body.prepend(panel);
});
