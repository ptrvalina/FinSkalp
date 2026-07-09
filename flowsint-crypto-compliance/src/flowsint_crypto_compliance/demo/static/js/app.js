const API = "";
let selectedId = null;
let investigating = false;
let currentView = "dashboard";
let registryTab = "banks";
let feedEs = null;
let platformCache = null;
let combatMode = false;
let osintCollectorsCache = null;
let msCache = null;
let selectedMsId = null;
let finskalpRunning = false;
let fusionRunning = false;
const kpiPrev = { kpiInst: null, kpiTps: null };

function prefersReducedMotion() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;
}

function easeOutExpo(t) {
  return t >= 1 ? 1 : 1 - Math.pow(2, -10 * t);
}

function animateKpiValue(el, from, to, formatFn, duration = 600) {
  if (!el || from === to) {
    if (el && formatFn) el.textContent = formatFn(to);
    return;
  }
  if (prefersReducedMotion()) {
    el.textContent = formatFn(to);
    return;
  }
  const wrap = el.closest(".kpi");
  wrap?.classList.add("kpi-counting", "kpi-updated");
  const start = performance.now();
  const tick = (now) => {
    const p = easeOutExpo(Math.min(1, (now - start) / duration));
    const v = from + (to - from) * p;
    el.textContent = formatFn(v);
    if (p < 1) requestAnimationFrame(tick);
    else {
      wrap?.classList.remove("kpi-counting");
      setTimeout(() => wrap?.classList.remove("kpi-updated"), duration);
    }
  };
  requestAnimationFrame(tick);
}

function updateKpiInst(text) {
  const el = document.getElementById("kpiInst");
  if (!el) return;
  const m = String(text).match(/^(\d+)\/(\d+)$/);
  if (!m) { el.textContent = text; return; }
  const online = Number(m[1]);
  const total = m[2];
  const prev = kpiPrev.kpiInst ?? online;
  kpiPrev.kpiInst = online;
  animateKpiValue(el, prev, online, (v) => `${Math.round(v)}/${total}`);
}

function updateKpiTps(text) {
  const el = document.getElementById("kpiTps");
  if (!el) return;
  const m = String(text).match(/^([\d.]+)/);
  if (!m) { el.textContent = text; return; }
  const val = Number(m[1]);
  const suffix = text.slice(m[0].length);
  const prev = kpiPrev.kpiTps ?? val;
  kpiPrev.kpiTps = val;
  animateKpiValue(el, prev, val, (v) => {
    const n = Number.isInteger(val) ? Math.round(v) : Math.round(v * 10) / 10;
    return `${n}${suffix}`;
  });
}

function staggerWorkspaceCards(root) {
  if (!root || prefersReducedMotion()) return;
  const cards = root.querySelectorAll(".mega-card, .section, .osint-source-card, .platform-card, .partner-card, .cis-node");
  cards.forEach((card, i) => {
    card.classList.remove("motion-stagger-1", "motion-stagger-2", "motion-stagger-3", "motion-stagger-4", "motion-stagger-5");
    card.classList.add(`motion-stagger-${(i % 5) + 1}`);
  });
}

const VIEW_IDS = {
  dashboard: "viewDashboard",
  wallet: "viewWallet",
  osint: "viewOsint",
  microservices: "viewMicroservices",
  platform: "viewPlatform",
  ops: "viewOps",
  instruments: "viewInstruments",
  registries: "viewRegistries",
  reports: "viewReports",
};

const PIPELINE_LABELS = {
  new: "Новые",
  triage: "Триаж",
  investigating: "В работе",
  pending_filing: "К подаче",
  filed_mtd: "Подано (мес.)",
};

const WORKFLOW_STEPS = [
  { id: "new", label: "Новое" },
  { id: "triage", label: "Триаж" },
  { id: "investigating", label: "Расследование" },
  { id: "pending_filing", label: "К подаче" },
  { id: "filed", label: "Подано" },
  { id: "archived", label: "Архив" },
];

const WORKFLOW_NEXT = {
  new: [{ status: "triage", label: "→ Триаж", primary: true }],
  triage: [
    { status: "investigating", label: "▶ Расследование", primary: true },
    { status: "archived", label: "Архив" },
  ],
  investigating: [
    { status: "pending_filing", label: "К подаче", primary: false },
    { status: "triage", label: "← Триаж" },
  ],
  pending_filing: [
    { status: "filed", label: "✓ Подано 115-ФЗ", primary: true },
    { status: "investigating", label: "← Доработка" },
  ],
  filed: [{ status: "archived", label: "В архив", primary: true }],
  archived: [],
};

let opsFeedEs = null;
let workflowAssignees = [];

function sk(rows = 4, cols = 3) {
  return window.FinSkalpUI?.skeletonHtml(rows, cols) || "";
}

function loadingHtml(rows, cols, text, sub) {
  return `<div class="ic-running">${sk(rows, cols)}${text ? `<div class="ic-progress">${text}</div>` : ""}${sub ? `<div class="ic-progress-sub">${sub}</div>` : ""}</div>`;
}

function showSkeleton(elId, rows = 4, cols = 3) {
  const el = document.getElementById(elId);
  if (el) el.innerHTML = sk(rows, cols);
}

const SOURCE_TYPE_RU = {
  domestic: "Суверенный",
  technical: "Технический",
  operational: "Оперативный",
  sovereign: "Суверенный реестр",
  open: "Открытый OSINT",
};

async function refreshAll() {
  await Promise.all([loadDashboard(), loadInbox(), pollWatchlistBadge()]);
  if (currentView === "reports") loadReportsRegistry();
}

async function pollWatchlistBadge() {
  try {
    const d = await fetch(`${API}/api/kyt/watchlist`).then((r) => r.json());
    const n = d.count ?? (d.addresses?.length ?? 0);
    document.querySelectorAll("[data-watchlist-badge]").forEach((el) => {
      el.textContent = String(n);
      el.hidden = !n;
    });
  } catch {
    /* ignore */
  }
}

async function loadDashboard() {
  const megaEl = document.getElementById("megaStats");
  if (megaEl && !megaEl.dataset.hydrated && window.FinSkalpUI) {
    megaEl.innerHTML = FinSkalpUI.skeletonHtml(2, 4);
  }
  try {
    const [d, platform] = await Promise.all([
      fetch(`${API}/api/dashboard`).then(r => r.json()),
      fetch(`${API}/api/platform`).then(r => r.json()),
    ]);

    updateKpiInst(`${d.institutions_online}/${d.institutions_connected}`);
    const live = d.data_source === "live";
    const screens = d.transactions_screened_session ?? d.wallet_screens ?? 0;
    updateKpiTps(live
      ? `${d.screening_tps || 0} т/с · live`
      : `${d.screening_tps} т/с`);
    ["kpiInst", "kpiTps"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.classList.remove("kpi-pulse");
      void el.offsetWidth;
      el.classList.add("kpi-pulse");
    });
    if (live && document.getElementById("orgName")) {
      document.getElementById("orgName").textContent =
        "FinSkalp · LIVE · on-chain KPI · 115-ФЗ";
    }

    document.getElementById("megaStats").innerHTML = live ? `
      <div class="mega-card accent"><div class="mega-v">${screens}</div><div class="mega-k">Скринингов · сессия</div></div>
      <div class="mega-card"><div class="mega-v">${(d.str_received ?? d.hub_messages_24h ?? 0).toLocaleString("ru")}</div><div class="mega-k">СОО / STR · сессия</div></div>
      <div class="mega-card"><div class="mega-v">${(d.investigations_session ?? 0).toLocaleString("ru")}</div><div class="mega-k">Расследований · live</div></div>
      <div class="mega-card"><div class="mega-v">${(d.graph_nodes_session ?? 0).toLocaleString("ru")}</div><div class="mega-k">Узлов в графах · сессия</div></div>
      <div class="mega-card"><div class="mega-v">${d.avg_decision_ms || "—"}${d.avg_decision_ms ? "мс" : ""}</div><div class="mega-k">Средняя задержка решения</div></div>
      <div class="mega-card crit"><div class="mega-v">${d.critical_queue}</div><div class="mega-k">Критичные · в очереди</div></div>
      <div class="mega-card"><div class="mega-v">${d.cases_active}</div><div class="mega-k">Активных дел</div></div>
      <div class="mega-card"><div class="mega-v">${(d.kyt_alerts ?? d.corridors_monitored ?? 0)}</div><div class="mega-k">Live KYT · алерты</div></div>` : `
      <div class="mega-card accent"><div class="mega-v">${d.transactions_screened_24h_m}M</div><div class="mega-k">Транзакций проверено · 24ч</div></div>
      <div class="mega-card"><div class="mega-v">${d.sar_messages_24h.toLocaleString("ru")}</div><div class="mega-k">СОО / STR · 24ч</div></div>
      <div class="mega-card"><div class="mega-v">${d.vasp_otc_flagged.toLocaleString("ru")}</div><div class="mega-k">VASP/OTC · под риском</div></div>
      <div class="mega-card"><div class="mega-v">${d.wallets_in_graph_m}M</div><div class="mega-k">Кошельков · граф расследований</div></div>
      <div class="mega-card"><div class="mega-v">${d.avg_decision_ms}мс</div><div class="mega-k">Средняя задержка решения</div></div>
      <div class="mega-card crit"><div class="mega-v">${d.critical_queue}</div><div class="mega-k">Критичные · в очереди</div></div>
      <div class="mega-card"><div class="mega-v">${d.cases_active}</div><div class="mega-k">Активных расследований</div></div>
      <div class="mega-card"><div class="mega-v">${d.false_positive_rate_pct}%</div><div class="mega-k">Доля ложных срабатываний</div></div>`;

    const pipe = d.case_pipeline || {};
    document.getElementById("casePipeline").innerHTML = Object.entries(PIPELINE_LABELS).map(([key, label]) => {
      const v = pipe[key] ?? 0;
      const colors = { new: "var(--accent)", triage: "#6366f1", investigating: "#0891b2", pending_filing: "var(--gold)", filed_mtd: "var(--low)" };
      return `
      <div class="funnel-step">
        <div class="funnel-bar" style="width:${Math.min(100, (v / (pipe.investigating || 1)) * 60 + 20)}%;background:${colors[key]}"></div>
        <span class="funnel-label">${label}</span><span class="funnel-val">${v?.toLocaleString?.("ru") ?? v}</span>
      </div>`;
    }).join("");

    const modules = await fetch(`${API}/api/platform/modules`).then(r => r.json());
    document.getElementById("slaGrid").innerHTML = modules.filter(m => m.ic_code !== "—").slice(0, 4).map(m => `
      <div class="sla-item"><span>${esc(m.code)}</span><span class="sla-pct">${m.sla_pct}%</span></div>`).join("");

    document.getElementById("partnersGrid").innerHTML = (platform.integrations || []).map(p => `
      <div class="partner-card ${p.status}">
        <div class="partner-name">${esc(p.name)}</div>
        <div class="partner-products">${(p.products_ru || p.products || []).map(esc).join(" · ")}</div>
        <div class="partner-mode">${esc(p.mode_ru || p.mode || "")}</div>
        <span class="partner-status">${p.status === "connected" ? "● Подключено" : "◆ Нативный паритет"}</span>
      </div>`).join("");

    const cis = await fetch(`${API}/api/cis`).then(r => r.json());
    document.getElementById("cisMap").innerHTML = cis.map(c => `
      <div class="cis-node ${c.status}">
        <div class="cis-code">${esc(c.code)}</div>
        <div class="cis-name">${esc(c.name_ru)}</div>
        <div class="cis-meta">${c.entities ? c.entities.toLocaleString("ru") + " субъектов" : "транзит"}</div>
        <div class="cis-fiu">${esc(c.fiu)}</div>
      </div>`).join("");
    if (megaEl) megaEl.dataset.hydrated = "1";
    staggerWorkspaceCards(document.getElementById("viewDashboard"));
  } catch {}
}

