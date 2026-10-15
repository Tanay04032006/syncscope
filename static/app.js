const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const methodNames = {
  pipe: "Pipe",
  queue: "Message Queue",
  shared_memory: "Shared Memory",
  socket: "Socket",
};

const mechanisms = {
  pipe: {
    title: "Pipe · sequential byte transfer",
    description: "send_bytes() writes framed bytes into a one-way connection. recv_bytes() reads each frame in order.",
    markup: '<div class="pipe-buffer"><i>A</i><i>B</i><i>C</i></div><span>WRITE → PIPE BUFFER → READ</span>',
    steps: ["Producer writes frame A into the pipe.", "Bytes travel through the operating-system buffer.", "Consumer reads frame A, then B and C in order."],
  },
  queue: {
    title: "Queue · buffered FIFO messages",
    description: "put() serializes a Python object. The queue buffers messages until get() removes the next item. This experiment has one producer and one consumer.",
    markup: '<div class="queue-buffer"><i>M3</i><i>M2</i><i>M1</i></div><span>ENQUEUE → FIFO → DEQUEUE</span>',
    steps: ["Producer enqueues distinct messages M1, M2 and M3.", "Messages wait in the bounded queue while the consumer catches up.", "Consumer dequeues M1 first, preserving producer order."],
  },
  shared_memory: {
    title: "Shared memory · one region, coordinated access",
    description: "Both processes map the same memory region. The producer signals data_ready after writing; the consumer reads the payload and signals consumed before the next write.",
    markup: '<div class="shared-region"><b>SHARED REGION</b><div><i>00</i><i>00</i><i>00</i><i>00</i></div><em>data_ready / consumed</em></div>',
    steps: ["Producer writes the shared region; consumer waits on data_ready.", "Producer releases data_ready. Consumer reads the same region.", "Consumer releases consumed, allowing the producer to overwrite the slot."],
  },
  socket: {
    title: "Socket · connected byte-stream endpoints",
    description: "A local socket pair connects the processes. sendall() sends bytes; recv() may receive chunks of different sizes. The consumer counts bytes until the whole payload arrives.",
    markup: '<div class="socket-stream"><b>TX</b><i>bytes</i><b>RX</b></div><span>SENDALL → LOCAL SOCKET PAIR → RECV</span>',
    steps: ["Two connected local socket endpoints are created.", "Producer sends bytes; consumer assembles received chunks.", "Producer shuts down writing. Consumer verifies the total byte count."],
  },
};

let explanationTimer;
function processNode(role, label) {
  return `<div class="process-node ${role}"><span class="node-icon">${role === "producer" ? "P₁" : "P₂"}</span><div><strong>${label}</strong><small id="${role}-pid">PID waiting</small></div><span class="node-state">READY</span></div>`;
}

function mechanismScene(method) {
  const producer = processNode("producer", method === "socket" ? "Endpoint A" : "Producer");
  const consumer = processNode("consumer", method === "socket" ? "Endpoint B" : "Consumer");
  const channel = `<div class="channel" id="channel">${mechanisms[method].markup}</div>`;
  if (method === "pipe") return `<div class="ipc-scene pipe-scene"><div class="scene-heading">ONE-WAY PIPELINE</div>${producer}<div class="path-label">send_bytes() ↓</div>${channel}<div class="path-label">↓ recv_bytes()</div>${consumer}</div>`;
  if (method === "queue") return `<div class="ipc-scene queue-scene"><div class="scene-heading">MESSAGE WAITING ROOM</div><div class="queue-producer">${producer}<small>put(message) ↓</small></div>${channel}<div class="queue-consumer"><small>↓ get() removes the oldest item</small>${consumer}</div></div>`;
  if (method === "shared_memory") return `<div class="ipc-scene memory-scene"><div class="scene-heading">BOTH PROCESSES MAP ONE MEMORY REGION</div><div class="memory-peers">${producer}${consumer}</div><div class="memory-access"><span>WRITE ↓</span><span>↓ READ</span></div>${channel}<div class="memory-signals"><span>data_ready: writer signals reader</span><span>consumed: reader releases writer</span></div></div>`;
  return `<div class="ipc-scene socket-scene"><div class="scene-heading">CONNECTED LOCAL SOCKET ENDPOINTS</div><div class="socket-peers"><div>${producer}<code>sendall(payload)</code><small>Application bytes: ABCDEF</small></div><div>${consumer}<code>recv(chunk_size)</code><small>Received chunks: AB / CDEF</small></div></div>${channel}<div class="socket-note">Byte stream: receive boundaries can differ from send boundaries.</div></div>`;
}

