"""Render akhir: klip 9:16 dengan zoom sinematik, B-roll Ken Burns, colour
grade, vignette, grain, subtitle ASS, SFX dan muzik latar dengan ducking."""

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

FPS = 30
W, H = 1080, 1920
SS = 1.5  # supersampling sebelum zoompan (kurangkan jitter)
GRADE = ("eq=contrast=1.07:saturation=1.1:gamma=0.97,"
         "colorbalance=rs=-0.03:bs=0.04:rh=0.05:gh=0.01:bh=-0.04")
ZOOM_LEVELS = [1.0, 1.12, 1.05, 1.16]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg gagal:\n" + " ".join(cmd) + "\n" + r.stderr[-3000:])
    return r


def probe(path):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", path])
    j = json.loads(r.stdout)
    st = j["streams"][0]
    w, h = st["width"], st["height"]
    rot = 0
    for sd in st.get("side_data_list", []) or []:
        rot = int(sd.get("rotation", 0) or 0)
    if abs(rot) in (90, 270):
        w, h = h, w
    return w, h, float(j["format"]["duration"])


def assign_zoom(timeline):
    """Tetapkan zoom bagi setiap klip: tukar tahap zoom pada potongan (sembunyi
    jump cut) tetapi tidak lebih kerap daripada setiap ~2.5s; tambah dolly-in
    perlahan sepanjang setiap bahagian."""
    secs = {s["sid"]: s for s in timeline["sections"]}
    level_i, last_change = 0, -99.0
    for i, c in enumerate(timeline["clips"]):
        if i and c["out_start"] - last_change >= 2.5:
            level_i = (level_i + 1) % len(ZOOM_LEVELS)
            last_change = c["out_start"]
        base = ZOOM_LEVELS[level_i]
        sec = secs[c["sid"]]
        sd = max(0.5, sec["end"] - sec["start"])
        p0 = 0.05 * (c["out_start"] - sec["start"]) / sd
        p1 = 0.05 * (c["out_start"] + c["dur"] - sec["start"]) / sd
        c["z0"], c["z1"] = round(base + p0, 4), round(base + p1, 4)
        c["punch"] = i == 0  # punch-out dramatik pada hook


def _fit_chain(src_w, src_h, fit, crop_x, crop_y):
    ow, oh = int(W * SS) // 2 * 2, int(H * SS) // 2 * 2
    if fit == "blur":
        return (f"split=2[bg][fg];[bg]scale={ow}:{oh}:force_original_aspect_ratio=increase,"
                f"crop={ow}:{oh},gblur=sigma=40,eq=brightness=-0.12[bgb];"
                f"[fg]scale={ow}:-2[fgs];[bgb][fgs]overlay=(W-w)/2:(H-h)/2*0.85")
    return (f"scale={ow}:{oh}:force_original_aspect_ratio=increase,"
            f"crop={ow}:{oh}:(iw-{ow})*{crop_x}:(ih-{oh})*{crop_y}")


def render_clip(src, c, path, fit, crop_x, crop_y, src_wh):
    n = round(c["dur"] * FPS)
    z = f"({c['z0']}+({c['z1']}-{c['z0']})*on/{max(1, n)})"
    if c.get("punch"):
        z += f"+0.22*max(0\\,1-on/{int(0.45 * FPS)})^2"
    zp = (f"zoompan=z='{z}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)*0.42':d=1:"
          f"s={W}x{H}:fps={FPS}")
    vf = f"fps={FPS},{_fit_chain(*src_wh, fit, crop_x, crop_y)},{zp},setsar=1,format=yuv420p"
    af = (f"aresample=48000,afade=t=in:d=0.012,"
          f"afade=t=out:st={max(0, c['dur'] - 0.02):.3f}:d=0.02,apad,atrim=0:{c['dur']:.4f}")
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{c['src_start']:.3f}", "-t", f"{c['dur'] + 0.2:.3f}",
         "-i", src, "-filter_complex", f"[0:v]{vf}[v];[0:a]{af}[a]", "-map", "[v]", "-map", "[a]",
         "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
         "-ac", "2", "-c:a", "pcm_s16le", path])


