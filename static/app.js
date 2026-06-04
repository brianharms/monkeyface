// Canonical field key -> the plain-language name shown to the user.
const CANONICAL_LABELS = {
  lot_id: "Lot ID",
  field_id: "Field name",
  lat: "Latitude",
  lon: "Longitude",
  harvest_date: "Harvest date",
  defect_rate: "Defect rate",
  grower: "Grower",
  variety: "Variety",
};
const CANONICAL = Object.keys(CANONICAL_LABELS);
let lastResult = null;

const $ = (id) => document.getElementById(id);

// HTML-escape any value before interpolating into innerHTML / popup strings.
const esc = (s) => { const d = document.createElement("div"); d.textContent = String(s ?? ""); return d.innerHTML; };

$("loadCols").onclick = async () => {
  const f = $("file").files[0];
  if (!f) { $("status").textContent = "Please choose a file in Step 1 first."; return; }
  $("loadCols").disabled = true;
  $("loadCols").textContent = "Reading…";
  const fd = new FormData(); fd.append("file", f);
  const r = await fetch("/api/columns", { method: "POST", body: fd });
  $("loadCols").disabled = false;
  $("loadCols").innerHTML = "Continue&nbsp;&rarr;";
  if (!r.ok) { $("status").textContent = "Sorry — we couldn't read that file. Is it a CSV or Excel file?"; return; }
  const { columns } = await r.json();
  buildMapping(columns);
  // Unlock steps 2 and 3 now that there's something to map and run.
  $("step2").classList.remove("is-locked");
  $("step3").classList.remove("is-locked");
  $("run").disabled = false;
  $("step2").scrollIntoView({ behavior: "smooth", block: "nearest" });
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
    const opts = ['<option value="">— ignore this column —</option>']
      .concat(CANONICAL.map((cn) =>
        `<option value="${cn}" ${guess(col) === cn ? "selected" : ""}>${CANONICAL_LABELS[cn]}</option>`))
      .join("");
    return `<div class="mapping-row"><label title="${esc(col)}">${esc(col)}</label>
            <span class="mapping-row__arrow">&rarr;</span>
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
  $("status").textContent = "Fetching each field's weather and analyzing… (the first run takes a few seconds)";
  $("run").disabled = true;
  $("run").textContent = "Analyzing…";
  const r = await fetch("/api/analyze", { method: "POST", body: fd });
  $("run").disabled = false;
  $("run").textContent = "Analyze fields";
  if (!r.ok) { const e = await r.json(); $("status").textContent = "Couldn't analyze: " + (e.detail || "unknown error"); return; }
  lastResult = await r.json();
  $("status").textContent = `Done — analyzed ${lastResult.lots.length} ${lastResult.lots.length === 1 ? "field" : "fields"}. Results are below.`;
  // Reveal results FIRST so the map/charts size themselves against a visible container.
  $("results").hidden = false;
  render(lastResult);
  $("results").scrollIntoView({ behavior: "smooth", block: "start" });
};

function render(res) {
  const banner = $("banner");
  banner.textContent = "Data: " + (res.data_mode === "simulated" ? "Simulated" : "Real");
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
  const pts = [];
  lots.forEach((l) => {
    const t = (l.defect_rate || 0) / max;
    // low defect = Titan navy, high defect = strawberry red
    const r = Math.round(6 + (188 - 6) * t);
    const g = Math.round(42 + (33 - 42) * t);
    const b = Math.round(70 + (51 - 70) * t);
    const color = `rgb(${r},${g},${b})`;
    pts.push([l.lat, l.lon]);
    L.circleMarker([l.lat, l.lon], { radius: 9, color: "#ffffff", weight: 2,
      fillColor: color, fillOpacity: 0.92 })
      .bindPopup(`<b>${esc(l.field_id)}</b><br>lot ${esc(l.lot_id)}<br>` +
                 `defect ${(100 * (l.defect_rate || 0)).toFixed(1)}%`)
      .on("click", () => renderWeather(l))
      .addTo(layer);
  });
  // Container may have just become visible — recompute size and frame all fields.
  setTimeout(() => {
    map.invalidateSize();
    if (pts.length) map.fitBounds(pts, { padding: [40, 40], maxZoom: 8 });
  }, 60);
}

// Plain-language names for the weather features.
const FACTOR_LABELS = {
  cold_nights: "Cold nights",
  heat_spike_days: "Hot days",
  bloom_rain_days: "Rainy days in bloom",
  gdd: "Total warmth (growing degree-days)",
  mean_rh: "Humidity",
  diurnal_swing: "Day-to-night temp swing",
  mean_wind: "Wind",
};
const factorLabel = (name) => FACTOR_LABELS[name] || name.replace(/_/g, " ");

// Map confidence -> a 0-5 "strength" dot rating and a plain label.
function strengthDots(f) {
  const r = Math.abs(f.corr);
  const filled = Math.max(0, Math.min(5, Math.round(r * 5)));
  return "●".repeat(filled) + "○".repeat(5 - filled);
}
const CONF_LABEL = { strong: "Strong", suggestive: "Possible", weak: "Unclear" };

function renderFactors(a) {
  const rows = a.factors.map((f) => {
    const pushes = f.direction === "increases"
      ? `<span class="dir-up">▲ more defects</span>`
      : f.direction === "decreases"
      ? `<span class="dir-down">▼ fewer defects</span>`
      : `<span class="dir-none">— no clear effect</span>`;
    const statTip = esc(
      `effect ${f.std_effect.toFixed(3)} · correlation r=${f.corr.toFixed(2)} ` +
      `(95% CI ${f.ci_low.toFixed(2)} to ${f.ci_high.toFixed(2)})`);
    return `<tr title="${statTip}">
      <td class="f-name">${esc(factorLabel(f.name))}</td>
      <td>${pushes}</td>
      <td class="f-strength" title="${statTip}">${strengthDots(f)}</td>
      <td class="${esc(f.confidence)}">${esc(CONF_LABEL[f.confidence] || f.confidence)}</td></tr>`;
  }).join("");

  const note = a.notes.map((n) => `<div class="note">${esc(n)}</div>`).join("");

  $("factors").innerHTML =
    `<table class="factor-table">
       <tr>
         <th>Condition</th>
         <th title="The direction the defect rate moves when this condition is higher.">Effect on defects</th>
         <th title="How tightly this condition tracks the defect rate. More filled dots = a tighter relationship (correlation strength).">Strength</th>
         <th title="Whether the relationship is statistically solid given how few fields there are. Strong = confident; Possible = a hint; Unclear = not enough signal.">How sure</th>
       </tr>${rows}
     </table>${note}` +
    `<div class="caption">Hover any heading (or a row) for the underlying statistics. ` +
    `&ldquo;Strength&rdquo; is how closely a condition tracks the defect on its own; ` +
    `the ranking accounts for overlap between conditions, so the two can differ.</div>`;
}

function renderSpike(s) {
  if (!s) {
    $("spike").innerHTML = `<p class="spike-empty">Your data only covers one year, so there's no
      earlier "normal" to compare against. Add fields from more years to check whether a spike
      was foreseeable.</p>`;
    return;
  }
  const af = s.anomalous_factors.map((a) =>
    `<li><b>${esc(factorLabel(a.factor))}</b> was ${a.z > 0 ? "unusually high" : "unusually low"}
     that year (${esc(a.spike_mean)} vs. a typical ${esc(a.overall_mean)}).</li>`).join("");
  $("spike").innerHTML =
    `<p>The worst year was <b>${esc(s.year)}</b>, with an average defect rate of
     ${(100 * s.defect_rate).toFixed(1)}%.</p>` +
    (af
      ? `<p>What was unusual about that year's weather:</p><ul>${af}</ul>`
      : `<p>That year's weather wasn't notably unusual in any single condition &mdash; so this
         defect spike doesn't look like it was driven by one obvious weather anomaly.</p>`);
}

function renderScatter(lots, factorName) {
  const x = lots.map((l) => l.features[factorName]);
  const y = lots.map((l) => 100 * (l.defect_rate || 0));
  Plotly.newPlot("scatter", [{
    x, y, mode: "markers", type: "scatter",
    marker: { size: 11, color: "#bc2133", line: { color: "#ffffff", width: 1.5 } },
    text: lots.map((l) => l.field_id),
    hovertemplate: "%{text}<br>" + factorLabel(factorName) + ": %{x}<br>defect: %{y:.1f}%<extra></extra>",
  }], { paper_bgcolor: "#ffffff", plot_bgcolor: "#ffffff",
        font: { color: "#4a5d6e", family: "Inter, sans-serif" },
        margin: { t: 14, r: 14, b: 52, l: 56 },
        xaxis: { title: factorLabel(factorName), gridcolor: "#eef1f4", zerolinecolor: "#dde3e9" },
        yaxis: { title: "defect rate (%)", gridcolor: "#eef1f4", zerolinecolor: "#dde3e9" } },
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
