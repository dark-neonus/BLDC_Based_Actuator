// Tiny helpers shared by the demos: slider binding and a canvas line plot.

function css(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// Bind a range input: shows formatted value in <span id="<id>_v"> and calls onChange.
function bindSlider(id, fmt, onChange) {
  const el = document.getElementById(id);
  const out = document.getElementById(id + "_v");
  const update = () => { if (out) out.textContent = fmt(+el.value); onChange(); };
  el.addEventListener("input", update);
  if (out) out.textContent = fmt(+el.value);
  return () => +el.value;
}

// Prepare a canvas for crisp drawing at device pixel ratio; returns {ctx, w, h}.
function setupCanvas(canvas, heightPx) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = heightPx || canvas.clientHeight || 260;
  canvas.style.height = h + "px";
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w, h };
}

/*
 plot(canvas, {
   height, xlabel, ylabel, xmin, xmax, ymin, ymax,
   series: [{ x: [...], y: [...], color: "--c1", label: "I", width: 2, dash: [] }],
   bands: [{ x0, x1, color: "rgba(...)" }],   // shaded vertical regions
   hlines: [{ y, color: "--bad", label }]
 })
*/
function plot(canvas, o) {
  const { ctx, w, h } = setupCanvas(canvas, o.height || 240);
  const m = { l: 52, r: 12, t: 12, b: 34 };
  const pw = w - m.l - m.r, ph = h - m.t - m.b;
  let xmin = o.xmin, xmax = o.xmax, ymin = o.ymin, ymax = o.ymax;
  const all = o.series || [];
  if (xmin === undefined) xmin = Math.min(...all.map(s => Math.min(...s.x)));
  if (xmax === undefined) xmax = Math.max(...all.map(s => Math.max(...s.x)));
  if (ymin === undefined || ymax === undefined) {
    let lo = Infinity, hi = -Infinity;
    all.forEach(s => s.y.forEach(v => { if (isFinite(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v); } }));
    (o.hlines || []).forEach(l => { lo = Math.min(lo, l.y); hi = Math.max(hi, l.y); });
    const pad = (hi - lo) * 0.08 || 1;
    if (ymin === undefined) ymin = lo - pad;
    if (ymax === undefined) ymax = hi + pad;
  }
  const X = x => m.l + (x - xmin) / (xmax - xmin) * pw;
  const Y = y => m.t + (1 - (y - ymin) / (ymax - ymin)) * ph;

  ctx.fillStyle = css("--panel"); ctx.fillRect(0, 0, w, h);
  (o.bands || []).forEach(b => {
    ctx.fillStyle = b.color;
    ctx.fillRect(X(b.x0), m.t, X(b.x1) - X(b.x0), ph);
  });
  // grid + ticks
  ctx.strokeStyle = css("--grid"); ctx.lineWidth = 1;
  ctx.fillStyle = css("--muted"); ctx.font = "11px system-ui, sans-serif";
  const ticks = (a, b, n) => { const s = niceStep((b - a) / n); const out = []; for (let v = Math.ceil(a / s) * s; v <= b + 1e-12; v += s) out.push(+v.toPrecision(10)); return out; };
  ticks(xmin, xmax, 6).forEach(v => {
    ctx.beginPath(); ctx.moveTo(X(v), m.t); ctx.lineTo(X(v), m.t + ph); ctx.stroke();
    ctx.textAlign = "center"; ctx.fillText(fmtNum(v), X(v), h - m.b + 14);
  });
  ticks(ymin, ymax, 5).forEach(v => {
    ctx.beginPath(); ctx.moveTo(m.l, Y(v)); ctx.lineTo(m.l + pw, Y(v)); ctx.stroke();
    ctx.textAlign = "right"; ctx.fillText(fmtNum(v), m.l - 6, Y(v) + 4);
  });
  ctx.strokeStyle = css("--border"); ctx.strokeRect(m.l, m.t, pw, ph);
  if (o.xlabel) { ctx.textAlign = "center"; ctx.fillText(o.xlabel, m.l + pw / 2, h - 4); }
  if (o.ylabel) { ctx.save(); ctx.translate(12, m.t + ph / 2); ctx.rotate(-Math.PI / 2); ctx.textAlign = "center"; ctx.fillText(o.ylabel, 0, 0); ctx.restore(); }

  ctx.save();
  ctx.beginPath(); ctx.rect(m.l, m.t, pw, ph); ctx.clip();
  (o.hlines || []).forEach(l => {
    ctx.strokeStyle = css(l.color || "--bad"); ctx.setLineDash([5, 4]); ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.moveTo(m.l, Y(l.y)); ctx.lineTo(m.l + pw, Y(l.y)); ctx.stroke();
    ctx.setLineDash([]);
    if (l.label) { ctx.fillStyle = css(l.color || "--bad"); ctx.textAlign = "left"; ctx.fillText(l.label, m.l + 4, Y(l.y) - 4); }
  });
  all.forEach(s => {
    ctx.strokeStyle = s.color.startsWith("--") ? css(s.color) : s.color;
    ctx.lineWidth = s.width || 2; ctx.setLineDash(s.dash || []);
    ctx.beginPath();
    for (let i = 0; i < s.x.length; i++) {
      const px = X(s.x[i]), py = Y(s.y[i]);
      i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
    }
    ctx.stroke(); ctx.setLineDash([]);
  });
  ctx.restore();
  // legend
  let lx = m.l + 8;
  all.filter(s => s.label).forEach(s => {
    ctx.fillStyle = s.color.startsWith("--") ? css(s.color) : s.color;
    ctx.fillRect(lx, m.t + 6, 12, 3);
    ctx.fillStyle = css("--text"); ctx.textAlign = "left";
    ctx.fillText(s.label, lx + 16, m.t + 11);
    lx += ctx.measureText(s.label).width + 34;
  });
  return { X, Y };
}

function niceStep(raw) {
  const p = Math.pow(10, Math.floor(Math.log10(raw)));
  const f = raw / p;
  return (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * p;
}
function fmtNum(v) {
  const a = Math.abs(v);
  if (a === 0) return "0";
  if (a >= 1000) return v.toFixed(0);
  if (a >= 10) return (+v.toFixed(1)).toString();
  if (a >= 0.1) return (+v.toFixed(2)).toString();
  return v.toPrecision(2);
}
// Engineering format with unit, e.g. eng(0.0025,"A") -> "2.5 mA"
function eng(v, unit, digits = 3) {
  if (!isFinite(v)) return "—";
  if (v === 0) return "0 " + unit;
  const a = Math.abs(v);
  const pre = [[1e9, "G"], [1e6, "M"], [1e3, "k"], [1, ""], [1e-3, "m"], [1e-6, "µ"], [1e-9, "n"], [1e-12, "p"]];
  for (const [s, p] of pre) {
    if (a >= s * 0.9999 || s === 1e-12) {
      let t = (v / s).toPrecision(digits);
      if (t.includes(".") && !t.includes("e")) t = t.replace(/\.?0+$/, "");
      return t + " " + p + unit;
    }
  }
}
window.addEventListener("resize", () => window.redraw && window.redraw());
