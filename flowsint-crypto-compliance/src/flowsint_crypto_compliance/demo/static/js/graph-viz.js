/**
 * FinSkalp interactive graph — cluster drill-down, exposure paths, force-graph
 */
(function (global) {
  const instances = {};
  const sigmaInstances = {};
  const resizeObservers = {};
  const graphStates = {};
  const WEBGL_NODE_THRESHOLD = 200;

  const CHAIN_RING = {
    tron: "#ef4444",
    eth: "#6366f1",
    btc: "#f59e0b",
    bsc: "#eab308",
    polygon: "#a855f7",
    solana: "#14b8a6",
  };

  /** JS constants matching --fs-risk-* tokens */
  const RISK_TOKENS = {
    critical: "#ef4444",
    high: "#f97316",
    medium: "#eab308",
    clear: "#14b8a6",
    muted: "#94a3b8",
  };

  function prefersReducedMotion() {
    return window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;
  }

  function _edgeKey(source, target) {
    const s = typeof source === "object" ? source.id : source;
    const t = typeof target === "object" ? target.id : target;
    return `${s}|${t}`;
  }

  function _riskGlowForNode(node, mlScore) {
    if (node.flagged || node.role === "illicit" || node.sanctioned) return RISK_TOKENS.critical;
    const rs = node.risk_score != null ? Number(node.risk_score) : null;
    if (rs != null) {
      if (rs >= 80) return RISK_TOKENS.critical;
      if (rs >= 55) return RISK_TOKENS.high;
      if (rs >= 30) return RISK_TOKENS.medium;
      return RISK_TOKENS.clear;
    }
    const s = mlScore ?? 50;
    if (s >= 70) return RISK_TOKENS.high;
    if (s >= 40) return RISK_TOKENS.medium;
    return RISK_TOKENS.muted;
  }

  function _state(containerId) {
    if (!graphStates[containerId]) {
      graphStates[containerId] = {
        payload: null,
        viewMode: "cluster",
        expandedClusters: new Set(),
        highlightedPath: null,
        timelineCutoff: null,
        timelinePlaying: false,
        playTimer: null,
        opts: {},
        pins: {},
        lastPanelNode: null,
        selectedNodeId: null,
        prevVisibleEdgeKeys: new Set(),
        flashEdges: {},
        _animRaf: null,
        _animT: 0,
        rendererMode: "auto",
      };
    }
    return graphStates[containerId];
  }

  function _wrapFor(containerId) {
    const el = document.getElementById(containerId);
    return el?.closest(".graph-workspace, .ops-graph-panel") || null;
  }

  function _timelineSlot(containerId) {
    return document.querySelector(`[data-timeline-slot="${containerId}"]`);
  }

  function _crossChainSlot(containerId) {
    return document.querySelector(`[data-cross-chain-slot="${containerId}"]`);
  }

  function _toolbarActions(containerId) {
    return document.querySelector(`[data-graph-toolbar="${containerId}"]`);
  }

  function riskColor(node, mlScore) {
    if (node.flagged || node.role === "illicit" || node.sanctioned) {
      return getComputedStyle(document.documentElement).getPropertyValue("--fs-risk-critical").trim() || "#ef4444";
    }
    const rs = node.risk_score != null ? Number(node.risk_score) : null;
    if (rs != null) {
      if (rs >= 80) return getComputedStyle(document.documentElement).getPropertyValue("--fs-risk-critical").trim() || "#ef4444";
      if (rs >= 55) return getComputedStyle(document.documentElement).getPropertyValue("--fs-risk-high").trim() || "#f97316";
      if (rs >= 30) return getComputedStyle(document.documentElement).getPropertyValue("--fs-risk-medium").trim() || "#eab308";
      return getComputedStyle(document.documentElement).getPropertyValue("--fs-risk-clear").trim() || "#14b8a6";
    }
    if (node.hop === 0) return getComputedStyle(document.documentElement).getPropertyValue("--fs-risk-clear").trim() || "#14b8a6";
    const s = mlScore ?? 50;
    if (s >= 70) return getComputedStyle(document.documentElement).getPropertyValue("--fs-risk-high").trim() || "#f97316";
    if (s >= 40) return getComputedStyle(document.documentElement).getPropertyValue("--fs-risk-medium").trim() || "#eab308";
    return getComputedStyle(document.documentElement).getPropertyValue("--fs-color-text-secondary").trim() || "#94a3b8";
  }

  function nodeVal(node) {
    if (node.node_type === "cluster") {
      const mc = Number(node.member_count) || 1;
      const vol = Number(node.volume_usd) || 0;
      const volFactor = vol > 0 ? Math.min(8, Math.sqrt(vol) / 400) : 0;
      return 4 + Math.min(24, Math.sqrt(mc) * 3 + volFactor);
    }
    if (node.hop === 0) return 8;
    return 5;
  }

  function _edgeOnPath(source, target, path) {
    if (!path?.length) return false;
    for (let i = 0; i < path.length - 1; i += 1) {
      if (
        (path[i] === source && path[i + 1] === target)
        || (path[i] === target && path[i + 1] === source)
      ) return true;
    }
    return false;
  }

  function pickActiveGraph(payload, gs) {
    if (!payload) return { nodes: [], edges: [] };
    let base;
    if (gs.viewMode === "address" || !payload.cluster_view?.nodes?.length) {
      base = payload.address_view || payload;
    } else {
      const cv = payload.cluster_view;
      const expanded = gs.expandedClusters;
      if (!expanded.size) {
        base = cv;
      } else {
        const av = payload.address_view || payload;
        const avNodes = new Map((av.nodes || []).map((n) => [n.id, n]));
        const nodes = [];
        const keepIds = new Set();
        for (const n of cv.nodes || []) {
          if (n.node_type === "cluster" && expanded.has(n.id)) {
            for (const mid of n.members || []) {
              const m = avNodes.get(mid);
              if (m) {
                nodes.push({ ...m, node_type: "address" });
                keepIds.add(mid);
              }
            }
          } else {
            nodes.push(n);
            keepIds.add(n.id);
          }
        }
        const edges = (av.edges || []).filter((e) => keepIds.has(e.from) && keepIds.has(e.to));
        base = edges.length ? { ...cv, nodes, edges } : cv;
      }
    }
    return _filterTimeline(base, gs);
  }

  function _filterTimeline(graph, gs) {
    const cutoff = gs.timelineCutoff;
    if (!cutoff) return graph;
    const edges = (graph.edges || []).filter((e) => {
      const ts = _normTs(e.timestamp);
      return ts == null || ts <= cutoff;
    });
    const keep = new Set();
    for (const e of edges) {
      keep.add(e.from);
      keep.add(e.to);
    }
    const nodes = (graph.nodes || []).filter((n) => keep.has(n.id) || n.hop === 0);
    return { ...graph, nodes, edges };
  }

  function _normTs(ts) {
    if (ts == null) return null;
    const v = Number(ts);
    if (!Number.isFinite(v)) return null;
    return v < 1e10 ? v * 1000 : v;
  }

  function collapseLargeGraph(fusionGraph, gs, maxNodes = 120) {
    const nodes = fusionGraph.nodes || [];
    const edges = fusionGraph.edges || [];
    if (nodes.length <= maxNodes || gs.viewMode === "cluster") return fusionGraph;

    const root = nodes.find((n) => n.hop === 0) || nodes[0];
    const rootId = root.id;
    const byVolume = new Map();
    for (const e of edges) {
      const amt = Number(e.amount) || 1;
      const fr = e.from;
      const to = e.to;
      const otherId = fr === rootId ? to : to === rootId ? fr : null;
      if (!otherId || otherId === rootId) continue;
      byVolume.set(otherId, (byVolume.get(otherId) || 0) + amt);
    }
    const keepIds = new Set([rootId]);
    [...byVolume.entries()].sort((a, b) => b[1] - a[1]).slice(0, maxNodes - 2).forEach(([id]) => keepIds.add(id));
    return {
      ...fusionGraph,
      nodes: nodes.filter((n) => keepIds.has(n.id)),
      edges: edges.filter((e) => keepIds.has(e.from) && keepIds.has(e.to)),
    };
  }

  function toForceGraphData(fusionGraph, gs, mlScore) {
    const active = collapseLargeGraph(pickActiveGraph(fusionGraph, gs), gs);
    const flaggedAddrs = new Set(
      (fusionGraph.risk_annotations || [])
        .filter((a) => a.type === "illicit_hit")
        .map((a) => `${a.chain}:${a.address}`)
    );
    const pathSet = new Set(gs.highlightedPath || []);

    const nodes = (active.nodes || []).map((n) => ({
      ...n,
      id: n.id,
      label: n.label || n.address?.slice(0, 10),
      flagged: flaggedAddrs.has(n.id) || n.sanctioned,
      pathActive: pathSet.has(n.id),
    }));

    const links = (active.edges || []).map((e) => {
      const source = e.from || e.source;
      const target = e.to || e.target;
      const exposure = e.exposure_type || "transfer";
      const edgeType = e.edge_type || exposure;
      const hops = e.hops;
      const pathActive = pathSet.size > 0 && _edgeOnPath(source, target, gs.highlightedPath);
      const bridgeLabel = e.bridge_name ? ` · ${e.bridge_name}` : "";
      return {
        source,
        target,
        amount: e.amount,
        asset: e.asset,
        tx_hash: e.tx_hash,
        timestamp: e.timestamp,
        exposure_type: exposure,
        edge_type: edgeType,
        hops,
        pathActive,
        label: edgeType === "cross_chain_hop"
          ? `cross-chain${bridgeLabel}`
          : exposure === "indirect" && hops ? `${hops} hop` : exposure === "direct" ? "direct" : "",
      };
    });
    return { nodes, links, mlScore };
  }

  function riskTierMeta(score) {
    const s = Number(score ?? 15);
    if (s >= 80) return { cls: "risk-critical", label: "CRITICAL" };
    if (s >= 55) return { cls: "risk-high", label: "HIGH" };
    if (s >= 30) return { cls: "risk-medium", label: "MEDIUM" };
    return { cls: "risk-low", label: "LOW" };
  }

  function sparklineSvg(values) {
    if (!values?.length) return "";
    const w = 120, h = 28, pad = 2;
    const max = Math.max(...values, 1);
    const pts = values.map((v, i) => {
      const x = pad + (i / Math.max(1, values.length - 1)) * (w - pad * 2);
      const y = h - pad - (v / max) * (h - pad * 2);
      return `${x},${y}`;
    }).join(" ");
    return `<svg class="entity-sparkline" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline fill="none" stroke="var(--accent2,#5eead4)" stroke-width="1.5" points="${pts}"/></svg>`;
  }

  function portfolioHtml(node) {
    const tokens = node.portfolio || [];
    if (!tokens.length) return "";
    const total = tokens.reduce((s, t) => s + Number(t.balance_usd || t.usd || 0), 0) || node.balance_usd || 0;
    const rows = tokens.slice(0, 5).map((t) => {
      const usd = Number(t.balance_usd || t.usd || 0);
      const pct = total > 0 ? Math.round((100 * usd) / total) : 0;
      return `<div class="entity-portfolio-row"><span class="sym">${escapeHtml(t.symbol || "?")}</span><span class="pct">${pct}%</span><span class="usd">$${usd.toLocaleString("en", { maximumFractionDigits: 0 })}</span></div>`;
    }).join("");
    return `<div class="entity-portfolio"><div class="entity-portfolio-title">Портфель</div>${rows}</div>`;
  }

  function showNodePanel(node, linkMeta, panelId, containerId) {
    const panel = document.getElementById(panelId || "graphNodePanel");
    if (!panel) return;
    const cid = containerId || (panelId === "opsGraphNodePanel" ? "opsForceGraphMount" : "forceGraphMount");
    const gs = _state(cid);
    gs.lastPanelNode = node;
    panel.classList.remove("hidden");
    const pid = panelId || "graphNodePanel";
    const rs = node.risk_score != null ? Number(node.risk_score) : 15;
    const tier = riskTierMeta(rs);
    const title = node.label && node.label !== node.address ? node.label : (node.address || node.id || "—");
    const subtitle = node.category && !["unknown", "eoa"].includes(node.category)
      ? node.category : (node.role || "address");
    const clusterHint = node.node_type === "cluster"
      ? `<p class="entity-hint">Двойной клик — развернуть/свернуть ${node.member_count} адресов</p>` : "";
    const spark = sparklineSvg(node.activity_sparkline);
    const pin = gs.pins?.[node.id];
    const pinBlock = pin
      ? `<p class="entity-hint">📌 ${escapeHtml(pin.note)} <button type="button" class="btn-link" onclick="FinSkalpGraph.unpinNode('${escapeHtml(node.id)}','${cid}')">снять</button></p>`
      : `<button type="button" class="btn btn-outline btn-sm" style="margin:0.35rem 0" onclick="FinSkalpGraph.pinNode('${escapeHtml(node.id)}', prompt('Заметка аналитика','pin')||'pin','${cid}')">📌 Закрепить узел</button>`;
    panel.innerHTML = `
      <div class="entity-card">
        <div class="graph-panel-head">
          <div class="entity-card-head">
            <h4 class="entity-title">${escapeHtml(title)}</h4>
            <span class="entity-subtitle">${escapeHtml(subtitle)}</span>
          </div>
          <button type="button" class="btn-icon" onclick="FinSkalpGraph.closePanel('${pid}')" aria-label="Закрыть">×</button>
        </div>
        <div class="entity-risk-badge ${tier.cls}">
          <span class="entity-risk-num">${Math.round(rs)}</span>
          <span class="entity-risk-lbl">Risk Score · ${tier.label}</span>
        </div>
        ${clusterHint}
        ${pinBlock}
        ${portfolioHtml(node)}
        ${spark ? `<div class="entity-spark-wrap"><span class="entity-spark-label">Активность</span>${spark}</div>` : ""}
        <dl class="graph-dl entity-dl">
          <dt>Адрес</dt><dd class="mono">${escapeHtml(node.address || node.id)}</dd>
          <dt>Сеть</dt><dd>${escapeHtml(node.chain || "—")}</dd>
          <dt>Hop</dt><dd>${node.hop ?? "—"}</dt>
          <dt>Роль</dt><dd>${escapeHtml(node.role || "—")}</dd>
          ${node.member_count ? `<dt>В кластере</dt><dd>${node.member_count} адресов</dd>` : ""}
          ${node.category ? `<dt>Категория</dt><dd>${escapeHtml(node.category)}</dd>` : ""}
          ${node.confidence_pct != null ? `<dt>Confidence</dt><dd>${node.confidence_pct}%</dd>` : ""}
          ${node.attribution_source ? `<dt>Источник</dt><dd>${escapeHtml(node.attribution_source)}</dd>` : ""}
          ${node.flagged || node.sanctioned ? '<dt>Статус</dt><dd class="risk-critical-text">⚠ Flagged</dd>' : ""}
          ${linkMeta ? `<dt>Связь</dt><dd>${escapeHtml(linkMeta.exposure || "")} ${linkMeta.hops ? `· ${linkMeta.hops} hop` : ""} · ${escapeHtml(linkMeta.asset || "")} ${escapeHtml(String(linkMeta.amount || ""))}</dd>` : ""}
        </dl>
      </div>`;
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function findPathForLink(link, payload) {
    const paths = payload?.exposure_paths || [];
    const source = typeof link.source === "object" ? link.source.id : link.source;
    const target = typeof link.target === "object" ? link.target.id : link.target;
    const edgeMatch = paths.find((p) => _edgeOnPath(source, target, p.path));
    if (edgeMatch?.path) return edgeMatch.path;
    const nodeMatch = paths.find((p) => p.path?.includes(target) || p.path?.includes(source));
    return nodeMatch?.path || null;
  }

  function _linkParticles(link, gs, edgeCount) {
    if (edgeCount > 200 || prefersReducedMotion()) return 0;
    if (link.pathActive) return Math.min(4, 3);
    if (link.exposure_type === "direct") return 3;
    if (link.edge_type === "cross_chain_hop") return 2;
    if (link.exposure_type === "indirect") return 1;
    return gs.timelinePlaying ? 2 : 0;
  }

  function _linkParticleSpeed(gs) {
    return gs.timelinePlaying ? 0.014 : 0.006;
  }

  function _linkColor(l, isDark, gs) {
    const flashKey = _edgeKey(l.source, l.target);
    const flashUntil = gs.flashEdges?.[flashKey];
    if (flashUntil && Date.now() < flashUntil) return isDark ? "#fde68a" : "#f59e0b";
    if (l.pathActive) return isDark ? "rgba(251,191,36,0.95)" : "#f59e0b";
    if (l.edge_type === "cross_chain_hop") return isDark ? "rgba(167,139,250,0.9)" : "rgba(124,58,237,0.75)";
    if (l.exposure_type === "direct") return isDark ? "rgba(248,113,113,0.85)" : "rgba(220,38,38,0.75)";
    if (l.exposure_type === "indirect") return isDark ? "rgba(148,163,184,0.35)" : "rgba(100,116,139,0.45)";
    return isDark ? "rgba(148,163,184,0.45)" : "rgba(71,85,105,0.5)";
  }

  function _linkWidth(l) {
    if (l.pathActive) return 4.5;
    if (l.edge_type === "cross_chain_hop") return 2.4;
    if (l.exposure_type === "direct") return 2.8;
    if (l.exposure_type === "indirect") return 1.2;
    return 1.2;
  }

  function _trackTimelineEdges(links, gs) {
    const nextKeys = new Set();
    for (const l of links) nextKeys.add(_edgeKey(l.source, l.target));
    if (gs.timelinePlaying && gs.prevVisibleEdgeKeys.size) {
      for (const k of nextKeys) {
        if (!gs.prevVisibleEdgeKeys.has(k)) {
          gs.flashEdges[k] = Date.now() + 480;
        }
      }
    }
    gs.prevVisibleEdgeKeys = nextKeys;
  }

  function _startAnimLoop(containerId) {
    const gs = _state(containerId);
    if (gs._animRaf || prefersReducedMotion()) return;
    const tick = (ts) => {
      gs._animT = ts / 1000;
      instances[containerId]?.refresh?.();
      gs._animRaf = requestAnimationFrame(tick);
    };
    gs._animRaf = requestAnimationFrame(tick);
  }

  function _stopAnimLoop(containerId) {
    const gs = _state(containerId);
    if (gs._animRaf) {
      cancelAnimationFrame(gs._animRaf);
      gs._animRaf = null;
    }
  }

  function _paintNodeCanvas(node, ctx, globalScale, containerId, mlScore) {
    const gs = _state(containerId);
    const ring = CHAIN_RING[node.chain] || "#64748b";
    const baseR = Math.sqrt(Math.max(0, nodeVal(node))) * 4 + 2;
    const t = gs._animT || 0;
    const isCluster = node.node_type === "cluster";
    const breathe = isCluster && !prefersReducedMotion() ? 1 + 0.06 * Math.sin(t * 1.8) : 1;
    const r = baseR * breathe;
    const glowColor = _riskGlowForNode(node, mlScore);

    if (!prefersReducedMotion()) {
      const glowR = r + 5 / globalScale;
      ctx.beginPath();
      ctx.arc(node.x, node.y, glowR, 0, 2 * Math.PI, false);
      ctx.strokeStyle = glowColor;
      ctx.globalAlpha = node.pathActive ? 0.55 : 0.28;
      ctx.lineWidth = 3 / globalScale;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    if (gs.selectedNodeId === node.id && !prefersReducedMotion()) {
      const pulse = 0.5 + 0.5 * Math.sin(t * 4.2);
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + (4 + pulse * 4) / globalScale, 0, 2 * Math.PI, false);
      ctx.strokeStyle = "#60a5fa";
      ctx.lineWidth = (1.5 + pulse) / globalScale;
      ctx.globalAlpha = 0.35 + pulse * 0.35;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    ctx.beginPath();
    ctx.arc(node.x, node.y, r + 2 / globalScale, 0, 2 * Math.PI, false);
    ctx.strokeStyle = ring;
    ctx.lineWidth = 1.5 / globalScale;
    ctx.stroke();

    const pin = gs.pins?.[node.id];
    if (pin) {
      ctx.fillStyle = "#fbbf24";
      ctx.beginPath();
      ctx.arc(node.x + r * 0.7, node.y - r * 0.7, 3 / globalScale, 0, 2 * Math.PI);
      ctx.fill();
      if (pin.note && globalScale > 0.35) {
        const note = String(pin.note).slice(0, 28);
        ctx.font = `${Math.max(5, 7 / globalScale)}px sans-serif`;
        ctx.fillStyle = "rgba(251,191,36,0.95)";
        ctx.fillText(note, node.x + r * 0.4, node.y - r - 5 / globalScale);
      }
    }
    if (node.defi_type || node.category === "defi") {
      ctx.fillStyle = "#a855f7";
      ctx.font = `${8 / globalScale}px sans-serif`;
      ctx.fillText("DeFi", node.x - r, node.y + r + 8 / globalScale);
    }
  }

  function _applyForceGraphVisuals(fg, containerId, nodes, links, mlScore) {
    const gs = _state(containerId);
    const isDark = (document.documentElement.getAttribute("data-theme") || "dark") === "dark";
    const pathSet = new Set(gs.highlightedPath || []);
    const edgeCount = links.length;

    _trackTimelineEdges(links, gs);

    fg
      .nodeVal(nodeVal)
      .nodeColor((n) => (pathSet.size && pathSet.has(n.id) ? "#fbbf24" : riskColor(n, mlScore)))
      .nodeCanvasObjectMode(() => "after")
      .nodeCanvasObject((node, ctx, globalScale) => _paintNodeCanvas(node, ctx, globalScale, containerId, mlScore))
      .linkWidth(_linkWidth)
      .linkLabel((l) => l.label || "")
      .linkColor((l) => _linkColor(l, isDark, gs))
      .linkDirectionalParticles((l) => _linkParticles(l, gs, edgeCount))
      .linkDirectionalParticleWidth((l) => (l.pathActive ? 2.8 : 2))
      .linkDirectionalParticleSpeed(_linkParticleSpeed(gs));
  }

  function _focusNodeCamera(containerId, node) {
    const fg = instances[containerId];
    if (!fg || node.x == null || prefersReducedMotion()) return;
    const curZoom = fg.zoom?.() ?? 1;
    const targetZoom = Math.min(4, Math.max(curZoom, 2.2));
    fg.centerAt(node.x, node.y, 600);
    fg.zoom(targetZoom, 600);
  }

  function _resizeGraph(containerId) {
    if (_isSigmaInstance(containerId)) {
      _resizeSigma(containerId);
      return;
    }
    const el = document.getElementById(containerId);
    const fg = instances[containerId];
    if (!el || !fg) return;
    const w = el.clientWidth;
    const h = el.clientHeight;
    if (w > 0 && h > 0) {
      fg.width(w).height(h);
    }
  }

  function refreshGraph(containerId) {
    const cid = containerId || "forceGraphMount";
    if (_isSigmaInstance(cid)) {
      _refreshSigma(cid);
      _resizeSigma(cid);
      return;
    }
    const fg = instances[cid];
    const gs = _state(cid);
    if (!fg || !gs.payload) return;
    const { nodes, links, mlScore } = toForceGraphData(gs.payload, gs, gs.opts.mlScore);

    fg.graphData({ nodes, links });
    _applyForceGraphVisuals(fg, cid, nodes, links, mlScore);
    _resizeGraph(cid);
  }

  function _sigmaAvailable() {
    return typeof graphology !== "undefined" && typeof Sigma !== "undefined";
  }

  function _pickRenderer(totalNodes, gs) {
    const mode = gs.rendererMode || "auto";
    if (mode === "force") return "force";
    if (mode === "sigma") return _sigmaAvailable() ? "sigma" : "force";
    if (totalNodes > WEBGL_NODE_THRESHOLD && _sigmaAvailable()) return "sigma";
    return "force";
  }

  function _layoutCircle(nodes) {
    const n = nodes.length;
    const R = Math.max(90, Math.sqrt(n) * 14);
    nodes.forEach((node, i) => {
      if (node.x == null || node.y == null) {
        const a = (2 * Math.PI * i) / Math.max(1, n);
        node.x = R * Math.cos(a);
        node.y = R * Math.sin(a);
      }
    });
  }

  function _isSigmaInstance(containerId) {
    return Boolean(instances[containerId]?._sigma);
  }

  function _destroySigma(containerId) {
    const sig = sigmaInstances[containerId];
    if (sig) {
      sig.kill?.();
      delete sigmaInstances[containerId];
    }
  }

  function _mountSigmaRenderer(containerId, fusionGraph, opts, gs) {
    const el = document.getElementById(containerId);
    if (!el || !_sigmaAvailable()) return null;
    _destroySigma(containerId);
    el.innerHTML = "";
    const panelId = opts.panelId || (containerId === "opsForceGraphMount" ? "opsGraphNodePanel" : "graphNodePanel");
    const { nodes, links, mlScore } = toForceGraphData(fusionGraph, gs, opts.mlScore);
    _layoutCircle(nodes);
    const Graph = graphology.Graph;
    const g = new Graph();
    const isDark = (document.documentElement.getAttribute("data-theme") || "dark") === "dark";
    nodes.forEach((n) => {
      g.addNode(n.id, {
        label: String(n.address || n.id || "").slice(0, 14),
        size: nodeVal(n),
        color: riskColor(n, mlScore),
        x: n.x,
        y: n.y,
        finNode: n,
      });
    });
    links.forEach((l) => {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      if (g.hasNode(s) && g.hasNode(t) && !g.hasUndirectedEdge(s, t)) {
        g.addEdge(s, t, {
          size: _linkWidth(l),
          color: _linkColor(l, isDark, gs),
        });
      }
    });
    const sigma = new Sigma(g, el, {
      renderLabels: nodes.length < 350,
      labelDensity: 0.07,
      labelGridCellSize: 60,
      enableEdgeEvents: true,
      allowInvalidContainer: true,
      defaultNodeType: "circle",
      defaultEdgeType: "line",
    });
    sigma.on("clickNode", ({ node }) => {
      const fin = g.getNodeAttributes(node).finNode;
      if (fin) {
        gs.selectedNodeId = fin.id;
        showNodePanel(fin, null, panelId, containerId);
      }
    });
    sigmaInstances[containerId] = sigma;
    instances[containerId] = {
      _sigma: true,
      _destructor: () => _destroySigma(containerId),
      zoom: () => 1 / (sigma.getCamera().ratio || 1),
      centerAt: (x, y) => {
        const cam = sigma.getCamera();
        cam.x = x ?? cam.x;
        cam.y = y ?? cam.y;
        sigma.refresh();
        return { x: cam.x, y: cam.y };
      },
      zoomToFit: () => {
        sigma.getCamera().animatedReset({ duration: prefersReducedMotion() ? 0 : 400 });
      },
      refresh: () => sigma.refresh(),
      width: () => instances[containerId],
      height: () => instances[containerId],
    };
    if (!prefersReducedMotion()) {
      sigma.getCamera().animatedReset({ duration: 500 });
    }
    return sigma;
  }

  function _refreshSigma(containerId) {
    const gs = _state(containerId);
    const sigma = sigmaInstances[containerId];
    if (!sigma || !gs.payload) return;
    const { nodes, links, mlScore } = toForceGraphData(gs.payload, gs, gs.opts.mlScore);
    const g = sigma.getGraph();
    const isDark = (document.documentElement.getAttribute("data-theme") || "dark") === "dark";
    g.forEachNode((id) => {
      if (!nodes.find((n) => n.id === id)) g.dropNode(id);
    });
    _layoutCircle(nodes);
    nodes.forEach((n) => {
      const attrs = {
        label: String(n.address || n.id || "").slice(0, 14),
        size: nodeVal(n),
        color: riskColor(n, mlScore),
        x: n.x,
        y: n.y,
        finNode: n,
      };
      if (g.hasNode(n.id)) g.mergeNodeAttributes(n.id, attrs);
      else g.addNode(n.id, attrs);
    });
    g.clearEdges();
    links.forEach((l) => {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      if (g.hasNode(s) && g.hasNode(t)) {
        g.addEdge(s, t, { size: _linkWidth(l), color: _linkColor(l, isDark, gs) });
      }
    });
    sigma.refresh();
  }

  function _resizeSigma(containerId) {
    const el = document.getElementById(containerId);
    const sigma = sigmaInstances[containerId];
    if (!el || !sigma) return;
    sigma.resize();
  }

  function _toggleRendererMode(containerId) {
    const gs = _state(containerId);
    const cur = gs.rendererMode || "auto";
    if (cur === "auto") gs.rendererMode = "sigma";
    else if (cur === "sigma") gs.rendererMode = "force";
    else gs.rendererMode = "auto";
    const payload = gs.payload;
    const opts = gs.opts;
    if (payload) mount(containerId, payload, opts);
    const labels = { auto: "WebGL авто", sigma: "WebGL вкл", force: "Canvas2D" };
    toastFallback(`Рендер: ${labels[gs.rendererMode] || gs.rendererMode}`);
  }

  function _viewsApiUrl(gs) {
    const inv = gs.opts?.investigationId;
    if (!inv) return null;
    return `${gs.opts.apiBase || ""}/api/investigations/${encodeURIComponent(inv)}/graph/views`;
  }

  async function _fetchSavedViews(gs) {
    const url = _viewsApiUrl(gs);
    if (url) {
      try {
        const r = await fetch(url);
        if (r.ok) {
          const body = await r.json();
          return body.views || [];
        }
      } catch { /* local fallback */ }
    }
    return _loadSavedViews(gs);
  }

  async function _persistViewRemote(gs, entry) {
    const url = _viewsApiUrl(gs);
    if (!url) return false;
    try {
      const r = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: entry.name,
          zoom: entry.zoom,
          center: entry.center,
          expanded_clusters: entry.expandedClusters || entry.expanded_clusters || [],
          timeline_ts: entry.timelineCutoff ?? entry.timeline_ts,
          pins: gs.pins || entry.pins || {},
          view_mode: entry.viewMode || entry.view_mode || "cluster",
          highlighted_path: entry.highlightedPath || entry.highlighted_path,
        }),
      });
      return r.ok;
    } catch {
      return false;
    }
  }

  function _perfTune(fg, nodeCount, edgeCount) {
    if (!fg || fg._sigma) return;
    const edges = edgeCount ?? 0;
    if (nodeCount > 500 || edges > 200) {
      fg.enableNodeDrag?.(false);
      fg.linkDirectionalParticles(0).cooldownTicks(40).d3AlphaDecay(0.06).d3VelocityDecay(0.45);
    } else if (nodeCount > 200) {
      fg.linkDirectionalParticles(0).cooldownTicks(80).d3AlphaDecay(0.04);
    } else if (nodeCount > 80) {
      fg.cooldownTicks(120);
    }
  }

  function _loadPins(gs) {
    const inv = gs.opts?.investigationId;
    if (!inv) return;
    try {
      const raw = localStorage.getItem(`finskalp:pins:${inv}`);
      gs.pins = raw ? JSON.parse(raw) : {};
    } catch {
      gs.pins = {};
    }
  }

  function _savePins(gs) {
    const inv = gs.opts?.investigationId;
    if (!inv) return;
    try {
      localStorage.setItem(`finskalp:pins:${inv}`, JSON.stringify(gs.pins || {}));
    } catch { /* ignore */ }
  }

  function _viewsKey(inv) {
    return `finskalp:graph-views:${inv}`;
  }

  function _loadSavedViews(gs) {
    const inv = gs.opts?.investigationId;
    if (!inv) return [];
    try {
      const raw = localStorage.getItem(_viewsKey(inv));
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  function _persistSavedViews(gs, views) {
    const inv = gs.opts?.investigationId;
    if (!inv) return;
    try {
      localStorage.setItem(_viewsKey(inv), JSON.stringify(views.slice(-12)));
    } catch { /* ignore */ }
  }

  function captureGraphView(containerId) {
    const gs = _state(containerId);
    const fg = instances[containerId];
    const sigma = sigmaInstances[containerId];
    if (sigma) {
      const cam = sigma.getCamera();
      return {
        viewMode: gs.viewMode,
        expandedClusters: [...gs.expandedClusters],
        highlightedPath: gs.highlightedPath ? [...gs.highlightedPath] : null,
        timelineCutoff: gs.timelineCutoff,
        zoom: 1 / (cam.ratio || 1),
        center: { x: cam.x ?? 0, y: cam.y ?? 0 },
        pins: { ...(gs.pins || {}) },
      };
    }
    if (!fg) return null;
    const center = fg.centerAt?.() || { x: 0, y: 0 };
    return {
      viewMode: gs.viewMode,
      expandedClusters: [...gs.expandedClusters],
      highlightedPath: gs.highlightedPath ? [...gs.highlightedPath] : null,
      timelineCutoff: gs.timelineCutoff,
      zoom: fg.zoom?.() ?? 1,
      center: { x: center.x ?? 0, y: center.y ?? 0 },
      pins: { ...(gs.pins || {}) },
    };
  }

  function restoreGraphView(containerId, viewState) {
    const gs = _state(containerId);
    if (!viewState) return;
    gs.viewMode = viewState.viewMode || viewState.view_mode || "cluster";
    gs.expandedClusters = new Set(viewState.expandedClusters || viewState.expanded_clusters || []);
    gs.highlightedPath = viewState.highlightedPath || viewState.highlighted_path || null;
    gs.timelineCutoff = viewState.timelineCutoff ?? viewState.timeline_ts ?? gs.payload?.timeline?.max_ts ?? null;
    if (viewState.pins) gs.pins = viewState.pins;
    const slot = _timelineSlot(containerId);
    const slider = slot?.querySelector("[data-tl-slider]");
    if (slider && gs.timelineCutoff != null) slider.value = String(gs.timelineCutoff);
    refreshGraph(containerId);
    document.querySelectorAll(`[data-graph-toolbar="${containerId}"] [data-graph-view]`).forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.graphView === gs.viewMode);
    });
    const dur = prefersReducedMotion() ? 0 : 400;
    if (_isSigmaInstance(containerId)) {
      const cam = sigmaInstances[containerId]?.getCamera?.();
      if (cam) {
        cam.animate(
          { x: viewState.center?.x ?? 0, y: viewState.center?.y ?? 0, ratio: viewState.zoom ?? 1 },
          { duration: dur }
        );
      }
      return;
    }
    const fg = instances[containerId];
    if (!fg) return;
    fg.centerAt(viewState.center?.x ?? 0, viewState.center?.y ?? 0, dur);
    fg.zoom(viewState.zoom ?? 1, dur);
  }

  async function saveNamedView(name, containerId) {
    const cid = containerId || "forceGraphMount";
    const gs = _state(cid);
    const label = (name || "").trim();
    if (!label) return false;
    const state = captureGraphView(cid);
    if (!state) return false;
    const entry = { name: label, saved_at: Date.now(), ...state };
    const remoteOk = await _persistViewRemote(gs, entry);
    if (!remoteOk) {
      const views = _loadSavedViews(gs);
      const idx = views.findIndex((v) => v.name === label);
      if (idx >= 0) views[idx] = entry;
      else views.push(entry);
      _persistSavedViews(gs, views);
    }
    await _refreshViewsDropdown(cid);
    return true;
  }

  async function _refreshViewsDropdown(containerId) {
    const gs = _state(containerId);
    const sel = _toolbarActions(containerId)?.querySelector("[data-graph-restore-view]");
    if (!sel) return;
    const views = await _fetchSavedViews(gs);
    sel.innerHTML = views.length
      ? `<option value="">Вид…</option>${views.map((v) => `<option value="${escapeHtml(v.name)}">${escapeHtml(v.name)}</option>`).join("")}`
      : `<option value="">Нет сохранённых</option>`;
  }

  function pinNode(nodeId, note, containerId) {
    const gs = _state(containerId || "forceGraphMount");
    if (!nodeId) return;
    gs.pins = gs.pins || {};
    gs.pins[nodeId] = { note: note || "Analyst pin", ts: Date.now() };
    _savePins(gs);
    refreshGraph(containerId || "forceGraphMount");
    if (gs.lastPanelNode?.id === nodeId) showNodePanel(gs.lastPanelNode, null, gs.opts.panelId);
  }

  function unpinNode(nodeId, containerId) {
    const gs = _state(containerId || "forceGraphMount");
    if (gs.pins) delete gs.pins[nodeId];
    _savePins(gs);
    refreshGraph(containerId || "forceGraphMount");
  }

  function setViewMode(mode, containerId) {
    const cid = containerId || "forceGraphMount";
    const gs = _state(cid);
    gs.viewMode = mode;
    document.querySelectorAll(`[data-graph-toolbar="${cid}"] [data-graph-view]`).forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.graphView === mode);
    });
    refreshGraph(cid);
  }

  function _cleanupUi(containerId) {
    const gs = _state(containerId);
    _stopAnimLoop(containerId);
    if (gs.playTimer) clearInterval(gs.playTimer);
    gs.timelinePlaying = false;
    const slot = _timelineSlot(containerId);
    if (slot) slot.innerHTML = "";
    const ccSlot = _crossChainSlot(containerId);
    if (ccSlot) ccSlot.innerHTML = "";
    const actions = _toolbarActions(containerId);
    if (actions) {
      actions.innerHTML = "";
      delete actions.dataset.graphToolbarBound;
    }
  }

  function _bindToolbar(containerId) {
    const actions = _toolbarActions(containerId);
    if (!actions || actions.dataset.graphToolbarBound) return;
    actions.dataset.graphToolbarBound = "1";
    const gs = _state(containerId);
    const rawCount = (gs.payload?.address_view?.nodes || gs.payload?.nodes || []).length;
    actions.innerHTML = `
      <span class="graph-node-badge" data-graph-badge>${rawCount} узл.</span>
      <button type="button" class="btn btn-outline btn-sm ${gs.viewMode === "cluster" ? "active" : ""}" data-graph-view="cluster">Кластеры</button>
      <button type="button" class="btn btn-outline btn-sm ${gs.viewMode === "address" ? "active" : ""}" data-graph-view="address">Адреса</button>
      <button type="button" class="btn btn-outline btn-sm" data-graph-paths>Exposure</button>
      <button type="button" class="btn btn-outline btn-sm" data-graph-cross-chain>Cross-chain</button>
      <button type="button" class="btn btn-outline btn-sm" data-graph-export="json">JSON</button>
      <button type="button" class="btn btn-outline btn-sm" data-graph-export="graphml">GraphML</button>
      <button type="button" class="btn btn-outline btn-sm" data-graph-export="png">PNG</button>
      <button type="button" class="btn btn-outline btn-sm" data-graph-webgl title="Переключить WebGL (sigma.js)">WebGL</button>
      <button type="button" class="btn btn-outline btn-sm" data-graph-save-view title="Сохранить zoom/кластеры">💾</button>
      <select class="graph-views-select" data-graph-restore-view title="Восстановить вид"><option value="">Вид…</option></select>`;
    actions.querySelectorAll("[data-graph-view]").forEach((btn) => {
      btn.addEventListener("click", () => setViewMode(btn.dataset.graphView, containerId));
    });
    actions.querySelector("[data-graph-paths]")?.addEventListener("click", () => {
      const paths = gs.payload?.exposure_paths || [];
      if (!paths.length) {
        toastFallback("Нет indirect exposure paths");
        return;
      }
      const lines = paths.slice(0, 8).map((p) =>
        `· ${p.hops} hop · risk ${p.risk_score ?? "—"} · ${(p.path || []).slice(-2).join(" → ")}`
      ).join("\n");
      toastFallback(lines.slice(0, 240));
    });
    actions.querySelector("[data-graph-cross-chain]")?.addEventListener("click", () => {
      _toggleCrossChainPanel(containerId);
    });
    actions.querySelector("[data-graph-export=json]")?.addEventListener("click", () => {
      if (!gs.payload) return;
      const blob = new Blob([JSON.stringify(gs.payload, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "finskalp_graph.json";
      a.click();
    });
    actions.querySelector("[data-graph-export=graphml]")?.addEventListener("click", async () => {
      const inv = gs.opts.investigationId;
      const q = inv ? `?investigation_id=${encodeURIComponent(inv)}&format=graphml` : "";
      try {
        const r = await fetch(`${gs.opts.apiBase || ""}/api/graph/export${q}`);
        if (!r.ok) throw new Error("export failed");
        const blob = await r.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "finskalp_graph.graphml";
        a.click();
      } catch {
        toastFallback("GraphML export requires investigation_id");
      }
    });
    actions.querySelector("[data-graph-export=png]")?.addEventListener("click", () => {
      const canvas = document.getElementById(containerId)?.querySelector("canvas");
      if (!canvas) return;
      canvas.toBlob((blob) => {
        if (!blob) return;
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "finskalp_graph.png";
        a.click();
      }, "image/png");
    });
    actions.querySelector("[data-graph-webgl]")?.addEventListener("click", () => {
      _toggleRendererMode(containerId);
    });
    actions.querySelector("[data-graph-save-view]")?.addEventListener("click", async () => {
      if (!gs.opts.investigationId) {
        toastFallback("Сохранение вида требует investigation_id");
        return;
      }
      const name = prompt("Имя сохранённого вида", `view-${new Date().toISOString().slice(0, 16)}`);
      if (await saveNamedView(name, containerId)) toastFallback(`Вид «${name}» сохранён`);
    });
    actions.querySelector("[data-graph-restore-view]")?.addEventListener("change", async (ev) => {
      const name = ev.target.value;
      if (!name) return;
      const views = await _fetchSavedViews(gs);
      const view = views.find((v) => v.name === name);
      if (view) {
        restoreGraphView(containerId, view);
        toastFallback(`Вид «${name}» восстановлен`);
      }
      ev.target.value = "";
    });
    _refreshViewsDropdown(containerId);
  }

  function _crossChainLinks(payload) {
    return payload?.cross_chain_links
      || payload?.address_view?.cross_chain_links
      || [];
  }

  function _renderCrossChainPanel(containerId) {
    const slot = _crossChainSlot(containerId);
    const gs = _state(containerId);
    if (!slot) return;
    const links = _crossChainLinks(gs.payload);
    if (!links.length) {
      slot.innerHTML = `<div class="graph-cross-chain-panel"><p class="graph-cross-chain-empty">Нет cross-chain связей (bridge heuristic)</p></div>`;
      return;
    }
    const rows = links.slice(0, 12).map((l) => {
      const from = shortAddr(l.from_address);
      const to = shortAddr(l.to_address);
      const conf = l.confidence != null ? `${Math.round(l.confidence * 100)}%` : "—";
      const bridge = l.bridge_name ? ` · ${l.bridge_name}` : "";
      return `<div class="graph-cross-chain-row">
        <span class="chain">${escapeHtml(l.from_chain || "?")}→${escapeHtml(l.to_chain || "?")}</span>
        <span class="addrs" title="${escapeHtml(l.from_address || "")} → ${escapeHtml(l.to_address || "")}">${escapeHtml(from)} → ${escapeHtml(to)}</span>
        <span class="conf">${escapeHtml(conf)}${escapeHtml(bridge)}</span>
      </div>`;
    }).join("");
    slot.innerHTML = `<div class="graph-cross-chain-panel"><div class="graph-cross-chain-title">Cross-chain hops · ${links.length}</div>${rows}</div>`;
  }

  function _toggleCrossChainPanel(containerId) {
    const slot = _crossChainSlot(containerId);
    const btn = _toolbarActions(containerId)?.querySelector("[data-graph-cross-chain]");
    if (!slot) return;
    const open = slot.dataset.open === "1";
    if (open) {
      slot.innerHTML = "";
      slot.dataset.open = "0";
      btn?.classList.remove("active");
      return;
    }
    _renderCrossChainPanel(containerId);
    slot.dataset.open = "1";
    btn?.classList.add("active");
  }

  function shortAddr(a) {
    if (!a) return "—";
    const s = String(a);
    return s.length > 14 ? `${s.slice(0, 6)}…${s.slice(-4)}` : s;
  }

  function _bindTimeline(containerId) {
    const slot = _timelineSlot(containerId);
    const gs = _state(containerId);
    const tl = gs.payload?.timeline;
    if (!slot || !tl?.event_count) return;

    slot.innerHTML = `
      <div class="graph-timeline">
        <button type="button" class="btn btn-outline btn-sm" data-tl-play>▶ Play</button>
        <input type="range" class="graph-tl-slider" data-tl-slider min="${tl.min_ts}" max="${tl.max_ts}" value="${tl.max_ts}" />
        <span class="graph-tl-label" data-tl-label></span>
      </div>`;

    const slider = slot.querySelector("[data-tl-slider]");
    const label = slot.querySelector("[data-tl-label]");
    const fmt = (ts) => new Date(Number(ts)).toLocaleString("ru");

    const update = () => {
      gs.timelineCutoff = Number(slider.value);
      label.textContent = fmt(slider.value);
      refreshGraph(containerId);
    };
    slider.addEventListener("input", update);
    update();

    slot.querySelector("[data-tl-play]")?.addEventListener("click", () => {
      const playBtn = slot.querySelector("[data-tl-play]");
      if (gs.timelinePlaying) {
        gs.timelinePlaying = false;
        clearInterval(gs.playTimer);
        playBtn.textContent = "▶ Play";
        return;
      }
      gs.timelinePlaying = true;
      playBtn.textContent = "⏸ Pause";
      gs.prevVisibleEdgeKeys = new Set();
      slider.value = String(tl.min_ts);
      const step = Math.max(1, Math.floor((tl.max_ts - tl.min_ts) / Math.min(60, tl.event_count)));
      gs.playTimer = setInterval(() => {
        const cur = Number(slider.value) + step;
        if (cur >= tl.max_ts) {
          slider.value = String(tl.max_ts);
          gs.timelinePlaying = false;
          clearInterval(gs.playTimer);
          playBtn.textContent = "▶ Play";
        } else {
          slider.value = String(cur);
        }
        update();
      }, 120);
    });
  }

  function _observeResize(containerId) {
    const el = document.getElementById(containerId);
    if (!el || typeof ResizeObserver === "undefined") return;
    resizeObservers[containerId]?.disconnect();
    let raf = 0;
    resizeObservers[containerId] = new ResizeObserver(() => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        if (_isSigmaInstance(containerId)) _resizeSigma(containerId);
        else _resizeGraph(containerId);
      });
    });
    resizeObservers[containerId].observe(el);
  }

  function hasGraphData(fusionGraph) {
    return Boolean(
      fusionGraph?.nodes?.length
      || fusionGraph?.cluster_view?.nodes?.length
      || fusionGraph?.address_view?.nodes?.length
    );
  }

  function mount(containerId, fusionGraph, opts = {}) {
    const el = document.getElementById(containerId);
    const wrap = opts.wrapId ? document.getElementById(opts.wrapId) : _wrapFor(containerId);
    const panelId = opts.panelId || (containerId === "opsForceGraphMount" ? "opsGraphNodePanel" : "graphNodePanel");
    const gs = _state(containerId);

    if (!el || !hasGraphData(fusionGraph)) {
      if (wrap && !opts.alwaysShow) wrap.classList.add("hidden");
      destroy({ containerId, skipWrap: opts.alwaysShow });
      return null;
    }
    if (wrap && !opts.alwaysShow) {
      wrap.classList.remove("hidden");
      wrap.setAttribute("aria-hidden", "false");
    }

    if (typeof ForceGraph !== "function") {
      el.innerHTML = '<p class="summary-text">Force-graph library not loaded</p>';
      return null;
    }

    _cleanupUi(containerId);
    el.innerHTML = "";

    gs.payload = fusionGraph;
    gs.viewMode = fusionGraph.default_view || "cluster";
    _loadPins(gs);
    const totalNodes = (fusionGraph.address_view?.nodes || fusionGraph.nodes || []).length;
    if (totalNodes > 150) {
      gs.viewMode = "cluster";
      toastFallback(`Граф ${totalNodes} узлов — режим кластеров (A6)`);
    }
    if (totalNodes > WEBGL_NODE_THRESHOLD && _pickRenderer(totalNodes, gs) === "sigma") {
      toastFallback(`Граф ${totalNodes} узлов — WebGL (sigma.js) · prefers-reduced-motion: ${prefersReducedMotion() ? "статично" : "анимации"}`);
    } else if (totalNodes > 500) {
      toastFallback(`Граф ${totalNodes} узлов — Canvas2D + auto-cluster`);
    }
    gs.expandedClusters = new Set();
    gs.highlightedPath = null;
    gs.timelineCutoff = fusionGraph.timeline?.max_ts || null;
    gs.opts = opts;

    if (instances[containerId]) {
      instances[containerId]._destructor?.();
      instances[containerId] = null;
    }
    _destroySigma(containerId);

    gs.selectedNodeId = null;
    gs.prevVisibleEdgeKeys = new Set();
    gs.flashEdges = {};

    const renderer = _pickRenderer(totalNodes, gs);
    gs.activeRenderer = renderer;

    if (renderer === "sigma") {
      _mountSigmaRenderer(containerId, fusionGraph, opts, gs);
      _bindToolbar(containerId);
      _bindTimeline(containerId);
      _observeResize(containerId);
      return sigmaInstances[containerId];
    }

    const { nodes, links, mlScore } = toForceGraphData(fusionGraph, gs, opts.mlScore);

    const fg = ForceGraph()(el)
      .graphData({ nodes, links })
      .backgroundColor("transparent")
      .nodeRelSize(6)
      .nodeLabel((n) => `${n.address || n.id}\n hop ${n.hop ?? 0}${n.member_count ? `\n cluster ×${n.member_count}` : ""}`)
      .onNodeClick((node) => {
        const gsLocal = _state(containerId);
        const now = Date.now();
        const dbl = gsLocal._lastNodeClick?.id === node.id && now - (gsLocal._lastNodeClick?.t || 0) < 400;
        gsLocal._lastNodeClick = { id: node.id, t: now };
        if (dbl && node.node_type === "cluster" && node.id) {
          if (gsLocal.expandedClusters.has(node.id)) {
            gsLocal.expandedClusters.delete(node.id);
          } else {
            gsLocal.expandedClusters.add(node.id);
          }
          gsLocal.viewMode = "cluster";
          refreshGraph(containerId);
          return;
        }
        gsLocal.selectedNodeId = node.id;
        _focusNodeCamera(containerId, node);
        showNodePanel(node, null, panelId, containerId);
        fg.d3ReheatSimulation?.();
      })
      .onLinkClick((link) => {
        const target = typeof link.target === "object" ? link.target : { id: link.target };
        showNodePanel(target, {
          asset: link.asset,
          amount: link.amount,
          exposure: link.exposure_type,
          hops: link.hops,
        }, panelId, containerId);
        if (link.exposure_type === "indirect") {
          gs.highlightedPath = findPathForLink(link, gs.payload);
        } else {
          gs.highlightedPath = null;
        }
        refreshGraph(containerId);
      })
      .width(Math.max(el.clientWidth, 200))
      .height(Math.max(el.clientHeight, 180));

    instances[containerId] = fg;
    _applyForceGraphVisuals(fg, containerId, nodes, links, mlScore);
    _bindToolbar(containerId);
    _bindTimeline(containerId);
    _observeResize(containerId);
    if (!prefersReducedMotion()) _startAnimLoop(containerId);

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        _resizeGraph(containerId);
        fg.zoomToFit(400, 36);
        _perfTune(fg, nodes.length, links.length);
      });
    });

    return fg;
  }

  function toastFallback(msg) {
    if (typeof global.toast === "function") global.toast(msg);
  }

  function closePanel(panelId) {
    document.getElementById(panelId || "graphNodePanel")?.classList.add("hidden");
  }

  function destroy(opts = {}) {
    const containerId = opts.containerId || "forceGraphMount";
    _stopAnimLoop(containerId);
    _cleanupUi(containerId);
    resizeObservers[containerId]?.disconnect();
    delete resizeObservers[containerId];
    if (instances[containerId]) {
      instances[containerId]._destructor?.();
      delete instances[containerId];
    }
    _destroySigma(containerId);
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = "";
    graphStates[containerId] = {
      payload: null,
      viewMode: "cluster",
      expandedClusters: new Set(),
      highlightedPath: null,
      timelineCutoff: null,
      timelinePlaying: false,
      playTimer: null,
      opts: {},
      pins: {},
      lastPanelNode: null,
      selectedNodeId: null,
      prevVisibleEdgeKeys: new Set(),
      flashEdges: {},
        _animRaf: null,
        _animT: 0,
        rendererMode: "auto",
        activeRenderer: "force",
      };
    if (!opts.skipWrap) {
      const wrapId = opts.wrapId || (containerId === "opsForceGraphMount" ? "opsGraphPanel" : "graphWorkspace");
      const wrap = document.getElementById(wrapId);
      wrap?.classList.add("hidden");
      wrap?.setAttribute("aria-hidden", "true");
    }
  }

  global.FinSkalpGraph = {
    mount, destroy, closePanel, setViewMode, refreshGraph, hasGraphData,
    pinNode, unpinNode, saveNamedView, restoreGraphView, captureGraphView,
  };
})(window);