function focusWalletInput() {
  setTimeout(() => document.getElementById("walletAddress")?.focus(), 50);
}

async function screenWallet() {
  const input = document.getElementById("walletAddress");
  const chain = document.getElementById("walletChain")?.value || "";
  const btn = document.getElementById("btnWalletScreen");
  const out = document.getElementById("walletResult");
  const address = (input?.value || "").trim();

  if (!address) {
    toast("Введите адрес кошелька");
    input?.focus();
    return;
  }

  btn.disabled = true;
  btn.textContent = "Проверка…";
  out.innerHTML = loadingHtml(4, 2, "Проверяем адрес, on-chain окружение и KYT-контекст…");

  try {
    const resp = await fetch(`${API}/api/wallet/screen`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address, chain: chain || null, depth: 1, limit: 50 }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Ошибка проверки");
    out.innerHTML = renderWalletScreening(data);
    toast(`Проверка завершена · риск ${Math.round(data.risk_score)}/100`);
  } catch (e) {
    out.innerHTML = `<div class="empty-state" style="color:var(--critical)"><h2>Проверка не выполнена</h2><p>${esc(String(e.message || e))}</p></div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "▶ Проверить кошелёк";
  }
}

function renderWalletScreening(data) {
  const risk = (data.risk_level || "unknown").toLowerCase();
  const sourceRows = Object.entries(data.source_status || {}).map(([k, v]) =>
    `<div class="source-row"><span>${esc(k)}</span><span>${esc(v)}</span></div>`).join("");
  const findings = (data.findings || []).map(f => `
    <div class="finding-card severity-${esc(f.severity || "low")}">
      <div class="finding-head"><span>${esc(f.code || "FINDING")}</span><b>${esc(f.severity || "low")}</b></div>
      <h4>${esc(f.title_ru || "")}</h4>
      <p>${esc(f.description_ru || "")}</p>
      ${f.evidence ? `<div class="mono finding-evidence">${esc(f.evidence)}</div>` : ""}
    </div>`).join("") || `<div class="empty-mini">Критичных признаков не найдено</div>`;
  const evidence = (data.evidence_chain || []).map(e => `<li>${esc(e)}</li>`).join("");
  const recs = (data.recommendations_ru || []).map(r => `<li>${esc(r)}</li>`).join("");
  const limitations = (data.limitations_ru || []).map(r => `<li>${esc(r)}</li>`).join("");
  const onchain = data.onchain_summary || {};
  const riskModel = onchain.risk_model || {};
  const xgbBlock = riskModel.model_version ? `
      <div class="section xgb-panel">
        <h4>XGBoost · ${esc(riskModel.model_version)}</h4>
        <div class="metrics">
          <div class="metric"><div class="v">${Math.round(riskModel.heuristic_score || 0)}</div><div class="k">Эвристика</div></div>
          <div class="metric"><div class="v">${Math.round(riskModel.model_score || 0)}</div><div class="k">Модель</div></div>
          <div class="metric"><div class="v">${Math.round(data.risk_score || 0)}</div><div class="k">Итог</div></div>
        </div>
      </div>` : "";

  return `
    <div class="wallet-result">
      <div class="wallet-result-head">
        <div>
          <div class="mono wallet-id">${esc(data.screening_id)}</div>
          <h2>${esc(data.chain)} · ${esc(shortAddress(data.address))}</h2>
        </div>
        <div class="score risk-${risk}">
          <div class="num">${Math.round(data.risk_score || 0)}</div>
          <div class="lbl">${riskLabel(risk)}</div>
        </div>
      </div>
      <p class="summary-text">${esc(data.summary_ru)}</p>
      <div class="metrics">
        <div class="metric"><div class="v">${Math.round((data.confidence || 0) * 100)}%</div><div class="k">Уверенность</div></div>
        <div class="metric"><div class="v">${onchain.inbound_count ?? 0}</div><div class="k">Входящие</div></div>
        <div class="metric"><div class="v">${onchain.outbound_count ?? 0}</div><div class="k">Исходящие</div></div>
        <div class="metric"><div class="v">${onchain.counterparties ?? 0}</div><div class="k">Контрагенты</div></div>
      </div>
      ${xgbBlock}
      <div class="section"><h4>Findings</h4>${findings}</div>
      <div class="section"><h4>Evidence chain</h4><ul class="legal-list">${evidence}</ul></div>
      <div class="section"><h4>Статус источников</h4><div class="source-grid">${sourceRows}</div></div>
      <div class="section"><h4>Рекомендации</h4><ul class="legal-list">${recs}</ul></div>
      <div class="section"><h4>Ограничения безопасности</h4><ul class="legal-list">${limitations}</ul></div>
    </div>`;
}

function shortAddress(addr) {
  if (!addr || addr.length <= 18) return addr || "";
  return `${addr.slice(0, 10)}…${addr.slice(-6)}`;
}

async function loadScenariosForOsint() {
  const sel = document.getElementById("osintScenario");
  if (!sel || sel.dataset.loaded) return;
  try {
    const items = await fetch(`${API}/api/scenarios`).then(r => r.json());
    sel.innerHTML = `<option value="">— авто по адресу —</option>` +
      items.map(s => `<option value="${esc(s.id)}">${esc(s.title_ru)}</option>`).join("");
    sel.dataset.loaded = "1";
  } catch {}
}

async function quickRiskScore() {
  const address = (document.getElementById("fsAddress")?.value || "").trim();
  const chain = document.getElementById("fsChain")?.value || "";
  const out = document.getElementById("fsQuickScore");
  if (!address) {
    toast("Введите адрес для Quick Score");
    return;
  }
  out.textContent = "…";
  try {
    const q = chain ? `?chain=${encodeURIComponent(chain)}` : "";
    const data = await fetch(`${API}/api/v1/score/${encodeURIComponent(address)}${q}`).then(async (r) => {
      if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
      return r.json();
    });
    const cls = (data.risk_level || "medium").toLowerCase();
    out.innerHTML = `<span class="risk-${cls}" style="font-weight:700">${Math.round(data.risk_score)}</span> · ${data.latency_ms} мс`;
    toast(`Score ${data.risk_score} · ${data.summary_ru?.slice(0, 60) || ""}`);
  } catch (e) {
    out.textContent = "ошибка";
    toast(`Score API: ${e.message || e}`);
  }
}

async function loadOsintCollectors() {
  const grid = document.getElementById("osintCollectors");
  if (!grid || grid.dataset.loaded) return;
  try {
    const data = await fetch(`${API}/api/scalpel/collectors`).then(r => r.json());
    osintCollectorsCache = data.collectors || [];
    grid.innerHTML = osintCollectorsCache.map(c => {
      const disabled = c.selectable === false;
      const checked = !disabled && c.default_checked !== false;
      const hot = c.hot ? " 🔥" : "";
      const cat = (c.category || "osint").toUpperCase();
      const statusNote = c.status === "works" ? "" : ` · ${c.status_ru || c.status}`;
      return `
      <label class="osint-collector-chip${checked ? " selected" : ""}${disabled ? " disabled" : ""}" data-id="${esc(c.id)}" title="${esc((c.legal_basis_ru || "") + statusNote)}">
        <input type="checkbox" name="osintCollector" value="${esc(c.id)}" ${checked ? "checked" : ""} ${disabled ? "disabled" : ""} />
        <span>
          <span class="name">${esc(c.name_ru)}${c.category === "darknet" ? " 🧅" : ""}${hot}</span>
          <span class="id">${esc(cat)} · ${esc(c.status || "—")}</span>
        </span>
      </label>`;
    }).join("");
    grid.querySelectorAll(".osint-collector-chip:not(.disabled)").forEach(chip => {
      chip.addEventListener("click", (ev) => {
        if (ev.target.tagName === "INPUT") {
          chip.classList.toggle("selected", ev.target.checked);
          return;
        }
        const cb = chip.querySelector("input");
        if (cb.disabled) return;
        cb.checked = !cb.checked;
        chip.classList.toggle("selected", cb.checked);
      });
    });
    grid.dataset.loaded = "1";
  } catch {
    grid.innerHTML = `<div class="empty-state">Не удалось загрузить коллекторы</div>`;
  }
}

function selectAllOsintCollectors(on) {
  document.querySelectorAll('input[name="osintCollector"]:not(:disabled)').forEach(cb => {
    cb.checked = on;
    cb.closest(".osint-collector-chip")?.classList.toggle("selected", on);
  });
}

function getSelectedOsintCollectors() {
  const ids = [...document.querySelectorAll('input[name="osintCollector"]:checked')].map(cb => cb.value);
  return ids.length ? ids : null;
}

async function loadOsintCenter() {
  showSkeleton("osintStatus", 1, 4);
  showSkeleton("osintSources", 3, 3);
  showSkeleton("osintPipeline", 5, 1);
  await Promise.all([loadScenariosForOsint(), loadOsintCollectors()]);
  const [status, sources, pipeline] = await Promise.all([
    fetch(`${API}/api/osint/status`).then(r => r.json()),
    fetch(`${API}/api/osint/sources`).then(r => r.json()),
    fetch(`${API}/api/osint/pipeline`).then(r => r.json()),
  ]);

  document.getElementById("osintStatus").innerHTML = `
    <div class="osint-stat"><span class="k">ФинСкальп</span><span class="v ok">Работает</span></div>
    <div class="osint-stat"><span class="k">Fusion Engine</span><span class="v ok">${status.fusion_engine === "operational" ? "Работает" : status.fusion_engine}</span></div>
    <div class="osint-stat"><span class="k">Источников</span><span class="v">${status.sources_active}</span></div>
    <div class="osint-stat"><span class="k">Реестр 115-ФЗ</span><span class="v">${status.registry_labels_loaded ?? "—"} меток</span></div>
    <div class="osint-stat"><span class="k">Live API</span><span class="v">${status.live_chain_apis ? "Вкл." : "Выкл. (demo+live)"}</span></div>
    <div class="osint-stat"><span class="k">PostgreSQL</span><span class="v ok">${status.postgres_required ? "Нужен" : "Не нужен"}</span></div>
    <div class="osint-stat"><span class="k">Суверенный режим</span><span class="v ok">${status.sovereign_mode ? "Вкл." : "Выкл."}</span></div>`;

  document.getElementById("osintSources").innerHTML = sources.map(s => `
    <div class="osint-source-card type-${s.type}">
      <div class="osc-head">
        <span class="osc-priority">P${s.priority}</span>
        <span class="osc-type">${SOURCE_TYPE_RU[s.type] || s.type}</span>
      </div>
      <h4>${esc(s.name_ru)}</h4>
      <p>${esc(s.description_ru)}</p>
      <div class="osc-meta">
        <span>${s.records_24h?.toLocaleString("ru")} записей/24ч</span>
        <span>Доверие: ${Math.round((s.trust_weight || 0) * 100)}%</span>
      </div>
    </div>`).join("");

  document.getElementById("osintPipeline").innerHTML = pipeline.map((p, i) => `
    <div class="osint-pipe-step" id="osint-step-${p.step}">
      <span class="pipe-num">${i + 1}</span>
      <span class="pipe-label">${esc(p.label_ru)}</span>
      <span class="pipe-status" id="pipe-status-${p.step}">—</span>
    </div>`).join("");
}

function getSelectedScenario() {
  const v = document.getElementById("osintScenario")?.value;
  return v || "p2p_rub_offshore";
}

function collectFinSkalpPayload() {
  const amountRaw = document.getElementById("fsAmount")?.value;
  const collectors = getSelectedOsintCollectors();
  return {
    address: (document.getElementById("fsAddress")?.value || "").trim(),
    chain: document.getElementById("fsChain")?.value || null,
    tx_hash: (document.getElementById("fsTxHash")?.value || "").trim() || null,
    bank_reference: (document.getElementById("fsBankRef")?.value || "").trim() || null,
    bank_name: (document.getElementById("fsBankName")?.value || "").trim() || null,
    subject_id: (document.getElementById("fsSubject")?.value || "").trim() || null,
    amount: amountRaw ? Number(amountRaw) : null,
    currency: "RUB",
    notes: (document.getElementById("fsNotes")?.value || "").trim() || null,
    scenario_id: document.getElementById("osintScenario")?.value || null,
    depth: Number(document.getElementById("fsOnchainDepth")?.value || 2),
    osint_depth: Number(document.getElementById("fsOsintDepth")?.value || 2),
    collectors,
  };
}

function renderScalpelResult(data) {
  const statusRows = Object.entries(data.source_status || {}).map(
    ([k, v]) => `<li><span class="mono">${esc(k)}</span> · ${esc(v)}</li>`
  ).join("");
  return `
    <div class="osint-result finskalp-result">
      <div class="osint-result-head">
        <h3>Scalpel · ${esc(data.address)}</h3>
        <div class="score risk-${data.open_risk_score >= 70 ? "high" : "medium"}">
          <div class="num">${Math.round(data.open_risk_score || 0)}</div>
          <div class="lbl">Open-risk</div>
        </div>
      </div>
      <p class="summary-text">Depth ${data.osint_depth ?? "—"} · коллекторов: ${(data.collectors_run || []).length} · веток: ${(data.branch_targets || []).length}</p>
      <div class="section"><h4>Статус инструментов</h4><ul class="legal-list">${statusRows || "<li>—</li>"}</ul></div>
      <div class="section"><h4>Darknet / .onion (Ahmia)</h4>
        <ul class="legal-list">${(data.mentions || []).filter(m => (m.source_type || "").includes("darknet") || (m.risk_tag || "").includes("darknet")).slice(0, 8).map(m =>
          `<li>[${esc(m.source_name)}] ${esc(m.title_ru)} — ${esc((m.excerpt_ru || "").slice(0, 100))}</li>`
        ).join("") || "<li>Совпадений в darknet-индексе не найдено (live scan выполнен)</li>"}</ul>
      </div>
      <div class="section"><h4>Сигналы (${data.mentions_count ?? 0})</h4>
        <ul class="legal-list">${(data.mentions || []).slice(0, 12).map(m =>
          `<li>[${esc(m.source_type)}] ${esc(m.title_ru)} — ${esc((m.excerpt_ru || "").slice(0, 90))}</li>`
        ).join("") || "<li>Упоминаний не найдено</li>"}</ul>
      </div>
      ${(data.branch_targets || []).length ? `<div class="section"><h4>2-hop ветки</h4><p class="mono">${data.branch_targets.map(esc).join(", ")}</p></div>` : ""}
    </div>`;
}

async function runScalpelSelected() {
  const address = (document.getElementById("fsAddress")?.value || "").trim();
  if (!address) {
    toast("Введите криптоадрес");
    document.getElementById("fsAddress")?.focus();
    return;
  }
  const collectors = getSelectedOsintCollectors();
  if (collectors && collectors.length === 0) {
    toast("Выберите хотя бы один OSINT-инструмент");
    return;
  }
  const btn = document.getElementById("btnScalpelOnly");
  const out = document.getElementById("osintOutput");
  btn.disabled = true;
  btn.textContent = "Scalpel…";
  out.innerHTML = loadingHtml(4, 2, "Scalpel · выбранные коллекторы…", `depth ${document.getElementById("fsOsintDepth")?.value || 2}`);
  try {
    const body = {
      address,
      chain: document.getElementById("fsChain")?.value || "tron",
      depth: Number(document.getElementById("fsOsintDepth")?.value || 2),
      onchain_depth: Number(document.getElementById("fsOnchainDepth")?.value || 2),
      collectors,
    };
    const data = await fetch(`${API}/api/scalpel/collect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(async r => {
      if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
      return r.json();
    });
    out.innerHTML = renderScalpelResult(data);
    toast(`Scalpel: ${data.mentions_count ?? 0} сигналов`);
  } catch (e) {
    out.innerHTML = `<div class="empty-state" style="color:var(--critical)">${esc(String(e.message || e))}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Scalpel · выбранные инструменты";
  }
}

function renderSarBlock(sar) {
  if (!sar?.evidence_sections?.length) return "";
  const indicators = (sar.suspicion_indicators || []).map(i =>
    `<tr><td>${esc(i.article_ru)}</td><td>${esc(i.indicator_ru)}</td><td>${esc(i.confirmed)}</td><td>${esc(i.source)}</td></tr>`
  ).join("");
  const sections = (sar.evidence_sections || []).map(s =>
    `<div class="sar-section"><h5>${esc(s.title_ru)}</h5><ul class="legal-list">${
      (s.items || []).slice(0, 6).map(it => `<li>${esc(String(it))}</li>`).join("")
    }</ul></div>`
  ).join("");
  const rp = sar.risk_profile || {};
  const dec = sar.decision || {};
  return `
    <div class="section sar-block" id="sarReportBlock">
      <h4>SAR · структурированный отчёт · 115-ФЗ</h4>
      <p class="summary-text">${esc(sar.narrative_ru || sar.executive_summary_ru || "")}</p>
      <div class="metrics">
        <div class="metric"><div class="v">${rp.composite_score ?? "—"}</div><div class="k">Композит</div></div>
        <div class="metric"><div class="v">${rp.wallet_score ?? "—"}</div><div class="k">Скрининг</div></div>
        <div class="metric"><div class="v">${rp.fusion_score ?? "—"}</div><div class="k">Fusion</div></div>
        <div class="metric"><div class="v">${dec.str_recommended ? "да" : "нет"}</div><div class="k">SAR/СПО</div></div>
      </div>
      <div class="sar-subsection"><h5>Признаки подозрительности</h5>
        <table class="data-table"><thead><tr><th>Основание</th><th>Индикатор</th><th>Подтв.</th><th>Источник</th></tr></thead>
        <tbody>${indicators || "<tr><td colspan=4>—</td></tr>"}</tbody></table>
      </div>
      <div class="sar-subsection"><h5>Доказательная база</h5>${sections}</div>
      <p class="summary-text"><strong>Решение:</strong> ${esc(dec.decision_ru || "—")}</p>
      <ul class="legal-list">${(dec.recommended_actions_ru || []).map(a => `<li>${esc(a)}</li>`).join("")}</ul>
    </div>`;
}

function renderFinSkalpResult(data) {
  const risk = (data.risk_level || "medium").toLowerCase();
  const fr = data.fusion_report || {};
  const attachments = (data.attachments || []).map(a =>
    `<a class="btn btn-primary" style="display:inline-block;margin:0.25rem 0.5rem 0.25rem 0" href="${API}${a.url}" target="_blank" download>⬇ ${esc(a.title_ru)}</a>`
  ).join("");
  return `
    <div class="osint-result finskalp-result">
      <div class="osint-result-head">
        <h3>ФинСкальп · ${esc(data.case_ref)}</h3>
        <div class="score risk-${risk}">
          <div class="num">${Math.round(data.risk_score || 0)}</div>
          <div class="lbl">Risk Score</div>
        </div>
      </div>
      <p class="summary-text mono">${esc(data.address)} · ${esc(data.chain)}</p>
      <p class="summary-text">${esc(data.summary_ru || "")}</p>
      <button type="button" class="btn btn-outline btn-sm" style="margin-bottom:0.5rem" onclick="addToKytWatchlist(${JSON.stringify(data.address)})">📡 Добавить в KYT watchlist</button>
      <p class="summary-text"><strong>Композит:</strong> ${esc(data.composite_risk || "—")} · ${data.duration_ms} мс</p>
      <div class="section"><h4>Открытый OSINT</h4>
        <p class="summary-text">${esc(
          "Scalpel · depth " + (data.open_osint?.osint_depth ?? "—")
          + " · " + (data.open_osint?.mentions_count ?? 0) + " сигналов · "
          + (data.open_osint?.collectors_run?.length ?? 0) + " инстр. · fusion "
          + (data.open_osint?.fusion_confidence?.composite_pct ?? "—") + "% · отсев "
          + (data.open_osint?.noise_filter?.rejected_count ?? 0) + " · open-risk "
          + (data.open_osint?.open_risk_score ?? 0) + "/100"
        )}</p>
        <div id="evidenceChainMount" class="ev-chain-mount"></div>
        <div class="connection-grid" style="margin-top:0.5rem">${(data.screening?.findings || []).filter(f => String(f.code||"").startsWith("open_osint") || f.code === "prior_case_match").slice(0, 6).map(f =>
          (window.FinSkalpEvidenceChain?.findingCardHtml || ((x) => `<div>${esc(x.title_ru)}</div>`))(f)).join("") || ""}</div>
        <ul class="legal-list">${(data.open_osint?.mentions || []).slice(0, 8).map(m =>
          `<li>${window.FinSkalpEvidenceChain?.iconFor?.(m.source_type) || "◉"} [${esc(m.source_type)}] ${esc(m.title_ru)} — ${esc(m.excerpt_ru?.slice(0, 80) || "")}</li>`).join("") || "<li>Упоминаний не найдено</li>"}</ul>
      </div>
      <div class="section"><h4>Вложения (PDF/HTML)</h4>${attachments || "—"}</div>
      ${renderSarBlock(data.sar_report)}
      <div class="section"><h4>Фазы расследования</h4>
        ${(data.phases || []).map(s => `<div class="step done"><div class="step-icon">✓</div><div><div class="step-label">${esc(s.label_ru)}</div><div class="step-detail">${esc(s.detail_ru || "")}</div></div></div>`).join("")}
      </div>
      <div class="section"><h4>Live Fusion · multi-hop</h4>
        ${data.live_fusion?.node_count ? `
        <div class="metrics">
          <div class="metric"><div class="v">${data.live_fusion.node_count}</div><div class="k">Узлов</div></div>
          <div class="metric"><div class="v">${data.live_fusion.edge_count}</div><div class="k">Рёбер</div></div>
          <div class="metric"><div class="v">${Math.round(data.live_fusion.ml_score?.score || 0)}</div><div class="k">ML Score</div></div>
          <div class="metric"><div class="v">${data.live_fusion.corridor_flagged ? "⚠" : "✓"}</div><div class="k">Corridor</div></div>
        </div>
        <ul class="legal-list">${(data.live_fusion.risk_annotations || []).slice(0, 6).map(a =>
          `<li>[hop ${a.hop ?? "—"}] ${esc(a.address || a.reason_ru || a.type)}</li>`).join("") || "<li>Флагов нет</li>"}</ul>
        <button type="button" class="btn btn-outline btn-sm" onclick="scrollToInvestigationGraph()">↗ Открыть интерактивный граф</button>
        <p class="summary-text" style="font-size:0.72rem;color:var(--muted)">Тот же fusion-граф — в секции 8 forensic PDF · zoom, drag, клик по узлу</p>` : `<p class="summary-text">Live fusion не запускался (демо-адрес или сценарий)</p>`}
      </div>
      <div class="section"><h4>Граф · связь с forensic §8</h4>
        ${(() => {
          const lf = data.live_fusion || {};
          const nodes = lf.node_count ?? fr.evidence_graph?.nodes ?? "—";
          const edges = lf.edge_count ?? fr.evidence_graph?.edges ?? "—";
          const fusionScore = lf.ml_score?.score ?? fr.illegal_flow_score ?? 0;
          return `<div class="metrics">
          <div class="metric"><div class="v">${nodes}</div><div class="k">Узлов</div></div>
          <div class="metric"><div class="v">${edges}</div><div class="k">Рёбер</div></div>
          <div class="metric"><div class="v">${Math.round(fusionScore)}</div><div class="k">Fusion</div></div>
        </div>`;
        })()}
        ${data.live_fusion?.node_count ? `<button type="button" class="btn btn-outline btn-sm" onclick="scrollToInvestigationGraph()">↗ Интерактивный граф</button>` : ""}
      </div>
      <div class="section"><h4>Ключевые выводы</h4>
        <ul class="legal-list">${((data.forensic_report?.executive_summary?.key_findings_ru) || []).map(h => `<li>${esc(h)}</li>`).join("")}</ul>
      </div>
    </div>`;
  if (data?.investigation_id && window.FinSkalpEvidenceChain) {
    requestAnimationFrame(() => {
      FinSkalpEvidenceChain.mountFromApi("evidenceChainMount", data.investigation_id, API);
    });
  }
}

function scrollToInvestigationGraph() {
  const gw = document.getElementById("graphWorkspace");
  if (!gw) return;
  gw.classList.remove("hidden");
  gw.setAttribute("aria-hidden", "false");
  gw.classList.remove("motion-reveal");
  void gw.offsetWidth;
  gw.classList.add("motion-reveal");
  gw.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
  const mount = document.getElementById("forceGraphMount");
  if (mount) mount.focus?.({ preventScroll: true });
}

function mountInvestigationGraph(data) {
  const gw = document.getElementById("graphWorkspace");
  const fusion = data?.live_fusion || data?.graph_viz;
  if (FinSkalpGraph?.hasGraphData?.(fusion)) {
    gw?.classList.remove("hidden");
    gw?.setAttribute("aria-hidden", "false");
    gw?.classList.remove("motion-reveal");
    void gw?.offsetWidth;
    gw?.classList.add("motion-reveal");
    requestAnimationFrame(() => {
      FinSkalpGraph.mount("forceGraphMount", fusion, {
        mlScore: fusion.ml_score?.score,
        investigationId: data?.investigation_id,
        apiBase: API,
      });
    });
  } else {
    FinSkalpGraph?.destroy({ containerId: "forceGraphMount" });
    gw?.classList.remove("motion-reveal");
    gw?.setAttribute("aria-hidden", "true");
  }
}

async function addToKytWatchlist(address) {
  if (!address) return;
  try {
    const r = await fetch(`${API}/api/kyt/watchlist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || r.statusText);
    toast(`KYT watchlist · ${shortAddress(d.address)} · всего ${d.watchlist_size}`);
    pollWatchlistBadge();
  } catch (e) {
    toast(`Watchlist: ${e.message || e}`);
  }
}

