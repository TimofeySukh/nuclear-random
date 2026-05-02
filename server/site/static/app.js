const statusUrl = "/api/v1/status";
const randomUrl = "/api/v1/random/int";

const nodes = {
  pill: document.querySelector("#health-pill"),
  latestUpdate: document.querySelector("#latest-update"),
  statusNote: document.querySelector("#status-note"),
  poolBits: document.querySelector("#pool-bits"),
  clicks: document.querySelector("#clicks"),
  extractedBits: document.querySelector("#extracted-bits"),
  cpm: document.querySelector("#cpm"),
  maxValue: document.querySelector("#max-value"),
  drawButton: document.querySelector("#draw-button"),
  drawResult: document.querySelector("#draw-result"),
};

function formatInteger(value) {
  return new Intl.NumberFormat("en-US").format(Number(value || 0));
}

function formatTime() {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date());
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

function renderStatus(status) {
  nodes.pill.classList.add("online");
  nodes.pill.lastChild.textContent = " Online";
  nodes.latestUpdate.textContent = formatTime();
  nodes.statusNote.textContent = `Last ESP32 click dt_us: ${formatInteger(status.last_click_dt_us)}.`;
  nodes.poolBits.textContent = `${formatInteger(status.pool_bits)} bits`;
  nodes.clicks.textContent = formatInteger(status.total_clicks);
  nodes.extractedBits.textContent = `${formatInteger(status.total_extracted_bits)} bits`;
  nodes.cpm.textContent = `${formatInteger(status.estimated_cpm)} CPM`;
}

async function refreshStatus() {
  try {
    renderStatus(await fetchJson(statusUrl));
  } catch (error) {
    nodes.pill.classList.remove("online");
    nodes.pill.lastChild.textContent = " Offline";
    nodes.statusNote.textContent = error.message;
  }
}

async function drawNumber() {
  const max = Number.parseInt(nodes.maxValue.value, 10);
  if (!Number.isSafeInteger(max) || max < 0) {
    nodes.drawResult.textContent = "Enter a non-negative safe integer.";
    return;
  }

  nodes.drawButton.disabled = true;
  nodes.drawResult.textContent = "Waiting for extracted entropy...";
  try {
    const payload = await fetchJson(`${randomUrl}?max=${max}`);
    nodes.drawResult.textContent = `Result ${payload.value}. Used ${payload.bits_used} bits, rejected ${payload.rejected} candidates.`;
    await refreshStatus();
  } catch (error) {
    nodes.drawResult.textContent = error.message;
  } finally {
    nodes.drawButton.disabled = false;
  }
}

nodes.drawButton.addEventListener("click", drawNumber);
refreshStatus();
setInterval(refreshStatus, 5000);
