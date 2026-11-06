"""Editor video dakwah sinematik automatik (9:16, 1080p).

Contoh:
    python -m dakwah_editor ceramah.mp4 -o dakwah_final.mp4 --broll broll/
"""

import argparse
import json
import os
import sys

from . import audio, broll, render, selector, subtitles, textfix
from .keywords import KEYWORD_WEIGHTS


def log(msg):
    print(f"[dakwah] {msg}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dakwah_editor", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="video ceramah asal")
    ap.add_argument("-o", "--output", default="dakwah_final.mp4")
    ap.add_argument("--work", default="work", help="folder kerja (cache transkrip, klip)")
    ap.add_argument("--target", type=float, default=120, help="durasi sasaran saat (90-180)")
    ap.add_argument("--transcript", help="guna transkrip JSON sedia ada")
    ap.add_argument("--plan", help="guna pelan JSON (selepas disunting secara manual)")
    ap.add_argument("--plan-only", action="store_true", help="berhenti selepas jana pelan & prompt")
    ap.add_argument("--model", default="large-v3", help="model faster-whisper")
    ap.add_argument("--language", default="ms")
    ap.add_argument("--broll", default="broll", help="folder imej/video AI")
    ap.add_argument("--music", default="ambient",
                    help="fail muzik/nasyid, 'ambient' (pad lembut), 'nasheed' (koir humming "
                         "sedih tanpa alat muzik) atau 'none'")
    ap.add_argument("--music-db", type=float, default=-16, help="kekuatan muzik (dB)")
    ap.add_argument("--no-sfx", action="store_true")
    ap.add_argument("--title", help="tajuk besar di atas semasa hook (pilihan)")
    ap.add_argument("--cta", default="SEMOGA BERMANFAAT|Kongsikan kepada yang tersayang")
    ap.add_argument("--font", default="DejaVu Sans", help="nama fon (cth. Montserrat ExtraBold)")
    ap.add_argument("--callout-font", help="fon callout besar (cth. 'Bebas Neue')")
    ap.add_argument("--brand-font", help="fon tag jenama & kad penutup (cth. 'Cinzel')")
    ap.add_argument("--sub-size", type=int, default=84)
    ap.add_argument("--max-chars", type=int, default=20, help="aksara maksimum sebaris subtitle")
    ap.add_argument("--fit", choices=["cover", "blur"], default="cover",
                    help="cover = crop penuh 9:16; blur = video penuh atas latar kabur")
    ap.add_argument("--crop-x", type=float, default=0.5, help="kedudukan crop mendatar 0..1")
    ap.add_argument("--crop-y", type=float, default=0.5)
    ap.add_argument("--no-upper", action="store_true", help="subtitle huruf biasa")
    ap.add_argument("--fixes", help="JSON pembetulan perkataan transkrip")
    ap.add_argument("--cues", help="JSON {broll: [...], callouts: [...]} — B-roll & "
                    "teks grafik diletakkan pada perkataan tertentu")
    ap.add_argument("--keep-all", action="store_true",
                    help="kekalkan semua ayat mengikut susunan asal (hanya buang "
                         "senyap/gagap); ayat pertama jadi hook")
    ap.add_argument("--premium", action="store_true",
                    help="lapisan premium: tirai pembukaan, tag jenama, habuk emas, light leak, "
                         "bloom, punch-zoom, bar progres")
    ap.add_argument("--reuse-base", action="store_true",
                    help="guna semula work/base.mkv (klip penceramah) jika ada — render pantas")
    ap.add_argument("--logo", help="imej logo berlatar putih (boleh beberapa logo bersebelahan): "
                    "lencana di sudut atas + kad logo pada penutup")
    ap.add_argument("--brand", help="tag jenama emas di atas (cth. 'Madrasah Zawiyah')")
    ap.add_argument("--keep-silence", action="store_true",
                    help="jangan laraskan cap masa perkataan kepada senyap sebenar")
    ap.add_argument("--drop", type=int, nargs="*", default=[], help="id ayat untuk dibuang")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    a = ap.parse_args(argv)

    os.makedirs(a.work, exist_ok=True)

    # 1. Transkripsi
    tpath = a.transcript or os.path.join(a.work, "transcript.json")
    if os.path.exists(tpath):
        log(f"guna transkrip {tpath}")
        data = json.load(open(tpath, encoding="utf-8"))
    else:
        from .transcribe import transcribe, write_srt
        log(f"transkripsi dengan faster-whisper ({a.model}) ... (boleh ambil masa)")
        data = transcribe(a.input, tpath, model=a.model, language=a.language)
        write_srt(data, os.path.join(a.work, "transcript.srt"))
    textfix.load_and_fix(data, a.fixes)
    if not a.keep_silence:
        n = textfix.snap_to_silences(data, textfix.detect_silences(a.input))
        log(f"jeda senyap: {n} cap masa perkataan dilaraskan")

    # 2. Pelan suntingan
    ppath = os.path.join(a.work, "plan.json")
    if a.plan:
        plan = json.load(open(a.plan, encoding="utf-8"))
        log(f"guna pelan {a.plan}")
    else:
        plan = selector.make_plan(data, target=a.target)
        if a.keep_all:
            plan["order"] = [x["id"] for x in plan["sentences"] if x["id"] not in a.drop]
            plan["hook"] = plan["order"][0]
        with open(ppath, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=1)
    tl = selector.build_timeline(data, plan)
    hook = next(s for s in plan["sentences"] if s["id"] == plan["order"][0])
    log(f"hook: \"{hook['text']}\"")
    log(f"{len(plan['order'])} ayat dipilih, {len(tl['clips'])} potongan, "
        f"suara {tl['duration']:.1f}s (+3s outro)")
    if tl["duration"] + 3 < 85:
        log("AMARAN: isi yang ada lebih pendek daripada 90s selepas dibersihkan.")
    broll.write_prompts(plan, tl, os.path.join(a.work, "broll_prompts.md"))
    log(f"prompt B-roll AI: {os.path.join(a.work, 'broll_prompts.md')}")
    if a.plan_only:
        log(f"pelan: {ppath} — sunting 'order' jika perlu, kemudian jalankan dengan --plan")
        return 0

    # 3. B-roll
    cues = json.load(open(a.cues, encoding="utf-8")) if a.cues else {}
    if cues.get("broll"):
        placed = broll.place_cued(tl, cues["broll"], a.broll)
        log(f"B-roll (cue manual): {len(placed)} diletakkan")
    else:
        lib = broll.load_library(a.broll)
        placed = broll.place_broll(tl, lib)
        log(f"B-roll: {len(lib)} fail dalam pustaka, {len(placed)} diletakkan")
    callouts = broll.resolve_callouts(tl, cues.get("callouts", []))
    with open(os.path.join(a.work, "edl.json"), "w", encoding="utf-8") as f:
        json.dump({"timeline": tl, "broll": placed}, f, ensure_ascii=False, indent=1)

    # 4. Kesan: flash + SFX
    outro = 3.0
    total = tl["duration"] + outro
    hook_end = tl["sections"][0]["end"]
    flashes = [(0.0, 0.85), (hook_end, 0.35)] + [
        (b["start"], 0.22 if b["dur"] >= 2 else 0.1) for b in placed]
    events = [(0.0, "impact", 0.9), (hook_end - 0.35, "whoosh", 0.6),
              (tl["duration"] - 1.4, "riser", 0.35), (tl["duration"], "impact", 0.45)]
    for b in placed:
        events.append((b["start"] - 0.3, "whoosh", 0.45 if b["dur"] >= 2 else 0.25))
        if b["dur"] >= 2:
            events.append((b["start"] + b["dur"] - 0.35, "whoosh", 0.22))
    for c in callouts:
        events.append((c["start"], "impact", 0.35))
    last_tick = -9
    for w in tl["words"]:
        if w["kw"] and KEYWORD_WEIGHTS.get(w["kw"], 0) >= 4 and w["s"] - last_tick > 3:
            events.append((w["s"], "tick", 0.3))
            last_tick = w["s"]

    cta = (a.cta.split("|") + [""])[:2]
    logos = {}
    if a.logo:
        from .brandkit import build as build_brandkit
        logos = build_brandkit(a.logo, os.path.join(a.work, "brand"))
        log("logo: lencana sudut atas + kad penutup")
    ass = os.path.abspath(os.path.join(a.work, "subs.ass"))
    subtitles.build_ass(tl, ass, font=a.font, uppercase=not a.no_upper, title=a.title,
                        cta=cta, flashes=flashes, outro_start=tl["duration"], total=total,
                        callouts=callouts, premium=a.premium, brand=a.brand,
                        callout_font=a.callout_font, brand_font=a.brand_font,
                        sub_size=a.sub_size, max_chars=a.max_chars,
                        logo_badge=bool(logos), logo_card=bool(logos),
                        leaks=[b["start"] for b in placed if b["dur"] >= 1.5])

    sfx_wav = None
    if not a.no_sfx:
        sfx_wav = os.path.join(a.work, "sfx.wav")
        audio.write_wav(sfx_wav, audio.sfx_track(total, events))
    music = None
    if a.music == "ambient":
        music = os.path.join(a.work, "ambient.wav")
        audio.write_wav(music, audio.ambient_pad(total + 1))
        log("muzik: pad ambient lembut (dijana)")
    elif a.music == "nasheed":
        from .nasheed import sad_nasheed
        music = os.path.join(a.work, "nasheed.wav")
        audio.write_wav(music, sad_nasheed(total + 1))
        log("muzik: nasyid humming sedih, maqam Hijaz (dijana)")
    elif a.music != "none":
        music = a.music

    # 5. Render
    log("render klip 9:16 dengan zoom ...")
    base = os.path.join(a.work, "base.mkv")
    if a.reuse_base and os.path.exists(base):
        log("guna semula base.mkv")
    else:
        base = render.render_base(a.input, tl, a.work, fit=a.fit, crop_x=a.crop_x,
                                  crop_y=a.crop_y, jobs=a.jobs)
    log("komposit akhir (B-roll, grade, subtitle, audio) ...")
    dur = render.render_final(base, tl, placed, ass, music, sfx_wav, a.output,
                              outro=outro, music_db=a.music_db, premium=a.premium,
                              logo_badge=logos.get("badge"), logo_card=logos.get("card"))
    log(f"siap: {a.output} ({dur:.1f}s, 1080x1920)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