async function runFinSkalpInvestigation() {
  if (finskalpRunning) return;
  const payload = collectFinSkalpPayload();
  if (!payload.address) {
    toast("Введите криптоадрес");
    document.getElementById("fsAddress")?.focus();
    return;
  }
  if (payload.collectors && payload.collectors.length === 0) {
    toast("Выберите хотя бы один OSINT-инструмент");
    return;
  }
  finskalpRunning = true;
  const btn = document.getElementById("btnFinSkalp");
  const out = document.getElementById("osintOutput");
  btn.disabled = true;
  btn.textContent = "Расследование…";
  const phaseHints = [
    "Валидация адреса и сети…",
    "Скрининг · реестр 115-ФЗ…",
    "On-chain · загрузка транзакций (один запрос)…",
    "Открытый OSINT · Telegram / форумы / TronScan…",
    "OSINT Fusion · граф доказательств…",
    "Суверенная атрибуция РФ/СНГ…",
    "Детектор рисков + XGBoost…",
    "Формирование PDF-отчётов…",
  ];
  let phaseIdx = 0;
  const renderProgress = (hint) => {
    out.innerHTML = `<div class="ic-running">${FinSkalpUI?.skeletonHtml(5, 2) || ""}<div class="ic-progress">${esc(hint)}</div><div class="ic-progress-sub">Live TRON: 1–5 мин · демо TRU_HUB_MSK — мгновенно</div></div>`;
  };
  renderProgress(phaseHints[0]);
  const progressTimer = setInterval(() => {
    phaseIdx = Math.min(phaseIdx + 1, phaseHints.length - 1);
    const el = out.querySelector(".ic-progress");
    if (el) el.textContent = phaseHints[phaseIdx];
  }, 2200);
  const timeoutMs = Number(window.FINSKALP_INVESTIGATE_TIMEOUT_MS) || 300000;
  const abort = new AbortController();
  const abortTimer = setTimeout(() => abort.abort(), timeoutMs);
  try {
    const data = await fetch(`${API}/api/finskalp/investigate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: abort.signal,
    }).then(async r => {
      if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
      return r.json();
    });
    (data.phases || []).forEach(s => {
      const el = document.getElementById(`pipe-status-${s.id}`);
      if (el) { el.textContent = "✓"; el.className = "pipe-status done"; }
    });
    out.innerHTML = renderFinSkalpResult(data);
    mountInvestigationGraph(data);
    toast(`ФинСкальп · ${data.case_ref}`);
  } catch (e) {
    const msg = e.name === "AbortError"
      ? `Превышено время ожидания (${Math.round(timeoutMs / 1000)} с). Live-адрес с TronGrid и всеми Scalpel-инструментами может занимать несколько минут — подождите или снимите лишние коллекторы.`
      : String(e.message || e);
    out.innerHTML = `<div class="empty-state" style="color:var(--critical)">${esc(msg)}</div>`;
  } finally {
    clearInterval(progressTimer);
    clearTimeout(abortTimer);
    finskalpRunning = false;
    btn.disabled = false;
    btn.textContent = "▶ Запустить расследование ФинСкальп";
  }
}

async function uploadOcrDocument() {
  const input = document.getElementById("ocrFile");
  const backend = document.getElementById("ocrBackend")?.value || "auto";
  const btn = document.getElementById("btnOcr");
  const out = document.getElementById("ocrResult");
  const file = input?.files?.[0];
  if (!file) {
    toast("Выберите файл PDF или изображение");
    return;
  }
  btn.disabled = true;
  btn.textContent = "OCR…";
  out.innerHTML = loadingHtml(3, 2, "Извлечение текста и полей изъятия…");
  try {
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`${API}/api/ocr/extract?backend=${encodeURIComponent(backend)}`, {
      method: "POST",
      body: form,
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "OCR failed");
    const wallets = (data.seizure_fields?.wallets || data.entities?.crypto_addresses || [])
      .map(w => typeof w === "string" ? w : w.address).filter(Boolean);
    out.innerHTML = `
      <div class="finding-card severity-${data.suitable_for_seizure_report ? "high" : "low"}">
        <h4>${esc(file.name)} · ${esc(data.backend)} · conf ${Math.round((data.confidence || 0) * 100)}%</h4>
        <p>${esc((data.full_text_preview || "").slice(0, 600))}</p>
        ${wallets.length ? `<div class="mono">Кошельки: ${wallets.map(esc).join(", ")}</div>` : ""}
        ${(data.warnings || []).length ? `<ul class="legal-list">${data.warnings.map(w => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}
      </div>`;
    toast(data.suitable_for_seizure_report ? "Готово для отчёта изъятия" : "OCR завершён");
  } catch (e) {
    out.innerHTML = `<div class="empty-state" style="color:var(--critical)">${esc(String(e.message || e))}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "▶ OCR извлечение";
  }
}

async function runOsintFusion() {
  if (combatMode) {
    toast("Live-режим: используйте «Полный цикл расследования» по адресу");
    return;
  }
  if (fusionRunning) return;
  fusionRunning = true;
  const btn = document.getElementById("btnOsintFusion");
  const scenario = getSelectedScenario();
  btn.disabled = true;
  btn.textContent = "Fusion выполняется…";
  const out = document.getElementById("osintOutput");
  out.innerHTML = loadingHtml(5, 2, `OSINT Fusion · демо-сценарий ${esc(scenario)}…`, "Без адреса · только пресет сценария");

  const abort = new AbortController();
  const abortTimer = setTimeout(() => abort.abort(), 35000);
  try {
    const resp = await fetch(`${API}/api/osint/fusion`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_id: scenario }),
      signal: abort.signal,
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || resp.statusText);

    (data.steps || []).forEach(s => {
      const el = document.getElementById(`pipe-status-${s.id}`);
      if (el) {
        el.textContent = s.status === "done" ? "✓" : "…";
        el.className = `pipe-status ${s.status}`;
      }
    });

    const r = data.report || {};
    const risk = (r.risk_level || "medium").toLowerCase();
    const xgb = (r.metrics?.risk_scoring?.xgboost) || {};
    const xgbHtml = xgb.model_version ? `
        <div class="section xgb-panel">
          <h4>XGBoost · ${esc(xgb.model_version)}</h4>
          <div class="metrics">
            <div class="metric"><div class="v">${Math.round(r.metrics?.risk_scoring?.heuristic_score || 0)}</div><div class="k">Эвристика</div></div>
            <div class="metric"><div class="v">${Math.round(xgb.model_score || 0)}</div><div class="k">Модель</div></div>
            <div class="metric"><div class="v">${Math.round(xgb.blended_score || r.illegal_flow_score || 0)}</div><div class="k">Итог</div></div>
          </div>
        </div>` : "";
    out.innerHTML = `
      <div class="osint-result">
        <div class="osint-result-head">
          <h3>Результат OSINT Fusion</h3>
          <div class="score risk-${risk}">
            <div class="num">${Math.round(r.illegal_flow_score || 0)}</div>
            <div class="lbl">Индекс риска</div>
          </div>
        </div>
        <p class="summary-text">${esc(data.summary_ru)}</p>
        ${xgbHtml}
        <div class="section"><h4>Ключевые доказательства</h4>
          <ul class="legal-list">${(data.evidence_highlights_ru || []).map(h => `<li>${esc(h)}</li>`).join("")}</ul>
        </div>
        <div class="section"><h4>Шаги конвейера</h4>
          ${(data.steps || []).map(s => `<div class="step done"><div class="step-icon">✓</div><div><div class="step-label">${esc(s.label_ru)}</div><div class="step-detail">${esc(s.detail_ru || "")}</div></div></div>`).join("")}
        </div>
        <div class="section"><h4>Граф доказательств</h4>
          <div class="metrics">
            <div class="metric"><div class="v">${r.evidence_graph?.nodes ?? "—"}</div><div class="k">Узлов</div></div>
            <div class="metric"><div class="v">${r.evidence_graph?.edges ?? "—"}</div><div class="k">Рёбер</div></div>
            <div class="metric"><div class="v">${(data.sources_used || []).length}</div><div class="k">Источников</div></div>
          </div>
        </div>
        <p class="summary-text">${esc(r.executive_summary_ru || "")}</p>
      </div>`;
    toast("OSINT Fusion завершён");
  } catch (e) {
    const msg = e.name === "AbortError"
      ? "Fusion: превышено время ожидания (35 с)."
      : String(e.message || e);
    out.innerHTML = `<div class="empty-state" style="color:var(--critical)">${esc(msg)}</div>`;
  } finally {
    clearTimeout(abortTimer);
    fusionRunning = false;
    btn.disabled = false;
    btn.textContent = "Fusion по сценарию";
  }
}

async function loadMicroservices() {
  showSkeleton("msSummary", 1, 2);
  showSkeleton("msMeshStats", 1, 4);
  showSkeleton("msServiceList", 6, 1);
  const [services, mesh] = await Promise.all([
    fetch(`${API}/api/microservices`).then(r => r.json()),
    fetch(`${API}/api/microservices/mesh`).then(r => r.json()),
  ]);
  msCache = services;

  document.getElementById("msSummary").textContent =
    `${mesh.total_services} сервисов · кластер OSINT: ${mesh.osint_cluster_size} · healthy: ${mesh.healthy}/${mesh.total_services}`;

  document.getElementById("msMeshStats").innerHTML = Object.entries(mesh.layers || {}).map(([layer, items]) => `
    <div class="ms-layer-stat">
      <span class="ms-layer-name">${esc(layer)}</span>
      <span class="ms-layer-count">${items.length}</span>
    </div>`).join("");

  const byLayer = {};
  services.forEach(s => {
    byLayer[s.layer_label_ru] = byLayer[s.layer_label_ru] || [];
    byLayer[s.layer_label_ru].push(s);
  });

  document.getElementById("msServiceList").innerHTML = Object.entries(byLayer).map(([layer, items]) => `
    <div class="ms-layer-group">
      <div class="ms-layer-head">${esc(layer)} <span>${items.length}</span></div>
      ${items.map(s => `
        <div class="ms-service-row ${selectedMsId === s.id ? "active" : ""} ${s.layer === "osint" ? "osint-svc" : ""}"
          onclick="selectMicroservice('${s.id}')">
          <div class="ms-svc-name">${esc(s.name_ru)}</div>
          <div class="ms-svc-meta">
            <span class="status-${s.status}">${s.status === "healthy" ? "●" : "◆"}</span>
            <span>${s.replicas} repl</span>
            <span>${s.latency_ms}мс</span>
          </div>
        </div>`).join("")}
    </div>`).join("");

  if (!selectedMsId && services[0]) selectMicroservice(services[0].id, false);
}

async function selectMicroservice(id, runDefault = true) {
  selectedMsId = id;
  document.querySelectorAll(".ms-service-row").forEach(el => el.classList.remove("active"));
  document.querySelector(`.ms-service-row[onclick*="${id}"]`)?.classList.add("active");

  const svc = (msCache || []).find(s => s.id === id);
  const detail = document.getElementById("msDetail");
  if (!svc) return;

  detail.innerHTML = `
    <div class="ms-detail-card">
      <div class="ms-detail-head">
        <div>
          <span class="ms-id mono">${esc(svc.id)}</span>
          <h2>${esc(svc.name_ru)}</h2>
        </div>
        <span class="ms-status status-${svc.status}">${svc.status === "healthy" ? "Работает" : svc.status}</span>
      </div>
      <p>${esc(svc.description_ru)}</p>
      <div class="metrics">
        <div class="metric"><div class="v">${svc.replicas}</div><div class="k">Реплики</div></div>
        <div class="metric"><div class="v">${svc.latency_ms}мс</div><div class="k">Latency</div></div>
        <div class="metric"><div class="v">${svc.uptime_pct}%</div><div class="k">Uptime</div></div>
        <div class="metric"><div class="v">${esc(svc.tech)}</div><div class="k">Стек</div></div>
      </div>
      ${svc.depends_on?.length ? `<div class="section"><h4>Зависимости</h4><div class="cap-tags">${svc.depends_on.map(d => `<span class="cap-tag mono">${esc(d)}</span>`).join("")}</div></div>` : ""}
      ${svc.ic_code ? `<div class="section"><h4>Инструмент</h4><span class="cap-tag">${esc(svc.ic_code)}</span></div>` : ""}
      <button class="btn btn-primary" id="btnMsRun" onclick="runMicroservice('${svc.id}')">▶ Запустить сервис</button>
      <div id="msRunOutput"></div>
    </div>`;

  if (runDefault && svc.layer === "osint" && svc.id === "ms-osint-fusion") {
    runMicroservice(id);
  }
}

async function runMicroservice(id) {
  const btn = document.getElementById("btnMsRun");
  const outEl = document.getElementById("msRunOutput");
  if (btn) { btn.disabled = true; btn.textContent = "Выполняется…"; }
  outEl.innerHTML = loadingHtml(3, 2);

  try {
    const scenario = getSelectedScenario();
    const data = await fetch(`${API}/api/microservices/${encodeURIComponent(id)}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_id: scenario }),
    }).then(r => r.json());
    outEl.innerHTML = `
      <div class="ms-run-result">
        <h4>Результат выполнения</h4>
        <p class="summary-text">${esc(data.summary_ru)}</p>
        ${data.scenario_id ? `<p class="summary-text mono">Сценарий: ${esc(data.scenario_id)}</p>` : ""}
        <div class="metrics">${Object.entries(data.metrics || {}).map(([k, v]) =>
          `<div class="metric"><div class="v">${typeof v === "number" ? v.toLocaleString("ru") : esc(String(v))}</div><div class="k">${esc(k)}</div></div>`).join("")}</div>
        <div class="section"><h4>Журнал</h4>${(data.log_ru || []).map(l => `<div class="log-line">${esc(l)}</div>`).join("")}</div>
      </div>`;
    toast(`Сервис выполнен · ${data.latency_ms}мс`);
  } catch (e) {
    outEl.innerHTML = `<div style="color:var(--critical)">${esc(String(e))}</div>`;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "▶ Запустить сервис"; }
  }
}

