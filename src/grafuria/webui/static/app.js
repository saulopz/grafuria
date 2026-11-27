// Grafuria web interface. Talks to the local server through one WebSocket.
"use strict";

// Same values as core/state.py
const STATE_CLASS = { 0: "none", 1: "active", 2: "testing", 4: "invalid" };

const $ = (id) => document.getElementById(id);
let ws = null;
let directed = false;
let finishedState = ""; // "", "solved" or "failed"

// ---------------------------------------------------------------- canvas
const cy = cytoscape({
  container: $("cy"),
  layout: { name: "preset" },
  wheelSensitivity: 0.3,
  style: [
    { selector: "node", style: {
        "width": 12, "height": 12, "background-color": "gold",
        "border-width": 2, "border-color": "#1d1d1f",
        "label": "data(name)", "font-size": 12, "text-valign": "top", "text-margin-y": -4 } },
    { selector: "edge", style: {
        "width": 2, "line-color": "gold", "curve-style": "straight",
        "target-arrow-color": "gold", "arrow-scale": 0.8 } },
    { selector: "edge.directed", style: { "target-arrow-shape": "triangle" } },
    { selector: "edge.weights", style: {
        "label": "data(weight)", "font-size": 10, "text-background-color": "#fff",
        "text-background-opacity": 0.8, "text-background-padding": 1 } },
    { selector: ".testing", style: { "background-color": "blue", "line-color": "blue", "target-arrow-color": "blue" } },
    { selector: ".active", style: { "background-color": "#1d1d1f", "line-color": "#1d1d1f", "target-arrow-color": "#1d1d1f" } },
    { selector: "edge.active", style: { "width": 4 } },
    { selector: ".invalid", style: { "background-color": "DarkOrange", "line-color": "DarkOrange", "target-arrow-color": "DarkOrange" } },
    { selector: ".area", style: { "background-color": "#fffacd" } },
  ],
});

function showGraph(graph) {
  cy.elements().remove();
  if (!graph) return;
  directed = !graph.bidirectional;
  const nodes = graph.vertex.map((v) => ({
    group: "nodes", data: { id: "v" + v.id, name: v.name || "" },
    position: { x: v.x, y: v.y }, classes: "none",
  }));
  const edges = graph.edge.map((e) => ({
    group: "edges",
    data: { id: "e" + e.id, source: "v" + e.a, target: "v" + e.b, weight: String(e.weight) },
    classes: "none" + (directed ? " directed" : "") + ($("show-weight").checked ? " weights" : ""),
  }));
  cy.add(nodes.concat(edges));
  cy.fit(undefined, 30);
}

function applyStates(kind, states) {
  cy.batch(() => {
    for (const [id, state] of Object.entries(states)) {
      const ele = cy.getElementById(kind + id);
      if (ele.empty()) continue;
      for (const cls of Object.values(STATE_CLASS)) ele.removeClass(cls);
      ele.addClass(STATE_CLASS[state] || "none");
    }
  });
}

function resetStates() {
  cy.batch(() => {
    cy.elements().removeClass("testing active invalid").addClass("none");
  });
}

// ---------------------------------------------------------------- log
function readSymbols() {
  try { return localStorage.getItem("grafuria.logSymbols"); } catch (e) { return null; }
}
function saveSymbols(value) {
  try { localStorage.setItem("grafuria.logSymbols", value); } catch (e) { /* ignore */ }
}

function appendLog(lines) {
  const symbols = $("log-symbols").value;
  const log = $("log");
  for (const line of lines) {
    let text = line.text;
    if (!line.system) {
      if (!text || !symbols.includes(text[0])) continue;
      text = text.slice(1);
    }
    const div = document.createElement("div");
    if (line.system) div.className = "system";
    div.textContent = text;
    log.appendChild(div);
  }
  log.scrollTop = log.scrollHeight;
}

// ---------------------------------------------------------------- status
function setStatus(text, cls) {
  $("status").textContent = text;
  $("status").className = cls || "";
}