function playMechanism(method) {
  clearInterval(explanationTimer);
  const topology = $("#topology");
  const model = mechanisms[method];
  let step = 0;
  topology.classList.add("explaining");
  function showStep() {
    topology.dataset.step = String(step);
    $("#mechanism-step").textContent = `${step + 1} / 3 · ${model.steps[step]}`;
    if (method === "shared_memory") {
      $$(".shared-region i").forEach((cell) => cell.textContent = "53");
      $(".shared-region em").textContent = ["WRITE · consumer waiting", "data_ready → READ", "consumed → next WRITE"][step];
    }
    if (method === "queue") {
      $(".queue-buffer").dataset.phase = String(step);
    }
  }
  showStep();
  explanationTimer = setInterval(() => {
    step += 1;
    if (step === model.steps.length) {
      clearInterval(explanationTimer);
      topology.classList.remove("explaining");
      return;
    }
    showStep();
  }, 1600);
}

const pageMeta = {
  lab: ["INTERPROCESS COMMUNICATION", "Live IPC Laboratory"],
  race: ["CONCURRENCY CONTROL", "Race Condition Laboratory"],
  benchmark: ["PERFORMANCE ANALYSIS", "IPC Benchmark Suite"],
  tools: ["WINDOWS INTERNALS", "Tool-Assisted Analysis Lab"],
  learn: ["CONCEPT REFERENCE", "IPC Field Guide"],
};

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value >= 10 || unit === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[unit]}`;
}

function formatNumber(value) {
  return Number(value).toLocaleString();
}

function toast(message, type = "success") {
  const element = document.createElement("div");
  element.className = `toast ${type}`;
  element.textContent = message;
  $("#toasts").append(element);
  setTimeout(() => element.remove(), 4200);
}

function setBusy(button, busy, busyLabel) {
  if (!button.dataset.label) button.dataset.label = button.innerHTML;
  button.disabled = busy;
  button.innerHTML = busy ? `◌ ${busyLabel}` : button.dataset.label;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function addLog(event) {
  const consoleElement = $("#console");
  const row = document.createElement("div");
  row.className = `log-row ${event.level || "info"}`;
  const timestamp = document.createElement("time");
  timestamp.textContent = new Date(event.time * 1000).toLocaleTimeString([], { hour12: false });
  const level = document.createElement("span");
  level.className = "log-level";
  level.textContent = (event.level || "info").toUpperCase();
  const message = document.createElement("p");
  message.textContent = event.message;
  row.append(timestamp, level, message);
  consoleElement.append(row);
  consoleElement.scrollTop = consoleElement.scrollHeight;
}

async function startJob(endpoint, payload, onUpdate) {
  const { job_id: jobId } = await api(endpoint, { method: "POST", body: JSON.stringify(payload) });
  let eventCount = 0;
  let attempts = 0;
  while (attempts < 600) {
    await new Promise((resolve) => setTimeout(resolve, 300));
    const job = await api(`/api/jobs/${jobId}`);
    const newEvents = job.events.slice(eventCount);
    eventCount = job.events.length;
    onUpdate?.(job, newEvents);
    if (job.status === "completed") return job.result;
    if (job.status === "failed") throw new Error(job.error || "Experiment failed");
    attempts += 1;
  }
  throw new Error("The experiment took too long to finish");
}

function selectView(name) {
  $$(".nav-item").forEach((item) => {
    const active = item.dataset.view === name;
    item.classList.toggle("active", active);
    item.toggleAttribute("aria-current", active);
  });
  $$(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${name}`));
  $("#page-eyebrow").textContent = pageMeta[name][0];
  $("#page-title").textContent = pageMeta[name][1];
  history.replaceState(null, "", `#${name}`);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateRangeLabels() {
  $("#messages-output").textContent = formatNumber($("#messages").value);
  $("#payload-output").textContent = formatBytes(Number($("#payload-size").value));
  $("#flow-messages").textContent = formatNumber($("#messages").value);
  $("#flow-payload").textContent = formatBytes(Number($("#payload-size").value));
  $("#workers-output").textContent = $("#workers").value;
  $("#iterations-output").textContent = formatNumber($("#iterations").value);
  $("#race-expected").textContent = formatNumber(Number($("#workers").value) * Number($("#iterations").value));
}

