"""TronGrid-inspired inline SVG styling for forensic report graphs (WeasyPrint-safe)."""

from __future__ import annotations

import math
import random
from typing import Any

# Mirrors --fs-risk-* tokens in demo/static/css/tokens.css (PDF cannot use CSS vars)
FS_RISK_CRITICAL = "#ef4444"
FS_RISK_HIGH = "#f97316"
FS_RISK_MEDIUM = "#eab308"
FS_RISK_CLEAR = "#14b8a6"
FS_RISK_MUTED = "#6b7280"

BG_DARK = "#0a0a0f"
BG_ALT = "#0f172a"
NODE_HIGH = FS_RISK_CRITICAL
NODE_MED = FS_RISK_HIGH
NODE_LOW = FS_RISK_MEDIUM
NODE_MUTED = FS_RISK_MUTED
EDGE_STROKE = "#ffffff"
LABEL_FILL = "#ffffff"
TITLE_FILL = "#e2e8f0"


def risk_node_color(risk: float, *, flagged: bool = False, is_subject: bool = False) -> str:
    if flagged or risk >= 80:
        return FS_RISK_CRITICAL
    if is_subject:
        return FS_RISK_CRITICAL if risk >= 55 else FS_RISK_HIGH
    if risk >= 55:
        return FS_RISK_HIGH
    if risk >= 30:
        return FS_RISK_MEDIUM
    if risk >= 15:
        return FS_RISK_CLEAR
    return FS_RISK_MUTED


def svg_defs() -> str:
    return (
        "<defs>"
        '<pattern id="hex-grid" width="28" height="24" patternUnits="userSpaceOnUse" patternTransform="scale(1)">'
        '<path d="M14 0 L28 8 L28 16 L14 24 L0 16 L0 8 Z" fill="none" stroke="#1e293b" stroke-width="0.5" opacity="0.35"/>'
        "</pattern>"
        "</defs>"
    )


def svg_background(width: float, height: float, *, bg: str = BG_DARK) -> str:
    return (
        f'<rect width="{width}" height="{height}" fill="{bg}"/>'
        f'<rect width="{width}" height="{height}" fill="url(#hex-grid)" opacity="0.6"/>'
    )


def svg_title(width: float, title: str, *, y: float = 20) -> str:
    return (
        f'<text x="{width / 2}" y="{y}" text-anchor="middle" fill="{TITLE_FILL}" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="500">{title}</text>'
    )


def svg_dashed_edge(x1: float, y1: float, x2: float, y2: float, *, width: float = 1.2) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{EDGE_STROKE}" stroke-width="{width}" stroke-dasharray="5,4" opacity="0.85"/>'
    )


def svg_node_circle(
    x: float,
    y: float,
    *,
    radius: float,
    fill: str,
    label: str,
    label_side: str = "right",
) -> str:
    glow = (
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius + 4:.1f}" fill="{fill}" opacity="0.18"/>'
    )
    core = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" stroke="#ffffff" stroke-width="0.6" opacity="0.95"/>'
    if label_side == "center":
        text = (
            f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" fill="{LABEL_FILL}" '
            f'font-family="Segoe UI, Arial, sans-serif" font-size="9" font-weight="500">{label}</text>'
        )
    elif label_side == "left":
        text = (
            f'<text x="{x - radius - 6:.1f}" y="{y + 4:.1f}" text-anchor="end" fill="{LABEL_FILL}" '
            f'font-family="Segoe UI, Arial, sans-serif" font-size="8">{label}</text>'
        )
    else:
        text = (
            f'<text x="{x + radius + 6:.1f}" y="{y + 4:.1f}" text-anchor="start" fill="{LABEL_FILL}" '
            f'font-family="Segoe UI, Arial, sans-serif" font-size="8">{label}</text>'
        )
    return glow + core + text


def _edge_endpoints(
    x1: float, y1: float, x2: float, y2: float, r1: float, r2: float
) -> tuple[float, float, float, float]:
    dx, dy = x2 - x1, y2 - y1
    dist = math.hypot(dx, dy) or 1.0
    ux, uy = dx / dist, dy / dist
    return x1 + ux * r1, y1 + uy * r1, x2 - ux * r2, y2 - uy * r2


def compute_network_positions(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    width: float,
    height: float,
    seed: int = 42,
) -> dict[str, tuple[float, float]]:
    if not nodes:
        return {}

    subject = next((n for n in nodes if n.get("hop") == 0), nodes[0])
    center_id = subject["id"]
    node_ids = [n["id"] for n in nodes]

    try:
        import networkx as nx

        g = nx.Graph()
        for n in nodes:
            g.add_node(n["id"])
        for e in edges:
            src = e.get("from") or e.get("source")
            dst = e.get("to") or e.get("target")
            if src and dst:
                g.add_edge(src, dst)
        if center_id in g:
            pos = nx.spring_layout(g, seed=seed, k=1.4, iterations=60)
            return _scale_positions(pos, width, height, margin=48)
    except ImportError:
        pass

    return _force_layout(node_ids, edges, width=width, height=height, center_id=center_id, seed=seed)


