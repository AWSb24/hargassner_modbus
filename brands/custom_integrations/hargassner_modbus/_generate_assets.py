"""Generate icon/logo PNGs for the hargassner_modbus integration (home-assistant/brands)."""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = r"Z:/wir/Entwicklung/SW/Hargassner/brands/custom_integrations/hargassner_modbus"
os.makedirs(OUT, exist_ok=True)
SS = 4  # supersampling


def bezier(p0, p1, p2, p3, n=40):
    pts = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        x = mt**3*p0[0] + 3*mt*mt*t*p1[0] + 3*mt*t*t*p2[0] + t**3*p3[0]
        y = mt**3*p0[1] + 3*mt*mt*t*p1[1] + 3*mt*t*t*p2[1] + t**3*p3[1]
        pts.append((x, y))
    return pts


# Flame outline in normalized 0..1 coords (y down), assembled from bezier segments.
TIP = (0.50, 0.05)
SEGMENTS = [
    (TIP,          (0.82, 0.30), (0.74, 0.52), (0.70, 0.62)),
    ((0.70, 0.62), (0.88, 0.74), (0.80, 0.92), (0.56, 0.96)),
    ((0.56, 0.96), (0.42, 0.99), (0.29, 0.91), (0.30, 0.78)),
    ((0.30, 0.78), (0.17, 0.66), (0.41, 0.56), (0.38, 0.42)),
    ((0.38, 0.42), (0.36, 0.25), (0.44, 0.13), TIP),
]


def flame_outline(scale=1.0, cx=0.5, cy=0.60, dy=0.0):
    pts = []
    for seg in SEGMENTS:
        pts.extend(bezier(*seg))
    # scale toward centroid (for the inner flame) and optionally shift down
    return [(cx + (x - cx) * scale, cy + (y - cy) * scale + dy) for x, y in pts]


def vgradient(size, top, bottom):
    w, h = size
    grad = Image.new("RGBA", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
        grad.putpixel((0, y), c)
    return grad.resize((w, h))


def fill_polygon(img, norm_pts, top, bottom, box):
    """Fill a normalized polygon with a vertical gradient inside box=(x,y,w,h)."""
    x0, y0, bw, bh = box
    poly = [(x0 + x * bw, y0 + y * bh) for x, y in norm_pts]
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    grad = vgradient(img.size, top, bottom)
    img.paste(grad, (0, 0), mask)


def make_icon(px):
    S = px * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # rounded-square tile filling the whole canvas (square + trimmed for brands CI)
    tile = vgradient((S, S), (255, 138, 26), (200, 28, 28))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(0.22 * S), fill=255)
    img.paste(tile, (0, 0), mask)
    # flame: cream outer, warm-gold inner — inset within the tile
    box = (int(0.16 * S), int(0.10 * S), int(0.68 * S), int(0.80 * S))
    fill_polygon(img, flame_outline(1.0), (255, 248, 238), (255, 230, 200), box)
    fill_polygon(img, flame_outline(0.52, dy=0.07), (255, 209, 122), (255, 170, 70), box)
    return img.resize((px, px), Image.LANCZOS)


def make_logo(h):
    """Build a horizontal logo (flame + wordmark); width derived from the text."""
    S = SS
    H = h * S
    fb = H  # flame occupies a square of height H
    txt = "Hargassner"
    font_path = next(
        (c for c in (r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf")
         if os.path.exists(c)), None)
    font = ImageFont.truetype(font_path, int(0.42 * H)) if font_path else None

    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    tb = tmp.textbbox((0, 0), txt, font=font) if font else (0, 0, 0, 0)
    tw = tb[2] - tb[0]
    gap = int(0.06 * H)
    pad = int(0.06 * H)
    W = int(0.92 * fb) + gap + tw + pad

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    box = (int(0.04 * fb), int(0.05 * fb), int(0.84 * fb), int(0.9 * fb))
    fill_polygon(img, flame_outline(1.0), (255, 150, 20), (206, 28, 28), box)
    fill_polygon(img, flame_outline(0.52, dy=0.07), (255, 224, 130), (255, 122, 0), box)
    if font:
        draw = ImageDraw.Draw(img)
        tx = int(0.92 * fb) + gap - tb[0]
        ty = (H - (tb[3] - tb[1])) // 2 - tb[1]
        draw.text((tx, ty), txt, font=font, fill=(43, 43, 43, 255))
    bbox = img.getbbox()  # trim transparent border for brands
    if bbox:
        img = img.crop(bbox)
    return img.resize((img.width // S, img.height // S), Image.LANCZOS)


make_icon(256).save(os.path.join(OUT, "icon.png"))
make_icon(512).save(os.path.join(OUT, "icon@2x.png"))
make_logo(128).save(os.path.join(OUT, "logo.png"))
make_logo(256).save(os.path.join(OUT, "logo@2x.png"))
print("written to", OUT)
for f in sorted(os.listdir(OUT)):
    p = os.path.join(OUT, f)
    print(" ", f, os.path.getsize(p), "bytes", Image.open(p).size)
