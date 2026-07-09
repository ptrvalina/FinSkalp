"""Render fusion graph to PNG for PDF reports."""

from __future__ import annotations

import base64
import io
from typing import Any

from flowsint_crypto_compliance.reporting.svg_graph_style import (
    BG_ALT,
    NODE_HIGH,
    NODE_MUTED,
    render_fusion_graph_svg,
)


def render_graph_png(
    graph: dict[str, Any],
    *,
    width: int = 900,
    height: int = 520,
) -> bytes | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        return None

    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    if not nodes:
        return None

    G = nx.DiGraph()
    flagged: set[str] = set()
    for ann in graph.get("risk_annotations") or []:
        if ann.get("type") == "illicit_hit":
            flagged.add(f"{ann.get('chain')}:{ann.get('address')}")

    for n in nodes:
        G.add_node(n["id"], label=n.get("label", n["address"][:10]), hop=n.get("hop", 0))
    for e in edges:
        G.add_edge(e["from"], e["to"])

    pos = nx.spring_layout(G, seed=42, k=1.2)
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    colors = [
        NODE_HIGH if n in flagged else "#ef4444" if G.nodes[n].get("hop") == 0 else NODE_MUTED
        for n in G.nodes
    ]
    nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=400, ax=ax)
    nx.draw_networkx_edges(
        G, pos, edge_color="#ffffff", style="dashed", arrows=False, ax=ax, alpha=0.75, width=0.8
    )
    labels = {n: G.nodes[n].get("label", n)[:12] for n in G.nodes}
    nx.draw_networkx_labels(G, pos, labels, font_size=6, font_color="white", ax=ax)
    ax.set_title("Граф связей · FinSkalp Fusion", fontsize=10, color="#e2e8f0")
    ax.axis("off")
    ax.set_facecolor(BG_ALT)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", facecolor=BG_ALT)
    plt.close(fig)
    return buf.getvalue()


def render_graph_svg(graph: dict[str, Any], *, width: int = 900, height: int = 520) -> str | None:
    """TronGrid-style inline SVG for WeasyPrint PDF reports."""
    return render_fusion_graph_svg(graph, width=width, height=height)


def _fallback_fusion_svg(graph: dict[str, Any], *, width: int = 520, height: int = 280) -> str | None:
    """Lightweight SVG when primary renderer unavailable (same visual language)."""
    return render_fusion_graph_svg(graph, width=width, height=height)


def graph_section_for_report(
    graph: dict[str, Any],
    *,
    investigation_id: str | None = None,
) -> dict[str, Any]:
    """Metadata + PNG/SVG for PDF/HTML report section."""
    png = render_graph_png(graph)
    png_data_uri = None
    if png:
        png_data_uri = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    svg = render_graph_svg(graph)
    if svg is None and (graph.get("nodes") or []):
        svg = _fallback_fusion_svg(graph)
    annotations_ru = []
    for ann in graph.get("risk_annotations") or []:
        if ann.get("type") == "illicit_hit":
            annotations_ru.append(
                f"⚠ {ann.get('address', '')[:16]}… hop={ann.get('hop')} · {', '.join(ann.get('sources') or [])}"
            )
        elif ann.get("type") == "corridor_flagged":
            annotations_ru.append(f"🚩 Коридор помечен: {ann.get('reason_ru', '')}")
    interop_formats = ["ftm-ndjson", "graphml"]
    export_urls: dict[str, str] = {}
    if investigation_id:
        base = f"/api/interop/ftm/fusion-graph/{investigation_id}"
        export_urls = {
            "ftm_bundle": base,
            "ftm_ndjson": f"{base}?format=ndjson",
            "graphml": f"/api/graph/export?format=graphml&investigation_id={investigation_id}",
        }
    return {
        "title_ru": "Граф связей (multi-hop fusion)",
        "node_count": len(graph.get("nodes") or []),
        "edge_count": len(graph.get("edges") or []),
        "corridor_flagged": graph.get("corridor_flagged", False),
        "annotations_ru": annotations_ru,
        "has_png": png is not None,
        "png_data_uri": png_data_uri,
        "svg": svg,
        "has_svg": svg is not None,
        "interop_formats": interop_formats,
        "export_urls": export_urls,
    }
