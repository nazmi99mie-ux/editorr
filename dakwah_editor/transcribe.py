"""Transkripsi audio dengan cap masa perkataan demi perkataan (faster-whisper)."""

import json
import subprocess

import numpy as np


def transcribe(video_path: str, out_json: str, model: str = "large-v3",
               language: str = "ms", device: str = "auto") -> dict:
    from faster_whisper import WhisperModel  # import lewat: hanya bila perlu

    # Baca audio terus melalui ffmpeg (elak kebergantungan pada versi PyAV).
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", video_path, "-vn", "-ac", "1",
         "-ar", "16000", "-f", "s16le", "-"],
        check=True, capture_output=True,
    ).stdout
    wav = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    compute = "int8" if device in ("auto", "cpu") else "float16"
    wm = WhisperModel(model, device=device, compute_type=compute)
    segments, info = wm.transcribe(
        wav,
        language=language,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400},
        beam_size=5,
        condition_on_previous_text=False,
        initial_prompt="Ceramah agama Islam dalam Bahasa Melayu. Allah, Rasulullah, syurga, neraka, solat, doa, taubat.",
    )
    data = {"language": info.language, "segments": []}
    for seg in segments:
        words = [
            {"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3),
             "p": round(w.probability, 3)}
            for w in (seg.words or []) if w.word.strip()
        ]
        data["segments"].append(
            {"s": round(seg.start, 3), "e": round(seg.end, 3),
             "text": seg.text.strip(), "words": words}
        )
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return data


def write_srt(data: dict, path: str) -> None:
    def ts(t):
        h, r = divmod(t, 3600)
        m, s = divmod(r, 60)
        return f"{int(h):02}:{int(m):02}:{s:06.3f}".replace(".", ",")

    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(data["segments"], 1):
            f.write(f"{i}\n{ts(seg['s'])} --> {ts(seg['e'])}\n{seg['text']}\n\n")
