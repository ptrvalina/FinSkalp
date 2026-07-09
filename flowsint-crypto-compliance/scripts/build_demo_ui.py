#!/usr/bin/env python3
"""Build index.html: FinSkalp enterprise shell + full live SPA views."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "flowsint_crypto_compliance" / "demo" / "static"
CLASSIC = STATIC / "index.classic.html"
OUT = STATIC / "index.html"
VER = "20260704b"

NAV = [
    ("dashboard", "dashboard", "Командный центр", "Обзор"),
    ("osint", "public", "Центр OSINT", None),
    ("wallet", "account_balance_wallet", "Проверка кошелька", None),
    ("microservices", "hub", "Микросервисы", None),
    ("platform", "extension", "Модули платформы", None),
    ("ops", "find_in_page", "Расследования", "Операции"),
    ("instruments", "terminal", "Консоль ИЦ", None),
    ("registries", "storage", "Реестры", None),
    ("reports", "description", "Отчёты 115-ФЗ", None),
]

TAILWIND_CONFIG = """<script id="tailwind-config">
tailwind.config = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: "#8ed5ff", surface: "#031427", background: "#031427",
        "surface-dim": "#031427", "surface-container": "#102034",
        "surface-container-low": "#0b1c30", "surface-container-high": "#1b2b3f",
        "surface-container-highest": "#26364a", "surface-container-lowest": "#000f21",
        "on-surface": "#d3e4fe", "on-surface-variant": "#bdc8d1",
        "outline-variant": "#3e484f", outline: "#87929a",
        "primary-container": "#38bdf8", error: "#ffb4ab", tertiary: "#ffc176",
        "secondary-container": "#3e495d", "on-primary": "#00354a",
      },
      spacing: { "container-margin": "32px", "block-gap": "24px", "compact-gap": "8px" },
      fontFamily: {
        h1: ["Public Sans"], h2: ["Public Sans"], h3: ["Public Sans"],
        "body-md": ["Public Sans"], "body-sm": ["Public Sans"],
        "label-caps": ["Public Sans"], "data-mono": ["IBM Plex Mono"],
      },
    },
  },
};
</script>"""


def extract_views(html: str) -> str:
    start = html.index("<!-- КОМАНДНЫЙ ЦЕНТР -->")
    end = html.index('<div id="toastContainer"')
    chunk = html[start:end].strip()
    if chunk.endswith("</div>"):
        chunk = chunk[: chunk.rfind("</div>")].strip()
    return chunk


def nav_html() -> str:
    parts: list[str] = []
    section = None
    for view, icon, label, sec in NAV:
        if sec and sec != section:
            section = sec
            parts.append(
                f'<div class="px-3 pt-4 pb-1 font-label-caps text-[10px] '
                f'text-on-surface-variant uppercase tracking-widest">{sec}</div>'
            )
        parts.append(
            f'<button type="button" class="fs-nav w-full flex items-center gap-3 px-3 py-2 text-left '
            f'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors rounded '
            f'font-body-sm text-body-sm" data-fs-view="{view}" onclick="switchView(\'{view}\')">'
            f'<span class="material-symbols-outlined text-[20px]">{icon}</span>'
            f'<span class="font-label-caps text-label-caps">{label}</span>'
            f'<span class="nav-badge ml-auto" data-watchlist-badge hidden></span>'
            f"</button>"
        )
    parts.append('<div class="mt-auto px-4 py-4 border-t border-outline-variant">')
    parts.append(
        '<a class="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary text-body-sm" href="/status">'
        '<span class="material-symbols-outlined text-[18px]">monitoring</span><span>Статус системы</span></a>'
    )
    parts.append(
        '<div class="urls mt-3 text-[10px] font-data-mono text-on-surface-variant break-all" id="urls">—</div>'
    )
    parts.append("</div>")
    return "\n".join(parts)


def build() -> None:
    if not CLASSIC.is_file():
        raise SystemExit(f"Missing classic template: {CLASSIC}")
    views = extract_views(CLASSIC.read_text(encoding="utf-8"))

    html = f"""<!DOCTYPE html>