function updateMethod() {
  const selected = $('input[name="method"]:checked');
  $$(".method-card").forEach((card) => card.classList.toggle("selected", card.contains(selected)));
  const name = methodNames[selected.value];
  $("#metric-transport").textContent = name;
  const method = selected.value;
  $("#topology").dataset.method = method;
  $("#topology").innerHTML = mechanismScene(method);
  $("#mechanism-title").textContent = mechanisms[method].title;
  $("#mechanism-description").textContent = mechanisms[method].description;
  $("#metric-rate").textContent = "—";
  $("#metric-rate-note").textContent = "Run the selected mechanism";
  ["#metric-latency", "#metric-data", "#flow-throughput"].forEach((id) => $(id).textContent = "—");
  $("#consumer-pid").textContent = "PID waiting";
  $("#topology-state").textContent = "Ready";
  $("#topology-state").classList.remove("failed");
  $("#transfer-error").hidden = true;
  playMechanism(method);
}

function updateSyncPrediction() {
  const enabled = $("#synchronized").checked;
  $("#race-state").textContent = enabled ? "Lock enabled" : "Unprotected";
  $("#race-state").classList.toggle("warning", !enabled);
  $("#race-prediction").textContent = enabled
    ? "The lock serializes updates, so the final value should be exact."
    : "The final value may be lower because updates overlap.";
}

function showIpcResult(result) {
  $$("#topology .node-state").forEach((node) => node.textContent = "VERIFIED");
  $("#metric-rate").textContent = formatNumber(result.messages_per_second);
  $("#metric-rate-note").textContent = `${result.throughput_mbps.toFixed(2)} Mbps throughput`;
  $("#metric-latency").textContent = `${result.latency_ms.toFixed(3)} ms`;
  $("#metric-data").textContent = formatBytes(result.bytes_transferred);
  $("#flow-throughput").textContent = `${result.throughput_mbps.toFixed(2)} Mbps`;
  $("#consumer-pid").textContent = `PID ${result.worker_pids[0]}`;
  $("#producer-pid").textContent = `PID ${$("#system-pid").textContent}`;
}

