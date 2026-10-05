const $ = (id) => document.getElementById(id);
const SVG_NS = "http://www.w3.org/2000/svg";
const methods = {
  minimum_regret: { name: "Minimum disappointment", note: "Smallest worst rank", color: "#5ba486" },
  gale_shapley_v_proposes: { name: "GS · M proposes", note: "Male side proposes", color: "#cc9072" },
  gale_shapley_u_proposes: { name: "GS · F proposes", note: "Female side proposes", color: "#aa93c6" },
};
const state = {
  wave: 2, round: 1, removal: 5, seed: 7,
  method: "minimum_regret", showEligible: true,
  snapshot: null, waves: [], request: 0, selected: null,
};
let debounceTimer;

function label(id) { return (id.startsWith("v") ? "M " : "F ") + id.slice(1); }
function fmt(value, digits = 0) {
  return value == null ? "—" : Number(value).toFixed(digits).replace(/\.0+$/, "");
}
function percentile(sorted, fraction) {
  if (!sorted.length) return null;
  const position = (sorted.length - 1) * fraction;
  const lower = Math.floor(position), upper = Math.ceil(position);
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
}
function fmtPercentile(value) {
  return value == null ? "—" : String(Number(value.toFixed(2)));
}
function svgElement(name, attrs = {}) {
  const el = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, String(value));
  return el;
}
function selectedPairs() {
  const matching = state.snapshot?.results[state.method]?.matching || {};
  return new Set(Object.entries(matching).filter(([, v]) => v != null).map(([u, v]) => v + "|" + u));
}
function setLoading(show, message = "Computing stable matchings…") {
  $("loading").classList.toggle("hidden", !show);
  $("loading").lastElementChild.textContent = message;
}
function updateControlLabels() {
  $("wave-value").textContent = String(state.wave).padStart(2, "0");
  $("round-value").textContent = String(state.round).padStart(2, "0");
  $("removal-value").textContent = state.removal + "%";
  $("seed-value").textContent = "#" + String(state.seed).padStart(2, "0");
}
function nearestWave(value) {
  return state.waves.reduce((best, wave) =>
    Math.abs(wave - value) < Math.abs(best - value) ? wave : best, state.waves[0]);
}
function scheduleLoad() {
  // Invalidate an in-flight response as soon as a control changes, before debounce.
  ++state.request;
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(loadSnapshot, 180);
}
async function loadSnapshot() {
  const request = ++state.request;
  setLoading(true);
  const params = new URLSearchParams({
    wave: state.wave, iteration: state.round, removal: state.removal, seed: state.seed,
  });
  try {
    const response = await fetch("/api/iteration?" + params);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Could not load this iteration");
    if (request !== state.request) return;
    state.snapshot = payload;
    state.selected = null;
    render();
    setLoading(false);
  } catch (error) {
    if (request !== state.request) return;
    setLoading(true, error.message);
  }
}
function positions(ids) {
  const count = ids.length;
  if (count === 0) return {};
  const start = count <= 6 ? 120 : 50;
  const end = count <= 6 ? 570 : 640;
  const map = {};
  ids.forEach((id, index) => {
    map[id] = count === 1 ? 345 : start + index * (end - start) / (count - 1);
  });
  return map;
}
function renderGraph() {
  const svg = $("graph");
  svg.style.opacity = "0";
  svg.replaceChildren();
  const { male, female, edges } = state.snapshot.population;
  const my = positions(male), fy = positions(female);
  const edgeLayer = svgElement("g", { class: "edge-layer" });
  for (const edge of edges) {
    const from = my[edge.male], to = fy[edge.female];
    const path = svgElement("path", {
      class: "edge", d: `M 147 ${from} C 408 ${from}, 592 ${to}, 853 ${to}`,
      "data-pair": edge.male + "|" + edge.female,
    });
    const title = svgElement("title");
    title.textContent = `${label(edge.male)} ↔ ${label(edge.female)} · ranks ${edge.male_rank} / ${edge.female_rank}`;
    path.appendChild(title);
    edgeLayer.appendChild(path);
  }
  svg.appendChild(edgeLayer);
  const nodeLayer = svgElement("g", { class: "node-layer" });
  const makeNode = (id, side, y, x) => {
    const group = svgElement("g", {
      class: "node " + side, "data-person": id, tabindex: 0,
      role: "button", "aria-label": `Spotlight ${label(id)}'s match`,
    });
    const circle = svgElement("circle", { cx: x, cy: y, r: 20 });
    const text = svgElement("text", {
      x, y: y + 4, "text-anchor": "middle", class: "node-id",
    });
    text.textContent = id.slice(1);
    const title = svgElement("title");
    title.textContent = label(id);
    group.append(circle, text, title);
    group.addEventListener("click", () => selectNode(id));
    group.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectNode(id);
      }
    });
    return group;
  };
  male.forEach(id => nodeLayer.appendChild(makeNode(id, "male", my[id], 120)));
  female.forEach(id => nodeLayer.appendChild(makeNode(id, "female", fy[id], 880)));
  svg.appendChild(nodeLayer);
  updateGraphMatches();
  requestAnimationFrame(() => { svg.style.opacity = "1"; });
}
function selectNode(id) {
  state.selected = state.selected === id ? null : id;
  updateGraphMatches();
}
function showEdgeDisappointment(svg, edge, male, female, assignments) {
  const point = edge.getPointAtLength(edge.getTotalLength() / 2);
  const group = svgElement("g", { class: "edge-disappointment" });
  group.appendChild(svgElement("rect", {
    x: point.x - 88, y: point.y - 26, width: 176, height: 52, rx: 13,
  }));
  const heading = svgElement("text", {
    x: point.x, y: point.y - 5, "text-anchor": "middle", class: "edge-disappointment-heading",
  });
  heading.textContent = "DISAPPOINTMENT";
  const ranks = svgElement("text", {
    x: point.x, y: point.y + 16, "text-anchor": "middle", class: "edge-disappointment-ranks",
  });
  ranks.textContent = `M: ${assignments[male].regret}  ·  F: ${assignments[female].regret}`;
  group.append(heading, ranks);
  svg.appendChild(group);
}
function updateGraphMatches() {
  if (!state.snapshot) return;
  const pairs = selectedPairs();
  const selected = state.selected;
  const assignments = state.snapshot.results[state.method].metrics.assignments;
  const assignment = selected && assignments[selected];
  const partner = assignment?.partner ?? null;
  const selectedPair = partner && (selected.startsWith("v")
    ? selected + "|" + partner : partner + "|" + selected);
  const [selectedMale, selectedFemale] = selectedPair?.split("|") ?? [];
  const svg = $("graph");
  svg.style.setProperty("--edge-color", methods[state.method].color);
  svg.querySelector(".edge-disappointment")?.remove();
  let spotlightEdge = null;
  svg.querySelectorAll(".edge").forEach(edge => {
    const matched = pairs.has(edge.dataset.pair);
    if (selectedPair && edge.dataset.pair === selectedPair) spotlightEdge = edge;
    edge.classList.toggle("matched", matched);
    edge.classList.toggle("hidden-edge", !matched && !state.showEligible);
    edge.classList.toggle("deemphasized", Boolean(selected && edge.dataset.pair !== selectedPair));
    edge.classList.toggle("spotlight", Boolean(selectedPair && edge.dataset.pair === selectedPair));
  });
  const matching = state.snapshot.results[state.method].matching;
  const matchedPeople = new Set();
  Object.entries(matching).forEach(([u, v]) => {
    if (v != null) { matchedPeople.add(u); matchedPeople.add(v); }
  });
  svg.querySelectorAll(".node").forEach(node => {
    const id = node.dataset.person;
    node.classList.toggle("has-match", matchedPeople.has(id));
    node.classList.toggle("selected", id === selected);
    node.classList.toggle("spotlight-partner", Boolean(partner && id === partner));
    node.classList.toggle("dimmed", Boolean(selected && id.startsWith("v") !== selected.startsWith("v") && id !== partner));
    node.setAttribute("aria-pressed", String(id === selected));
  });
  if (spotlightEdge) {
    showEdgeDisappointment(svg, spotlightEdge, selectedMale, selectedFemale, assignments);
  }
  $("selection-note").textContent = selected
    ? partner ? `Selected match · M disappointment ${assignments[selectedMale].regret}, F disappointment ${assignments[selectedFemale].regret}. Click again to clear.`
      : "No match in this round. Click again to clear."
    : "Click a node to spotlight its current match.";
}
function renderMetrics() {
  if (!state.snapshot) return;
  const method = methods[state.method];
  const result = state.snapshot.results[state.method];
  const metrics = result.metrics;
  const ranks = Object.values(metrics.assignments).map(entry => entry.regret)
    .filter(value => value != null).sort((a, b) => a - b);
  $("selected-method-name").textContent = method.name;
  $("selected-method-note").textContent = method.note;
  $("stable-pill").textContent = result.stable ? "STABLE" : "UNSTABLE";
  $("stable-pill").style.background = result.stable ? "#ebf6ee" : "#fae9e5";
  $("stable-pill").style.color = result.stable ? "#62a17c" : "#c27766";
  $("highest-regret").textContent = ranks.length ? Math.max(...ranks) : "—";
  $("lowest-regret").textContent = ranks.length ? Math.min(...ranks) : "—";
  $("mean-regret").textContent = fmt(metrics.mean_regret, 1);
  $("p25-disappointment").textContent = fmtPercentile(percentile(ranks, .25));
  $("median-disappointment").textContent = fmtPercentile(percentile(ranks, .5));
  $("p75-disappointment").textContent = fmtPercentile(percentile(ranks, .75));
  $("matched-pairs").textContent = fmt(metrics.matched_participants / 2);
  $("unmatched-people").textContent = fmt(metrics.unmatched_participants);
  $("total-regret").textContent = "Total " + fmt(metrics.total_regret);
  renderDistribution(metrics);
}
function renderDistribution(metrics) {
  const { max_rank: maxRank, max_people: maxPeople } = state.snapshot.distribution_axes;
  const distribution = metrics.regret_distribution;
  const chart = $("distribution-chart");
  const svg = svgElement("svg", {
    viewBox: "0 0 300 160", role: "img",
    "aria-label": `Disappointment by partner rank, ranks 1 to ${maxRank}, people 0 to ${maxPeople}`,
  });
  const left = 29, right = 292, top = 10, bottom = 127;
  const width = right - left, height = bottom - top;
  for (const count of new Set([0, Math.ceil(maxPeople / 2), maxPeople])) {
    const y = bottom - count / maxPeople * height;
    svg.appendChild(svgElement("line", { x1: left, x2: right, y1: y, y2: y, class: "chart-grid" }));
    const label = svgElement("text", { x: left - 7, y: y + 3, "text-anchor": "end", class: "chart-tick" });
    label.textContent = String(count);
    svg.appendChild(label);
  }
  const band = width / maxRank;
  const barWidth = Math.min(22, band * .72);
  for (let rank = 1; rank <= maxRank; rank++) {
    const count = Number(distribution[rank] || 0);
    if (!count) continue;
    const barHeight = count / maxPeople * height;
    const bar = svgElement("rect", {
      x: left + (rank - 1) * band + (band - barWidth) / 2,
      y: bottom - barHeight, width: barWidth, height: barHeight,
      class: "chart-bar", fill: methods[state.method].color,
    });
    const title = svgElement("title");
    title.textContent = `Rank ${rank}: ${count} ${count === 1 ? "person" : "people"}`;
    bar.appendChild(title);
    svg.appendChild(bar);
  }
  for (const rank of new Set([1, Math.ceil(maxRank / 2), maxRank])) {
    const x = left + (rank - .5) * band;
    const label = svgElement("text", { x, y: bottom + 16, "text-anchor": "middle", class: "chart-tick" });
    label.textContent = String(rank);
    svg.appendChild(label);
  }
  if (!Object.keys(distribution).length) {
    const label = svgElement("text", { x: (left + right) / 2, y: 73,
      "text-anchor": "middle", class: "chart-empty" });
    label.textContent = "No matched people in this round";
    svg.appendChild(label);
  }
  chart.replaceChildren(svg);
}
function render() {
  const data = state.snapshot;
  $("view-label").replaceChildren(document.createTextNode(
    `Wave ${String(state.wave).padStart(2, "0")} · Round ${String(state.round).padStart(2, "0")}`));
  $("pool-note").textContent = `${data.population.male.length} M · ${data.population.female.length} F · ${data.population.mutual_edges} eligible pairs`;
  $("edge-count").textContent = data.population.mutual_edges + " eligible pairs";
  renderGraph();
  renderMetrics();
}
function chooseMethod(method) {
  state.method = method;
  document.querySelectorAll(".method").forEach(button => {
    const active = button.dataset.method === method;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  updateGraphMatches();
  renderMetrics();
}
async function init() {
  document.querySelectorAll(".method").forEach(button =>
    button.addEventListener("click", () => chooseMethod(button.dataset.method)));
  $("show-eligible").addEventListener("change", event => {
    state.showEligible = event.target.checked;
    updateGraphMatches();
  });
  $("wave-slider").addEventListener("input", event => {
    state.wave = nearestWave(Number(event.target.value));
    event.target.value = state.wave;
    state.round = 1;
    $("round-slider").value = 1;
    updateControlLabels();
    scheduleLoad();
  });
  $("round-slider").addEventListener("input", event => {
    state.round = Number(event.target.value);
    updateControlLabels();
    scheduleLoad();
  });
  $("removal-slider").addEventListener("input", event => {
    state.removal = Number(event.target.value);
    updateControlLabels();
    scheduleLoad();
  });
  $("reshuffle").addEventListener("click", () => {
    state.seed = crypto.getRandomValues(new Uint32Array(1))[0] % 10000;
    updateControlLabels();
    loadSnapshot();
  });
  try {
    const response = await fetch("/api/waves");
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Could not discover waves");
    state.waves = payload.waves;
    state.wave = payload.default;
    $("wave-slider").min = Math.min(...state.waves);
    $("wave-slider").max = Math.max(...state.waves);
    $("wave-slider").value = state.wave;
    updateControlLabels();
    loadSnapshot();
  } catch (error) {
    setLoading(true, error.message);
  }
}
init();