def _scale_positions(
    pos: dict[str, tuple[float, float]],
    width: float,
    height: float,
    *,
    margin: float,
) -> dict[str, tuple[float, float]]:
    if not pos:
        return {}
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)
    usable_w = width - 2 * margin
    usable_h = height - 2 * margin
    out: dict[str, tuple[float, float]] = {}
    for nid, (x, y) in pos.items():
        nx_ = margin + (x - min_x) / span_x * usable_w
        ny_ = margin + (y - min_y) / span_y * usable_h
        out[nid] = (nx_, ny_)
    return out


def _force_layout(
    node_ids: list[str],
    edges: list[dict[str, Any]],
    *,
    width: float,
    height: float,
    center_id: str,
    seed: int,
) -> dict[str, tuple[float, float]]:
    rng = random.Random(seed)
    cx, cy = width / 2, height / 2
    positions: dict[str, tuple[float, float]] = {}
    for i, nid in enumerate(node_ids):
        if nid == center_id:
            positions[nid] = (cx, cy)
        else:
            angle = (2 * math.pi * i) / max(1, len(node_ids) - 1) + rng.uniform(-0.3, 0.3)
            radius = min(width, height) * rng.uniform(0.28, 0.36)
            positions[nid] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))

    edge_pairs: list[tuple[str, str]] = []
    for e in edges:
        src = e.get("from") or e.get("source")
        dst = e.get("to") or e.get("target")
        if src and dst and src in positions and dst in positions:
            edge_pairs.append((src, dst))

    for _ in range(90):
        forces: dict[str, list[float]] = {nid: [0.0, 0.0] for nid in node_ids}
        for i, a in enumerate(node_ids):
            ax, ay = positions[a]
            for b in node_ids[i + 1 :]:
                bx, by = positions[b]
                dx, dy = ax - bx, ay - by
                dist2 = max(dx * dx + dy * dy, 120.0)
                rep = 5200.0 / dist2
                fx, fy = dx * rep, dy * rep
                forces[a][0] += fx
                forces[a][1] += fy
                forces[b][0] -= fx
                forces[b][1] -= fy
        for src, dst in edge_pairs:
            sx, sy = positions[src]
            dx, dy = positions[dst][0] - sx, positions[dst][1] - sy
            dist = math.hypot(dx, dy) or 1.0
            pull = (dist - min(width, height) * 0.22) * 0.04
            ux, uy = dx / dist, dy / dist
            if src != center_id:
                forces[src][0] += ux * pull
                forces[src][1] += uy * pull
            if dst != center_id:
                forces[dst][0] -= ux * pull
                forces[dst][1] -= uy * pull

        for nid in node_ids:
            if nid == center_id:
                positions[nid] = (cx, cy)
                continue
            x, y = positions[nid]
            x += max(-8.0, min(8.0, forces[nid][0]))
            y += max(-8.0, min(8.0, forces[nid][1]))
            x = max(36.0, min(width - 36.0, x))
            y = max(36.0, min(height - 36.0, y))
            positions[nid] = (x, y)
    return positions


def _flagged_ids(graph: dict[str, Any]) -> set[str]:
    flagged: set[str] = set()
    for ann in graph.get("risk_annotations") or []:
        if ann.get("type") == "illicit_hit":
            flagged.add(f"{ann.get('chain')}:{ann.get('address')}")
            if ann.get("address"):
                flagged.add(str(ann["address"]))
    return flagged


def render_fusion_graph_svg(
    graph: dict[str, Any],
    *,
    width: int = 900,
    height: int = 520,
    title: str = "FinSkalp Fusion Graph",
) -> str | None:
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    if not nodes:
        return None

    flagged = _flagged_ids(graph)
    positions = compute_network_positions(nodes, edges, width=width, height=height)
    subject = next((n for n in nodes if n.get("hop") == 0), nodes[0])
    subject_id = subject["id"]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        svg_defs(),
        svg_background(width, height),
        svg_title(width, title),
    ]

    radii: dict[str, float] = {}
    for n in nodes:
        radii[n["id"]] = 30.0 if n["id"] == subject_id else 14.0

    for e in edges:
        src = e.get("from") or e.get("source")
        dst = e.get("to") or e.get("target")
        if not src or not dst or src not in positions or dst not in positions:
            continue
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        ex1, ey1, ex2, ey2 = _edge_endpoints(x1, y1, x2, y2, radii[src], radii[dst])
        parts.append(svg_dashed_edge(ex1, ey1, ex2, ey2))

    for n in nodes:
        nid = n["id"]
        x, y = positions.get(nid, (width / 2, height / 2))
        label = (n.get("label") or n.get("address", nid).split(":")[-1])[:14]
        risk = float(n.get("risk_score") or 15)
        is_flagged = nid in flagged or (n.get("address") in flagged)
        color = risk_node_color(risk, flagged=is_flagged, is_subject=(nid == subject_id))
        radius = radii[nid]
        side = "center" if nid == subject_id else ("left" if x > width * 0.55 else "right")
        parts.append(svg_node_circle(x, y, radius=radius, fill=color, label=label, label_side=side))

    parts.append("</svg>")
    return "".join(parts)
