"""Bina aset logo untuk video daripada satu imej logo berlatar putih
(boleh mengandungi beberapa logo bersebelahan):

    python -m dakwah_editor.brandkit logo.jpg outdir/

Menghasilkan:
  outdir/lencana.png  — lencana kecil (kad putih bersudut bulat, bingkai emas) untuk sudut atas
  outdir/kad_logo.png — kad logo besar untuk kad penutup
"""

import argparse
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

GOLD = (255, 200, 55, 255)
DIVIDER = (30, 120, 40, 255)


def _whiten(im: Image.Image) -> Image.Image:
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    lo = a.min(axis=2, keepdims=True)
    t = np.clip((lo - 215) / 25, 0, 1)  # latar hampir putih (JPEG) -> putih tulen
    return Image.fromarray((a * (1 - t) + 255 * t).astype(np.uint8))


def split_logos(im: Image.Image, thresh=225, min_gap=30) -> list:
    """Pisahkan logo bersebelahan ikut lajur kosong (putih)."""
    a = np.asarray(im.convert("RGB")).astype(int)
    ink = a.min(axis=2) < thresh
    cols = ink.sum(0) > 2
    # garis pemisah nipis dikira kosong
    cols &= ink.sum(0) < ink.shape[0] * 0.5
    spans, start, gap = [], None, 0
    for x, c in enumerate(cols):
        if c:
            if start is None:
                start = x
            gap = 0
        elif start is not None:
            gap += 1
            if gap >= min_gap:
                spans.append((start, x - gap + 1))
                start, gap = None, 0
    if start is not None:
        spans.append((start, len(cols)))
    out = []
    for x0, x1 in spans:
        if x1 - x0 < 60:
            continue
        ys = np.where(ink[:, x0:x1].sum(1) > 2)[0]
        out.append(im.crop((x0, ys[0], x1, ys[-1] + 1)))
    return out


def _rounded(w, h, r, fill):
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(c).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=fill)
    return c


def _with_shadow(card, blur, off):
    w, h = card.size
    m = blur * 2
    sh = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    mask = Image.new("RGBA", card.size, (0, 0, 0, 160))
    mask.putalpha(card.getchannel("A").point(lambda v: int(v * 0.65)))
    sh.paste(mask, (m, m + off))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    sh.alpha_composite(card, (m, m))
    return sh


def _row(logos, height, pad, radius, border, inner=False, width=None):
    ih = height - 2 * pad
    rs = [lg.resize((max(1, int(lg.width * ih / lg.height)), ih), Image.LANCZOS) for lg in logos]
    content = sum(r.width for r in rs)
    if width is None:
        gap = pad
        width = content + gap * (len(rs) + 1)
    else:
        gap = max(pad // 2, (width - content) // (len(rs) + 1))
    card = _rounded(width, height, radius, (255, 255, 255, 255))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, width - 1, height - 1], radius, outline=GOLD, width=border)
    if inner:
        d.rounded_rectangle([12, 12, width - 13, height - 13], radius - 8,
                            outline=(255, 200, 55, 150), width=2)
    x = gap
    for i, r in enumerate(rs):
        card.paste(r, (x, pad))
        x += r.width
        if i < len(rs) - 1:
            dx = x + gap // 2
            d.line([dx, pad + ih * 0.1, dx, pad + ih * 0.9], fill=DIVIDER, width=max(2, border - 2))
        x += gap
    return card


def build(logo_path: str, outdir: str) -> dict:
    os.makedirs(outdir, exist_ok=True)
    im = _whiten(Image.open(logo_path))
    logos = split_logos(im) or [im]
    badge = _with_shadow(_row(logos, 150, 16, 26, 3), 10, 6)
    card = _with_shadow(_row(logos, 510, 45, 40, 5, inner=True, width=820), 18, 12)
    paths = {"badge": os.path.join(outdir, "lencana.png"),
             "card": os.path.join(outdir, "kad_logo.png")}
    badge.save(paths["badge"])
    card.save(paths["card"])
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("logo")
    ap.add_argument("outdir")
    a = ap.parse_args()
    print(build(a.logo, a.outdir))