def render_base(src, timeline, work, fit="cover", crop_x=0.5, crop_y=0.5, jobs=4):
    src_wh = probe(src)[:2]
    assign_zoom(timeline)
    cdir = os.path.join(work, "clips")
    os.makedirs(cdir, exist_ok=True)
    paths = [os.path.join(cdir, f"c{i:04}.mkv") for i in range(len(timeline["clips"]))]
    with ThreadPoolExecutor(jobs) as ex:
        list(ex.map(lambda a: render_clip(src, a[0], a[1], fit, crop_x, crop_y, src_wh),
                    zip(timeline["clips"], paths)))
    lst = os.path.join(work, "concat.txt")
    with open(lst, "w") as f:
        for p in paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    base = os.path.join(work, "base.mkv")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", base])
    return base


def render_final(base, timeline, brolls, ass_path, music_wav, sfx_wav, out,
                 outro=3.0, music_db=-16):
    speech = timeline["duration"]
    total = speech + outro
    inputs = ["-i", base]
    fc = [f"[0:v]{GRADE}[g0]"]
    last = "g0"
    for i, b in enumerate(brolls, 1):
        if b["video"]:
            inputs += ["-stream_loop", "-1", "-t", f"{b['dur']:.3f}", "-i", b["path"]]
            mv = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                  f"fps={FPS},setsar=1")
        else:
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{b['dur']:.3f}", "-i", b["path"]]
            nfr = max(1, round(b["dur"] * FPS))
            if i % 2:
                z = f"1.0+0.10*on/{nfr}"
            else:
                z = f"1.10-0.10*on/{nfr}"
            ox = "(iw-iw/zoom)/2" if i % 3 else f"(iw-iw/zoom)*on/{nfr}"
            mv = (f"scale={int(W * SS)}:{int(H * SS)}:force_original_aspect_ratio=increase,"
                  f"crop={int(W * SS)}:{int(H * SS)},"
                  f"zoompan=z='{z}':x='{ox}':y='(ih-ih/zoom)/2':d=1:s={W}x{H}:fps={FPS},setsar=1")
        fd = min(0.3, b["dur"] / 4)
        fc.append(
            f"[{i}:v]{mv},{GRADE},format=yuva420p,"
            f"fade=t=in:st=0:d={fd}:alpha=1,fade=t=out:st={b['dur'] - fd:.3f}:d={fd}:alpha=1,"
            f"setpts=PTS-STARTPTS+{b['start']}/TB[b{i}]")
        fc.append(f"[{last}][b{i}]overlay=eof_action=pass:"
                  f"enable='between(t,{b['start']},{b['start'] + b['dur']:.3f})'[o{i}]")
        last = f"o{i}"
    ass = ass_path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    fc.append(
        f"[{last}]tpad=stop_mode=clone:stop_duration={outro},vignette=PI/4.5,"
        f"noise=alls=5:allf=t,ass='{ass}',"
        f"fade=t=in:st=0:d=0.25,fade=t=out:st={total - 1.0:.3f}:d=1.0,format=yuv420p[vout]")

    k = len(brolls)
    acur = 0
    fc.append(
        f"[0:a]apad=pad_dur={outro},highpass=f=70,"
        "acompressor=threshold=-20dB:ratio=3:attack=10:release=200:makeup=2,"
        "loudnorm=I=-15:TP=-1.5:LRA=9,aresample=48000,asplit=2[voice][sc]")
    mix = ["[voice]"]
    if music_wav:
        inputs += ["-stream_loop", "-1", "-i", music_wav]
        mi = k + 1 + acur
        acur += 1
        fc.append(
            f"[{mi}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.3f},"
            f"afade=t=in:d=2.5,afade=t=out:st={total - 2.5:.3f}:d=2.5,volume={music_db}dB[mus]")
        fc.append("[mus][sc]sidechaincompress=threshold=0.02:ratio=6:attack=25:release=450:makeup=1[duck]")
        mix.append("[duck]")
    else:
        fc.append("[sc]anullsink")
    if sfx_wav:
        inputs += ["-i", sfx_wav]
        si = k + 1 + acur
        fc.append(f"[{si}:a]aresample=48000,volume=-7dB[fx]")
        mix.append("[fx]")
    fc.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first,"
              f"alimiter=limit=0.95,atrim=0:{total:.3f}[aout]")

    script = os.path.join(os.path.dirname(ass_path), "filter.txt")
    with open(script, "w") as f:
        f.write(";\n".join(fc))
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex_script", script,
         "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high",
         "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", out])
    return total
