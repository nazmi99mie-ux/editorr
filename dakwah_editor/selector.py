"""Pilih isi paling menarik, buang pengulangan & ruang senyap, susun hook,
dan bina garis masa (timeline) klip."""

import re
from difflib import SequenceMatcher

from .keywords import FILLERS, HOOK_CUES, KEYWORD_WEIGHTS, keyword_of, norm

SENTENCE_GAP = 0.7     # jeda (s) yang dikira sebagai hujung ayat
MAX_KEEP_GAP = 0.22    # jeda lebih panjang daripada ini dipotong
EDGE_PAD = 0.06        # ruang sebelum/selepas perkataan pada titik potong
STUTTER_WINDOW = 0.8   # perkataan sama berulang dalam tempoh ini = gagap
FPS = 30               # semua potongan dikuantumkan pada grid bingkai


def build_sentences(data: dict) -> list:
    words = [dict(w) for seg in data["segments"] for w in seg["words"]]
    words.sort(key=lambda w: w["s"])
    sentences, cur = [], []
    for i, w in enumerate(words):
        if cur and (w["s"] - cur[-1]["e"] > SENTENCE_GAP):
            sentences.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.?!]$", w["w"]) and len(cur) >= 3:
            sentences.append(cur)
            cur = []
    if cur:
        sentences.append(cur)
    out = []
    for i, ws in enumerate(sentences):
        out.append({"id": i, "words": ws, "text": " ".join(w["w"] for w in ws)})
    return out


def clean_words(words: list) -> list:
    """Buang perkataan pengisi dan gagap (perkataan/frasa diulang serta-merta)."""
    kept = []
    for w in words:
        n = norm(w["w"])
        if not n or n in FILLERS:
            continue
        if kept and norm(kept[-1]["w"]) == n and w["s"] - kept[-1]["e"] < STUTTER_WINDOW:
            # gagap: simpan sebutan terakhir (biasanya paling jelas)
            kept[-1] = w
            continue
        kept.append(w)
    # buang pengulangan frasa 2-3 perkataan, cth: "kita mesti kita mesti"
    for n_len in (3, 2):
        i = 0
        while i + 2 * n_len <= len(kept):
            a = [norm(x["w"]) for x in kept[i:i + n_len]]
            b = [norm(x["w"]) for x in kept[i + n_len:i + 2 * n_len]]
            if a == b:
                del kept[i:i + n_len]
            else:
                i += 1
    return kept


def speech_dur(words: list) -> float:
    """Tempoh ayat selepas jeda panjang dipendekkan."""
    if not words:
        return 0.0
    d = 2 * EDGE_PAD
    for i, w in enumerate(words):
        d += w["e"] - w["s"]
        if i:
            d += min(max(0.0, w["s"] - words[i - 1]["e"]), MAX_KEEP_GAP)
    return d


def score_sentence(s: dict) -> float:
    words = s["clean"]
    if not words:
        return -99
    text = " ".join(norm(w["w"]) for w in words)
    sc = 0.0
    for w in words:
        k = keyword_of(w["w"])
        if k:
            sc += KEYWORD_WEIGHTS[k]
    if any(c in text for c in HOOK_CUES):
        sc += 3
    raw = s["text"]
    if "?" in raw:
        sc += 2
    if "!" in raw:
        sc += 1
    d = s["dur"]
    if d < 1.5:
        sc -= 3
    elif d > 18:
        sc -= (d - 18) * 0.5
    # keyakinan transkripsi rendah -> mungkin bunyi bising/tidak jelas
    probs = [w.get("p", 1.0) for w in words]
    if probs and sum(probs) / len(probs) < 0.5:
        sc -= 3
    # normalisasi supaya ayat panjang tidak sentiasa menang
    return sc / (1 + d / 12)


def dedupe(sentences: list) -> None:
    """Tandakan ayat yang hampir sama (penceramah mengulang isi)."""
    texts = [" ".join(norm(w["w"]) for w in s["clean"]) for s in sentences]
    for i in range(len(sentences)):
        if sentences[i].get("dup_of") is not None:
            continue
        for j in range(i + 1, len(sentences)):
            if sentences[j].get("dup_of") is not None:
                continue
            if not texts[i] or not texts[j]:
                continue
            if SequenceMatcher(None, texts[i], texts[j]).ratio() > 0.72:
                lo, hi = (i, j) if sentences[i]["score"] >= sentences[j]["score"] else (j, i)
                sentences[hi]["dup_of"] = lo


