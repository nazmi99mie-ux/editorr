"""Pembetulan transkrip: cantum token bersempang ("anak -anak" -> "anak-anak")
dan betulkan/buang perkataan yang tersalah dengar oleh Whisper."""

import json

from .keywords import norm


def merge_hyphens(data: dict) -> dict:
    for seg in data["segments"]:
        out = []
        for w in seg["words"]:
            if out and w["w"].startswith("-"):
                out[-1] = {**out[-1], "w": out[-1]["w"] + w["w"], "e": w["e"]}
            else:
                out.append(dict(w))
        seg["words"] = out
    return data


def apply_fixes(data: dict, fixes: list) -> dict:
    """fixes: [{"from": "Ayak", "to": "Air", "after": 32.0}] — gantikan perkataan
    pertama yang sepadan selepas masa `after` (saat sumber). "to": "" = buang.
    "all": true = gantikan setiap kemunculan."""
    for fx in fixes:
        src, dst = norm(fx["from"]), fx["to"]
        after = fx.get("after", 0.0)
        for seg in data["segments"]:
            hit = False
            for w in seg["words"]:
                if w["s"] + 1e-3 >= after and norm(w["w"]) == src and not w.get("_fixed"):
                    tail = w["w"][len(w["w"].rstrip(".,?!")):]
                    w["w"] = (dst + tail) if dst else ""
                    w["_fixed"] = True
                    hit = True
                    if not fx.get("all"):
                        break
            if hit and not fx.get("all"):
                break
        else:
            if not fx.get("all"):
                print(f"[textfix] tidak dijumpai: {fx}")
    for seg in data["segments"]:
        seg["words"] = [{k: v for k, v in w.items() if k != "_fixed"}
                        for w in seg["words"] if w["w"].strip()]
    data["segments"] = [s for s in data["segments"] if s["words"]]
    return data


def load_and_fix(data: dict, fixes_path: str = None) -> dict:
    merge_hyphens(data)
    if fixes_path:
        with open(fixes_path, encoding="utf-8") as f:
            apply_fixes(data, json.load(f))
    return data


def detect_silences(media: str, noise_db: float = -32, min_dur: float = 0.25) -> list:
    import re
    import subprocess
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", media, "-af",
                        f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(starts, ends))


def snap_to_silences(data: dict, silences: list, margin: float = 0.04) -> int:
    """Whisper sering 'meregangkan' perkataan merentasi jeda. Pangkas cap masa
    perkataan supaya tidak menutupi senyap sebenar — jeda itu kemudian dipotong
    oleh build_timeline. Pulangkan bilangan perkataan yang diubah."""
    n = 0
    for a, b in silences:
        a2, b2 = a + margin, b - margin
        if b2 - a2 < 0.12:
            continue
        for seg in data["segments"]:
            for w in seg["words"]:
                if w["s"] < a2 < w["e"] and w["e"] - a2 > 0.05:
                    w["e"] = round(max(w["s"] + 0.08, a2), 3)
                    n += 1
                elif w["s"] < b2 < w["e"] and b2 - w["s"] > 0.05:
                    w["s"] = round(min(w["e"] - 0.08, b2), 3)
                    n += 1
    return n
