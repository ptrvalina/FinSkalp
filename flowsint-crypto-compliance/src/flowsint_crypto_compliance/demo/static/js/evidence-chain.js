/**
 * FinSkalp evidence-chain visualization — subject center, sources around,
 * line thickness = fusion contribution. Russian UI strings.
 */
(function (global) {
  const SOURCE_ICONS = {
    explorer_tag: "🔍",
    darknet_index: "🧅",
    abuse_registry: "⚠️",
    username_social: "👤",
    username: "👤",
    sanctions: "🚫",
    prior_case_match: "📂",
    telegram: "✈️",
    forum: "💬",
    web: "🌐",
    paste: "📋",
    otc_board: "🏦",
    leak: "💧",
    clearnet_dork: "🔎",
    correlation: "🔗",
    default: "◉",
  };

  function iconFor(sourceType) {
    return SOURCE_ICONS[sourceType] || SOURCE_ICONS.default;
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderSvg(data) {
    const subject = data.subject || data.address || "Субъект";
    const fusion = data.fusion || {};
    const explain = (fusion.explain || []).filter((c) => c.included_in_fusion);
    const w = 420;
    const h = 320;
    const cx = w / 2;
    const cy = h / 2;
    const r = 105;
    const nodes = explain.length ? explain : (data.mentions || []).slice(0, 8).map((m, i) => ({
      source_type: m.source_type,
      source_name: m.source_name,
      adjusted_confidence: m.confidence || 0.5,
      raw_confidence: m.confidence || 0.5,
      source_reliability: 0.6,
      included_in_fusion: true,
    }));

    let lines = "";
    let labels = "";
    nodes.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / Math.max(nodes.length, 1) - Math.PI / 2;
      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);
      const thick = 1 + (n.adjusted_confidence || 0.5) * 5;
      const st = n.source_type || "unknown";
      lines += `<line class="ev-chain-line" data-idx="${i}" x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="var(--accent,#38bdf8)" stroke-width="${thick}" stroke-opacity="0.85"/>`;
      labels += `<g class="ev-chain-node" data-idx="${i}" transform="translate(${x},${y})">
        <circle r="18" fill="var(--surface-container-high,#1e293b)" stroke="var(--border,#334155)"/>
        <text text-anchor="middle" dy="5" font-size="14">${iconFor(st)}</text>
        <title>${esc(st)} · ${esc(n.source_name || "")}</title>
      </g>`;
    });

    const pct = fusion.composite_pct ?? Math.round((fusion.composite_confidence || 0) * 100);
    return `<svg class="evidence-chain-svg" viewBox="0 0 ${w} ${h}" width="100%" height="auto" role="img" aria-label="Цепочка доказательств OSINT">
      ${lines}
      <circle cx="${cx}" cy="${cy}" r="28" fill="var(--primary,#0ea5e9)" opacity="0.2"/>
      <circle cx="${cx}" cy="${cy}" r="22" fill="var(--surface-container,#0f172a)" stroke="var(--primary,#0ea5e9)" stroke-width="2"/>
      <text x="${cx}" y="${cy - 4}" text-anchor="middle" font-size="10" fill="var(--muted,#94a3b8)">Субъект</text>
      <text x="${cx}" y="${cy + 10}" text-anchor="middle" font-size="11" font-weight="600" fill="var(--on-surface,#e2e8f0)">${pct}%</text>
      ${labels}
    </svg>`;
  }

  function explainHtml(node) {
    if (!node) return "<p class='summary-text'>Выберите источник на графе</p>";
    const raw = Math.round((node.raw_confidence || 0) * 100);
    const rel = Math.round((node.source_reliability || 0) * 100);
    const adj = Math.round((node.adjusted_confidence || 0) * 100);
    return `<div class="ev-chain-explain">
      <div><strong>${iconFor(node.source_type)} ${esc(node.source_type)}</strong> · ${esc(node.source_name || "")}</div>
      <p class="summary-text">raw ${raw}% × надёжность ${rel}% = <strong>${adj}%</strong></p>
      <p class="summary-text" style="font-size:0.75rem;color:var(--muted)">${esc(node.reason_ru || "Вклад в байесовскую fusion")}</p>
    </div>`;
  }

  function mount(containerId, data) {
    const el = document.getElementById(containerId);
    if (!el || !data) return;
    const explain = (data.fusion?.explain || []).filter((c) => c.included_in_fusion);
    const nodes = explain.length ? explain : [];
    el.innerHTML = `
      <div class="ev-chain-wrap">
        <h4 class="font-label-caps">Цепочка доказательств · fusion ${data.fusion?.composite_pct ?? 0}%</h4>
        <div class="ev-chain-grid">
          <div id="${containerId}-svg">${renderSvg(data)}</div>
          <div id="${containerId}-panel" class="ev-chain-panel"></div>
        </div>
      </div>`;
    const panel = document.getElementById(`${containerId}-panel`);
    const svg = el.querySelector(".evidence-chain-svg");
    if (panel) panel.innerHTML = explainHtml(nodes[0]);
    svg?.querySelectorAll(".ev-chain-line, .ev-chain-node").forEach((item) => {
      item.style.cursor = "pointer";
      item.addEventListener("click", () => {
        const idx = Number(item.getAttribute("data-idx"));
        if (panel) panel.innerHTML = explainHtml(nodes[idx]);
      });
    });
  }

  async function mountFromApi(containerId, investigationId, apiBase) {
    const base = apiBase || "";
    try {
      const r = await fetch(`${base}/api/osint/fusion-explain/${encodeURIComponent(investigationId)}`);
      if (!r.ok) throw new Error("fusion explain unavailable");
      const data = await r.json();
      mount(containerId, {
        subject: data.subject,
        fusion: data.fusion,
        mentions: data.mentions,
      });
      return data;
    } catch (e) {
      const el = document.getElementById(containerId);
      if (el) el.innerHTML = `<p class="summary-text" style="color:var(--muted)">Цепочка доказательств: ${esc(e.message)}</p>`;
      return null;
    }
  }

  function findingCardHtml(f) {
    const st = f.source_type || (f.code || "").replace("open_osint_", "") || "unknown";
    const prior = f.priority_flag === "PRIOR_CASE_MATCH" || f.code === "prior_case_match";
    const cls = prior ? "osint-finding-card prior-case-match" : "osint-finding-card";
    const conf = Math.round((f.confidence || 0) * 100);
    const ev = f.preserved_evidence || f.evidence_snapshot;
    const preview = ev?.screenshot_path
      ? `<button type="button" class="btn btn-outline btn-sm" onclick="FinSkalpEvidenceChain.previewEvidence(${JSON.stringify(ev)})">🖼 Снимок</button>`
      : "";
    return `<div class="${cls}">
      <div class="osint-finding-head">${iconFor(st)} <strong>${esc(f.title_ru || st)}</strong>${prior ? ' <span class="prior-badge">PRIOR CASE MATCH</span>' : ""}</div>
      <p class="summary-text" style="font-size:0.78rem">${esc(f.description_ru || "")}</p>
      <div class="summary-text" style="font-size:0.72rem;color:var(--muted)">уверенность ${conf}% · ${esc(st)}</div>
      ${preview}
    </div>`;
  }

  function previewEvidence(ev) {
    const url = ev.snapshot_api_url || ev.screenshot_path;
    if (!url) {
      global.toast?.("Снимок недоступен");
      return;
    }
    const w = window.open("", "_blank", "width=900,height=700");
    if (!w) return;
    w.document.write(`<html><head><title>Снимок доказательства</title></head><body style="margin:0;background:#111;color:#eee;font-family:sans-serif">
      <p style="padding:8px;font-size:12px">${esc(ev.report_link_ru || ev.discovery_at || "")}</p>
      ${ev.screenshot_path ? `<img src="file://${esc(ev.screenshot_path)}" style="max-width:100%" onerror="this.alt='PNG локально: ${esc(ev.screenshot_sha256 || "")}'"/>` : ""}
      <pre style="padding:8px;font-size:11px;white-space:pre-wrap">${esc(JSON.stringify(ev, null, 2))}</pre>
    </body></html>`);
  }

  function renderTimeline(events) {
    if (!events?.length) return "<p class='summary-text' style='color:var(--muted)'>Нет событий continuous OSINT</p>";
    return `<ul class="osint-timeline">${events.map((e) =>
      `<li><span class="mono">${esc(e.scanned_at || e.at || "")}</span> · ${esc(e.address?.slice(0, 14) || "")}… · ${e.mentions_count ?? 0} находок · fusion ${e.fusion?.composite_pct ?? "—"}%</li>`
    ).join("")}</ul>`;
  }

  global.FinSkalpEvidenceChain = {
    iconFor,
    mount,
    mountFromApi,
    findingCardHtml,
    previewEvidence,
    renderTimeline,
    renderSvg,
  };
})(typeof window !== "undefined" ? window : globalThis);
