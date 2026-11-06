"""Jana video ujian sintetik + transkrip palsu (untuk menguji pipeline tanpa
model Whisper). Audio ialah nada pendek bagi setiap perkataan."""
import json, os, random, subprocess, sys, wave
import numpy as np

out = sys.argv[1] if len(sys.argv) > 1 else "fixture"
os.makedirs(out, exist_ok=True)
random.seed(0)
SENTS = [
 "Bayangkan kalau esok adalah hari terakhir kita di dunia ini?",
 "Emm saudara saudara sekalian, hidup ini terlalu singkat.",
 "Kita sibuk mengejar harta, mengejar dunia, sehingga lupa kepada Allah.",
 "Rasulullah pernah bersabda, orang yang paling bijak ialah yang paling banyak mengingati mati.",
 "Kita kita selalu rasa masih muda, masih ada masa.",
 "Tapi kubur tidak pernah bertanya berapa umur kita.",
 "Hidup ini terlalu singkat saudara sekalian.",
 "Berapa ramai kawan kita yang pergi dalam usia muda?",
 "Maka bertaubatlah sebelum terlambat.",
 "Allah itu Maha Pengampun, pintu taubat sentiasa terbuka.",
 "Selagi nyawa belum sampai ke kerongkong, selagi itu ada harapan.",
 "Jangan tunggu esok untuk kembali kepada Allah.",
 "Eh solat lah, kerana solat itulah yang pertama akan dihisab.",
 "Hargailah ibu dan ayah selagi mereka masih ada.",
 "Satu hari nanti kita akan menangis rindu kepada mereka.",
 "Sedekahlah walaupun sedikit, kerana ia memadamkan kemurkaan Allah.",
 "Dunia ini hanya persinggahan, akhirat itulah tempat yang kekal.",
 "Syurga itu mahal saudara, perlu dibayar dengan pengorbanan.",
 "Dan neraka itu dekat, dikelilingi dengan hawa nafsu.",
 "Maka pilihlah jalan yang membawa kita kepada keredhaan Allah.",
 "Semoga Allah mengampunkan dosa dosa kita semua.",
 "Dan semoga kita semua dikumpulkan di dalam syurga Nya.",
 "Ya Allah, ampunilah kami, rahmatilah kami.",
 "Ini satu ini satu peringatan untuk diri saya sendiri juga.",
 "Mari kita sama sama berubah mulai hari ini.",
]
SR = 48000
words, t = [], 1.0
segs = []
for si, s in enumerate(SENTS * 2):  # ulang untuk menguji buang pengulangan
    sw = []
    for w in s.split():
        d = 0.18 + 0.045 * len(w.strip(",.?"))
        sw.append({"w": w, "s": round(t, 3), "e": round(t + d, 3), "p": 0.9})
        t += d + random.choice([0.05, 0.08, 0.12, 0.4, 0.06])
    segs.append({"s": sw[0]["s"], "e": sw[-1]["e"], "text": s, "words": sw})
    t += random.choice([0.8, 1.2, 2.0])
dur = t + 1
json.dump({"language": "ms", "segments": segs}, open(f"{out}/transcript.json", "w"), ensure_ascii=False, indent=1)
x = np.zeros(int(dur * SR))
for seg in segs:
    for w in seg["words"]:
        a, b = int(w["s"] * SR), int(w["e"] * SR)
        tt = np.arange(b - a) / SR
        f = 140 + 40 * np.sin(len(w["w"]))
        x[a:b] += np.sin(2 * np.pi * f * tt) * np.sin(np.pi * tt / tt[-1]) * 0.4
d = (np.clip(x, -1, 1) * 32767).astype("<i2")
with wave.open(f"{out}/voice.wav", "wb") as wv:
    wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR); wv.writeframes(d.tobytes())
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=s=1920x1080:r=25:d={dur:.2f}",
                "-i", f"{out}/voice.wav", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
                "-shortest", f"{out}/ceramah.mp4"], check=True)
os.makedirs(f"{out}/broll", exist_ok=True)
for name, col in [("syurga_1", "0x2e8b57"), ("kubur_1", "0x223344"), ("solat_1", "0xc89b3c"),
                  ("ibu_1", "0xaa6644"), ("taubat_1", "0x334477")]:
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"gradients=s=1024x1792:c0={col}:c1=white:x0=0:y0=0:x1=1024:y1=1792:d=1",
                    "-frames:v", "1", f"{out}/broll/{name}.jpg"], check=True)
print(f"fixture ok: {dur:.1f}s")
