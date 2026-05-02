const statusUrl = "/api/v1/status";
const timelineUrl = "/api/v1/clicks/timeline?buckets=90";
const randomUrl = "/api/v1/random/int";

const nodes = {
  navLinks: [...document.querySelectorAll(".nav a")],
  pages: [...document.querySelectorAll(".page")],
  pill: document.querySelector("#health-pill"),
  latestUpdate: document.querySelector("#latest-update"),
  statusNote: document.querySelector("#status-note"),
  poolBits: document.querySelector("#pool-bits"),
  clicks: document.querySelector("#clicks"),
  extractedBits: document.querySelector("#extracted-bits"),
  cpm: document.querySelector("#cpm"),
  rawBits: document.querySelector("#raw-bits"),
  discardedPairs: document.querySelector("#discarded-pairs"),
  timelineWindow: document.querySelector("#timeline-window"),
  chart: document.querySelector("#click-chart"),
  maxValue: document.querySelector("#max-value"),
  drawButton: document.querySelector("#draw-button"),
  drawResult: document.querySelector("#draw-result"),
};

let lastTimeline = [];

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

function route() {
  const name = (window.location.hash || "#overview").slice(1);
  for (const page of nodes.pages) {
    page.classList.toggle("active", page.id === `${name}-page`);
  }
  for (const link of nodes.navLinks) {
    link.classList.toggle("active", link.hash === `#${name}`);
  }
  if (name === "entropy") {
    drawChart(lastTimeline);
  }
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
  nodes.rawBits.textContent = formatInteger(status.total_raw_bits);
  nodes.discardedPairs.textContent = formatInteger(status.total_discarded_pairs);
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

async function refreshTimeline() {
  try {
    const payload = await fetchJson(timelineUrl);
    lastTimeline = payload.points || [];
    nodes.timelineWindow.textContent = `${Math.round(payload.window_seconds / 60)} min rolling window`;
    drawChart(lastTimeline);
  } catch {
    drawChart(lastTimeline);
  }
}

function drawChart(points) {
  if (!nodes.chart) {
    return;
  }
  const canvas = nodes.chart;
  const context = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);

  const padding = { left: 58, right: 18, top: 20, bottom: 42 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const maxClicks = Math.max(1, ...points.map((point) => point.clicks));
  const maxElapsed = Math.max(1, ...points.map((point) => point.elapsed_seconds));

  context.strokeStyle = "rgba(98, 215, 255, 0.09)";
  context.lineWidth = 1;
  context.fillStyle = "#92aaa3";
  context.font = "11px ui-monospace, monospace";

  for (let index = 0; index <= 4; index += 1) {
    const y = padding.top + chartHeight - (chartHeight * index) / 4;
    context.beginPath();
    context.moveTo(padding.left, y);
    context.lineTo(width - padding.right, y);
    context.stroke();
    context.fillText(String(Math.round((maxClicks * index) / 4)), 10, y + 4);
  }

  for (let index = 0; index <= 4; index += 1) {
    const x = padding.left + (chartWidth * index) / 4;
    context.beginPath();
    context.moveTo(x, padding.top);
    context.lineTo(x, height - padding.bottom);
    context.stroke();
    context.fillText(`${Math.round((maxElapsed * index) / 60)}m`, x - 10, height - 14);
  }

  if (!points.length) {
    context.fillText("Waiting for click timeline.", padding.left, padding.top + 28);
    return;
  }

  const coordinates = points.map((point) => ({
    x: padding.left + (point.elapsed_seconds / maxElapsed) * chartWidth,
    y: padding.top + chartHeight - (point.clicks / maxClicks) * chartHeight,
  }));

  const gradient = context.createLinearGradient(0, padding.top, 0, height - padding.bottom);
  gradient.addColorStop(0, "rgba(77, 255, 172, 0.32)");
  gradient.addColorStop(1, "rgba(77, 255, 172, 0.02)");
  context.beginPath();
  context.moveTo(coordinates[0].x, height - padding.bottom);
  for (const point of coordinates) {
    context.lineTo(point.x, point.y);
  }
  context.lineTo(coordinates.at(-1).x, height - padding.bottom);
  context.closePath();
  context.fillStyle = gradient;
  context.fill();

  context.beginPath();
  for (const [index, point] of coordinates.entries()) {
    if (index === 0) {
      context.moveTo(point.x, point.y);
    } else {
      context.lineTo(point.x, point.y);
    }
  }
  context.strokeStyle = "#4dffac";
  context.lineWidth = 3;
  context.stroke();
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
    await Promise.all([refreshStatus(), refreshTimeline()]);
  } catch (error) {
    nodes.drawResult.textContent = error.message;
  } finally {
    nodes.drawButton.disabled = false;
  }
}

window.addEventListener("hashchange", route);
window.addEventListener("resize", () => drawChart(lastTimeline));
nodes.drawButton.addEventListener("click", drawNumber);
route();
refreshStatus();
refreshTimeline();
setInterval(refreshStatus, 5000);
setInterval(refreshTimeline, 5000);
