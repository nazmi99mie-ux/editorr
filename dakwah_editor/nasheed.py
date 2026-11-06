"""Muzik latar sedih gaya nasyid: koir humming tanpa alat muzik, maqam Hijaz.

Semuanya disintesis (tiada sampel berhak cipta):
- drone humming rendah (kelima terbuka D–A, beralih ke G–D),
- melodi "ooh/aah" perlahan dengan vibrato, glide dan ornamen,
- koir 3 suara (detune + timing berbeza) + suara oktaf bawah,
- reverb dewan/masjid (konvolusi impuls sintetik).
"""

import numpy as np

SR = 48000
D4 = 293.66
# Maqam Hijaz atas D: D Eb F# G A Bb C D (semiton dari D4), darjah negatif di bawah
HIJAZ = {-3: -5, -2: -4, -1: -2, 0: 0, 1: 1, 2: 4, 3: 5, 4: 7, 5: 8, 6: 10, 7: 12}

# (darjah, rentak). None = rehat. Frasa menurun yang sayu.
PHRASES = [
    [(4, 2), (5, 1), (4, 1), (3, 1), (2, 1.5), (1, .5), (0, 3), (None, 1)],
    [(0, 1), (1, 1), (2, 1), (3, 2), (4, 1), (5, 1.5), (4, .5), (3, 1), (2, 2), (None, 1)],
    [(6, 1), (5, 1), (4, 2), (3, 1), (2, 1), (3, 1), (4, 3), (None, 1)],
    [(5, 1), (4, 1), (3, 1), (2, 1), (1, 1.5), (2, .5), (1, 1), (0, 4), (None, 1)],
]
# Drone bagi setiap frasa: akar (Hz)
DRONE_ROOT = [73.42, 98.00, 98.00, 73.42]  # D2, G2, G2, D2

FORMANTS = {  # (frekuensi, lebar, gain)
    "oo": [(300, 90, 1.0), (870, 120, 0.35), (2240, 200, 0.08)],
    "aa": [(730, 110, 1.0), (1090, 130, 0.6), (2440, 220, 0.12)],
    "mm": [(250, 80, 1.0), (1000, 300, 0.05)],
}


def _formant_gain(f, vowel_mix):
    """vowel_mix: 0 = 'oo', 1 = 'aa' (tatasusunan ikut masa)."""
    def g(spec):
        out = np.zeros_like(f)
        for fc, bw, gain in spec:
            out += gain * np.exp(-0.5 * ((f - fc) / bw) ** 2)
        return out + 0.02
    return g(FORMANTS["oo"]) * (1 - vowel_mix) + g(FORMANTS["aa"]) * vowel_mix


def _voice(f0, amp, vowel_mix, rng, n_harm=24, vib_rate=5.2, vib_depth=0.0045):
    n = len(f0)
    t = np.arange(n) / SR
    # vibrato muncul perlahan dalam setiap nota panjang (amp sebagai proksi)
    vib = 1 + vib_depth * np.sin(2 * np.pi * vib_rate * t + rng.uniform(0, 6.28)) * np.clip(amp * 1.4, 0, 1)
    jitter = 1 + 0.0015 * np.convolve(rng.standard_normal(n), np.ones(2400) / 2400, "same") * 20
    f = f0 * vib * jitter
    phase = 2 * np.pi * np.cumsum(f) / SR
    sig = np.zeros(n)
    for k in range(1, n_harm + 1):
        fk = f * k
        a = _formant_gain(fk, vowel_mix) / k ** 0.7
        a[fk > 5000] = 0
        sig += a * np.sin(k * phase)
    breath = np.convolve(rng.standard_normal(n), np.ones(12) / 12, "same") * 0.015
    return (sig + breath) * amp


