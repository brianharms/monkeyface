let lastResult = null;

const $ = (id) => document.getElementById(id);

// HTML-escape any value before interpolating into innerHTML / popup strings.
const esc = (s) => { const d = document.createElement("div"); d.textContent = String(s ?? ""); return d.innerHTML; };

// ---------------------------------------------------------------------------
// Mode switching: Analyze  <->  Format files
// ---------------------------------------------------------------------------
function setMode(mode) {
  const analyze = mode === "analyze";
  $("analyzeMode").hidden = !analyze;
  $("formatMode").hidden = analyze;
  $("tabAnalyze").classList.toggle("is-active", analyze);
  $("tabFormat").classList.toggle("is-active", !analyze);
}
$("tabAnalyze").onclick = () => setMode("analyze");
$("tabFormat").onclick = () => setMode("format");
$("goFormat").onclick = () => setMode("format");
// The real workflow starts at Step 1 (normalize & unify).
setMode("format");

// ---------------------------------------------------------------------------
// Analyze flow: pick a formatted file -> unlock step 2 -> analyze
// ---------------------------------------------------------------------------
let fileObjectUrl = null;
$("file").onchange = () => {
  const f = $("file").files[0];
  const link = $("fileLink");
  if (fileObjectUrl) { URL.revokeObjectURL(fileObjectUrl); fileObjectUrl = null; }
  if (!f) { link.hidden = true; $("step2").classList.add("is-locked"); $("run").disabled = true; return; }
  // Make the chosen file clickable to open in a new tab.
  fileObjectUrl = URL.createObjectURL(f);
  link.href = fileObjectUrl;
  link.textContent = "Open “" + f.name + "”";
  link.download = f.name;
  link.hidden = false;
  // Unlock step 2.
  $("step2").classList.remove("is-locked");
  $("run").disabled = false;
  $("status").textContent = "";
};

$("run").onclick = async () => {
  const f = $("file").files[0];
  if (!f) { $("status").textContent = "Choose a formatted file first."; return; }
  const fd = new FormData();
  fd.append("file", f);
  $("status").textContent = "Fetching each field's weather and analyzing… (the first run takes a few seconds)";
  $("run").disabled = true;
  $("run").textContent = "Analyzing…";
  const r = await fetch("/api/analyze", { method: "POST", body: fd });
  $("run").disabled = false;
  $("run").textContent = "Analyze fields";
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    $("status").innerHTML = "Couldn't analyze: " + esc(e.detail || "unknown error");
    return;
  }
  lastResult = await r.json();
  $("status").textContent = `Done — analyzed ${lastResult.lots.length} ${lastResult.lots.length === 1 ? "field" : "fields"}. Results are below.`;
  // Reveal results FIRST so the map/charts size themselves against a visible container.
  $("results").hidden = false;
  render(lastResult);
  $("results").scrollIntoView({ behavior: "smooth", block: "start" });
};

// ---------------------------------------------------------------------------
// Format flow: pick many raw files -> normalize -> download clean set
// ---------------------------------------------------------------------------
$("formatFiles").onchange = () => {
  $("runFormat").disabled = $("formatFiles").files.length === 0;
  $("formatResults").innerHTML = "";
  $("formatStatus").textContent = "";
};

$("runFormat").onclick = async () => {
  const files = $("formatFiles").files;
  if (!files.length) return;
  const fd = new FormData();
  for (const f of files) fd.append("files", f);
  $("runFormat").disabled = true;
  $("runFormat").textContent = "Working…";
  $("formatStatus").textContent =
    `Normalizing and unifying ${files.length} file${files.length === 1 ? "" : "s"}…`;
  const r = await fetch("/api/format", { method: "POST", body: fd });
  $("runFormat").disabled = false;
  $("runFormat").innerHTML = "Normalize &amp; unify";
  if (!r.ok) { $("formatStatus").textContent = "Something went wrong. Please try again."; return; }
  renderFormatResults(await r.json());
};

function renderFormatResults(res) {
  // Per-file breakdown (what cleaned, what couldn't be read).
  const fileRows = res.per_file.map((f) => {
    if (!f.ok) {
      return `<div class="fmt-row fmt-row--bad">
        <span class="fmt-name">${esc(f.name)}</span>
        <span class="fmt-detail fmt-error">${esc(f.error)}</span></div>`;
    }
    return `<div class="fmt-row">
      <span class="fmt-name">${esc(f.name)}</span>
      <span class="fmt-detail">${f.rows_out} row${f.rows_out === 1 ? "" : "s"} cleaned</span>
      <span class="fmt-ok">✓</span></div>`;
  }).join("");
  const fileList = `<div class="fmt-list">${fileRows}</div>`;

  // Blocking conflicts: same lot in two files with different data.
  if (res.conflicts && res.conflicts.length) {
    const items = res.conflicts.map((c) =>
      `<li><b>${esc(c.lot_id)}</b> appears in ${c.files.map(esc).join(", ")} with different data.</li>`
    ).join("");
    $("formatStatus").innerHTML =
      `<span class="fmt-block">Couldn't merge &mdash; ${res.conflicts.length} ` +
      `lot ID${res.conflicts.length === 1 ? "" : "s"} conflict across files.</span>`;
    $("formatResults").innerHTML = fileList +
      `<div class="fmt-conflict">
        <p>Each lot must be unique. These appear in more than one file with
           <em>different</em> values &mdash; fix them in your source files, then re-run:</p>
        <ul>${items}</ul></div>`;
    return;
  }

  if (!res.ok) {
    $("formatStatus").textContent = "No files could be formatted. Check the column names.";
    $("formatResults").innerHTML = fileList;
    return;
  }

  // Success: one unified master file to download.
  const href = "data:text/csv;base64," + res.csv_b64;
  $("formatStatus").innerHTML =
    `Unified <b>${res.total_rows}</b> lot${res.total_rows === 1 ? "" : "s"} from ` +
    `<b>${res.file_count}</b> file${res.file_count === 1 ? "" : "s"} into one master file.`;
  $("formatResults").innerHTML = fileList +
    `<div class="fmt-master">
      <a class="fmt-dl fmt-dl--master" href="${href}" download="master.csv">Download master.csv</a>
      <button type="button" class="link-button" id="masterToAnalyze">Go to Step 2 · Analyze &rarr;</button>
    </div>`;
  $("masterToAnalyze").onclick = () => {
    setMode("analyze");
    $("analyzeMode").scrollIntoView({ behavior: "smooth", block: "start" });
  };
}


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
  }], { paper_bgcolor: "#ffffff", plot_bgcolor: "#ffffff", autosize: true,
        font: { color: "#4a5d6e", family: "Inter, sans-serif" },
        margin: { t: 14, r: 14, b: 52, l: 56 },
        xaxis: { title: factorLabel(factorName), gridcolor: "#eef1f4", zerolinecolor: "#dde3e9" },
        yaxis: { title: "defect rate (%)", gridcolor: "#eef1f4", zerolinecolor: "#dde3e9" } },
    { displayModeBar: false, responsive: true });
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
  ], { paper_bgcolor: "#ffffff", plot_bgcolor: "#ffffff", autosize: true,
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
     { displayModeBar: false, responsive: true });
}