function animateCounter(target) {
  const output = $("#race-actual");
  const started = performance.now();
  const duration = 650;
  function frame(now) {
    const progress = Math.min((now - started) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    output.textContent = formatNumber(Math.round(target * eased));
    if (progress < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

function showRaceResult(result) {
  animateCounter(result.actual);
  $("#race-expected").textContent = formatNumber(result.expected);
  $("#race-lost").textContent = formatNumber(result.lost_updates);
  $("#race-accuracy").textContent = `${result.accuracy_percent.toFixed(2)}%`;
  $("#race-elapsed").textContent = `${result.elapsed_ms.toFixed(1)} ms`;
}

function showBenchmark(results) {
  const max = Math.max(...results.map((result) => result.throughput_mbps), 0.001);
  const chart = $("#benchmark-chart");
  chart.innerHTML = "";
  results.forEach((result) => {
    const group = document.createElement("div");
    group.className = "bar-group";
    const value = document.createElement("span");
    value.className = "bar-value";
    value.textContent = `${result.throughput_mbps.toFixed(1)} Mbps`;
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.height = `${Math.max(5, (result.throughput_mbps / max) * 185)}px`;
    const label = document.createElement("span");
    label.className = "bar-label";
    label.textContent = methodNames[result.method];
    group.append(value, bar, label);
    chart.append(group);
  });

  const body = $("#benchmark-body");
  body.innerHTML = "";
  [...results]
    .sort((a, b) => b.throughput_mbps - a.throughput_mbps)
    .forEach((result, index) => {
      const row = document.createElement("tr");
      const values = [
        `${index === 0 ? "★ " : ""}${methodNames[result.method]}`,
        `${result.latency_ms.toFixed(4)} ms`,
        `${result.throughput_mbps.toFixed(3)} Mbps`,
        formatNumber(result.messages_per_second),
        result.worker_pids.join(", "),
      ];
      values.forEach((text) => {
        const cell = document.createElement("td");
        cell.textContent = text;
        row.append(cell);
      });
      body.append(row);
    });
}

function readableEvidenceValue(key, value) {
  if (value === null || value === undefined || value === "") return "Not reported";
  if (typeof value === "string" && /^\/Date\(\d+\)\/$/.test(value)) {
    return new Date(Number(value.match(/\d+/)[0])).toLocaleString();
  }
  if (["WorkingSet64", "VirtualMemorySize64", "WorkingSetSize", "VirtualSize"].includes(key)) {
    return formatBytes(Number(value));
  }
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function showEvidence(title, result) {
  $("#evidence-empty").hidden = true;
  $("#evidence-result").hidden = false;
  $("#evidence-title").textContent = title;
  $("#evidence-state").textContent = "Captured";
  $("#evidence-command").textContent = result.command || result.query_command || result.commands?.[0] || "Completed";
  const data = result.data || result.values || {};
  const grid = $("#evidence-grid");
  grid.innerHTML = "";
  Object.entries(data).forEach(([key, value]) => {
    const item = document.createElement("div");
    const label = document.createElement("dt");
    const content = document.createElement("dd");
    label.textContent = key.replace(/([a-z])([A-Z])/g, "$1 $2");
    content.textContent = readableEvidenceValue(key, value);
    item.append(label, content);
    grid.append(item);
  });
  const raw = $("#evidence-raw");
  raw.hidden = !result.output;
  raw.textContent = result.output || "";
}

async function loadToolStatus() {
  try {
    const status = await api("/api/tools/status");
    $("#tools-ready").textContent = `${status.available} / ${status.total}`;
    $("#tools-target-pid").textContent = `PID ${status.target_pid}`;
    $("#command-powershell").textContent = `Get-Process -Id ${status.target_pid}`;
    $("#command-wmi").textContent = `Get-CimInstance Win32_Process -Filter "ProcessId = ${status.target_pid}"`;
    status.tools.forEach((tool) => {
      const badge = $(`#status-${tool.id}`);
      if (!badge) return;
      badge.className = `tool-status ${tool.available ? "available" : "missing"}`;
      badge.textContent = tool.available ? "Available" : "Missing";
    });
  } catch (error) {
    toast(`Tool detection failed: ${error.message}`, "error");
  }
}

async function runToolAction(button, endpoint, title, busyLabel) {
  setBusy(button, true, busyLabel);
  $("#evidence-state").textContent = "Running";
  try {
    const result = await api(endpoint, { method: "POST", body: "{}" });
    showEvidence(title, result);
    toast(`${title} completed`);
    return result;
  } catch (error) {
    $("#evidence-state").textContent = "Failed";
    toast(error.message, "error");
    return null;
  } finally {
    setBusy(button, false);
  }
}

async function loadSystem() {
  try {
    const system = await api("/api/system");
    $("#system-platform").textContent = `${system.platform} ${system.release}`;
    $("#system-pid").textContent = system.server_pid;
    $("#system-cpus").textContent = system.cpu_count ?? "—";
  } catch (error) {
    toast(`Engine connection failed: ${error.message}`, "error");
  }
}

function bindEvents() {
  $("#replay-mechanism").addEventListener("click", () => playMechanism($('input[name="method"]:checked').value));
  $$(".nav-item").forEach((item) => item.addEventListener("click", () => selectView(item.dataset.view)));
  $$("input[type=range]").forEach((input) => input.addEventListener("input", updateRangeLabels));
  $$('input[name="method"]').forEach((input) => input.addEventListener("change", updateMethod));
  $("#synchronized").addEventListener("change", updateSyncPrediction);
  $("#clear-console").addEventListener("click", () => { $("#console").innerHTML = ""; });
  $("#theme-toggle").addEventListener("click", () => {
    document.documentElement.classList.toggle("light");
    localStorage.setItem("syncscope-theme", document.documentElement.classList.contains("light") ? "light" : "dark");
  });

  $("#ipc-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = $("#run-ipc");
    const topology = $("#topology");
    const method = $('input[name="method"]:checked').value;
    setBusy(button, true, "Experiment running");
    $("#transfer-error").hidden = true;
    $("#topology-state").classList.remove("failed");
    $$("#topology .node-state").forEach((node) => node.textContent = "RUNNING");
    ["#metric-rate", "#metric-latency", "#metric-data", "#flow-throughput"].forEach((id) => $(id).textContent = "—");
    $("#metric-rate-note").textContent = "Measuring real transfer…";
    $("#consumer-pid").textContent = "PID starting";
    $$('#ipc-form input').forEach((input) => input.disabled = true);
    playMechanism(method);
    topology.classList.add("running");
    $("#topology-state").textContent = "Transferring";
    try {
      const result = await startJob("/api/experiments/ipc", {
        method,
        messages: Number($("#messages").value),
        payload_size: Number($("#payload-size").value),
      }, (_job, events) => events.forEach(addLog));
      showIpcResult(result);
      addLog({time: Date.now() / 1000, level: "success", message: `${methodNames[method]} consumer verified ${formatNumber(result.received_bytes)} received bytes.`});
      $("#topology-state").textContent = "Completed";
      toast(`${methodNames[method]} experiment completed`);
    } catch (error) {
      $("#topology-state").textContent = "Failed";
      $("#topology-state").classList.add("failed");
      $$("#topology .node-state").forEach((node) => node.textContent = "FAILED");
      $("#transfer-error").textContent = `Transfer failed: ${error.message}`;
      $("#transfer-error").hidden = false;
      $("#metric-rate-note").textContent = "No measurements: transfer failed";
      addLog({ time: Date.now() / 1000, level: "error", message: error.message });
      toast(error.message, "error");
    } finally {
      topology.classList.remove("running");
      setBusy(button, false);
      $$('#ipc-form input').forEach((input) => input.disabled = false);
    }
  });

  $("#race-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = $("#run-race");
    const synchronized = $("#synchronized").checked;
    setBusy(button, true, "Processes racing");
    try {
      const result = await startJob("/api/experiments/race", {
        workers: Number($("#workers").value),
        iterations: Number($("#iterations").value),
        synchronized,
      });
      showRaceResult(result);
      toast(synchronized ? "Lock protected every update" : `${formatNumber(result.lost_updates)} updates were lost`);
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setBusy(button, false);
    }
  });

  $("#benchmark-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = $("#run-benchmark");
    setBusy(button, true, "Benchmarking");
    try {
      const result = await startJob("/api/experiments/benchmark", {
        messages: Number($("#benchmark-messages").value),
        payload_size: Number($("#benchmark-payload").value),
      });
      showBenchmark(result.results);
      toast("Four-method comparison completed");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setBusy(button, false);
    }
  });

  $("#run-powershell").addEventListener("click", () =>
    runToolAction($("#run-powershell"), "/api/tools/powershell", "PowerShell process snapshot", "Inspecting")
  );
  $("#run-wmi").addEventListener("click", () =>
    runToolAction($("#run-wmi"), "/api/tools/wmi", "WMI Win32_Process result", "Querying WMI")
  );
  $("#run-registry").addEventListener("click", () =>
    runToolAction($("#run-registry"), "/api/tools/registry", "Registry experiment evidence", "Writing lab key")
  );
  $("#open-regedit").addEventListener("click", async () => {
    const button = $("#open-regedit");
    setBusy(button, true, "Opening");
    try {
      const result = await api("/api/tools/regedit", { method: "POST", body: "{}" });
      toast(result.instruction);
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setBusy(button, false);
    }
  });
}

function init() {
  if (localStorage.getItem("syncscope-theme") === "light") document.documentElement.classList.add("light");
  bindEvents();
  updateRangeLabels();
  updateMethod();
  updateSyncPrediction();
  const initialView = pageMeta[location.hash.slice(1)] ? location.hash.slice(1) : "lab";
  selectView(initialView);
  loadSystem();
  loadToolStatus();
}

init();