async function loadPlatformSuite() {
  showSkeleton("platformGrid", 4, 3);
  if (!platformCache) platformCache = await fetch(`${API}/api/platform/modules`).then(r => r.json());
  document.getElementById("platformGrid").innerHTML = platformCache.map(m => `
    <div class="platform-card">
      <div class="pc-head">
        <span class="pc-code">${esc(m.code)}</span>
        <span class="pc-sla">${m.sla_pct}% SLA</span>
      </div>
      <h3>${esc(m.name_ru)}</h3>
      <div class="pc-parity">${esc(m.capability_tag_ru)}</div>
      <p>${esc(m.description_ru)}</p>
      <div class="pc-caps">${(m.capabilities_ru || []).map(c => `<span class="cap-tag">${esc(c)}</span>`).join("")}</div>
      ${m.ic_code !== "—" ? `<button class="btn-run-ic" onclick="runInstrument('${m.ic_code}')">Запустить модуль</button>` : `<span class="pc-native">Нативный · ${esc(m.suite_ru)}</span>`}
    </div>`).join("");
}

function startLiveFeed() {
  if (feedEs) return;
  feedEs = new EventSource(`${API}/api/feed/live`);
  feedEs.onmessage = (ev) => handleLiveFeedEvent(ev);
}

function startOpsLiveFeed() {
  if (opsFeedEs) return;
  if (feedEs) {
    opsFeedEs = feedEs;
    return;
  }
  startLiveFeed();
  opsFeedEs = feedEs;
}

