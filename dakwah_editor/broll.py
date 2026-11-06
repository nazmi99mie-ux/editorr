"""Padankan gambar/video AI (B-roll) dengan perkara yang diceritakan, dan jana
senarai prompt AI untuk setiap isi."""

import json
import os
import re

from .keywords import DEFAULT_VISUAL, PROMPT_STYLE, VISUALS, keyword_of, norm

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
VID_EXT = {".mp4", ".mov", ".mkv", ".webm"}


def load_library(broll_dir: str) -> list:
    """Setiap fail dipadankan melalui nama fail (cth. 'syurga_taman.jpg' ->
    kata kunci {syurga, taman}) atau broll.json [{file, keywords}]."""
    lib = []
    if not broll_dir or not os.path.isdir(broll_dir):
        return lib
    manifest = os.path.join(broll_dir, "broll.json")
    if os.path.exists(manifest):
        with open(manifest, encoding="utf-8") as f:
            for item in json.load(f):
                p = os.path.join(broll_dir, item["file"])
                if os.path.exists(p):
                    lib.append({"path": p, "keywords": {norm(k) for k in item["keywords"]},
                                "uses": 0})
    listed = {x["path"] for x in lib}
    for name in sorted(os.listdir(broll_dir)):
        p = os.path.join(broll_dir, name)
        stem, ext = os.path.splitext(name)
        if p in listed or ext.lower() not in IMG_EXT | VID_EXT:
            continue
        kws = {norm(k) for k in re.split(r"[_\-\s.]+", stem) if k and not k.isdigit()}
        lib.append({"path": p, "keywords": kws, "uses": 0})
    for x in lib:
        x["video"] = os.path.splitext(x["path"])[1].lower() in VID_EXT
    return lib


def place_broll(timeline: dict, lib: list, clip_len=3.2, min_gap=3.5,
                hook_protect=2.5, max_uses=2) -> list:
    """Pulangkan senarai {path, start, dur, video} pada garis masa output."""
    if not lib:
        return []
    placed, last_end = [], -99.0
    total = timeline["duration"]
    for w in timeline["words"]:
        if w["s"] < hook_protect or w["s"] - last_end < min_gap:
            continue
        n = norm(w["w"])
        k = w["kw"]
        cands = [x for x in lib if x["uses"] < max_uses and
                 (n in x["keywords"] or (k and k in x["keywords"]))]
        if not cands:
            continue
        item = min(cands, key=lambda x: x["uses"])
        start = max(0.0, w["s"] - 0.15)
        dur = min(clip_len, total - start - 0.5)
        if dur < 1.2:
            continue
        item["uses"] += 1
        placed.append({"path": item["path"], "start": round(start, 3),
                       "dur": round(dur, 3), "video": item["video"]})
        last_end = start + dur
    return placed


def write_prompts(data_plan: dict, timeline: dict, path: str) -> None:
    """Fail Markdown: satu prompt AI bagi setiap isi terpilih + nama fail
    cadangan supaya ia dipadankan secara automatik."""
    by_sid = {}
    for w in timeline["words"]:
        by_sid.setdefault(w["sid"], []).append(w)
    texts = {s["id"]: s["text"] for s in data_plan["sentences"]}
    out = ["# Prompt B-roll AI\n",
           "Jana imej/video (Midjourney, Flux, Runway, Kling, Veo, dsb.) mengikut prompt di bawah, "
           "simpan dalam folder `broll/` dengan **nama fail yang dicadangkan**, kemudian jalankan "
           "semula `render`. Fail dipadankan dengan perkataan yang disebut berdasarkan nama fail.\n"]
    seen = set()
    for sec in timeline["sections"]:
        ws = by_sid.get(sec["sid"], [])
        kws = []
        for w in ws:
            k = w["kw"] or keyword_of(w["w"])
            if k and k in VISUALS and k not in kws:
                kws.append(k)
        if not kws:
            continue
        k = next((x for x in kws if x not in seen), kws[0])
        seen.add(k)
        visual = VISUALS.get(k, DEFAULT_VISUAL)
        mm, ss = divmod(int(sec["start"]), 60)
        out.append(f"## {mm:02}:{ss:02} — \"{texts.get(sec['sid'], '')}\"\n")
        out.append(f"- Kata kunci: **{k}**  → nama fail: `{k}_1.jpg` (atau `{k}_1.mp4`)")
        out.append(f"- Prompt: `{visual}, {PROMPT_STYLE}`\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def find_cue(timeline: dict, cue: str, nth: int = 1):
    """Cari kemunculan ke-n perkataan `cue` (atau frasa 'a b') pada garis masa
    output. Pulangkan perkataan pertama frasa itu, atau None."""
    toks = [norm(x) for x in cue.split()]
    ws = timeline["words"]
    seen = 0
    for i in range(len(ws) - len(toks) + 1):
        if all(norm(ws[i + j]["w"]) == toks[j] for j in range(len(toks))):
            seen += 1
            if seen == nth:
                return ws[i]
    return None


def place_cued(timeline: dict, cues: list, broll_dir: str) -> list:
    """B-roll ditetapkan secara manual: [{"file", "cue", "nth", "dur", "offset"}].
    Klip dipotong supaya tidak bertindih dengan klip seterusnya."""
    placed = []
    total = timeline["duration"]
    for c in cues:
        path = os.path.join(broll_dir, c["file"])
        if not os.path.exists(path):
            print(f"[broll] tiada fail: {path}")
            continue
        w = find_cue(timeline, c["cue"], c.get("nth", 1))
        if not w:
            print(f"[broll] cue tidak dijumpai: {c['cue']} #{c.get('nth', 1)}")
            continue
        start = max(0.0, w["s"] + c.get("offset", -0.12))
        dur = c.get("dur", 3.0)
        if c.get("to_end"):
            dur = total - start
        placed.append({"path": path, "start": round(start, 3), "dur": round(dur, 3),
                       "video": os.path.splitext(path)[1].lower() in VID_EXT})
    placed.sort(key=lambda b: b["start"])
    for a, b in zip(placed, placed[1:]):
        a["dur"] = round(min(a["dur"], b["start"] - a["start"]), 3)
    placed = [b for b in placed if b["dur"] >= 0.6]
    for b in placed:
        b["dur"] = round(min(b["dur"], total - b["start"]), 3)
    return placed


def resolve_callouts(timeline: dict, callouts: list) -> list:
    out = []
    for c in callouts:
        w = find_cue(timeline, c["cue"], c.get("nth", 1))
        if not w:
            print(f"[callout] cue tidak dijumpai: {c['cue']}")
            continue
        out.append({"start": round(w["s"] + c.get("offset", 0.0), 3),
                    "dur": c.get("dur", 2.2), "text": c["text"], "sub": c.get("sub", "")})
    return out