def _pitch_track(duration, beat, start, octave=0, rng=None):
    n = int(duration * SR)
    f0 = np.full(n, D4 / 2)
    amp = np.zeros(n)
    t = start
    pi = 0
    prev = None
    while t < duration - 4:
        ph = PHRASES[pi % len(PHRASES)]
        for deg, beats in ph:
            d = beats * beat
            a, b = int(t * SR), min(n, int((t + d) * SR))
            if a >= n:
                break
            if deg is None:
                prev = None
            else:
                fz = D4 * 2 ** ((HIJAZ[deg] + 12 * octave) / 12)
                seg = np.full(b - a, fz)
                if prev is not None:  # glide/portamento 140ms
                    g = min(b - a, int(0.14 * SR))
                    seg[:g] = prev * (fz / prev) ** (np.linspace(0, 1, g) ** 0.6)
                f0[a:b] = seg
                tt = np.linspace(0, 1, b - a)
                env = np.clip(tt * d / 0.18, 0, 1) * (0.85 + 0.15 * np.sin(np.pi * tt))
                if prev is None:
                    env *= np.clip(tt * d / 0.4, 0, 1)
                amp[a:b] = np.maximum(amp[a:b], env)
                prev = fz
            t += d
        # lepaskan nota pada hujung frasa
        pi += 1
    # licinkan amplitud (legato, tiada klik)
    k = int(0.06 * SR)
    amp = np.convolve(amp, np.ones(k) / k, "same")
    return f0, amp


def _reverb(x, seconds=3.2, decay=0.9, seed=9):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = []
    for ch in range(2):
        ir = rng.standard_normal(n) * np.exp(-t / decay * 2.2)
        ir = np.convolve(ir, np.ones(6) / 6, "same")  # lembutkan
        ir[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
        ir /= np.sqrt((ir ** 2).sum())
        L = len(x) + n
        nfft = 1 << (L - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[: len(x)]
        out.append(y)
    return np.stack(out, 1)


def _lowpass(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def sad_nasheed(duration: float, seed: int = 11, beat: float = 0.78) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(duration * SR)
    t = np.arange(n) / SR
    vowel = 0.5 + 0.5 * np.sin(2 * np.pi * t / 23.0 - 1.2)  # oo <-> aa perlahan

    # Melodi: masuk selepas 5s; ulangan kedua oktaf bawah supaya lebih sayu.
    mel = np.zeros(n)
    f0, amp = _pitch_track(duration, beat, 5.0, 0, rng)
    for i, (det, dly) in enumerate([(0, 0), (0.0035, 0.025), (-0.004, 0.04)]):
        s = int(dly * SR)
        v = _voice(f0 * (1 + det), amp, vowel, rng)
        mel[s:] += v[: n - s] * (1.0 if i == 0 else 0.6)
    mel += _voice(f0 / 2, amp, vowel * 0.3, rng) * 0.45  # suara oktaf bawah

    # Drone humming "mm": kelima terbuka, akar ikut frasa
    phrase_len = [sum(b for _, b in p) * beat for p in PHRASES]
    root = np.full(n, DRONE_ROOT[0])
    tt, i = 5.0, 0
    while tt < duration:
        a, b = int(tt * SR), min(n, int((tt + phrase_len[i % 4]) * SR))
        root[a:b] = DRONE_ROOT[i % 4]
        tt += phrase_len[i % 4]
        i += 1
    k = int(1.5 * SR)
    root = np.convolve(np.pad(root, (k, k), mode="edge"), np.ones(k) / k, "same")[k:-k]
    drone_amp = np.clip(t / 4.0, 0, 1)
    drone = np.zeros(n)
    for mult, g in [(1, 1.0), (1.5, 0.7), (2, 0.5)]:
        for det in (-0.0012, 0.0012):
            drone += _voice(root * mult * (1 + det), drone_amp, np.zeros(n), rng,
                            n_harm=12, vib_depth=0.002) * g
    drone = _lowpass(drone, 900)

    dry = mel / (np.abs(mel).max() + 1e-9) * 0.8 + drone / (np.abs(drone).max() + 1e-9) * 0.32
    dry = _lowpass(dry, 4200)
    wet = _reverb(dry)
    mix = np.stack([dry, dry], 1) * 0.55 + wet / (np.abs(wet).max() + 1e-9) * 0.75
    fade = np.clip(t / 3.0, 0, 1) * np.clip((duration - t) / 4.0, 0, 1)
    mix *= fade[:, None]
    return mix / (np.abs(mix).max() + 1e-9) * 0.8
