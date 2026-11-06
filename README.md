# editorr — Editor Video Dakwah Sinematik (9:16, 1080p)

Pipeline automatik yang menukar rakaman ceramah panjang kepada video dakwah pendek
(1.5–3 minit) untuk TikTok / Reels / Shorts.

## Apa yang dibuat

| Langkah | Butiran |
|---|---|
| Transkripsi | `faster-whisper` (Bahasa Melayu) dengan cap masa **perkataan demi perkataan** |
| Pilih isi | Markah setiap ayat ikut kata kunci dakwah (Allah, mati, syurga, taubat, ibu…), soalan & frasa kuat |
| Hook 3–5s | Ayat pendek paling kuat (cth. "Bayangkan…", soalan) diletakkan di depan + punch-zoom, flash & bunyi *impact* |
| Bersihkan | Buang "emm/eh", gagap ("kita kita"), frasa berulang, ayat yang diulang semula, dan jeda senyap > 0.22s |
| Cerita | Ayat lain dikekalkan **mengikut susunan asal** supaya maksud penceramah tidak berubah |
| Visual | Crop 9:16, zoom berselang pada setiap potongan + dolly-in perlahan, colour grade hangat, vignette, grain filem |
| Subtitle | ASS perkataan demi perkataan: perkataan aktif emas & pop, kata kunci bersinar (glow) |
| B-roll AI | Imej/video AI dipadankan dengan perkataan yang disebut (Ken Burns + crossfade + whoosh) |
| Audio | Suara: compressor + loudnorm (-15 LUFS). Muzik latar di-*duck* automatik bila penceramah bercakap. SFX whoosh/impact/riser dijana sendiri (bebas hak cipta) |
| Penutup | Kad "SEMOGA BERMANFAAT" 3s + fade |

## Cara guna

```bash
pip install -r requirements.txt        # perlukan ffmpeg (dengan libass)

# 1) Jana transkrip, pelan suntingan & prompt B-roll
python -m dakwah_editor ceramah.mp4 --plan-only

# 2) Jana imej/video AI ikut work/broll_prompts.md, simpan dalam broll/
#    dengan nama fail dicadangkan (cth. broll/kubur_1.jpg, broll/syurga_1.mp4)

# 3) Render akhir
python -m dakwah_editor ceramah.mp4 -o dakwah_final.mp4 \
    --title "Hidup Ini Singkat" --music nasyid.mp3
```

Pilihan berguna:

- `--target 150` — durasi sasaran (90–180s).
- `--plan work/plan.json` — sunting `order` dalam pelan (tukar hook / buang ayat) kemudian render semula.
- `--music ambient|none|fail.mp3` — lalai `ambient` (pad lembut tanpa melodi). Guna `none` jika mahu tanpa muzik, atau fail nasyid/zikir anda sendiri.
- `--fit blur` — kekalkan bingkai landskap penuh di atas latar kabur (lalai `cover` = crop penuh).
- `--crop-x 0.4` — anjak crop jika penceramah tidak di tengah.
- `--font "Montserrat ExtraBold"` — fon subtitle (mesti dipasang dalam sistem).
- `--model medium` — model Whisper lebih kecil/laju (lalai `large-v3`, paling tepat untuk Melayu).

Fail dalam `work/`: `transcript.json/.srt`, `plan.json`, `broll_prompts.md`, `subs.ass`, `edl.json`.

## Ujian tanpa model Whisper

```bash
python tests/make_fixture.py fx
python -m dakwah_editor fx/ceramah.mp4 -o fx/out.mp4 --work fx/work \
    --transcript fx/transcript.json --broll fx/broll
```
