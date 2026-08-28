function line(points, { w = 340, h = 180, pad = 28 } = {}) {
  if (!points || points.length < 2) return `<p class="skipped">No curve points.</p>`;
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs) || 1;
  const y0 = Math.min(0, ...ys);
  const y1 = Math.max(1, ...ys);
  const sx = (x) => pad + ((x - x0) / (x1 - x0 || 1)) * (w - 2 * pad);
  const sy = (y) => h - pad - ((y - y0) / (y1 - y0 || 1)) * (h - 2 * pad);
  const d = points.map((p, i) => `${i ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(" ");
  return `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img">
    <line x1="${pad}" y1="${h - pad}" x2="${w - pad}" y2="${h - pad}" stroke="#d0d0d0"/>
    <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${h - pad}" stroke="#d0d0d0"/>
    <path d="${d}" fill="none" stroke="#111" stroke-width="1.6"/>
  </svg>`;
}

export function rocChart(points) {
  const diag = "M28,152 L312,28";
  const svg = line(points);
  return svg.replace("</svg>", `<path d="${diag}" fill="none" stroke="#cfcfcf" stroke-dasharray="3 3"/></svg>`);
}

export function prChart(points) {
  return line(points);
}

export function calibrationChart(bins) {
  if (!bins || !bins.length) return `<p class="skipped">No calibration bins.</p>`;
  const points = bins.map((b) => ({ x: b.mean_predicted, y: b.observed_default }));
  const svg = line(points);
  return svg.replace("</svg>", `<path d="M28,152 L312,28" fill="none" stroke="#cfcfcf" stroke-dasharray="3 3"/></svg>`);
}

export function bandChart(bands) {
  if (!bands || !bands.length) return `<p class="skipped">No score bands.</p>`;
  const w = 340;
  const h = 180;
  const pad = 28;
  const n = bands.length;
  const bw = (w - 2 * pad) / n;
  const max = Math.max(...bands.map((b) => Math.max(b.mean_predicted, b.observed_default)), 0.01);
  const bars = bands
    .map((b, i) => {
      const x = pad + i * bw;
      const h1 = ((b.mean_predicted / max) * (h - 2 * pad));
      const h2 = ((b.observed_default / max) * (h - 2 * pad));
      return `<rect x="${x + 2}" y="${h - pad - h1}" width="${bw / 2 - 3}" height="${h1}" fill="#111"/>
        <rect x="${x + bw / 2}" y="${h - pad - h2}" width="${bw / 2 - 3}" height="${h2}" fill="#8f1d13"/>`;
    })
    .join("");
  return `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img"><line x1="${pad}" y1="${h - pad}" x2="${w - pad}" y2="${h - pad}" stroke="#d0d0d0"/>${bars}</svg>
    <p class="fineprint">Black = predicted default. Red = observed default.</p>`;
}
