// Grafuria web interface. Talks to the local server through one WebSocket.
// The server owns the graph: the page sends commands and draws what the
// server answers (so several tabs stay in sync).
"use strict";

// Same values as core/state.py
const STATE_CLASS = { 0: "none", 1: "active", 2: "testing", 4: "invalid" };
const STATE_CLASSES = Object.values(STATE_CLASS).join(" ");

const $ = (id) => document.getElementById(id);
let ws = null;
let running = false;
let finishedState = ""; // "", "solved" or "failed"
let selected = null;    // {kind: "v" | "e", id: number}

// ---------------------------------------------------------------- canvas
const cy = cytoscape({
  container: $("cy"),
  layout: { name: "preset" },
  wheelSensitivity: 0.3,
  boxSelectionEnabled: false,
  autounselectify: true, // selection is handled here ("picked" class)
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
    // Selection: a halo, so it never hides the state colour.
    { selector: ".picked", style: {
        "underlay-color": "#1d1d1f", "underlay-opacity": 0.25, "underlay-padding": 7 } },
    { selector: "node.picked", style: { "underlay-shape": "ellipse" } },
  ],
});

const nodeId = (id) => "v" + id;
const edgeId = (id) => "e" + id;

function edgeClasses() {
  return "none" + ($("directed").checked ? " directed" : "") +
         ($("show-weight").checked ? " weights" : "");
}

function nodeElement(v) {
  return { group: "nodes", data: { id: nodeId(v.id), vid: v.id, name: v.name || "" },
           position: { x: v.x, y: v.y }, classes: "none" };
}

function edgeElement(e) {
  return { group: "edges",
           data: { id: edgeId(e.id), eid: e.id, source: nodeId(e.a), target: nodeId(e.b),
                   weight: String(e.weight) },
           classes: edgeClasses() };
}

function showGraph(graph) {
  select(null);
  cy.elements().remove();
  if (!graph) return;
  $("directed").checked = !graph.bidirectional;
  cy.add(graph.vertex.map(nodeElement).concat(graph.edge.map(edgeElement)));
  if (graph.vertex.length) cy.fit(undefined, 30);
}

function applyStates(kind, states) {
  cy.batch(() => {
    for (const [id, state] of Object.entries(states)) {
      const ele = cy.getElementById(kind + id);
      if (ele.empty()) continue;
      ele.removeClass(STATE_CLASSES).addClass(STATE_CLASS[state] || "none");
    }
  });
}

function resetStates() {
  cy.batch(() => cy.elements().removeClass(STATE_CLASSES).addClass("none"));
}

// ---------------------------------------------------------------- selection
function select(target) {
  cy.elements(".picked").removeClass("picked");
  selected = target;
  const box = $("selection");
  box.innerHTML = "";
  if (!target) {
    box.innerHTML = '<p class="hint">Nothing selected.</p>';
    return;
  }
  const ele = cy.getElementById(target.kind + target.id);
  ele.addClass("picked");
  const field = (label, value, onChange, readonly) => {
    const wrap = document.createElement("label");
    wrap.textContent = label;
    const input = document.createElement("input");
    input.value = value;
    input.readOnly = !!readonly;
    if (onChange) input.onchange = () => onChange(input.value);
    wrap.appendChild(input);
    box.appendChild(wrap);
    return input;
  };
  if (target.kind === "v") {
    field("Vertex ID", target.id, null, true);
    field("Name", ele.data("name"), (name) => send({ cmd: "rename_vertex", id: target.id, name }));
  } else {
    field("Edge ID", target.id, null, true);
    field("Weight", ele.data("weight"), (weight) => send({ cmd: "set_weight", id: target.id, weight }));
  }
}

// ---------------------------------------------------------------- editing
cy.on("dbltap", (evt) => {
  if (evt.target !== cy || running) return;
  send({ cmd: "add_vertex", x: evt.position.x, y: evt.position.y });
});

cy.on("tap", (evt) => {
  if (evt.target === cy) select(null);
});

cy.on("tap", "node", (evt) => {
  const id = evt.target.data("vid");
  const shift = evt.originalEvent && evt.originalEvent.shiftKey;
  if (shift && selected && selected.kind === "v" && selected.id !== id && !running) {
    send({ cmd: "add_edge", a: selected.id, b: id });
  }
  select({ kind: "v", id });
});

cy.on("tap", "edge", (evt) => select({ kind: "e", id: evt.target.data("eid") }));

cy.on("dragfree", "node", (evt) => {
  const p = evt.target.position();
  send({ cmd: "move_vertex", id: evt.target.data("vid"), x: p.x, y: p.y });
});

document.addEventListener("keydown", (evt) => {
  const typing = ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName);
  if (typing || !selected || running) return;
  if (evt.key === "Delete" || evt.key === "Backspace") {
    evt.preventDefault();
    send({ cmd: selected.kind === "v" ? "delete_vertex" : "delete_edge", id: selected.id });
  }
});

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

function setRunning(value) {
  running = value;
  cy.autoungrabify(running); // no dragging while a script runs
  document.body.classList.toggle("locked", running);
  for (const id of ["save", "new-graph", "directed", "graph-select"]) $(id).disabled = running;
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
    $("save-name").value = m.name;
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
  vertex_added(m) {
    cy.add(nodeElement(m.vertex));
    select({ kind: "v", id: m.vertex.id });
  },
  edge_added(m) { cy.add(edgeElement(m.edge)); },
  vertex_moved(m) {
    const node = cy.getElementById(nodeId(m.id));
    if (!node.grabbed()) node.position({ x: m.x, y: m.y });
  },
  vertex_renamed(m) { cy.getElementById(nodeId(m.id)).data("name", m.name); },
  edge_weight(m) { cy.getElementById(edgeId(m.id)).data("weight", String(m.weight)); },
  vertex_removed(m) {
    if (selected && ((selected.kind === "v" && selected.id === m.id) ||
                     (selected.kind === "e" && m.edges.includes(selected.id)))) select(null);
    cy.getElementById(nodeId(m.id)).remove();
  },
  edge_removed(m) {
    if (selected && selected.kind === "e" && selected.id === m.id) select(null);
    cy.getElementById(edgeId(m.id)).remove();
  },
  saved(m) {
    $("graph-select").value = m.name;
    $("save-name").value = m.name;
    setStatus(`Saved as ${m.name}`);
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
    setRunning(m.running);
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
$("new-graph").onclick = () => send({ cmd: "new_graph", directed: $("directed").checked });
$("directed").onchange = (e) => send({ cmd: "set_directed", directed: e.target.checked });
$("save").onclick = () => {
  const name = $("save-name").value.trim();
  if (!name) { setStatus("⚠ Type a file name to save."); return; }
  const file = name.endsWith(".json") ? name : name + ".json";
  const exists = [...$("graph-select").options].some((o) => o.value === file);
  if (exists && file !== $("graph-select").value && !confirm(`Replace ${file}?`)) return;
  send({ cmd: "save_graph", name: file });
};
$("play").onclick = () => {
  if (!running) { // new run
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