function handleLiveFeedEvent(ev) {
  let data;
  try { data = JSON.parse(ev.data); } catch { return; }
  appendFeedRow("liveFeed", data);
  appendFeedRow("opsLiveFeed", data);
  const sev = data.severity || "info";
  const isCase = data.type === "case_new" || data.type === "case_transition" || data.type === "case_investigation_done";
  const isLiveScreen = data.type === "wallet_screened" || data.type === "investigation_completed";
  if (isCase || isLiveScreen || sev === "critical" || sev === "severe" || sev === "high") {
    toast(data.text_ru || `${data.source}: ${data.text_ru || ""}`);
  }
  if (isCase && data.alert_id && currentView === "ops") {
    loadInbox();
    loadOpsWorkflowStats();
  }
  if (data.type === "case_new" && data.alert_id) {
    const row = document.getElementById(`item-${data.alert_id}`);
    row?.classList.add("new");
  }
}

function appendFeedRow(listId, data) {
  const list = document.getElementById(listId);
  if (!list) return;
  const row = document.createElement("div");
  const liveTag = combatMode && data.source && /KYT|FinSkalp|TX_MON|INST_HUB/i.test(data.source)
    ? " feed-live" : "";
  row.className = `feed-row sev-${data.severity || "info"}${data.type?.startsWith("case") ? " feed-case" : ""}${liveTag}`;
  const clickable = data.alert_id ? ` role="button" tabindex="0" onclick="openCaseFromFeed('${data.alert_id}')"` : "";
  row.innerHTML = `<span class="feed-src">${esc(data.source || "FinSkalp")}</span><span class="feed-text">${esc(data.text_ru || data.text || "")}</span>`;
  if (data.alert_id) {
    row.setAttribute("role", "button");
    row.tabIndex = 0;
    row.onclick = () => openCaseFromFeed(data.alert_id);
    row.onkeydown = (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openCaseFromFeed(data.alert_id); }
    };
  }
  list.prepend(row);
  while (list.children.length > 40) list.lastChild.remove();
}

function openCaseFromFeed(alertId) {
  switchView("ops");
  selectAlert(alertId);
}

async function loadServerInfo() {
  try {
    const [info, health] = await Promise.all([
      fetch(`${API}/api/server-info`).then(r => r.json()),
      fetch(`${API}/api/health`).then(r => r.json()).catch(() => ({})),
    ]);
    combatMode = !!health.combat_mode;
    if (health.investigate_timeout_sec) {
      window.FINSKALP_INVESTIGATE_TIMEOUT_MS = Math.round(Number(health.investigate_timeout_sec) * 1000) + 15000;
    }
    applyCombatUi();
    if (info.organization_ru && !combatMode) {
      document.getElementById("orgName").textContent = info.organization_ru;
    }
    document.getElementById("urls").innerHTML = `<a href="${info.lan_url}" target="_blank">${info.lan_url}</a>`;
  } catch {}
}

function applyCombatUi() {
  const fusionBtn = document.getElementById("btnOsintFusion");
  const scenarioSel = document.getElementById("osintScenario");
  const note = document.querySelector("#viewOsint .wallet-note");
  if (fusionBtn) {
    fusionBtn.hidden = combatMode;
    fusionBtn.disabled = combatMode;
  }
  if (scenarioSel) {
    const wrap = scenarioSel.closest(".form-row") || scenarioSel.parentElement;
    if (wrap) wrap.hidden = combatMode;
  }
  if (note && combatMode) {
    note.innerHTML = "<strong>Live-режим:</strong> только расследование по введённому on-chain адресу (скрининг + OSINT + fusion + PDF).";
  }
}

function switchView(view) {
  const prevView = currentView;
  const prevEl = document.getElementById(VIEW_IDS[prevView]);
  const nextEl = document.getElementById(VIEW_IDS[view]);
  const doSwitch = () => {
    currentView = view;
    document.querySelectorAll(".nav-item").forEach(n => n.classList.toggle("active", n.dataset.view === view));
    Object.values(VIEW_IDS).forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.classList.add("hidden");
      el.classList.remove("workspace-enter", "workspace-exit");
    });
    nextEl?.classList.remove("hidden");
    if (!prefersReducedMotion()) nextEl?.classList.add("workspace-enter");
    staggerWorkspaceCards(nextEl);
    if (view === "dashboard") { loadDashboard(); startLiveFeed(); }
    if (view === "wallet") focusWalletInput();
    if (view === "osint") {
      const wa = document.getElementById("walletAddress")?.value;
      if (wa && !document.getElementById("fsAddress")?.value) {
        document.getElementById("fsAddress").value = wa;
      }
      loadOsintCenter();
    }
    if (view === "microservices") loadMicroservices();
    if (view === "platform") loadPlatformSuite();
    if (view === "instruments") loadInstrumentsConsole();
    if (view === "registries") loadRegistry();
    if (view === "reports") loadReportsRegistry();
    if (view === "ops") {
      loadInbox();
      loadOpsWorkflowStats();
      startOpsLiveFeed();
    }
  };
  if (prevEl && nextEl && prevEl !== nextEl && !prefersReducedMotion()) {
    prevEl.classList.add("workspace-exit");
    setTimeout(() => doSwitch(), 140);
  } else {
    doSwitch();
  }
}

