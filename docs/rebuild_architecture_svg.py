"""Build a clean, one-page FinSkalp architecture diagram from scratch."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
SVG = ROOT / "FinSkalp-Architecture-v3-Client.svg"

W, H = 1600, 1000

COLORS = {
    "green": ("#D1FAE5", "#059669", "#064E3B"),
    "yellow": ("#FEF3C7", "#D97706", "#78350F"),
    "red": ("#FEE2E2", "#EF4444", "#7F1D1D"),
    "neutral": ("#F8FAFC", "#CBD5E1", "#0F172A"),
    "dark": ("#0F172A", "#0F172A", "#FFFFFF"),
}

parts: list[str] = []


def text(x, y, value, size=12, weight=500, fill="#0F172A", anchor="middle"):
    parts.append(
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
        f'font-family="Segoe UI,Arial,sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{escape(value)}</text>'
    )


def multiline(x, y, lines, size=11, weight=500, fill="#0F172A", gap=14):
    for i, line in enumerate(lines):
        text(x, y + i * gap, line, size, weight, fill)


def rect(x, y, w, h, status="neutral", radius=8, stroke_width=2):
    bg, stroke, _ = COLORS[status]
    parts.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
        f'fill="{bg}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )


def card(x, y, w, h, title, subtitle="", status="green", title_size=11):
    rect(x, y, w, h, status)
    _, stroke, ink = COLORS[status]
    parts.append(f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{stroke}"/>')
    text(x + w / 2 + 3, y + 19, title, title_size, 700, ink)
    if subtitle:
        text(x + w / 2 + 3, y + 36, subtitle, 9.5, 500, ink)


def band(x, y, w, h, title, subtitle=""):
    rect(x, y, w, h, "neutral", 10, 1)
    text(x + 16, y + 23, title.upper(), 12, 700, "#334155", "start")
    if subtitle:
        text(x + w - 16, y + 23, subtitle, 10, 500, "#64748B", "end")


def line(x1, y1, x2, y2, arrow=False):
    marker = ' marker-end="url(#arrow)"' if arrow else ""
    parts.append(
        f'<path d="M{x1} {y1} L{x2} {y2}" fill="none" stroke="#64748B" '
        f'stroke-width="1.6"{marker}/>'
    )


parts.append(
    f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
    <path d="M0,0 L8,4 L0,8 Z" fill="#64748B"/>
  </marker>
</defs>
<rect width="{W}" height="{H}" fill="#FFFFFF"/>
'''
)

# Header
parts.append('<rect x="20" y="18" width="1560" height="66" rx="12" fill="#0F172A"/>')
text(48, 47, "FINSKALP PLATFORM ARCHITECTURE v3.0", 23, 750, "#FFFFFF", "start")
text(48, 69, "Платформа финансовых расследований, AML, Blockchain Intelligence и OSINT", 12, 500, "#CBD5E1", "start")
text(1552, 49, "CLIENT ARCHITECTURE BLUEPRINT", 11, 700, "#93C5FD", "end")
text(1552, 68, "Confidential · One-page reference architecture", 10, 500, "#CBD5E1", "end")

# Workspace
band(20, 100, 1560, 110, "Аналитическое рабочее пространство", "Analyst Workspace")
workspace = [
    ("Dashboard и KPI", "Overview", "green"),
    ("Расследования", "Cases", "green"),
    ("Граф связей", "Knowledge Graph", "green"),
    ("Таймлайн", "Timeline", "green"),
    ("Доказательства", "Evidence", "red"),
    ("Отчёты", "Reports", "green"),
    ("AI Ассистент", "Explainable AI", "red"),
    ("Уведомления", "Alerts", "green"),
]
for i, (title, sub, status) in enumerate(workspace):
    card(38 + i * 192, 138, 178, 56, title, sub, status, 12)

# API Gateway
band(20, 224, 1560, 78, "API Gateway & Security Layer", "Единая точка входа")
api = [
    ("Аутентификация", "OAuth2 / OIDC", "yellow"),
    ("Авторизация", "RBAC / ABAC", "green"),
    ("Rate Limiting", "Квоты и защита", "green"),
    ("Шифрование", "TLS / mTLS", "green"),
    ("Аудит запросов", "Полный журнал", "red"),
]
for i, (title, sub, status) in enumerate(api):
    card(38 + i * 308, 253, 292, 39, title, sub, status, 11)

# Core connectors behind blocks
line(800, 210, 800, 224, True)
line(800, 302, 800, 334, True)
line(332, 482, 372, 482, True)
line(712, 482, 740, 482, True)
line(970, 482, 992, 482, True)
line(1248, 482, 1268, 482, True)

# Main body: analytics
band(20, 318, 312, 332, "Аналитические модули", "Capabilities")
analytics = [
    ("Нелегальная деятельность", "Обменники / фирмы", "green"),
    ("Криптооперации", "Незарегистрированные", "green"),
    ("Кластеризация", "Криптокошельки", "green"),
    ("Ретроспективный анализ", "Транзакции / события", "green"),
    ("Связи и контрагенты", "Correlation", "green"),
    ("Оценка риска", "Risk Scoring", "green"),
    ("Entity Resolution", "Разрешение сущностей", "green"),
    ("Case Management", "Управление делами", "green"),
    ("Timeline Engine", "Построение таймлайнов", "green"),
    ("Evidence Management", "Chain of Custody", "red"),
    ("AI-анализ", "Объяснения", "red"),
    ("Report Builder", "Конструктор отчётов", "green"),
]
for i, (title, sub, status) in enumerate(analytics):
    col = i % 2
    row = i // 2
    card(34 + col * 145, 355 + row * 47, 135, 39, title, sub, status, 9.5)

# Fusion core and normalization
band(348, 318, 376, 332, "Fusion Intelligence Core", "Investigation Core")
parts.append('<ellipse cx="485" cy="480" rx="112" ry="92" fill="#064E3B" stroke="#059669" stroke-width="5"/>')
text(485, 457, "FUSION", 20, 750, "#FFFFFF")
text(485, 481, "INTELLIGENCE CORE", 18, 750, "#FFFFFF")
text(485, 510, "Корреляция · Merge · Attribution", 10, 500, "#A7F3D0")
normalization = [
    ("Нормализация", "green"),
    ("Entity Extraction", "green"),
    ("Дедупликация", "green"),
    ("Обогащение", "green"),
    ("Достоверность", "green"),
    ("Quality & Confidence", "green"),
]
for i, (title, status) in enumerate(normalization):
    card(612, 354 + i * 46, 98, 37, title, "", status, 8.8)

# Connectors
band(740, 318, 230, 332, "Коннекторы и ввод данных", "Connectors")
connectors = [
    ("Банковские системы", "SWIFT · Payments", "yellow"),
    ("KYT / KYC / KYB", "External providers", "yellow"),
    ("Мануальный ввод", "Data entry", "green"),
    ("Blockchain Scanners", "BTC · ETH · TRON", "green"),
    ("Локальные системы", "Integration API", "yellow"),
    ("Реестры и БД", "Government / CRIF", "yellow"),
]
for i, (title, sub, status) in enumerate(connectors):
    card(754, 355 + i * 47, 202, 39, title, sub, status, 10)

# External sources
band(992, 318, 256, 332, "Внешние источники", "OSINT & Data")
sources = [
    ("Crypto Resources", "Darknet · Forums", "green"),
    ("Social Intelligence", "Telegram · X · Reddit", "green"),
    ("WHOIS / DNS / IP", "ASN · ENS · CT", "green"),
    ("Leak Intelligence", "HIBP · IntelligenceX", "yellow"),
    ("OSINT Tools", "Sherlock · Maltego", "green"),
    ("Geo Intelligence", "Maps · Geolocation", "yellow"),
]
for i, (title, sub, status) in enumerate(sources):
    card(1006, 355 + i * 47, 228, 39, title, sub, status, 10)

# Compliance & integrations
band(1268, 318, 312, 332, "Enterprise Controls", "Compliance & Extensions")
controls = [
    ("115-ФЗ / Regulators", "yellow"),
    ("Travel Rule / FATF", "yellow"),
    ("AML / CFT Rules", "green"),
    ("Chain of Custody", "red"),
    ("SIEM / SOAR", "yellow"),
    ("RBAC / ABAC", "green"),
    ("Encryption", "green"),
    ("Audit Logs", "red"),
    ("REST / GraphQL / gRPC", "green"),
    ("Webhooks / SDK", "green"),
    ("Plugin Architecture", "green"),
    ("Marketplace", "red"),
    ("External BI / DWH / CRM", "yellow"),
]
for i, (title, status) in enumerate(controls):
    col = i % 2
    row = i // 2
    card(1282 + col * 142, 354 + row * 42, 132, 34, title, "", status, 8.6)

# Platform services
band(20, 666, 1560, 98, "Ключевые сервисы платформы", "Key Platform Services")
services = [
    ("Investigation", "green"), ("Knowledge Graph", "green"),
    ("Entity Resolution", "green"), ("Timeline", "green"),
    ("Evidence", "red"), ("Risk Engine", "green"),
    ("AI & NLP", "red"), ("Report Engine", "green"),
    ("Notifications", "green"), ("Audit & Logging", "red"),
]
for i, (title, status) in enumerate(services):
    card(36 + i * 154, 706, 142, 43, title, "", status, 10)

line(800, 650, 800, 666, True)
line(800, 764, 800, 777, True)

# Storage
band(20, 777, 1560, 78, "Хранилища данных и сообщений", "Data Platform")
stores = [
    ("PostgreSQL", "green"), ("Neo4j Cluster", "green"), ("OpenSearch", "green"),
    ("Redis", "green"), ("Object Storage", "yellow"), ("Kafka / RabbitMQ", "green"),
    ("Data Lake / Archive", "red"),
]
for i, (title, status) in enumerate(stores):
    card(36 + i * 220, 808, 205, 36, title, "", status, 10)

line(800, 855, 800, 866, True)

# Infrastructure
band(20, 866, 1560, 68, "Инфраструктура и эксплуатация", "Infrastructure & Operations")
infra = [
    ("Docker", "green"), ("Kubernetes", "red"), ("Helm", "red"),
    ("Terraform", "red"), ("GitOps", "red"), ("CI/CD", "green"),
    ("Monitoring", "red"), ("Logs", "red"), ("Tracing", "red"),
    ("Backup & DR", "red"), ("Vault / KMS", "yellow"),
]
for i, (title, status) in enumerate(infra):
    card(34 + i * 141, 896, 130, 29, title, "", status, 9.2)

# Legend
legend_y = 959
legend = [
    ("green", "PRODUCTION READY", "реализовано и работает"),
    ("yellow", "INTEGRATION READY", "готово, ожидает внешних интеграций"),
    ("red", "ENTERPRISE HARDENING", "реализовано, требуется промышленное усиление"),
]
for i, (status, title, subtitle) in enumerate(legend):
    x = 38 + i * 520
    bg, stroke, ink = COLORS[status]
    parts.append(f'<rect x="{x}" y="{legend_y}" width="20" height="20" rx="4" fill="{stroke}"/>')
    text(x + 30, legend_y + 10, title, 11, 750, ink, "start")
    text(x + 30, legend_y + 25, subtitle, 9.5, 500, "#64748B", "start")

parts.append("</svg>")
SVG.write_text("".join(parts), encoding="utf-8")
print(SVG)
