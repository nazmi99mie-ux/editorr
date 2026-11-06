# Madrasah Zawiyah — video infak sinematik (9:16, 1080p)

Output: `output/dakwah_madrasah_zawiyah.mp4` (1:47, 1080×1920, 30fps, -15 LUFS)

Fail projek:
- `transcript.json/.srt` — transkrip Whisper large-v3 (cap masa perkataan)
- `fixes.json` — pembetulan perkataan (Ayak→Air, Allowan→Elaun, menyambut→menyambung, Fardun→Fardu, mengajak→mengajar)
- `cues.json` — B-roll AI & callout grafik ikut perkataan yang disebut
- `broll/real_*.jpg` — gambar sebenar Madrasah Zawiyah (dibekalkan)
- `broll_prompts.json` + `broll/*.jpg` lain — gambar AI (SD-Turbo) dijana dengan `python -m dakwah_editor.aigen`
- Muzik: `--music nasheed` — koir humming sedih maqam Hijaz tanpa alat muzik (dijana, bebas hak cipta)

Render semula (video sumber tidak disimpan dalam repo):

```bash
python -m dakwah_editor ceramah.mp4 -o dakwah_madrasah_zawiyah.mp4 \
  --transcript projects/madrasah_zawiyah/transcript.json \
  --fixes projects/madrasah_zawiyah/fixes.json \
  --cues projects/madrasah_zawiyah/cues.json \
  --broll projects/madrasah_zawiyah/broll --keep-all \
  --font "Poppins Black" --sub-size 86 --max-chars 15 \
  --callout-font "Bebas Neue" --brand-font "Cinzel" \
  --cta "JADI PENGINFAK TETAP|Madrasah Zawiyah An Nur  •  Tekan pautan di bawah" \
  --music nasheed --music-db -11 --premium --brand "Madrasah Zawiyah An Nur" \
  --logo projects/madrasah_zawiyah/brand/logo_asal.jpg
```

Fon (OFL, disertakan dalam `dakwah_editor/fonts/`): Poppins Black (subtitle), Bebas Neue (callout), Cinzel (jenama & penutup).
Tambah `--reuse-base` untuk render semula pantas jika hanya grafik/gambar/audio berubah.

Logo: `brand/logo_asal.jpg` (Madrasah Zawiyah An Nur + An Nur Centre) → lencana sudut atas & kad penutup (`python -m dakwah_editor.brandkit`).
