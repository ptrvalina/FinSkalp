"""Add compact readiness markers to the original FinSkalp v2.0 diagram."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SRC = Path(__file__).with_name("finskalp-platform-architecture-v2-source.png")
OUT_PNG = Path(__file__).with_name("FinSkalp-Architecture-v2-Status.png")
OUT_HTML = Path(__file__).with_name("finskalp-architecture-v2-print.html")

GREEN = (52, 211, 153)
YELLOW = (251, 191, 36)
ORANGE = (251, 146, 60)


def detect_red_boxes(img: Image.Image) -> list[tuple[int, int, int, int]]:
  px = img.load()
  w, h = img.size
  pred = lambda p: p[0] > 170 and p[1] < 120 and p[2] < 100
  visited: set[tuple[int, int]] = set()
  boxes: list[tuple[int, int, int, int]] = []
  for y in range(h):
    for x in range(w):
      if (x, y) in visited or not pred(px[x, y]):
        continue
      stack = [(x, y)]
      minx = maxx = x
      miny = maxy = y
      count = 0
      while stack:
        cx, cy = stack.pop()
        if (cx, cy) in visited:
          continue
        if cx < 0 or cy < 0 or cx >= w or cy >= h or not pred(px[cx, cy]):
          continue
        visited.add((cx, cy))
        count += 1
        minx, maxx = min(minx, cx), max(maxx, cx)
        miny, maxy = min(miny, cy), max(maxy, cy)
        if count > 8000:
          break
        stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])
      if 2000 < count < 8000 and (maxx - minx) > 80:
        boxes.append((minx, miny, maxx, maxy))
  return sorted(boxes, key=lambda b: (b[1], b[0]))


def detect_dark_rows(
  img: Image.Image, x0: int, x1: int, y0: int, y1: int, min_width: int = 60
) -> list[tuple[int, int, int, int]]:
  px = img.load()
  boxes: list[tuple[int, int, int, int]] = []
  y = y0
  while y < y1:
    dark_pixels = [x for x in range(x0, x1) if sum(px[x, y]) < 125]
    if len(dark_pixels) >= min_width:
      row_y1 = y
      while y < y1:
        row = [x for x in range(x0, x1) if sum(px[x, y]) < 125]
        if len(row) < min_width:
          break
        y += 1
      row_y2 = y - 1
      cols = [x for x in range(x0, x1) if sum(px[x, row_y1]) < 125]
      boxes.append((min(cols), row_y1, max(cols), row_y2))
    y += 1
  return boxes


def split_rows(box: tuple[int, int, int, int], n: int) -> list[tuple[int, int, int, int]]:
  x1, y1, x2, y2 = box
  h = y2 - y1
  step = h / n
  return [
    (x1, int(y1 + i * step), x2, int(y1 + (i + 1) * step - 1))
    for i in range(n)
  ]


def icon_row(x_start: int, x_end: int, y1: int, y2: int, n: int) -> list[tuple[int, int, int, int]]:
  width = (x_end - x_start) / n
  return [
    (int(x_start + i * width), y1, int(x_start + (i + 1) * width - 2), y2)
    for i in range(n)
  ]


def build_regions(img: Image.Image) -> list[tuple[int, int, int, int, tuple[int, int, int]]]:
  regions: list[tuple[int, int, int, int, tuple[int, int, int]]] = []

  def add(box: tuple[int, int, int, int], color: tuple[int, int, int]) -> None:
    regions.append((*box, color))

  # Top analyst workspace — measured on source image
  tops = [
    (33, 106, 119, 140, GREEN),
    (126, 106, 212, 140, GREEN),
    (219, 106, 305, 140, GREEN),
    (312, 106, 398, 140, GREEN),
    (33, 150, 119, 184, ORANGE),
    (126, 150, 212, 184, GREEN),
    (219, 150, 305, 184, ORANGE),
    (312, 150, 398, 184, GREEN),
  ]
  for r in tops:
    add(r[:4], r[4])

  # API Gateway — measured segments
  api = [
    (24, 196, 118, 218, YELLOW),
    (119, 196, 213, 218, GREEN),
    (214, 196, 308, 218, GREEN),
    (309, 196, 403, 218, GREEN),
    (404, 196, 516, 218, ORANGE),
  ]
  for r in api:
    add(r[:4], r[4])

  # Left analytics — auto-detected red boxes
  reds = detect_red_boxes(img)
  left_status = [
    GREEN, GREEN, GREEN, GREEN, GREEN,
    GREEN, GREEN, GREEN, GREEN, ORANGE, ORANGE, GREEN,
  ]
  for box, color in zip(reds, left_status):
    add(box, color)

  # Fusion core
  add((318, 278, 472, 402), GREEN)

  # Normalization column — 6 measured rows
  norm_rows = [
    (470, 248, 574, 266),
    (470, 268, 574, 286),
    (470, 288, 574, 306),
    (470, 308, 574, 326),
    (470, 328, 574, 346),
    (470, 348, 574, 368),
  ]
  for box in norm_rows:
    add(box, GREEN)

  # Inner connectors — 6 measured boxes
  conn_boxes = [
    (579, 234, 674, 252, YELLOW),
    (579, 256, 674, 274, YELLOW),
    (579, 278, 674, 296, GREEN),
    (579, 300, 674, 318, GREEN),
    (579, 322, 674, 340, YELLOW),
    (579, 344, 674, 362, YELLOW),
  ]
  for r in conn_boxes:
    add(r[:4], r[4])

  # External sources — 10 measured boxes
  ext_status = [
    GREEN, GREEN, YELLOW, GREEN, GREEN, GREEN, GREEN, YELLOW, GREEN, YELLOW,
  ]
  for i, color in enumerate(ext_status):
    add((728, 234 + i * 26, 903, 252 + i * 26), color)

  # Compliance panel — measured rows
  comp_status = [
    YELLOW, YELLOW, GREEN, ORANGE, YELLOW, GREEN, GREEN, ORANGE,
  ]
  for i, color in enumerate(comp_status):
    add((908, 248 + i * 26, 1002, 266 + i * 26), color)

  # Integrations panel — measured rows
  integ_status = [GREEN, GREEN, GREEN, GREEN, ORANGE, YELLOW]
  for i, color in enumerate(integ_status):
    add((908, 486 + i * 26, 1002, 504 + i * 26), color)

  # Key platform services — 10 measured icon slots
  svc_boxes = [
    (20, 446, 88, 472), (93, 446, 161, 472), (166, 446, 234, 472),
    (239, 446, 307, 472), (312, 446, 380, 472), (385, 446, 453, 472),
    (458, 446, 526, 472), (531, 446, 599, 472), (604, 446, 672, 472),
    (677, 446, 745, 472),
  ]
  svc_status = [
    GREEN, GREEN, GREEN, GREEN, ORANGE, GREEN, ORANGE, GREEN, GREEN, ORANGE,
  ]
  for box, color in zip(svc_boxes, svc_status):
    add(box, color)

  # Data storage — 7 measured icon slots
  store_boxes = [
    (20, 486, 125, 512), (130, 486, 235, 512), (240, 486, 345, 512),
    (350, 486, 455, 512), (460, 486, 565, 512), (570, 486, 675, 512),
    (680, 486, 785, 512),
  ]
  store_status = [GREEN, GREEN, GREEN, GREEN, YELLOW, GREEN, ORANGE]
  for box, color in zip(store_boxes, store_status):
    add(box, color)

  # Infrastructure — 11 measured icon slots
  infra_boxes = [
    (10, 534, 88, 560), (93, 534, 171, 560), (176, 534, 254, 560),
    (259, 534, 337, 560), (342, 534, 420, 560), (425, 534, 503, 560),
    (508, 534, 586, 560), (591, 534, 669, 560), (674, 534, 752, 560),
    (757, 534, 835, 560), (840, 534, 918, 560),
  ]
  infra_status = [
    GREEN, ORANGE, ORANGE, ORANGE, ORANGE, GREEN,
    ORANGE, ORANGE, ORANGE, ORANGE, YELLOW,
  ]
  for box, color in zip(infra_boxes, infra_status):
    add(box, color)

  return regions


def draw_status_markers(draw: ImageDraw.ImageDraw, regions: list, fusion_box=None) -> None:
  for x1, y1, x2, y2, color in regions:
    if fusion_box and (x1, y1, x2, y2) == fusion_box:
      draw.ellipse((x1, y1, x2, y2), outline=color, width=3)
      draw.ellipse((x2 - 14, y1 + 4, x2 - 4, y1 + 14), fill=color)
      continue
    draw.rectangle((x1, y1, x2, y2), outline=color, width=2)
    draw.rectangle((x1, y1, x1 + 4, y2), fill=color)
    draw.ellipse((x2 - 11, y1 + 2, x2 - 3, y1 + 12), fill=color)


def annotate() -> list:
  source = Image.open(SRC).convert("RGB")
  scale = 2
  img = source.resize((source.width * scale, source.height * scale), Image.Resampling.LANCZOS)
  legend_h = 112
  base = Image.new("RGB", (img.width, img.height + legend_h), "white")
  base.paste(img, (0, 0))
  d = ImageDraw.Draw(base)

  # Marker centres measured directly from the original 1024x646 diagram.
  markers: list[tuple[int, int, tuple[int, int, int]]] = []
  def add(x: int, y: int, color: tuple[int, int, int]) -> None:
    markers.append((x, y, color))

  # Analyst workspace: Dashboard, Cases, Graph, Timeline, Evidence, Reports, AI, Alerts.
  for x, color in zip(
    [294, 363, 432, 501, 570, 639, 708, 777],
    [GREEN, GREEN, GREEN, GREEN, ORANGE, GREEN, ORANGE, GREEN],
  ):
    add(x, 35, color)

  # API gateway: Authentication, Authorization, Rate limit, TLS, audit.
  for x, color in zip(
    [332, 420, 500, 582, 676],
    [YELLOW, GREEN, GREEN, GREEN, ORANGE],
  ):
    add(x, 103, color)

  # Additional analytical modules and capabilities.
  left_y = [132, 161, 190, 217, 246, 297, 321, 345, 369, 393, 417, 441]
  left_status = [
    GREEN, GREEN, GREEN, GREEN, GREEN,
    GREEN, GREEN, GREEN, GREEN, ORANGE, ORANGE, GREEN,
  ]
  for y, color in zip(left_y, left_status):
    add(174, y, color)

  # Fusion core.
  add(378, 184, GREEN)

  # Normalization pipeline.
  for y in [170, 197, 224, 251, 278, 305]:
    add(509, y, GREEN)

  # Internal connectors: banks, manual input, blockchain, local API, registries.
  connector_y = [146, 190, 239, 288, 332]
  connector_status = [YELLOW, GREEN, GREEN, YELLOW, YELLOW]
  for y, color in zip(connector_y, connector_status):
    add(669, y, color)

  # KYT/KYC, monitoring, identifiers, DNS/ENS.
  for y, color in zip([105, 159, 249, 307], [YELLOW, GREEN, YELLOW, GREEN]):
    add(806, y, color)

  # External OSINT/data sources.
  external_y = [130, 180, 230, 280, 330, 378]
  external_status = [GREEN, GREEN, GREEN, YELLOW, GREEN, YELLOW]
  for y, color in zip(external_y, external_status):
    add(930, y, color)

  # Key platform services.
  service_x = [275, 324, 375, 425, 475, 525, 575, 625, 675, 725]
  service_status = [
    GREEN, GREEN, GREEN, GREEN, ORANGE, GREEN, ORANGE, GREEN, GREEN, ORANGE,
  ]
  for x, color in zip(service_x, service_status):
    add(x, 395, color)

  # Compliance and security.
  compliance_y = [398, 422, 446, 470, 494, 518, 542, 566]
  compliance_status = [YELLOW, YELLOW, GREEN, ORANGE, YELLOW, GREEN, GREEN, ORANGE]
  for y, color in zip(compliance_y, compliance_status):
    add(871, y, color)

  # Integrations and extensions.
  integration_y = [398, 425, 452, 479, 506, 533]
  integration_status = [GREEN, GREEN, GREEN, GREEN, ORANGE, YELLOW]
  for y, color in zip(integration_y, integration_status):
    add(1004, y, color)

  # Data stores.
  store_x = [108, 216, 322, 431, 539, 647, 735]
  store_status = [GREEN, GREEN, GREEN, GREEN, YELLOW, GREEN, ORANGE]
  for x, color in zip(store_x, store_status):
    add(x, 477, color)

  # Infrastructure and operations.
  infra_x = [53, 97, 136, 177, 227, 301, 392, 462, 542, 650, 739]
  infra_status = [
    ORANGE, GREEN, ORANGE, ORANGE, ORANGE, GREEN,
    ORANGE, ORANGE, ORANGE, ORANGE, YELLOW,
  ]
  for x, color in zip(infra_x, infra_status):
    add(x, 539, color)

  # Draw only small dots: no frames, no overlays, no obscured text.
  radius = 6 * scale
  for x, y, color in markers:
    cx, cy = x * scale, y * scale
    d.ellipse(
      (cx - radius - 2, cy - radius - 2, cx + radius + 2, cy + radius + 2),
      fill="white",
      outline=(42, 53, 72),
      width=2,
    )
    d.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color)

  # Client-facing legend, rendered with a Cyrillic-capable font.
  regular = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 19)
  bold = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 20)
  ly = img.height + 18
  legend = [
    (GREEN, "Production Ready", "реализовано и работает"),
    (YELLOW, "Integration Ready", "готово, ожидает внешних интеграций"),
    (ORANGE, "Enterprise Hardening", "реализовано, требует промышленного усиления"),
  ]
  x = 38
  widths = [560, 640, 760]
  for (color, title, detail), width in zip(legend, widths):
    d.ellipse((x, ly + 4, x + 18, ly + 22), fill=color, outline=(42, 53, 72), width=1)
    d.text((x + 30, ly), title, font=bold, fill=(24, 36, 55))
    d.text((x + 30, ly + 27), detail, font=regular, fill=(74, 90, 118))
    x += width

  base.save(OUT_PNG, quality=96)
  return []


def write_html(regions: list) -> None:
  rects = []
  for x1, y1, x2, y2, color in regions:
    c = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
    w, h = x2 - x1, y2 - y1
    rects.append(
      f'<rect x="{x1}" y="{y1}" width="{w}" height="{h}" fill="none" stroke="{c}" stroke-width="2"/>'
      f'<rect x="{x1}" y="{y1}" width="4" height="{h}" fill="{c}"/>'
      f'<circle cx="{x2-6}" cy="{y1+7}" r="5" fill="{c}"/>'
    )
  html = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8"/>
<title>FinSkalp Architecture v2.0</title>
<style>
  @page {{ size: A3 landscape; margin: 6mm; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:Segoe UI,sans-serif; padding:14px 18px; background:#fff; }}
  h1 {{ font-size:17px; color:#0f1a2e; }}
  .sub {{ font-size:11px; color:#4a5a76; margin:3px 0 10px; }}
  .legend {{ display:flex; gap:22px; flex-wrap:wrap; font-size:11px; margin-bottom:10px; }}
  .legend span {{ display:flex; align-items:center; gap:7px; }}
  .dot {{ width:10px; height:10px; border-radius:50%; }}
  .wrap {{ position:relative; max-width:100%; }}
  img {{ width:100%; display:block; }}
  svg {{ position:absolute; inset:0; width:100%; height:100%; }}
  @media print {{ * {{ print-color-adjust:exact; -webkit-print-color-adjust:exact; }} }}
</style></head><body>
<h1>FinSkalp Platform Architecture v2.0 — Карта готовности</h1>
<p class="sub">Confidential · Prepared for Client Review</p>
<div class="legend">
  <span><i class="dot" style="background:#34d399"></i>Production Ready</span>
  <span><i class="dot" style="background:#fbbf24"></i>Integration Ready</span>
  <span><i class="dot" style="background:#fb923c"></i>Enterprise Hardening</span>
</div>
<div class="wrap">
  <img src="finskalp-platform-architecture-v2-source.png" width="1024" height="646"/>
  <svg viewBox="0 0 1024 646">{''.join(rects)}</svg>
</div>
</body></html>"""
  OUT_HTML.write_text(html, encoding="utf-8")


if __name__ == "__main__":
  regions = annotate()
  print(f"regions: {len(regions)}")
  print(f"saved: {OUT_PNG}")