function setCanvasMode(mode) {
  $("cy").classList.remove("running", "solved", "failed");
  if (mode) $("cy").classList.add(mode);
}

function fillSelect(select, items) {
  const current = select.value;
  select.length = 1;
  for (const item of items) select.add(new Option(item, item));
  select.value = current;
}

// ---------------------------------------------------------------- server
// Optional start from the address: /?graph=cube.json&script=bfs.lua&play=1
const startup = new URLSearchParams(location.search);

const handlers = {
  files(m) {
    fillSelect($("graph-select"), m.graphs);
    fillSelect($("script-select"), m.scripts);
    if (startup.get("graph")) send({ cmd: "load_graph", name: startup.get("graph") });
    if (startup.get("script")) send({ cmd: "load_script", name: startup.get("script") });
    if (startup.get("play") === "1") send({ cmd: "play" });
    startup.delete("graph"); startup.delete("script"); startup.delete("play"); // only once
  },
  graph(m) {
    $("graph-select").value = m.name;
    showGraph(m.graph);
    setCanvasMode("");
    finishedState = "";
  },
  script(m) {
    $("script-select").value = m.name;
    const params = $("params");
    params.innerHTML = "";
    const entries = Object.entries(m.params);
    if (!entries.length) params.innerHTML = "<dt>none</dt>";
    for (const [key, value] of entries) {
      const dt = document.createElement("dt"); dt.textContent = key;
      const dd = document.createElement("dd"); dd.textContent = String(value);
      params.append(dt, dd);
    }
  },
  states(m) {
    applyStates("v", m.v);
    applyStates("e", m.e);
  },
  log(m) { appendLog(m.lines); },
  area(m) { /* drawn by a later version */ },
  status(m) {
    $("speed").value = m.speed;
    $("speed-value").textContent = m.speed;
    $("pause").disabled = !m.running || m.paused;
    $("stop").disabled = !m.running;
    if (m.running) {
      setCanvasMode("running");
      setStatus(m.paused ? "⏸ Paused" : "▶ Running…");
    } else if (!finishedState) {
      setCanvasMode("");
      setStatus("Ready.");
    }
  },
  finished(m) {
    finishedState = m.solved ? "solved" : "failed";
    setCanvasMode(finishedState);
    const time = m.time == null ? "" : ` in ${Number(m.time).toFixed(4)} s`;
    setStatus(m.solved ? `✓ Solved${time}` : `✗ Not solved${time}`, finishedState);
  },
  error(m) { setStatus("⚠ " + m.message); },
};

function send(message) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(message));
}

function connect() {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () => { $("banner").hidden = true; };
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    const handler = handlers[message.type];
    if (handler) handler(message);
  };
  ws.onclose = () => {
    $("banner").textContent = "Connection to Grafuria lost. Retrying…";
    $("banner").hidden = false;
    setTimeout(connect, 1500);
  };
}

// ---------------------------------------------------------------- controls
$("graph-select").onchange = (e) => e.target.value && send({ cmd: "load_graph", name: e.target.value });
$("script-select").onchange = (e) => e.target.value && send({ cmd: "load_script", name: e.target.value });
$("play").onclick = () => {
  if ($("pause").disabled && $("stop").disabled) { // not running: new run
    $("log").innerHTML = "";
    finishedState = "";
    resetStates();
  }
  send({ cmd: "play" });
};
$("pause").onclick = () => send({ cmd: "pause" });
$("stop").onclick = () => send({ cmd: "stop" });
$("clear").onclick = () => {
  finishedState = "";
  $("log").innerHTML = "";
  resetStates();
  send({ cmd: "clear" });
};
$("speed").oninput = (e) => {
  $("speed-value").textContent = e.target.value;
  send({ cmd: "speed", value: Number(e.target.value) });
};
$("show-weight").onchange = (e) => cy.edges().toggleClass("weights", e.target.checked);
$("log-symbols").value = readSymbols() ?? "#$";
$("log-symbols").oninput = (e) => saveSymbols(e.target.value);

connect();