def make_plan(data: dict, target: float = 120.0, min_dur: float = 90.0,
              max_dur: float = 180.0) -> dict:
    sents = build_sentences(data)
    for s in sents:
        s["clean"] = clean_words(s["words"])
        s["dur"] = speech_dur(s["clean"])
        s["score"] = score_sentence(s)
    dedupe(sents)
    pool = [s for s in sents if s.get("dup_of") is None and s["clean"]]

    # Hook: ayat pendek (2.5-7s) paling kuat.
    hook_cands = [s for s in pool if 2.0 <= s["dur"] <= 7.5] or pool
    def hook_score(s):
        low = s["text"].lower()
        bonus = (4 if any(c in low for c in HOOK_CUES) else 0) + (2 if "?" in s["text"] else 0)
        return s["score"] + bonus
    hook = max(hook_cands, key=hook_score)

    target = min(max(target, min_dur), max_dur)
    budget = target - hook["dur"] - 3.0  # 3s untuk outro
    chosen = {hook["id"]}
    ranked = sorted((s for s in pool if s["id"] != hook["id"]), key=lambda s: -s["score"])
    total = 0.0
    for s in ranked:
        if total + s["dur"] > budget + 4:
            continue
        chosen.add(s["id"])
        total += s["dur"]
        if total >= budget:
            break
    # Kesinambungan cerita: masukkan ayat penghubung pendek di antara dua ayat
    # terpilih jika masih ada ruang.
    for s in pool:
        i = s["id"]
        if i in chosen or s["dur"] > 4:
            continue
        if (i - 1) in chosen and (i + 1) in chosen and total + s["dur"] <= budget + 6:
            chosen.add(i)
            total += s["dur"]

    order = [hook["id"]] + [s["id"] for s in pool if s["id"] in chosen and s["id"] != hook["id"]]
    return {
        "target": target,
        "hook": hook["id"],
        "order": order,
        "sentences": [
            {"id": s["id"], "text": s["text"], "start": s["words"][0]["s"],
             "end": s["words"][-1]["e"], "dur": round(s["dur"], 2),
             "score": round(s["score"], 2), "dup_of": s.get("dup_of"),
             "selected": s["id"] in chosen}
            for s in sents
        ],
    }


def build_timeline(data: dict, plan: dict) -> dict:
    """Tukar pelan kepada senarai klip sumber + perkataan pada garis masa output."""
    sents = {s["id"]: s for s in build_sentences(data)}
    clips, out_words, sections = [], [], []
    t = 0.0
    for idx, sid in enumerate(plan["order"]):
        words = clean_words(sents[sid]["words"])
        if not words:
            continue
        sec_start = t
        # kumpulkan perkataan berturutan kepada span (potong jeda panjang)
        spans, cur = [], [words[0]]
        for w in words[1:]:
            if w["s"] - cur[-1]["e"] > MAX_KEEP_GAP or w["s"] < cur[-1]["e"] - 0.05:
                spans.append(cur)
                cur = [w]
            else:
                cur.append(w)
        spans.append(cur)
        for sp in spans:
            a = round(max(0.0, sp[0]["s"] - EDGE_PAD), 3)
            # durasi tepat pada grid bingkai supaya audio & video tidak lari
            dur = max(1, round((sp[-1]["e"] + EDGE_PAD - a) * FPS)) / FPS
            b = a + dur
            for w in sp:
                out_words.append({
                    "w": w["w"], "s": round(t + (w["s"] - a), 3),
                    "e": round(t + (w["e"] - a), 3), "sid": sid,
                    "kw": keyword_of(w["w"]),
                })
            clips.append({"src_start": round(a, 3), "src_end": round(b, 3),
                          "out_start": round(t, 3), "dur": round(dur, 3),
                          "sid": sid, "hook": idx == 0})
            t += dur
        sections.append({"sid": sid, "start": round(sec_start, 3), "end": round(t, 3),
                         "hook": idx == 0})
    return {"clips": clips, "words": out_words, "sections": sections, "duration": round(t, 3)}
