"""Create a flattened, fully colour-filled FinSkalp readiness diagram."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
SOURCE = ROOT / "finskalp-platform-architecture-v2-source.png"
OUTPUT = ROOT / "FinSkalp-Architecture-v2-Filled.png"

GREEN = (16, 185, 129)
YELLOW = (245, 158, 11)
RED = (239, 68, 68)


def rect(draw, box, colour, alpha=105, radius=3):
    draw.rounded_rectangle(box, radius=radius, fill=(*colour, alpha), outline=(*colour, 245), width=2)


def ellipse(draw, box, colour, alpha=105):
    draw.ellipse(box, fill=(*colour, alpha), outline=(*colour, 245), width=3)


def main():
    source = Image.open(SOURCE).convert("RGBA")
    overlay = Image.new("RGBA", source.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Analyst workspace: eight cards.
    analyst_boxes = [
        (237, 30, 298, 84), (301, 30, 365, 84), (368, 30, 434, 84),
        (437, 30, 502, 84), (505, 30, 571, 84), (574, 30, 640, 84),
        (643, 30, 709, 84), (712, 30, 790, 84),
    ]
    analyst_status = [GREEN, GREEN, GREEN, GREEN, RED, GREEN, RED, GREEN]
    for box, colour in zip(analyst_boxes, analyst_status):
        rect(draw, box, colour, 72)

    # API Gateway & Security Layer.
    api_boxes = [
        (229, 99, 340, 131), (341, 99, 450, 131), (451, 99, 525, 131),
        (526, 99, 614, 131), (615, 99, 699, 131),
    ]
    for box, colour in zip(api_boxes, [YELLOW, GREEN, GREEN, GREEN, RED]):
        rect(draw, box, colour, 70)

    # Additional analytical modules and capabilities.
    upper_left = [
        (18, 130, 179, 154), (18, 159, 179, 182), (18, 187, 179, 209),
        (18, 214, 179, 237), (18, 242, 179, 262),
    ]
    lower_left = [
        (18, 292, 178, 310), (18, 314, 178, 333), (18, 338, 178, 357),
        (18, 362, 178, 381), (18, 386, 178, 405), (18, 409, 178, 427),
        (18, 432, 178, 451),
    ]
    for box in upper_left:
        rect(draw, box, GREEN, 140)
    for box, colour in zip(
        lower_left, [GREEN, GREEN, GREEN, GREEN, RED, RED, GREEN]
    ):
        rect(draw, box, colour, 140)

    # Fusion Intelligence Core.
    ellipse(draw, (229, 170, 396, 319), GREEN, 78)

    # Data Normalization Layer: six rows.
    normalization = [
        (459, 154, 503, 177), (459, 178, 503, 201), (459, 202, 503, 225),
        (459, 226, 503, 249), (459, 250, 503, 276), (459, 277, 503, 319),
    ]
    for box in normalization:
        rect(draw, box, GREEN, 108, 1)

    # Main connector column.
    connector_boxes = [
        (577, 140, 676, 184), (577, 188, 676, 229), (577, 233, 676, 272),
        (577, 276, 676, 315), (577, 319, 676, 357),
    ]
    connector_status = [YELLOW, GREEN, GREEN, YELLOW, YELLOW]
    for box, colour in zip(connector_boxes, connector_status):
        rect(draw, box, colour, 105)

    # KYT/KYC, monitoring, identifiers, DNS/ENS.
    middle_right_boxes = [
        (730, 98, 817, 146), (730, 150, 817, 229),
        (730, 233, 817, 288), (730, 292, 817, 344),
    ]
    for box, colour in zip(middle_right_boxes, [YELLOW, GREEN, YELLOW, GREEN]):
        rect(draw, box, colour, 105)

    # External intelligence and data sources.
    external_boxes = [
        (846, 124, 937, 176), (846, 180, 937, 225), (846, 229, 937, 274),
        (846, 278, 937, 323), (846, 327, 937, 372), (846, 376, 937, 416),
    ]
    external_status = [GREEN, GREEN, GREEN, YELLOW, GREEN, YELLOW]
    for box, colour in zip(external_boxes, external_status):
        rect(draw, box, colour, 105)

    # Key platform services.
    services = [
        (230, 389, 276, 449), (279, 389, 326, 449), (329, 389, 377, 449),
        (380, 389, 427, 449), (430, 389, 477, 449), (480, 389, 527, 449),
        (530, 389, 577, 449), (580, 389, 627, 449), (630, 389, 678, 449),
        (681, 389, 729, 449),
    ]
    service_status = [
        GREEN, GREEN, GREEN, GREEN, RED, GREEN, RED, GREEN, GREEN, RED,
    ]
    for box, colour in zip(services, service_status):
        rect(draw, box, colour, 75)

    # Compliance and security.
    compliance = [
        (766, 402, 878, 423), (766, 425, 878, 446), (766, 448, 878, 469),
        (766, 471, 878, 492), (766, 494, 878, 515), (766, 517, 878, 538),
        (766, 540, 878, 561), (766, 563, 878, 579),
    ]
    compliance_status = [YELLOW, YELLOW, GREEN, RED, YELLOW, GREEN, GREEN, RED]
    for box, colour in zip(compliance, compliance_status):
        rect(draw, box, colour, 72)

    # Integrations and extensions.
    integrations = [
        (899, 402, 1009, 425), (899, 429, 1009, 452), (899, 456, 1009, 479),
        (899, 483, 1009, 506), (899, 510, 1009, 533), (899, 536, 1009, 559),
    ]
    integration_status = [GREEN, GREEN, GREEN, GREEN, RED, YELLOW]
    for box, colour in zip(integrations, integration_status):
        rect(draw, box, colour, 72)

    # Data and message storage.
    stores = [
        (12, 479, 112, 513), (117, 479, 217, 513), (222, 479, 326, 513),
        (331, 479, 435, 513), (440, 479, 544, 513), (549, 479, 653, 513),
        (658, 479, 740, 513),
    ]
    store_status = [GREEN, GREEN, GREEN, GREEN, YELLOW, GREEN, RED]
    for box, colour in zip(stores, store_status):
        rect(draw, box, colour, 76)

    # Infrastructure and operations.
    infrastructure = [
        (11, 542, 65, 569), (66, 542, 111, 569), (112, 542, 151, 569),
        (152, 542, 199, 569), (200, 542, 250, 569), (251, 542, 326, 569),
        (327, 542, 407, 569), (408, 542, 478, 569), (479, 542, 550, 569),
        (551, 542, 666, 569), (667, 542, 740, 569),
    ]
    infrastructure_status = [
        RED, GREEN, RED, RED, RED, GREEN, RED, RED, RED, RED, YELLOW,
    ]
    for box, colour in zip(infrastructure, infrastructure_status):
        rect(draw, box, colour, 78)

    flattened = Image.alpha_composite(source, overlay).convert("RGB")
    scale = 2
    flattened = flattened.resize(
        (flattened.width * scale, flattened.height * scale),
        Image.Resampling.LANCZOS,
    )

    legend_h = 112
    result = Image.new("RGB", (flattened.width, flattened.height + legend_h), "white")
    result.paste(flattened, (0, 0))
    d = ImageDraw.Draw(result)
    regular = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 19)
    bold = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 20)
    entries = [
        (GREEN, "Production Ready", "реализовано и работает"),
        (YELLOW, "Integration Ready", "готово, ожидает внешних интеграций"),
        (RED, "Enterprise Hardening", "реализовано, требует промышленного усиления"),
    ]
    x, y = 38, flattened.height + 18
    for (colour, title, detail), width in zip(entries, [560, 640, 760]):
        d.rounded_rectangle((x, y + 3, x + 22, y + 25), radius=4, fill=colour)
        d.text((x + 34, y), title, font=bold, fill=(24, 36, 55))
        d.text((x + 34, y + 29), detail, font=regular, fill=(74, 90, 118))
        x += width

    result.save(OUTPUT, quality=96)
    print(OUTPUT)


if __name__ == "__main__":
    main()