<html class="dark" lang="ru">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="application-name" content="FinSkalp" />
<title>ФинСкальп · FinSkalp — суверенная криптофорензика</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;700;900&amp;family=IBM+Plex+Mono:wght@400;500&amp;family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<style>
.material-symbols-outlined {{ font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24; }}
.glass-stroke {{ box-shadow: inset 0 1px 1px 0 rgba(255, 255, 255, 0.06); }}
.fs-nav.fs-nav-active {{
  color: #8ed5ff; background: rgba(62, 73, 93, 0.15);
  border-right: 2px solid #8ed5ff; border-radius: 0.125rem 0 0 0.125rem;
}}
.fs-nav.fs-nav-active .material-symbols-outlined {{ font-variation-settings: 'FILL' 1; }}
</style>
{TAILWIND_CONFIG}
<link rel="stylesheet" href="/static/css/tokens.css?v={VER}" />
<link rel="stylesheet" href="/static/css/motion.css?v={VER}" />
<link rel="stylesheet" href="/static/css/app.css?v={VER}" />
<link rel="stylesheet" href="/static/css/enterprise-shell.css?v={VER}" />
</head>
<body class="fs-enterprise bg-surface text-on-surface font-body-md selection:bg-primary/30">
<div class="flex h-screen overflow-hidden">
<aside class="flex flex-col h-full w-64 shrink-0 bg-surface-container border-r border-outline-variant z-50 overflow-y-auto">
<div class="p-6 flex flex-col gap-1">
<span class="font-h2 text-h2 font-semibold text-primary tracking-tight">Фин<span class="text-primary-container">Скальп</span></span>
<span class="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-widest" id="orgName">FinSkalp · 115-ФЗ</span>
</div>
<nav class="flex-1 px-2 py-2 space-y-0.5 flex flex-col">
{nav_html()}
</nav>
</aside>
<div class="flex flex-col flex-1 min-w-0 min-h-0">
<header class="fs-topbar flex items-center justify-between h-14 px-4 shrink-0 bg-surface-container-low border-b border-outline-variant gap-4">
<div class="flex items-center gap-4 min-w-0">
<span class="font-h3 text-h3 font-bold text-on-surface truncate hidden sm:inline">Криптофорензика</span>
<span class="text-on-surface-variant text-body-sm truncate" id="fsBreadcrumb">Командный центр</span>
</div>
<div class="hidden lg:flex flex-1 max-w-md mx-4">
<div class="relative w-full flex items-center bg-surface-container-lowest border border-outline-variant rounded-lg px-3 py-1.5">
<span class="material-symbols-outlined text-on-surface-variant text-sm mr-2">search</span>
<span class="text-body-sm text-outline">Поиск: дела, кошельки, VASP, СОО…</span>
</div>
</div>
<div class="flex items-center gap-3 shrink-0">
<div class="fs-kpi hidden md:flex items-center gap-1 px-2 py-1 bg-surface-container rounded border border-outline-variant">
<span class="text-[10px] uppercase text-on-surface-variant">Банки</span>
<span class="font-data-mono text-primary text-sm" id="kpiInst">—</span>
</div>
<div class="fs-kpi hidden md:flex items-center gap-1 px-2 py-1 bg-surface-container rounded border border-outline-variant">
<span class="text-[10px] uppercase text-on-surface-variant">Скрининг</span>
<span class="font-data-mono text-primary text-sm" id="kpiTps">—</span>
</div>
<div class="fs-kpi hidden lg:flex items-center gap-1 px-2 py-1 bg-surface-container rounded border border-outline-variant">
<span class="text-[10px] uppercase text-on-surface-variant">SLA</span>
<span class="font-data-mono text-primary text-sm">99.97%</span>
</div>
<span class="inline-flex items-center gap-1 text-[10px] text-primary uppercase"><span class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>Онлайн</span>
<button type="button" id="themeToggle" class="p-2 rounded-lg hover:bg-surface-container-high text-on-surface-variant" onclick="FinSkalpUI.toggleTheme()" title="Тема">◐</button>
</div>
</header>
<main id="fsAppMain" class="fs-app-main flex-1 min-h-0 overflow-hidden">
{views}
</main>
</div>
</div>
<div id="toastContainer" role="status" aria-live="polite"></div>
<script src="https://cdn.jsdelivr.net/npm/force-graph@1.43.5/dist/force-graph.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/graphology@0.25.4/dist/graphology.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/sigma@2.4.0/dist/sigma.min.js"></script>
<script src="/static/js/ui-system.js?v={VER}"></script>
<script src="/static/js/graph-viz.js?v={VER}"></script>
<script src="/static/js/enterprise-shell.js?v={VER}"></script>
<script src="/static/js/app.js?v={VER}"></script>
</body>
</html>
"""
    OUT.write_text(html, encoding="utf-8")
    print(f"Built {OUT} ({len(html)} bytes)")


if __name__ == "__main__":
    build()
