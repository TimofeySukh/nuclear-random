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
  rateChart: document.querySelector("#rate-chart"),
  extractorChart: document.querySelector("#extractor-chart"),
  poolChart: document.querySelector("#pool-chart"),
  cpmChart: document.querySelector("#cpm-chart"),
  maxValue: document.querySelector("#max-value"),
  drawButton: document.querySelector("#draw-button"),
  drawResult: document.querySelector("#draw-result"),
  choiceValues: document.querySelector("#choice-values"),
  choiceButton: document.querySelector("#choice-button"),
  choiceResult: document.querySelector("#choice-result"),
};

let lastTimeline = [];
let lastStatus = null;
let statusHistory = [];

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
    drawRateChart(lastTimeline);
    drawExtractorChart(lastStatus);
    drawStatusHistoryCharts();
  }
}

function renderStatus(status) {
  lastStatus = status;
  statusHistory = [...statusHistory, status].slice(-90);
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
  drawExtractorChart(status);
  drawStatusHistoryCharts();
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
    drawRateChart(lastTimeline);
  } catch {
    drawChart(lastTimeline);
    drawRateChart(lastTimeline);
  }
}

function setupCanvas(canvas) {
  if (!canvas) {
    return null;
  }
  const context = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);
  return { context, width, height };
}

function drawChart(points) {
  const setup = setupCanvas(nodes.chart);
  if (!setup) {
    return;
  }
  const { context, width, height } = setup;

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

function drawRateChart(points) {
  const setup = setupCanvas(nodes.rateChart);
  if (!setup) {
    return;
  }
  const { context, width, height } = setup;
  const padding = { left: 44, right: 14, top: 16, bottom: 34 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const deltas = points.map((point, index) => {
    const previous = index > 0 ? points[index - 1].clicks : 0;
    return Math.max(0, point.clicks - previous);
  });
  const maxDelta = Math.max(1, ...deltas);

  context.strokeStyle = "rgba(98, 215, 255, 0.09)";
  context.fillStyle = "#92aaa3";
  context.font = "11px ui-monospace, monospace";
  for (let index = 0; index <= 3; index += 1) {
    const y = padding.top + chartHeight - (chartHeight * index) / 3;
    context.beginPath();
    context.moveTo(padding.left, y);
    context.lineTo(width - padding.right, y);
    context.stroke();
    context.fillText(String(Math.round((maxDelta * index) / 3)), 8, y + 4);
  }

  const barWidth = chartWidth / Math.max(1, deltas.length);
  for (const [index, value] of deltas.entries()) {
    const barHeight = (value / maxDelta) * chartHeight;
    const x = padding.left + index * barWidth;
    const y = padding.top + chartHeight - barHeight;
    context.fillStyle = value ? "rgba(98, 215, 255, 0.72)" : "rgba(98, 215, 255, 0.12)";
    context.fillRect(x, y, Math.max(1, barWidth - 2), barHeight);
  }
}

function drawExtractorChart(status) {
  const setup = setupCanvas(nodes.extractorChart);
  if (!setup || !status) {
    return;
  }
  const { context, width } = setup;
  const labels = ["raw", "clean", "discarded"];
  const values = [status.total_raw_bits, status.total_extracted_bits, status.total_discarded_pairs * 2];
  const colors = ["#62d7ff", "#4dffac", "#ff6680"];
  const maxValue = Math.max(1, ...values);
  const left = 104;
  const top = 34;
  const rowHeight = 58;
  const barMax = width - left - 24;

  context.font = "12px ui-monospace, monospace";
  for (const [index, value] of values.entries()) {
    const y = top + index * rowHeight;
    context.fillStyle = "#92aaa3";
    context.fillText(labels[index], 14, y + 18);
    context.fillStyle = "rgba(98, 215, 255, 0.08)";
    context.fillRect(left, y, barMax, 18);
    context.fillStyle = colors[index];
    context.fillRect(left, y, (value / maxValue) * barMax, 18);
    context.fillStyle = "#edf9f2";
    context.fillText(formatInteger(value), left, y + 40);
  }
}

function drawStatusHistoryCharts() {
  drawLineSeries(
    nodes.poolChart,
    statusHistory.map((status) => status.pool_bits),
    "#4dffac",
    "pool bits",
  );
  drawLineSeries(
    nodes.cpmChart,
    statusHistory.map((status) => status.estimated_cpm),
    "#ff9b45",
    "CPM",
  );
}

function drawLineSeries(canvas, values, color, label) {
  const setup = setupCanvas(canvas);
  if (!setup) {
    return;
  }
  const { context, width, height } = setup;
  const padding = { left: 46, right: 14, top: 18, bottom: 30 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const maxValue = Math.max(1, ...values);

  context.strokeStyle = "rgba(98, 215, 255, 0.09)";
  context.fillStyle = "#92aaa3";
  context.font = "11px ui-monospace, monospace";
  for (let index = 0; index <= 3; index += 1) {
    const y = padding.top + chartHeight - (chartHeight * index) / 3;
    context.beginPath();
    context.moveTo(padding.left, y);
    context.lineTo(width - padding.right, y);
    context.stroke();
    context.fillText(String(Math.round((maxValue * index) / 3)), 8, y + 4);
  }

  if (values.length < 2) {
    context.fillText(`Waiting for ${label} samples.`, padding.left, padding.top + 24);
    return;
  }

  const coordinates = values.map((value, index) => ({
    x: padding.left + (index / Math.max(1, values.length - 1)) * chartWidth,
    y: padding.top + chartHeight - (value / maxValue) * chartHeight,
  }));
  context.beginPath();
  for (const [index, point] of coordinates.entries()) {
    if (index === 0) {
      context.moveTo(point.x, point.y);
    } else {
      context.lineTo(point.x, point.y);
    }
  }
  context.strokeStyle = color;
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

async function chooseItem() {
  const options = nodes.choiceValues.value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
  if (!options.length) {
    nodes.choiceResult.textContent = "Enter at least one option.";
    return;
  }

  nodes.choiceButton.disabled = true;
  nodes.choiceResult.textContent = "Drawing QRNG-backed index...";
  try {
    const payload = await fetchJson(`${randomUrl}?max=${options.length - 1}`);
    nodes.choiceResult.textContent = `Index ${payload.value}: ${options[payload.value]}`;
    await Promise.all([refreshStatus(), refreshTimeline()]);
  } catch (error) {
    nodes.choiceResult.textContent = error.message;
  } finally {
    nodes.choiceButton.disabled = false;
  }
}

window.addEventListener("hashchange", route);
window.addEventListener("resize", () => {
  drawChart(lastTimeline);
  drawRateChart(lastTimeline);
  drawExtractorChart(lastStatus);
  drawStatusHistoryCharts();
});
nodes.drawButton.addEventListener("click", drawNumber);
nodes.choiceButton.addEventListener("click", chooseItem);
route();
refreshStatus();
refreshTimeline();
setInterval(refreshStatus, 5000);
setInterval(refreshTimeline, 5000);
