from PIL import Image, ImageDraw

img = Image.open("finskalp-platform-architecture-v2-source.png").convert("RGB")
w, h = img.size
px = img.load()
d = ImageDraw.Draw(img)

# API gateway segments - detect vertical dividers in band y=194-218
y = 206
segments = []
start = None
for x in range(15, 520):
    p = px[x, y]
    dark = sum(p) < 140
    if dark and start is None:
        start = x
    if not dark and start is not None:
        segments.append((start, 194, x, 218))
        start = None
if start is not None:
    segments.append((start, 194, 519, 218))
print("API segments:", segments)

# Top analyst icons - white card detection in y=95-175, x=30-430
def cards_in_region(x0, y0, x1, y1):
    visited = set()
    boxes = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if (x, y) in visited:
                continue
            p = px[x, y]
            if not (p[0] > 235 and p[1] > 235 and p[2] > 235):
                continue
            stack = [(x, y)]
            minx = maxx = x
            miny = maxy = y
            count = 0
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in visited:
                    continue
                if cx < x0 or cy < y0 or cx >= x1 or cy >= y1:
                    continue
                cp = px[cx, cy]
                if not (cp[0] > 230 and cp[1] > 230 and cp[2] > 230):
                    continue
                visited.add((cx, cy))
                count += 1
                minx = min(minx, cx)
                maxx = max(maxx, cx)
                miny = min(miny, cy)
                maxy = max(maxy, cy)
                if count > 8000:
                    break
                stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])
            if 500 < count < 8000 and (maxx - minx) > 40 and (maxy - miny) > 30:
                boxes.append((minx, miny, maxx, maxy, count))
    return sorted(boxes, key=lambda b: (b[1], b[0]))

tops = cards_in_region(25, 90, 450, 185)
print("TOP cards", len(tops))
for b in tops:
    print(b)

# Dark boxes right side
def dark_boxes(x0, x1, y0, y1):
    visited = set()
    boxes = []
    pred = lambda p: sum(p) < 125 and max(p) - min(p) < 20
    for y in range(y0, y1):
        for x in range(x0, x1):
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
                if cx < x0 or cy < y0 or cx >= x1 or cy >= y1:
                    continue
                if not pred(px[cx, cy]):
                    continue
                visited.add((cx, cy))
                count += 1
                minx = min(minx, cx)
                maxx = max(maxx, cx)
                miny = min(miny, cy)
                maxy = max(maxy, cy)
                if count > 15000:
                    break
                stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])
            if 600 < count < 15000 and (maxx - minx) > 60 and (maxy - miny) > 10:
                boxes.append((minx, miny, maxx, maxy, count))
    return sorted(boxes, key=lambda b: (b[1], b[0]))

conn = dark_boxes(575, 720, 230, 420)
ext = dark_boxes(725, 910, 230, 560)
comp = dark_boxes(905, 1010, 245, 470)
integ = dark_boxes(905, 1010, 475, 635)
norm = cards_in_region(470, 245, 575, 420)

print("CONN", len(conn))
for b in conn: print("C", b)
print("EXT", len(ext))
for b in ext: print("E", b)
print("NORM", len(norm))
for b in norm: print("N", b)
print("COMP", len(comp))
for b in comp: print("P", b)
print("INT", len(integ))
for b in integ: print("I", b)

# bottom icon squares - light blue/teal icons ~ y 455-575
icons = cards_in_region(15, 450, 1000, 580)
print("ICONS", len(icons))
for b in icons: print("IC", b)

out = Image.open("finskalp-platform-architecture-v2-source.png").convert("RGB")
d2 = ImageDraw.Draw(out)
for lst, color in [(tops,'lime'),(conn,'red'),(ext,'blue'),(norm,'yellow'),(comp,'orange'),(integ,'purple'),(icons,'cyan')]:
    for b in lst:
        d2.rectangle((b[0],b[1],b[2],b[3]), outline=color, width=2)
for b in [(18, 130, 179, 154)]:
    pass
# red left
reds = [(18, 130, 179, 154),(18, 159, 179, 182),(18, 187, 179, 209),(18, 214, 179, 237),(18, 242, 179, 262),(18, 292, 178, 310),(18, 314, 178, 333),(18, 338, 178, 357),(18, 362, 178, 381),(18, 386, 178, 405),(18, 409, 178, 427),(18, 432, 178, 451)]
for b in reds:
    d2.rectangle(b, outline='green', width=2)
for b in segments:
    d2.rectangle(b, outline='magenta', width=2)
d2.ellipse((318, 278, 472, 402), outline='white', width=2)
out.save("_debug_boxes2.png")
