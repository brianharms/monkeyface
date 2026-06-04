const CANONICAL = ["lot_id", "field_id", "lat", "lon", "harvest_date",
                   "defect_rate", "grower", "variety"];
let lastResult = null;

const $ = (id) => document.getElementById(id);

// HTML-escape any value before interpolating into innerHTML / popup strings.
const esc = (s) => { const d = document.createElement("div"); d.textContent = String(s ?? ""); return d.innerHTML; };

$("loadCols").onclick = async () => {
  const f = $("file").files[0];
  if (!f) { $("status").textContent = "Choose a file first."; return; }
  const fd = new FormData(); fd.append("file", f);
  const r = await fetch("/api/columns", { method: "POST", body: fd });
  if (!r.ok) { $("status").textContent = "Parse error."; return; }
  const { columns } = await r.json();
  buildMapping(columns);
  $("run").disabled = false;
};

function guess(col) {
  const c = col.toLowerCase();
  if (c.includes("lot")) return "lot_id";
  if (c.includes("field")) return "field_id";
  if (c.startsWith("lat")) return "lat";
  if (c.startsWith("lon") || c.includes("lng")) return "lon";
  if (c.includes("harv") || c.includes("date")) return "harvest_date";
  if (c.includes("defect")) return "defect_rate";
  if (c.includes("grow")) return "grower";
  if (c.includes("variet")) return "variety";
  return "";
}

function buildMapping(columns) {
  const html = columns.map((col) => {
    const opts = ['<option value="">— ignore —</option>']
      .concat(CANONICAL.map((cn) =>
        `<option value="${cn}" ${guess(col) === cn ? "selected" : ""}>${cn}</option>`))
      .join("");
    return `<div class="mapping-row"><label>${esc(col)}</label>
            <select data-src="${esc(col)}">${opts}</select></div>`;
  }).join("");
  $("mapping").innerHTML = html;
}

$("run").onclick = async () => {
  const f = $("file").files[0];
  const mapping = {};
  document.querySelectorAll("#mapping select").forEach((s) => {
    if (s.value) mapping[s.dataset.src] = s.value;
  });
  const fd = new FormData();
  fd.append("file", f);
  fd.append("mapping", JSON.stringify(mapping));
  $("status").textContent = "Pulling weather + analyzing… (first run is slower)";
  $("run").disabled = true;
  const r = await fetch("/api/analyze", { method: "POST", body: fd });
  $("run").disabled = false;
  if (!r.ok) { const e = await r.json(); $("status").textContent = e.detail; return; }
  lastResult = await r.json();
  $("status").textContent = `Done. ${lastResult.lots.length} lots analyzed.`;
  render(lastResult);
};

function render(res) {
  const banner = $("banner");
  banner.textContent = "DATA: " + res.data_mode.toUpperCase();
  banner.className = res.data_mode === "simulated" ? "sim" : "real";
  renderMap(res.lots);
  renderFactors(res.analysis);
  renderSpike(res.analysis.spike);
  renderScatter(res.lots, res.analysis.factors[0].name);
  renderWeather(res.lots[0]);
}

let map, layer;
function renderMap(lots) {
  if (!map) { map = L.map("map").setView([34, -119], 5);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
      { attribution: "© OpenStreetMap © CARTO" }).addTo(map); }
  if (layer) map.removeLayer(layer);
  layer = L.layerGroup().addTo(map);
  const max = Math.max(...lots.map((l) => l.defect_rate || 0), 0.0001);
  lots.forEach((l) => {
    const t = (l.defect_rate || 0) / max;
    // low defect = Titan navy, high defect = strawberry red
    const r = Math.round(6 + (188 - 6) * t);
    const g = Math.round(42 + (33 - 42) * t);
    const b = Math.round(70 + (51 - 70) * t);
    const color = `rgb(${r},${g},${b})`;
    L.circleMarker([l.lat, l.lon], { radius: 9, color: "#ffffff", weight: 2,
      fillColor: color, fillOpacity: 0.92 })
      .bindPopup(`<b>${esc(l.field_id)}</b><br>lot ${esc(l.lot_id)}<br>` +
                 `defect ${(100 * (l.defect_rate || 0)).toFixed(1)}%`)
      .on("click", () => renderWeather(l))
      .addTo(layer);
  });
}