async function loadInstrumentsConsole() {
  showSkeleton("instrumentsList", 5, 1);
  const items = await fetch(`${API}/api/instruments`).then(r => r.json());
  document.getElementById("instrumentsList").innerHTML = items.map(ic => `
    <div class="ic-row">
      <div class="ic-row-head">
        <span class="ic-code">${esc(ic.platform_code || ic.code)}</span>
        <span class="ic-intl">${esc(ic.capability_tag_ru || ic.capability_ru || "")}</span>
      </div>
      <div class="ic-name">${esc(ic.name_ru_module || ic.name_ru)}</div>
      <div class="ic-suite">${esc(ic.suite_ru || ic.category_label_ru || "")}</div>
      <button class="btn-run-ic" onclick="runInstrument('${ic.code}')" id="btn-${ic.code}">▶ Выполнить</button>
    </div>`).join("");
}

async function runInstrument(code) {
  const btn = document.getElementById(`btn-${code}`);
  if (btn) { btn.disabled = true; btn.textContent = "Выполняется…"; }
  const out = document.getElementById("instrumentOutput");
  out.innerHTML = loadingHtml(4, 2, "Обработка…");
  try {
    const data = await fetch(`${API}/api/instruments/${encodeURIComponent(code)}/run`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        alert_id: selectedId,
        address: (document.getElementById("fsAddress")?.value || document.getElementById("walletAddress")?.value || "").trim() || undefined,
        chain: document.getElementById("fsChain")?.value || document.getElementById("walletChain")?.value || undefined,
        bank_reference: document.getElementById("fsBankRef")?.value || undefined,
        amount: document.getElementById("fsAmount")?.value ? Number(document.getElementById("fsAmount").value) : undefined,
        scenario_id: document.getElementById("osintScenario")?.value || undefined,
      }),
    }).then(r => r.json());
    out.innerHTML = renderInstrumentResult(data);
    toast(`Готово · ${data.duration_ms}мс`);
    if (code === "ИЦ-01" || code === "ИЦ-02") refreshAll();
  } catch (e) {
    out.innerHTML = `<div class="empty-state" style="color:var(--critical)">${esc(String(e))}</div>`;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "▶ Выполнить"; }
  }
}

function renderInstrumentResult(data) {
  const metrics = Object.entries(data.metrics || {}).map(([k, v]) =>
    `<div class="metric"><div class="v">${typeof v === "number" ? v.toLocaleString("ru") : esc(String(v))}</div><div class="k">${esc(k)}</div></div>`).join("");
  const logs = (data.log_lines || []).map(l => `<div class="log-line">${esc(l)}</div>`).join("");
  return `
    <div class="ic-result">
      <div class="ic-result-head">
        <h2>${esc(data.instrument_code)}</h2>
        <span class="ic-duration">${data.duration_ms}мс</span>
      </div>
      <div class="pc-parity" style="margin-bottom:0.75rem">${esc(data.capability_ru || "")}</div>
      <p class="summary-text">${esc(data.summary_ru)}</p>
      <div class="metrics">${metrics}</div>
      <div class="section"><h3>Журнал аудита</h3>${logs}</div>
      <pre class="json-out">${esc(JSON.stringify(data.output, null, 2).slice(0, 5000))}</pre>
    </div>`;
}

function switchRegistry(tab) {
  registryTab = tab;
  document.querySelectorAll(".reg-tab").forEach((t, i) =>
    t.classList.toggle("active", (tab === "banks" && i === 0) || (tab === "exchangers" && i === 1)));
  loadRegistry();
}

let registryRows = [];
let registryHeaders = [];
let registryKeys = [];

async function loadRegistry() {
  const el = document.getElementById("registryContent");
  el.innerHTML = sk(6, 4);
  if (registryTab === "banks") {
    const data = await fetch(`${API}/api/registry/banks?limit=100`).then(r => r.json());
    registryHeaders = ["БИК", "Наименование", "Уровень"];
    registryKeys = ["bic", "name", "tier"];
    registryRows = data.items.map(b => ({
      bic: `<span class="mono">${esc(b.bic)}</span>`,
      name: esc(b.name),
      tier: esc(b.tier),
      _filter: `${b.bic} ${b.name} ${b.tier}`.toLowerCase(),
    }));
    el.innerHTML = `
      <div class="reg-summary"><b>${data.total}</b> уполномоченных банков · банковский хаб · 115-ФЗ</div>
      <input type="search" class="table-filter" id="registryFilter" placeholder="Фильтр по БИК или названию…" aria-label="Фильтр реестра" />
      <div class="data-table-wrap"><div id="registryTableMount"></div></div>`;
    paintRegistryTable();
    document.getElementById("registryFilter")?.addEventListener("input", paintRegistryTable);
  } else {
    const data = await fetch(`${API}/api/registry/exchangers?limit=80`).then(r => r.json());
    const meta = data.meta || {};
    registryHeaders = ["ID", "Наименование", "Юрисдикция", "Регулятор", "Тип лицензии", "Статус"];
    registryKeys = ["id", "name", "jurisdiction", "regulator", "license", "status"];
    registryRows = data.items.map(e => ({
      id: `<span class="mono">${esc(e.id)}</span>`,
      name: esc(e.legal_name_ru || e.label_ru),
      jurisdiction: esc(e.jurisdiction),
      regulator: esc(e.regulator || "—"),
      license: esc(e.license_type || e.channel),
      status: esc(e.status),
      _filter: `${e.id} ${e.legal_name_ru || e.label_ru} ${e.jurisdiction}`.toLowerCase(),
    }));
    el.innerHTML = `
      <div class="reg-summary"><b>${data.total.toLocaleString("ru")}</b> лицензированных VASP · ${meta.jurisdictions_covered || "—"} юрисдикций СНГ · обновлено ${esc(meta.updated_at || "")}</div>
      <p class="wallet-note" style="margin:0.5rem 0">Только записи из публичных реестров регуляторов.</p>
      <input type="search" class="table-filter" id="registryFilter" placeholder="Фильтр…" aria-label="Фильтр реестра VASP" />
      <div class="data-table-wrap"><div id="registryTableMount"></div></div>`;
    paintRegistryTable();
    document.getElementById("registryFilter")?.addEventListener("input", paintRegistryTable);
  }
}

function paintRegistryTable() {
  const q = (document.getElementById("registryFilter")?.value || "").trim().toLowerCase();
  const rows = q ? registryRows.filter(r => r._filter.includes(q)) : registryRows;
  const cells = rows.map(r => registryKeys.map(k => r[k]));
  FinSkalpUI?.renderDataTable("registryTableMount", registryHeaders, cells, { keys: registryKeys, defaultSortCol: registryKeys[0] });
}

function riskLabel(r) {
  const m = { severe: "КРИТИЧ.", high: "ВЫСОК.", medium: "СРЕД.", low: "НИЗК." };
  return m[r] || String(r).toUpperCase();
}

async function loadReportsRegistry() {
  const el = document.getElementById("reportsRegistry");
  el.innerHTML = sk(5, 5);
  const items = await fetch(`${API}/api/reports`).then(r => r.json());
  if (!items.length) { el.innerHTML = `<div class="empty-state"><p>Отчёты появятся после закрытия дела или запуска модуля «Дело и СОО».</p></div>`; return; }
  const rows = items.map(r => ({
    report_id: `<span class="mono">${esc(r.report_id)}</span>`,
    alert: `<span class="mono">${esc(r.alert_code)}</span>`,
    typology: esc(r.typology_code),
    risk: `<span class="prio-${r.risk_level || "medium"}">${riskLabel(r.risk_level || "medium")}</span>`,
    decision: esc((r.decision_ru || "").slice(0, 70)) + "…",
    action: `<button onclick="openReportByAlert('${r.alert_id}')">Открыть</button>`,
  }));
  el.innerHTML = `<div class="data-table-wrap"><div id="reportsTableMount"></div></div>`;
  FinSkalpUI?.renderDataTable(
    "reportsTableMount",
    ["ID отчёта", "Алерт", "Типология", "Риск", "Решение", ""],
    rows.map(r => [r.report_id, r.alert, r.typology, r.risk, r.decision, r.action]),
    { keys: ["report_id", "alert", "typology", "risk", "decision", "action"], defaultSortCol: "report_id" }
  );
}

function openReportByAlert(id) { switchView("ops"); selectAlert(id); }

async function loadOpsWorkflowStats() {
  try {
    const wf = await fetch(`${API}/api/cases/workflow/stats`).then(r => r.json());
    workflowAssignees = wf.assignees || [];
    const pipe = wf.pipeline || {};
    const mini = document.getElementById("opsInboxPipeline");
    if (mini) {
      mini.innerHTML = WORKFLOW_STEPS.filter(s => s.id !== "archived").map(s => {
        const v = pipe[s.id] ?? 0;
        return `<span class="ops-pipe-chip">${s.label}<b>${v}</b></span>`;
      }).join("");
    }
    if (selectedId) {
      const alert = await fetch(`${API}/api/inbox/${selectedId}`).then(r => r.json()).catch(() => null);
      if (alert) renderOpsWorkflowTrack(alert.workflow_status);
    } else {
      renderOpsWorkflowTrack(null);
    }
  } catch {}
}

function renderOpsWorkflowTrack(currentStatus) {
  const el = document.getElementById("opsWorkflowTrack");
  if (!el) return;
  if (!currentStatus) {
    el.innerHTML = WORKFLOW_STEPS.map(s =>
      `<div class="ops-workflow-step future"><div class="wf-dot">·</div><div class="wf-label">${s.label}</div></div>`
    ).join("");
    return;
  }
  const idx = WORKFLOW_STEPS.findIndex(s => s.id === currentStatus);
  el.innerHTML = WORKFLOW_STEPS.map((s, i) => {
    let cls = "future";
    if (i < idx) cls = "done";
    else if (i === idx) cls = "active";
    const icon = i < idx ? "✓" : i === idx ? "●" : (i + 1);
    return `<div class="ops-workflow-step ${cls}"><div class="wf-dot">${icon}</div><div class="wf-label">${s.label}</div></div>`;
  }).join("");
}

function mountOpsGraph(graph, mlScore) {
  const hint = document.getElementById("opsGraphHint");
  const mount = document.getElementById("opsForceGraphMount");
  if (!FinSkalpGraph?.hasGraphData?.(graph)) {
    hint && (hint.textContent = "Запустите расследование — граф появится здесь");
    mount && (mount.innerHTML = "");
    FinSkalpGraph?.destroy({ containerId: "opsForceGraphMount", skipWrap: true });
    return;
  }
  const nodeCount = graph.node_count || graph.cluster_view?.node_count || graph.nodes?.length || 0;
  const edgeCount = graph.edge_count || graph.cluster_view?.edge_count || graph.edges?.length || 0;
  hint && (hint.textContent = `${nodeCount} узлов · ${edgeCount} связей · drag · zoom`);
  requestAnimationFrame(() => {
    FinSkalpGraph?.mount("opsForceGraphMount", graph, {
      panelId: "opsGraphNodePanel",
      alwaysShow: true,
      mlScore: mlScore || graph.ml_score?.score,
    });
  });
}

function showOpsGraphBuilding(active) {
  const mount = document.getElementById("opsForceGraphMount");
  const hint = document.getElementById("opsGraphHint");
  if (!mount) return;
  if (active) {
    hint && (hint.textContent = "Построение графа доказательств…");
    mount.innerHTML = `<div class="graph-building">◉ OSINT Fusion · link scoring · evidence graph</div>`;
  }
}

