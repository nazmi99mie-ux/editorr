"""Lapisan grafik 'premium' (ASS): pembukaan bar sinematik, tag jenama emas,
habuk emas terapung, light leak pada peralihan, latar lembut subtitle,
bar progres dan ornamen kad penutup."""

import numpy as np

W, H = 1080, 1920
GOLD = "&H0037C8FF"
GOLD_DEEP = "&H00208FD8"


def _ts(t: float) -> str:
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02}:{t % 60:05.2f}"


def _rect(w, h):
    return f"m 0 0 l {w} 0 {w} {h} 0 {h}"


def _circle(r):
    k = r * 0.5523
    return (f"m 0 {-r} b {k} {-r} {r} {-k} {r} 0 b {r} {k} {k} {r} 0 {r} "
            f"b {-k} {r} {-r} {k} {-r} 0 b {-r} {-k} {-k} {-r} 0 {-r}")


def _d(layer, a, b, text, style="Fx"):
    return f"Dialogue: {layer},{_ts(a)},{_ts(b)},{style},,0,0,0,,{text}"


def layers(speech_end: float, total: float, brand: str = None, leaks=(),
           sub_y: int = 1340, seed: int = 5, font: str = "DejaVu Sans") -> list:
    rng = np.random.default_rng(seed)
    out = []
    base = "\\bord0\\shad0"

    # 1. Pembukaan: dua bar hitam terbuka seperti tirai pawagam
    half = H // 2
    out.append(_d(9, 0, 0.75, f"{{\\an7{base}\\1c&H000000&\\move(0,0,0,{-half - 40},60,700)\\p1}}"
                  f"{_rect(W, half + 4)}"))
    out.append(_d(9, 0, 0.75, f"{{\\an7{base}\\1c&H000000&\\move(0,{half - 4},0,{H + 40},60,700)\\p1}}"
                  f"{_rect(W, half + 4)}"))
    # garis cahaya emas di tengah semasa tirai terbuka
    out.append(_d(9, 0, 0.6, f"{{\\an5{base}\\1c{GOLD}\\blur6\\pos({W // 2},{half})\\fscx10"
                  f"\\t(0,350,\\fscx100)\\fad(0,250)\\p1}}m -540 -3 l 540 -3 540 3 -540 3"))

    # 2. Latar gelap lembut di belakang subtitle (kebolehbacaan)
    band = 360
    out.append(_d(1, 0, speech_end, f"{{\\an7{base}\\pos(0,{sub_y - band // 2})\\1c&H000000&"
                  f"\\1a&H9A&\\blur45\\fad(300,300)\\p1}}{_rect(W, band)}"))

    # 3. Tag jenama emas di atas
    if brand:
        a = 3.6
        out.append(_d(7, a, speech_end,
                      f"{{\\an5\\pos({W // 2},92)\\fn{font}\\fs42\\fsp12\\b1\\1c{GOLD}\\3c&H000000&"
                      f"\\bord2\\shad2\\4a&H60&\\fad(600,300)}}{brand.upper()}"))
        for x1, x2 in ((110, 238), (842, 970)):
            out.append(_d(7, a + 0.2, speech_end,
                          f"{{\\an7\\pos({x1},91){base}\\1c{GOLD}\\1a&H30&\\fad(600,300)\\p1}}"
                          f"{_rect(x2 - x1, 2)}"))
        # kilauan sekali-sekala pada tag
        t = a + 1.0
        while t < speech_end - 2:
            out.append(_d(8, t, t + 0.9,
                          f"{{\\an5\\pos({W // 2},92)\\fn{font}\\fs42\\fsp12\\b1\\1c&HFFFFFF&\\bord0\\shad0"
                          f"\\clip(230,40,290,140)\\t(0,800,\\clip(790,40,850,140))\\blur1}}{brand.upper()}"))
            t += 9.0

    # 4. Habuk emas terapung
    t = 0.3
    while t < total:
        x = rng.uniform(40, W - 40)
        y = rng.uniform(500, H - 150)
        life = rng.uniform(5, 9)
        rise = rng.uniform(250, 600)
        drift = rng.uniform(-80, 80)
        r = rng.uniform(2.5, 6.5)
        alpha = int(rng.uniform(0x70, 0xB8))
        col = GOLD if rng.random() < 0.7 else "&H00E8F4FF"
        out.append(_d(3, t, min(total, t + life),
                      f"{{\\an5{base}\\1c{col}\\1a&H{alpha:02X}&\\blur{r * 0.8:.1f}"
                      f"\\move({x:.0f},{y:.0f},{x + drift:.0f},{y - rise:.0f})"
                      f"\\fad(1200,1500)\\p1}}{_circle(r)}"))
        t += rng.uniform(0.25, 0.55)

    # 5. Light leak jingga hangat pada setiap peralihan
    for i, at in enumerate(leaks):
        side = -1 if i % 2 else 1
        x0, x1 = (W // 2 - side * 700), (W // 2 + side * 500)
        y = rng.uniform(500, 1400)
        out.append(_d(5, max(0, at - 0.25), at + 0.75,
                      f"{{\\an5{base}\\1c&H2A7CFF&\\blur140\\move({x0},{y:.0f},{x1},{y - 200:.0f})"
                      f"\\1a&HFF&\\t(0,300,\\1a&H8C&)\\t(450,1000,\\1a&HFF&)\\p1}}{_circle(520)}"))

    # 6. Bar progres emas di bawah
    out.append(_d(7, 0.6, speech_end, f"{{\\an7\\pos(0,{H - 10}){base}\\1c&H000000&\\1a&H70&\\p1}}"
                  f"{_rect(W, 10)}"))
    out.append(_d(8, 0.6, speech_end,
                  f"{{\\an7\\pos(0,{H - 10}){base}\\1c{GOLD}\\fscx0"
                  f"\\t(0,{int((speech_end - 0.6) * 1000)},\\fscx100)\\p1}}{_rect(W, 10)}"))
    return out


def outro_layers(outro_start: float, total: float, brand: str = None,
                 font: str = "DejaVu Sans") -> list:
    out = []
    base = "\\bord0\\shad0"
    a = outro_start
    # bingkai ornamen emas di sekeliling CTA
    for y in (780, 1080):
        out.append(_d(6, a + 0.3, total, f"{{\\an5\\pos({W // 2},{y}){base}\\1c{GOLD}\\fscx0"
                      f"\\t(0,500,\\fscx100)\\p1}}m -300 -1 l 300 -1 300 1 -300 1"))
        out.append(_d(6, a + 0.6, total, f"{{\\an5\\pos({W // 2},{y}){base}\\1c{GOLD}\\frz45"
                      f"\\fad(300,0)\\p1}}m -9 -9 l 9 -9 9 9 -9 9"))
    if brand:
        out.append(_d(6, a + 0.1, total,
                      f"{{\\an5\\pos({W // 2},720)\\fn{font}\\fs38\\fsp14\\b1\\1c&HFFFFFF&\\bord0"
                      f"\\shad2\\fad(400,0)}}{brand.upper()}"))
    return out