function renderFactors(a) {
  const rows = a.factors.map((f) =>
    `<tr><td>${esc(f.name)}</td>
     <td>${esc(f.direction)}</td>
     <td>${f.std_effect.toFixed(4)}</td>
     <td>r=${f.corr.toFixed(2)} [${f.ci_low.toFixed(2)}, ${f.ci_high.toFixed(2)}]</td>
     <td class="${esc(f.confidence)}">${esc(f.confidence)}</td></tr>`).join("");
  let note = a.notes.map((n) => `<div class="note">${esc(n)}</div>`).join("");
  $("factors").innerHTML =
    `<table><tr><th>factor</th><th>dir</th><th>effect</th><th>corr (95% CI)</th>
     <th>confidence</th></tr>${rows}</table>${note}` +
    `<div class="caption">Effect ranks each factor's contribution holding others fixed; ` +
    `confidence reflects each factor's standalone correlation. They can differ when factors overlap.</div>`;
}

function renderSpike(s) {
  if (!s) { $("spike").textContent = "No multi-year data to assess a spike."; return; }
  const af = s.anomalous_factors.map((a) =>
    `<li>${esc(a.factor)}: ${a.z > 0 ? "+" : ""}${esc(a.z)}σ vs normal ` +
    `(${esc(a.spike_mean)} vs ${esc(a.overall_mean)})</li>`).join("");
  $("spike").innerHTML =
    `<p>Highest-defect year: <b>${esc(s.year)}</b> ` +
    `(mean defect ${(100 * s.defect_rate).toFixed(1)}%).</p>` +
    `<p>Conditions that were anomalous that year:</p><ul>${af || "<li>none ≥1σ</li>"}</ul>`;
}

function renderScatter(lots, factorName) {
  const x = lots.map((l) => l.features[factorName]);
  const y = lots.map((l) => 100 * (l.defect_rate || 0));
  Plotly.newPlot("scatter", [{
    x, y, mode: "markers", type: "scatter",
    marker: { size: 11, color: "#bc2133", line: { color: "#ffffff", width: 1.5 } },
    text: lots.map((l) => l.field_id),
  }], { paper_bgcolor: "#ffffff", plot_bgcolor: "#ffffff",
        font: { color: "#4a5d6e", family: "Inter, sans-serif" },
        margin: { t: 14, r: 14, b: 46, l: 52 },
        xaxis: { title: factorName, gridcolor: "#eef1f4", zerolinecolor: "#dde3e9" },
        yaxis: { title: "defect %", gridcolor: "#eef1f4", zerolinecolor: "#dde3e9" } },
    { displayModeBar: false });
}

function renderWeather(lot) {
  if (!lot) return;
  const d = lot.weather.map((w) => w.date);
  Plotly.newPlot("weather", [
    { x: d, y: lot.weather.map((w) => w.t2m_min), name: "T min",
      type: "scatter", line: { color: "#114a72", width: 2 } },
    { x: d, y: lot.weather.map((w) => w.t2m_max), name: "T max",
      type: "scatter", line: { color: "#bc2133", width: 2 } },
    { x: d, y: lot.weather.map((w) => w.precip_mm), name: "precip mm",
      type: "bar", marker: { color: "#9cc2dd" }, yaxis: "y2", opacity: 0.85 },
  ], { paper_bgcolor: "#ffffff", plot_bgcolor: "#ffffff",
       font: { color: "#4a5d6e", family: "Inter, sans-serif" },
       margin: { t: 64, r: 52, b: 40, l: 52 },
       title: { text: `${lot.field_id} · bloom window`,
                font: { color: "#062a46", size: 14 }, x: 0, xanchor: "left",
                y: 0.97, yanchor: "top" },
       legend: { orientation: "h", y: 1.08, x: 1, xanchor: "right" },
       xaxis: { gridcolor: "#eef1f4", zerolinecolor: "#dde3e9" },
       yaxis: { title: "°C", gridcolor: "#eef1f4", zerolinecolor: "#dde3e9" },
       yaxis2: { title: "mm", overlaying: "y", side: "right",
                 gridcolor: "rgba(0,0,0,0)" } },
     { displayModeBar: false });
}
