from PIL import Image

img = Image.open("finskalp-platform-architecture-v2-source.png").convert("RGB")
px = img.load()

def white_cards(y0, y1, x0, x1):
    visited = set()
    boxes = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if (x, y) in visited:
                continue
            p = px[x, y]
            if not (p[0] > 240 and p[1] > 240 and p[2] > 240):
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
                if not (cp[0] > 238 and cp[1] > 238 and cp[2] > 238):
                    continue
                visited.add((cx, cy))
                count += 1
                minx, maxx = min(minx, cx), max(maxx, cx)
                miny, maxy = min(miny, cy), max(maxy, cy)
                if count > 2500:
                    break
                stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])
            w, h = maxx - minx, maxy - miny
            if 400 < count < 2500 and 50 < w < 100 and 20 < h < 45:
                boxes.append((minx, miny, maxx, maxy))
    return sorted(boxes, key=lambda b: (b[1], b[0]))

print(white_cards(100, 190, 25, 420))
