"""Sintesis kesan bunyi (whoosh, impact, tick) dan muzik latar ambient lembut.

Semua bunyi dijana secara prosedur (tiada fail berhak cipta). Anda boleh
gantikan dengan fail sendiri melalui --music / --sfx-dir.
"""

import wave

import numpy as np

SR = 48000


def _one_pole_lowpass(x: np.ndarray, cutoff: np.ndarray) -> np.ndarray:
    """Lowpass satu kutub dengan frekuensi potong berubah ikut masa."""
    a = np.exp(-2 * np.pi * np.clip(cutoff, 20, SR / 2.5) / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def whoosh(dur=0.7, seed=1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    env = np.sin(np.pi * t ** 0.7) ** 2
    cutoff = 300 + 5200 * np.sin(np.pi * t) ** 2
    noise = rng.standard_normal(n)
    sig = _one_pole_lowpass(noise, cutoff)
    sig = _one_pole_lowpass(sig, cutoff * 1.5)
    sig = sig / (np.abs(sig).max() + 1e-9) * env
    pan = t  # kiri -> kanan
    return np.stack([sig * np.cos(pan * np.pi / 2), sig * np.sin(pan * np.pi / 2)], 1) * 0.9


def impact(dur=1.8, seed=2) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    freq = 38 + 50 * np.exp(-t * 6)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    boom = np.sin(phase) * np.exp(-t * 2.6)
    click = rng.standard_normal(n) * np.exp(-t * 60) * 0.5
    click = _one_pole_lowpass(click, np.full(n, 2500.0))
    tail = _one_pole_lowpass(rng.standard_normal(n), np.full(n, 900.0)) * np.exp(-t * 3) * 0.6
    sig = boom + click * 3 + tail
    sig = np.tanh(sig * 1.5)
    sig /= np.abs(sig).max() + 1e-9
    return np.stack([sig, sig], 1) * 0.95


def tick(dur=0.12) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * 1800 * t) * 0.6 + np.sin(2 * np.pi * 3600 * t) * 0.25) * np.exp(-t * 55)
    return np.stack([sig, sig], 1) * 0.5


def riser(dur=1.5, seed=3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    cutoff = 200 + 7000 * t ** 2
    sig = _one_pole_lowpass(rng.standard_normal(n), cutoff)
    sig = sig / (np.abs(sig).max() + 1e-9) * t ** 2
    return np.stack([sig, sig], 1) * 0.6


def ambient_pad(duration: float, seed=4) -> np.ndarray:
    """Pad ambient sinematik tanpa melodi (drone harmoni lembut)."""
    n = int(duration * SR)
    t = np.arange(n) / SR
    # progresi lembut: Dm - Bb - F - C (frekuensi Hz)
    chords = [
        [73.42, 146.83, 220.00, 293.66, 349.23],
        [58.27, 116.54, 174.61, 233.08, 293.66],
        [87.31, 130.81, 174.61, 261.63, 349.23],
        [65.41, 130.81, 196.00, 261.63, 329.63],
    ]
    seg = 8.0
    out = np.zeros(n)
    for ci in range(int(np.ceil(duration / seg)) + 1):
        chord = chords[ci % len(chords)]
        start = ci * seg - 2.0
        a = max(0, int(start * SR))
        b = min(n, int((start + seg + 4.0) * SR))
        if a >= b:
            continue
        tt = t[a:b] - start
        env = np.clip(tt / 3.0, 0, 1) * np.clip((seg + 4.0 - tt) / 3.0, 0, 1)
        env = env ** 1.5
        sig = np.zeros(b - a)
        for k, f in enumerate(chord):
            for det in (-0.6, 0.0, 0.7):
                ff = f * (1 + det / 1200 * 8)
                sig += np.sin(2 * np.pi * ff * t[a:b] + k * 1.3 + det) / (1 + k * 0.6)
        out[a:b] += sig * env
    lfo = 0.8 + 0.2 * np.sin(2 * np.pi * 0.07 * t)
    out *= lfo
    out = _smooth(out, 1400.0)
    out /= np.abs(out).max() + 1e-9
    # stereo lebar sedikit
    left = out
    right = np.roll(out, int(0.012 * SR))
    fade = np.clip(t / 3.0, 0, 1) * np.clip((duration - t) / 3.0, 0, 1)
    return np.stack([left * fade, right * fade], 1) * 0.7


def _smooth(x, cutoff):
    # lowpass pantas (vektor) melalui FFT
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def write_wav(path: str, stereo: np.ndarray) -> None:
    data = np.clip(stereo, -1, 1)
    data = (data * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def sfx_track(duration: float, events: list) -> np.ndarray:
    """events: senarai (masa_s, jenis, gain). Pulangkan trek stereo SFX."""
    n = int(duration * SR) + SR
    out = np.zeros((n, 2))
    cache = {}
    makers = {"whoosh": whoosh, "impact": impact, "tick": tick, "riser": riser}
    for i, (at, kind, gain) in enumerate(events):
        key = (kind, i % 3)
        if key not in cache:
            cache[key] = makers[kind](seed=i % 3 + 1) if kind in ("whoosh",) else makers[kind]()
        s = cache[key]
        a = int(max(0.0, at) * SR)
        b = min(n, a + len(s))
        out[a:b] += s[: b - a] * gain
    return out[: int(duration * SR)]
