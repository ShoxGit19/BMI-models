"""
Har bir ijtimoiy tarmoq uchun rasmiy brand ranglarida PNG ikonka yaratadi.
Natija: static/icons/ papkasiga saqlanadi.
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "icons")
os.makedirs(ICONS_DIR, exist_ok=True)

FONT_BOLD   = "C:/Windows/Fonts/arialbd.ttf"
FONT_NORMAL = "C:/Windows/Fonts/arial.ttf"
SIZE = 200   # har bir ikonka o'lchami (piksel)


def _font(size):
    try:
        return ImageFont.truetype(FONT_BOLD, size)
    except Exception:
        return ImageFont.load_default()


def _circle_bg(color, size=SIZE):
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size - 1, size - 1], fill=color)
    return img, draw


def _round_rect_bg(color, size=SIZE, radius=None):
    radius = radius or size // 5
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=color)
    return img, draw


def _center_text(draw, text, font, size=SIZE, color="white"):
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - w) // 2 - bbox[0]
    y = (size - h) // 2 - bbox[1]
    draw.text((x, y), text, fill=color, font=font)


# ── LinkedIn ──────────────────────────────────────────────────
def make_linkedin():
    img, draw = _circle_bg("#0077B5")
    fn = _font(int(SIZE * 0.52))
    _center_text(draw, "in", fn, color="white")
    path = os.path.join(ICONS_DIR, "linkedin.png")
    img.save(path)
    print(f"✅ LinkedIn -> {path}")


# ── GitHub ────────────────────────────────────────────────────
def make_github():
    img, draw = _circle_bg("#181717")
    # Octocat silhouetti: bosh doira + quloqlar + tanasi
    s = SIZE
    # Bosh
    draw.ellipse([s*0.22, s*0.12, s*0.78, s*0.68], fill="white")
    # Chap quloq
    draw.polygon([(s*0.22, s*0.20), (s*0.10, s*0.06), (s*0.32, s*0.18)], fill="white")
    # O'ng quloq
    draw.polygon([(s*0.78, s*0.20), (s*0.90, s*0.06), (s*0.68, s*0.18)], fill="white")
    # Ko'zlar (qora)
    draw.ellipse([s*0.33, s*0.28, s*0.43, s*0.40], fill="#181717")
    draw.ellipse([s*0.57, s*0.28, s*0.67, s*0.40], fill="#181717")
    # Tana
    draw.ellipse([s*0.20, s*0.56, s*0.80, s*0.96], fill="white")
    # Quyruq (o'ng pastda)
    draw.arc([s*0.62, s*0.72, s*0.95, s*0.98], start=200, end=360, fill="white", width=int(s*0.06))
    path = os.path.join(ICONS_DIR, "github.png")
    img.save(path)
    print(f"✅ GitHub -> {path}")


# ── Instagram ────────────────────────────────────────────────
def make_instagram():
    s = SIZE
    # Gradient fon: to'rt burchak gradient (sariq → qizil → binafsha → ko'k)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    # Gradient uchun har bir pikselni hisoblaymiz
    pixels = img.load()
    corners = [
        (253, 218, 116),   # past-chap (sariq)
        (245, 133,  41),   # o'rta-chap (to'q sariq)
        (214,  36,  99),   # o'rta (qizil)
        (134,  49, 168),   # o'rta-o'ng (binafsha)
        ( 66,  87, 219),   # yuqori-o'ng (ko'k)
    ]
    for y in range(s):
        for x in range(s):
            # diagonalga qarab interpolatsiya
            t = (x + (s - 1 - y)) / (2 * (s - 1))
            t = max(0.0, min(1.0, t))
            idx = t * (len(corners) - 1)
            lo = int(idx); hi = min(lo + 1, len(corners) - 1)
            frac = idx - lo
            r = int(corners[lo][0] * (1 - frac) + corners[hi][0] * frac)
            g = int(corners[lo][1] * (1 - frac) + corners[hi][1] * frac)
            b = int(corners[lo][2] * (1 - frac) + corners[hi][2] * frac)
            pixels[x, y] = (r, g, b, 255)

    # Yumaloq burchaklar uchun mask
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s-1, s-1], radius=s//5, fill=255)
    img.putalpha(mask)

    draw = ImageDraw.Draw(img)
    m = int(s * 0.14)          # chegaradan masofa
    lw = max(6, int(s * 0.07)) # chiziq qalinligi

    # Kamera ramkasi (oq yumaloq to'rtburchak)
    draw.rounded_rectangle([m, m, s-m-1, s-m-1], radius=s//8,
                            outline="white", width=lw)
    # Kamera linzasi (tashqi doira)
    c = s // 2
    r1 = int(s * 0.22)
    draw.ellipse([c-r1, c-r1, c+r1, c+r1], outline="white", width=lw)
    # Linza ichi (to'ldirilgan)
    r2 = int(s * 0.10)
    draw.ellipse([c-r2, c-r2, c+r2, c+r2], fill="white")
    # Flash nuqtasi (yuqori o'ng)
    fr = max(4, int(s * 0.055))
    fx, fy = int(s * 0.72), int(s * 0.28)
    draw.ellipse([fx-fr, fy-fr, fx+fr, fy+fr], fill="white")

    path = os.path.join(ICONS_DIR, "instagram.png")
    img.save(path)
    print(f"✅ Instagram -> {path}")


# ── Telegram ─────────────────────────────────────────────────
def make_telegram():
    s = SIZE
    img, draw = _circle_bg("#2AABEE")
    # Qog'oz samolyot (paper plane) — Telegram rasmi logo
    cx, cy = s // 2, s // 2
    pts = [
        (int(s*0.18), int(s*0.48)),   # dum chap
        (int(s*0.82), int(s*0.28)),   # uchki (o'ng-yuqori)
        (int(s*0.45), int(s*0.72)),   # pastki burchak
        (int(s*0.45), int(s*0.52)),   # orqa ichki
    ]
    draw.polygon([pts[0], pts[1], pts[3]], fill="white")    # yuqori qanot
    draw.polygon([pts[3], pts[1], pts[2]], fill="#C2E5F5")  # pastki qanot (soya)
    # O'q chizig'i (tana)
    draw.line([pts[0], pts[1]], fill="white", width=max(4, int(s*0.045)))
    path = os.path.join(ICONS_DIR, "telegram.png")
    img.save(path)
    print(f"✅ Telegram -> {path}")


# ── Phone (WhatsApp uslubida) ─────────────────────────────────
def make_phone():
    s = SIZE
    img, draw = _round_rect_bg("#25D366", radius=s//4)
    # Telefon trubkasi shakli
    lw = max(5, int(s * 0.07))
    # Asosiy oval (trubka tanasi)
    draw.arc([int(s*0.28), int(s*0.18), int(s*0.72), int(s*0.55)],
             start=200, end=360, fill="white", width=lw)
    # Pastki qisim
    draw.arc([int(s*0.28), int(s*0.45), int(s*0.72), int(s*0.82)],
             start=0, end=160, fill="white", width=lw)
    # Chap ushlagich
    draw.arc([int(s*0.15), int(s*0.35), int(s*0.42), int(s*0.65)],
             start=90, end=270, fill="white", width=lw)
    # O'ng ushlagich
    draw.arc([int(s*0.58), int(s*0.35), int(s*0.85), int(s*0.65)],
             start=270, end=90, fill="white", width=lw)
    path = os.path.join(ICONS_DIR, "phone.png")
    img.save(path)
    print(f"✅ Phone -> {path}")


# ── iMessage / SMS ────────────────────────────────────────────
def make_imessage():
    s = SIZE
    img, draw = _round_rect_bg("#5BD15A", radius=s//4)
    # Nutq pufagi (speech bubble)
    m = int(s * 0.15)
    r = int(s * 0.12)
    # Asosiy oval
    draw.rounded_rectangle([m, m, s-m, int(s*0.72)],
                            radius=r, fill="white")
    # Dum (pastki chap)
    tail = [
        (int(s*0.22), int(s*0.72)),
        (int(s*0.18), int(s*0.86)),
        (int(s*0.42), int(s*0.72)),
    ]
    draw.polygon(tail, fill="white")
    path = os.path.join(ICONS_DIR, "imessage.png")
    img.save(path)
    print(f"✅ iMessage -> {path}")


if __name__ == "__main__":
    print(f"Ikonkalar yaratilmoqda: {ICONS_DIR}\n")
    make_linkedin()
    make_github()
    make_instagram()
    make_telegram()
    make_phone()
    make_imessage()
    print("\n🎉 Barcha ikonkalar tayyor!")