async function transitionWorkflow(alertId, target, note) {
  try {
    const body = { workflow_status: target, note: note || undefined, assignee: workflowAssignees[0] };
    const updated = await fetch(`${API}/api/inbox/${alertId}/workflow`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(async r => {
      if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
      return r.json();
    });
    toast(`Статус: ${updated.workflow_label_ru || target}`);
    await refreshAll();
    selectAlert(alertId);
  } catch (e) {
    toast(String(e.message || e));
  }
}

async function submitCaseComment(alertId) {
  const input = document.getElementById("caseCommentInput");
  const text = (input?.value || "").trim();
  if (!text) return;
  try {
    await fetch(`${API}/api/inbox/${alertId}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    input.value = "";
    selectAlert(alertId);
  } catch (e) {
    toast(String(e.message || e));
  }
}

let opsInboxView = "list";
let kanbanDragId = null;

function setOpsInboxView(mode) {
  opsInboxView = mode;
  document.getElementById("btnInboxList")?.classList.toggle("active", mode === "list");
  document.getElementById("btnInboxKanban")?.classList.toggle("active", mode === "kanban");
  document.getElementById("inbox")?.classList.toggle("hidden", mode === "kanban");
  document.getElementById("opsKanban")?.classList.toggle("hidden", mode !== "kanban");
  if (mode === "kanban") loadOpsKanban();
  else loadInbox();
}

async function loadOpsKanban() {
  const board = document.getElementById("opsKanban");
  if (!board) return;
  const items = await fetch(`${API}/api/inbox`).then(r => r.json()).catch(() => []);
  document.getElementById("inboxCount").textContent = items.length;
  const byStatus = Object.fromEntries(WORKFLOW_STEPS.map(s => [s.id, []]));
  items.forEach(a => {
    const ws = a.workflow_status || "new";
    (byStatus[ws] || byStatus.new).push(a);
  });
  board.innerHTML = WORKFLOW_STEPS.map(step => {
    const cards = (byStatus[step.id] || []).map(renderKanbanCard).join("");
    return `<div class="ops-kanban-col" data-wf-col="${step.id}"
      ondragover="kanbanDragOver(event)" ondragleave="kanbanDragLeave(event)" ondrop="kanbanDrop(event,'${step.id}')">
      <div class="ops-kanban-col-head"><span>${step.label}</span><b>${(byStatus[step.id] || []).length}</b></div>
      <div class="ops-kanban-col-body">${cards || `<div class="empty-mini" style="color:var(--muted);font-size:0.65rem">—</div>`}</div>
    </div>`;
  }).join("");
}

function renderKanbanCard(a) {
  const sla = a.sla_breached ? " sla-breach" : "";
  const active = selectedId === a.id ? " active" : "";
  return `<div class="ops-kanban-card${sla}${active}" draggable="true" id="kanban-${a.id}"
    ondragstart="kanbanDragStart(event,'${a.id}')" ondragend="kanbanDragEnd(event)"
    onclick="selectAlert('${a.id}')" role="button" tabindex="0">
    <div class="inbox-code">${esc(a.alert_code)}${a.sla_breached ? ' <span class="inbox-sla-warn">SLA</span>' : ""}</div>
    <div style="font-weight:600;margin:0.2rem 0">${esc((a.official_title_ru || a.title_ru || "").slice(0, 48))}</div>
    <div class="inbox-meta"><span class="prio-${a.priority}">${a.priority}</span></div>
    <button type="button" class="btn btn-outline btn-sm" style="margin-top:0.25rem;font-size:0.62rem" onclick="event.stopPropagation();kanbanQuickAdvance('${a.id}','${a.workflow_status}')">→ далее</button>
  </div>`;
}

function kanbanDragStart(ev, id) {
  kanbanDragId = id;
  ev.dataTransfer?.setData("text/plain", id);
  ev.target.classList.add("dragging");
}
function kanbanDragEnd(ev) { ev.target.classList.remove("dragging"); kanbanDragId = null; }
function kanbanDragOver(ev) { ev.preventDefault(); ev.currentTarget.classList.add("drag-over"); }
function kanbanDragLeave(ev) { ev.currentTarget.classList.remove("drag-over"); }
async function kanbanDrop(ev, targetStatus) {
  ev.preventDefault();
  ev.currentTarget.classList.remove("drag-over");
  const id = kanbanDragId || ev.dataTransfer?.getData("text/plain");
  if (!id) return;
  const item = await fetch(`${API}/api/inbox/${id}`).then(r => r.json()).catch(() => null);
  if (!item || item.workflow_status === targetStatus) return;
  await transitionWorkflow(id, targetStatus);
  await loadOpsKanban();
}

function kanbanQuickAdvance(id, current) {
  const next = (WORKFLOW_NEXT[current] || []).find(n => n.primary);
  if (next) transitionWorkflow(id, next.status);
}

async function loadInbox() {
  const inbox = document.getElementById("inbox");
  if (!inbox) return;
  if (opsInboxView === "kanban") { loadOpsKanban(); return; }
  if (!inbox.dataset.hydrated) inbox.innerHTML = sk(6, 1);
  const prev = inbox.querySelectorAll(".inbox-item").length;
  const items = await fetch(`${API}/api/inbox`).then(r => r.json());
  document.getElementById("inboxCount").textContent = items.length;
  inbox.innerHTML = items.map(renderInboxItem).join("") || `<div style="padding:1rem;color:var(--muted);font-size:0.82rem">Нет открытых дел</div>`;
  inbox.dataset.hydrated = "1";
  if (items.length > prev && prev > 0) toast("Новое дело в очереди");
  if (selectedId) document.getElementById(`item-${selectedId}`)?.classList.add("active");
}

function renderInboxItem(a) {
  const amt = a.amount ? `${Math.round(a.amount).toLocaleString("ru")} ₽` : "";
  const wf = a.workflow_label_ru || a.workflow_status || "";
  const sla = a.sla_breached ? `<span class="inbox-sla-warn">SLA</span>` : "";
  return `<div class="inbox-item ${a.status==="new"?"new":""} ${a.status==="completed"?"done":""} ${selectedId===a.id?"active":""}"
    id="item-${a.id}" role="button" tabindex="0"
    onclick="selectAlert('${a.id}')"
    onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();selectAlert('${a.id}')}">
    <div class="inbox-code">${esc(a.alert_code)} ${sla}</div>
    <div class="inbox-title">${esc(a.official_title_ru || a.title_ru)}</div>
    <div class="inbox-meta">
      <span class="badge badge-str">${a.source==="bank_hub"?"СОО":"KYT"}</span>
      <span class="inbox-wf-badge">${esc(wf)}</span>
      <span class="prio-${a.priority}">${a.priority.toUpperCase()}</span>
      ${a.typology_code ? `<span>${esc(a.typology_code)}</span>` : ""}${amt ? `<span>${amt}</span>` : ""}
    </div></div>`;
}

async function selectAlert(id) {
  selectedId = id;
  document.querySelectorAll(".inbox-item").forEach(el => el.classList.remove("active"));
  document.getElementById(`item-${id}`)?.classList.add("active");
  const alert = await fetch(`${API}/api/inbox/${id}`).then(r => r.json());
  renderAlertDetail(alert);
  renderOpsWorkflowTrack(alert.workflow_status);
  const graph = alert.evidence_graph || alert.report?.live_fusion || alert.report?.graph_viz;
  const ml = alert.report?.live_fusion?.ml_score?.score || alert.report?.illegal_flow_score;
  if (graph?.nodes?.length) {
    mountOpsGraph(graph, ml);
  } else {
    try {
      const g = await fetch(`${API}/api/inbox/${id}/graph`).then(r => r.ok ? r.json() : null);
      mountOpsGraph(g, ml);
    } catch {
      mountOpsGraph(null);
    }
  }
}

function renderWorkflowBar(a) {
  const ws = a.workflow_status || "new";
  const next = WORKFLOW_NEXT[ws] || [];
  const slaClass = a.sla_breached ? " sla-breach" : "";
  const due = a.due_at ? new Date(a.due_at).toLocaleString("ru") : "—";
  const actions = next.map(n =>
    `<button type="button" class="btn ${n.primary ? "btn-primary" : ""}" onclick="transitionWorkflow('${a.id}','${n.status}')">${esc(n.label)}</button>`
  ).join("");
  return `
    <div class="case-workflow-bar">
      <span class="wf-status-pill${slaClass}">${esc(a.workflow_label_ru || ws)}</span>
      ${a.assignee ? `<span class="summary-text" style="font-size:0.78rem;margin:0">👤 ${esc(a.assignee)}</span>` : ""}
      <span class="summary-text" style="font-size:0.72rem;margin:0;color:var(--muted)">SLA до ${esc(due)}</span>
      <div class="wf-actions">${actions}</div>
    </div>`;
}

function renderComments(comments) {
  if (!comments?.length) return `<div class="empty-mini" style="color:var(--muted);font-size:0.78rem">Комментариев пока нет</div>`;
  return comments.map(c => `
    <div class="comment-row">
      <div class="comment-meta">${esc(c.author)} · ${esc((c.created_at || "").slice(0, 19).replace("T", " "))}</div>
      <div>${esc(c.text_ru)}</div>
    </div>`).join("");
}

function renderAlertDetail(a) {
  const canRun = a.workflow_status !== "filed" && a.workflow_status !== "archived" &&
    !investigating && (a.workflow_status === "triage" || a.workflow_status === "investigating" || a.workflow_status === "new" || !a.report);
  const investigateLabel = a.report
    ? "↻ Повторный прогон"
    : a.workflow_status === "new"
      ? "▶ Принять в триаж и расследовать"
      : "▶ Полный цикл расследования";
  document.getElementById("detail").innerHTML = `
    <div class="alert-doc">
      ${renderWorkflowBar(a)}
      <div class="doc-header">
        <div class="doc-code">${esc(a.alert_code)} · ${esc(a.case_ref||"")}</div>
        <h2 class="doc-title">${esc(a.official_title_ru || a.title_ru)}</h2>
        <p class="doc-official">${esc(a.summary_ru)}</p>
        <div class="meta-grid">
          ${a.bank_name ? metaCell("Банк", a.bank_name) : ""}
          ${a.amount ? metaCell("Сумма", `${Math.round(a.amount).toLocaleString("ru")} ${a.currency||"RUB"}`) : ""}
          ${a.crypto_address ? metaCell("Кошелёк", `${shortAddress(a.crypto_address)} · ${esc(a.crypto_chain||"")}`) : ""}
          ${metaCell("Типология", `${a.typology_code}`)}
          ${metaCell("Субъект", a.subject_category_ru||"—")}
        </div>
        ${!a.crypto_address ? `<p class="wallet-note" style="margin-top:0.5rem">Укажите live-адрес в поле СОО или задайте <code>FINSKALP_COMBAT_SEED_ADDRESS</code> в .env</p>` : ""}
      </div>
      <div class="section"><h3>Признаки подозрительности · ст. 6 115-ФЗ</h3>
        <ul class="legal-list">${(a.legal_signs_ru||[]).map(s=>`<li>${esc(s)}</li>`).join("")}</ul></div>
      <div class="actions">
        <button class="btn btn-primary" id="btnInvestigate" onclick="startInvestigation('${a.id}')" ${canRun?"":"disabled"}>
          ${investigateLabel}</button>
        ${a.fz115_report ? `<a class="btn btn-outline" href="${API}/api/inbox/${a.id}/fz115/pdf" target="_blank">⬇ PDF 115-ФЗ</a>` : ""}
        ${(a.report?.forensic_report?.address_profile || a.report?.investigation_id) ? `<a class="btn btn-outline" href="${API}/api/inbox/${a.id}/forensic/pdf" target="_blank">⬇ Forensic PDF</a>` : ""}
        ${(a.report?.volumetric_report?.sections?.length || a.report?.attachments?.some(x => x.type === "volumetric")) ? `<a class="btn btn-outline" href="${API}/api/inbox/${a.id}/volumetric/pdf" target="_blank">⬇ Объёмный отчёт</a>` : ""}
        ${(a.report?.sar_report?.evidence_sections?.length || a.report?.attachments?.some(x => x.type === "sar")) ? `<a class="btn btn-outline" href="${API}/api/inbox/${a.id}/sar/pdf" target="_blank">⬇ SAR / СПО</a>` : ""}
        ${a.crypto_address ? `<button type="button" class="btn btn-outline" onclick="addToKytWatchlist(${JSON.stringify(a.crypto_address)})">📡 KYT watchlist</button>` : ""}
        ${a.workflow_status === "pending_filing" ? `<button class="btn btn-primary" onclick="transitionWorkflow('${a.id}','filed','Подано в Росфинмониторинг')">✓ Подтвердить filing</button>` : ""}
      </div>
      <div id="pipelineArea">${a.investigation_steps?.length ? `<div class="section"><h3>Конвейер OSINT · ИЦ</h3>${renderPipeline(a.investigation_steps)}</div>` : ""}</div>
      <div id="osintFindingsArea">${renderOsintFindings(a)}</div>
      <div id="reportArea">${a.report ? renderOsintReport(a.report) : ""}${a.report?.sar_report ? renderSarBlock(a.report.sar_report) : ""}${a.fz115_report ? renderFZ115Report(a.fz115_report) : ""}</div>
      <div class="section case-comments">
        <h3>Журнал аналитика</h3>
        ${renderComments(a.comments)}
        <div class="comment-form">
          <input id="caseCommentInput" placeholder="Комментарий к делу…" aria-label="Комментарий" />
          <button type="button" class="btn" onclick="submitCaseComment('${a.id}')">Добавить</button>
        </div>
      </div>
    </div>`;
}

function metaCell(k,v){return `<div class="meta-cell"><div class="k">${esc(k)}</div><div class="v">${esc(v)}</div></div>`;}

function _attributionConnections(alert) {
  const fromScreen = alert.report?.screening?.onchain_summary?.attribution?.connections;
  const fromForensic = alert.report?.forensic_report?.attribution?.connections;
  return fromScreen || fromForensic || [];
}

function renderOsintFindings(alert) {
  const conns = _attributionConnections(alert);
  if (!conns.length) {
    return `<div class="section"><h3>OSINT находки</h3><p class="summary-text" style="color:var(--muted)">Запустите расследование для connection-карточек</p></div>`;
  }
  const cards = conns.map((c, i) => {
    const tier = c.tier ?? c.confidence_tier ?? 2;
    const needsReview = tier > 1;
    const entity = c.entity_name || c.label || "—";
    const conf = Math.round((c.confidence ?? 0.5) * 100);
    const addr = esc(c.address || "");
    const actions = needsReview ? `
      <div class="attr-actions">
        <button type="button" class="btn btn-primary btn-sm" data-idx="${i}" data-action="confirm" onclick="reviewAttributionBtn(this,'${alert.id}')">Подтвердить</button>
        <button type="button" class="btn btn-outline btn-sm" data-idx="${i}" data-action="reject" onclick="reviewAttributionBtn(this,'${alert.id}')">Отклонить</button>
      </div>` : `<span class="inbox-wf-badge">Tier-1</span>`;
    return `<div class="connection-card" data-idx="${i}">
      <div class="connection-head"><strong>${esc(entity)}</strong> · Tier ${tier}</div>
      <div class="mono" style="font-size:0.72rem">${esc(shortAddress(c.address || ""))}</div>
      <div class="summary-text" style="font-size:0.78rem">confidence ${conf}% · ${esc(c.source || c.category || "")}</div>
      ${actions}
    </div>`;
  }).join("");
  window._lastAttributionConns = conns;
  return `<div class="section"><h3>OSINT находки</h3><div class="connection-grid">${cards}</div></div>`;
}

async function reviewAttributionBtn(btn, alertId) {
  const idx = Number(btn.getAttribute("data-idx"));
  const action = btn.getAttribute("data-action");
  const conn = (window._lastAttributionConns || [])[idx];
  if (!conn) return;
  await reviewAttribution(alertId, action, conn);
}

async function reviewAttribution(alertId, action, conn) {
  const path = action === "confirm" ? "confirm" : "reject";
  try {
    const r = await fetch(`${API}/api/compliance/attribution/${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Analyst-Role": "analyst",
        "X-Analyst-Id": "case-analyst",
      },
      body: JSON.stringify({
        chain: conn.chain || "tron",
        address: conn.address,
        label: conn.entity_name || conn.label || "unknown",
        category: conn.category || "exchange",
      }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    toast(action === "confirm" ? "Атрибуция подтверждена" : "Атрибуция отклонена");
    selectAlert(alertId);
  } catch (e) {
    toast(String(e.message || e));
  }
}

function renderPipeline(steps){return steps.map(s=>`<div class="step ${s.status}"><div class="step-icon">${s.status==="done"?"✓":"◌"}</div><div><div class="step-label">${esc(s.label_ru)}</div><div class="step-detail">${esc(s.detail_ru)}</div></div></div>`).join("");}
function renderOsintReport(r){
  const risk=(r.risk_level||"low").toLowerCase();
  return `<div class="report-block osint"><div class="report-head"><div><div class="report-type">Граф расследования</div><h3>${esc(r.scenario_title_ru)}</h3></div>
    <div class="score risk-${risk}"><div class="num">${Math.round(r.illegal_flow_score)}</div><div class="lbl">${riskLabel(risk)}</div></div></div>
    <div class="summary-text">${esc(r.executive_summary_ru)}</div></div>`;
}
function renderFZ115Report(r){
  return `<div class="report-block fz115" id="fz115Report"><div class="report-type">Отчёт регулятору · ${esc(r.report_id)}</div>
    <div class="decision-box"><div class="label">Решение</div><div class="text">${esc(r.decision_ru)}</div></div></div>`;
}
function printFZ115(){const el=document.getElementById("fz115Report");if(!el)return;const w=window.open("");w.document.write(el.outerHTML);w.print();}

async function startInvestigation(alertId){
  if(investigating)return;
  const alert = await fetch(`${API}/api/inbox/${alertId}`).then(r => r.json()).catch(() => ({}));
  if (alert.workflow_status === "new") {
    await transitionWorkflow(alertId, "triage", "Авто-триаж перед расследованием");
    await transitionWorkflow(alertId, "investigating", "Запуск OSINT Fusion");
  } else if (alert.workflow_status === "triage") {
    await transitionWorkflow(alertId, "investigating", "Запуск OSINT Fusion");
  }
  investigating=true;
  document.getElementById("btnInvestigate")?.setAttribute("disabled","true");
  document.getElementById("pipelineArea").innerHTML=`<div class="section"><h3>Конвейер OSINT · ИЦ</h3>${renderPipeline([])}</div>`;
  showOpsGraphBuilding(true);
  const es=new EventSource(`${API}/api/investigate/${alertId}/stream`);
  es.onmessage=(ev)=>{const d=JSON.parse(ev.data);
    if(d.type==="step"){
      document.getElementById("pipelineArea").innerHTML=`<div class="section"><h3>Конвейер OSINT · ИЦ</h3>${renderPipeline(d.steps)}</div>`;
      const linkStep = (d.steps || []).find(s => s.id === "link_scoring" && s.status === "running");
      if (linkStep) showOpsGraphBuilding(true);
    }
    if(d.type==="done"){
      es.close();investigating=false;
      selectAlert(alertId);
      toast("Расследование завершено · live-граф и отчёт 115-ФЗ готовы");
      refreshAll();
    }
    if(d.type==="error"){
      es.close();investigating=false;
      toast(d.detail || "Ошибка расследования");
      selectAlert(alertId);
    }};
  es.onerror=()=>{es.close();fetch(`${API}/api/investigate/${alertId}`,{method:"POST"}).then(()=>{investigating=false;selectAlert(alertId);refreshAll();});};
}

async function simulateBankStr(){
  document.getElementById("btnStr").disabled=true;
  const addr = (document.getElementById("strCryptoAddress")?.value || "").trim();
  const body = addr ? JSON.stringify({ crypto_address: addr }) : "{}";
  try{
    const a=await fetch(`${API}/api/hub/str`,{method:"POST",headers:{"Content-Type":"application/json"},body}).then(r=>r.json());
    if (!r_ok(a)) throw new Error(a.detail || "STR rejected");
    toast(`СОО принято · ${a.alert_code}${a.crypto_address ? " · " + shortAddress(a.crypto_address) : ""}`);
    switchView("ops");
    await refreshAll();
    selectAlert(a.id);
  } catch(e) {
    toast(String(e.message || e));
  } finally{document.getElementById("btnStr").disabled=false;}
}
function r_ok(a){return a && a.id;}
async function runPatternScan(){
  document.getElementById("btnScan").disabled=true;
  try{
    const d=await fetch(`${API}/api/monitor/scan`,{method:"POST"}).then(r=>r.json());
    toast(d.found ? `Live KYT: ${d.found} алерт(ов)` : "KYT: порог не превышен или watchlist пуст (FINSKALP_KYT_WATCHLIST)");
    if (d.found) switchView("ops");
    await refreshAll();
    if(d.alerts?.[0])selectAlert(d.alerts[0].id);
  }finally{document.getElementById("btnScan").disabled=false;}
}

function toast(msg){const t=document.createElement("div");t.className="toast";t.textContent=msg;document.getElementById("toastContainer").appendChild(t);setTimeout(()=>t.remove(),4000);}
function esc(s){if(!s)return"";const d=document.createElement("div");d.textContent=String(s);return d.innerHTML;}

let _searchTimer = null;
const _searchKindRu = { case: "Дело", wallet: "Кошелёк", vasp: "VASP", str: "СОО" };

function initGlobalSearch() {
  const input = document.getElementById("globalSearchInput");
  const dropdown = document.getElementById("globalSearchDropdown");
  if (!input || !dropdown) return;

  const hide = () => dropdown.classList.add("hidden");
  const show = () => dropdown.classList.remove("hidden");

  input.addEventListener("input", () => {
    clearTimeout(_searchTimer);
    const q = input.value.trim();
    if (q.length < 2) { hide(); dropdown.innerHTML = ""; return; }
    _searchTimer = setTimeout(async () => {
      try {
        const data = await fetch(`${API}/api/search?q=${encodeURIComponent(q)}&limit=12`).then(r => r.json());
        const hits = data.hits || [];
        if (!hits.length) {
          dropdown.innerHTML = `<div class="px-3 py-2 text-body-sm text-on-surface-variant">Ничего не найдено</div>`;
          show();
          return;
        }
        dropdown.innerHTML = hits.map(h => {
          const kind = _searchKindRu[h.kind] || h.kind || "—";
          const title = esc(h.title || h.address || h.case_ref || "—");
          const sub = esc(h.subtitle || h.label || "");
          return `<button type="button" class="w-full text-left px-3 py-2 hover:bg-surface-container-high border-b border-outline-variant/30 last:border-0" data-kind="${esc(h.kind)}" data-ref="${esc(h.case_ref || h.address || h.title || "")}">
            <div class="text-[10px] uppercase text-primary">${kind}</div>
            <div class="text-body-sm text-on-surface truncate">${title}</div>
            ${sub ? `<div class="text-[11px] text-on-surface-variant truncate">${sub}</div>` : ""}
          </button>`;
        }).join("");
        dropdown.querySelectorAll("button").forEach(btn => {
          btn.addEventListener("click", () => {
            const kind = btn.dataset.kind;
            hide();
            if (kind === "case") switchView("ops");
            else if (kind === "wallet") switchView("finskalp");
            else if (kind === "vasp") switchView("registry");
            else switchView("dashboard");
            toast(`Выбрано: ${btn.dataset.ref}`);
          });
        });
        show();
      } catch {
        dropdown.innerHTML = `<div class="px-3 py-2 text-body-sm text-error">Ошибка поиска</div>`;
        show();
      }
    }, 280);
  });

  document.addEventListener("click", (ev) => {
    if (!ev.target.closest("#globalSearchWrap")) hide();
  });
}

loadServerInfo();
pollWatchlistBadge();
initGlobalSearch();
switchView("dashboard");
setInterval(refreshAll, 15000);
