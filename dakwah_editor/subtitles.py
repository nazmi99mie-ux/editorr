"""Subtitle ASS perkataan-demi-perkataan dengan highlight beranimasi,
tajuk hook, flash peralihan dan kad penutup (CTA)."""

W, H = 1080, 1920

# Warna ASS dalam format &HAABBGGRR
WHITE = "&H00FFFFFF"
GOLD = "&H0037C8FF"      # kuning keemasan (#FFC837)
EMBER = "&H003C8CFF"     # oren hangat (#FF8C3C)
BLACK = "&H00000000"


def _ts(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = t % 60
    return f"{h}:{m:02}:{s:05.2f}"


def _esc(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def group_words(words: list, max_words=3, max_chars=20, gap=0.45) -> list:
    groups, cur = [], []
    for w in words:
        if cur:
            chars = sum(len(x["w"]) + 1 for x in cur) + len(w["w"])
            brk = (len(cur) >= max_words or chars > max_chars
                   or w["s"] - cur[-1]["e"] > gap or w["sid"] != cur[-1]["sid"]
                   or cur[-1]["w"].rstrip().endswith((".", "?", "!", ",")))
            if brk:
                groups.append(cur)
                cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def build_ass(timeline: dict, path: str, font="DejaVu Sans", uppercase=True,
              title=None, cta=("SEMOGA BERMANFAAT", "Kongsikan kepada yang tersayang"),
              flashes=(), outro_start=None, total=None, sub_y=1340) -> None:
    lines = []
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{font},84,{WHITE},{WHITE},{BLACK},&H96000000,-1,0,0,0,100,100,1,0,1,7,4,5,60,60,0,1
Style: Title,{font},66,{WHITE},{WHITE},{BLACK},&H80000000,-1,0,0,0,100,100,3,0,1,5,3,8,70,70,260,1
Style: Cta,{font},78,{GOLD},{WHITE},{BLACK},&H80000000,-1,0,0,0,100,100,2,0,1,6,3,5,70,70,0,1
Style: Cta2,{font},50,{WHITE},{WHITE},{BLACK},&H80000000,0,0,0,0,100,100,1,0,1,4,2,5,70,70,0,1
Style: Fx,{font},10,{WHITE},{WHITE},{BLACK},{BLACK},0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    words = timeline["words"]
    groups = group_words(words)
    for gi, g in enumerate(groups):
        g_end = g[-1]["e"] + 0.25
        if gi + 1 < len(groups):
            g_end = min(g_end, groups[gi + 1][0]["s"])
        g_end = max(g_end, g[-1]["e"])
        for wi, w in enumerate(g):
            start = w["s"] if wi else min(w["s"], max(0.0, w["s"] - 0.05))
            end = g[wi + 1]["s"] if wi + 1 < len(g) else g_end
            if end - start < 0.02:
                continue
            parts = []
            for j, x in enumerate(g):
                txt = _esc(x["w"].upper() if uppercase else x["w"])
                if j == wi:
                    if x["kw"]:
                        # perkataan penting: emas, glow, pop besar
                        parts.append(
                            "{\\c" + GOLD + "\\3c&H001A3A6B&\\bord9\\blur2\\fscx140\\fscy140"
                            "\\t(0,140,\\fscx118\\fscy118)}" + txt + "{\\r}")
                    else:
                        parts.append("{\\c" + GOLD + "\\fscx118\\fscy118\\t(0,110,\\fscx106\\fscy106)}"
                                     + txt + "{\\r}")
                elif j > wi:
                    parts.append("{\\alpha&H70&}" + txt + "{\\r}")
                else:
                    col = EMBER if x["kw"] else WHITE
                    parts.append("{\\c" + col + "}" + txt + "{\\r}")
            intro = ""
            if wi == 0:
                intro = "{\\fad(60,0)\\fscx85\\fscy85\\t(0,120,\\fscx100\\fscy100)}"
            text = f"{{\\an5\\pos({W // 2},{sub_y})}}" + intro + " ".join(parts)
            lines.append(f"Dialogue: 2,{_ts(start)},{_ts(end)},Sub,,0,0,0,,{text}")

    # Tajuk hook (pilihan)
    if title:
        lines.append(
            f"Dialogue: 3,{_ts(0.15)},{_ts(4.2)},Title,,0,0,0,,"
            "{\\fad(200,300)\\move(540,180,540,240,0,350)\\an8\\c" + GOLD + "}"
            + _esc(title.upper()))

    # Flash putih pada peralihan (lukisan ASS sepenuh skrin)
    rect = f"m 0 0 l {W} 0 {W} {H} 0 {H}"
    for at, strength in flashes:
        alpha = int(255 * (1 - strength))
        lines.append(
            f"Dialogue: 4,{_ts(at)},{_ts(at + 0.35)},Fx,,0,0,0,,"
            f"{{\\an7\\pos(0,0)\\bord0\\shad0\\1a&H{alpha:02X}&\\fad(0,300)\\p1}}{rect}")

    # Kad penutup
    if outro_start is not None and total:
        dim = f"{{\\an7\\pos(0,0)\\bord0\\shad0\\1c&H000000&\\1a&H50&\\fad(500,0)\\p1}}{rect}"
        lines.append(f"Dialogue: 1,{_ts(outro_start)},{_ts(total)},Fx,,0,0,0,,{dim}")
        lines.append(
            f"Dialogue: 5,{_ts(outro_start + 0.2)},{_ts(total)},Cta,,0,0,0,,"
            f"{{\\an5\\pos(540,880)\\fad(400,0)\\fscx80\\fscy80\\t(0,400,\\fscx100\\fscy100)}}{_esc(cta[0])}")
        lines.append(
            f"Dialogue: 5,{_ts(outro_start + 0.6)},{_ts(total)},Cta2,,0,0,0,,"
            f"{{\\an5\\pos(540,990)\\fad(400,0)}}{_esc(cta[1])}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines) + "\n")
