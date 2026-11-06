"""Kata kunci dakwah (Bahasa Melayu) untuk pemarkahan isi, highlight subtitle
dan cadangan prompt B-roll AI."""

import re
import unicodedata

# Berat kata kunci: semakin tinggi, semakin "kuat" emosi/isi ayat tersebut.
KEYWORD_WEIGHTS = {
    # Tauhid & akidah
    "allah": 3, "tuhan": 2, "rasulullah": 3, "nabi": 2, "muhammad": 2, "iman": 3,
    "islam": 2, "quran": 3, "al-quran": 3, "hadis": 2, "malaikat": 2, "syahadah": 3,
    # Akhirat
    "syurga": 4, "neraka": 4, "akhirat": 3, "kiamat": 4, "kubur": 4, "mati": 4,
    "kematian": 4, "maut": 4, "roh": 2, "hisab": 3, "mahsyar": 3, "titian": 2,
    "azab": 4, "pahala": 3, "dosa": 4, "kekal": 2,
    # Ibadah
    "solat": 3, "sembahyang": 3, "doa": 3, "berdoa": 3, "zikir": 2, "puasa": 2,
    "sedekah": 3, "zakat": 2, "haji": 2, "sujud": 3, "masjid": 2, "tahajud": 3,
    "istighfar": 3, "selawat": 2, "wuduk": 2,
    # Hati & emosi
    "taubat": 4, "bertaubat": 4, "ampun": 4, "keampunan": 4, "rahmat": 3,
    "kasih": 2, "sayang": 2, "cinta": 2, "hati": 3, "jiwa": 2, "menangis": 4,
    "tangis": 3, "air": 0, "mata": 0, "sabar": 3, "syukur": 3, "ikhlas": 3,
    "redha": 3, "tenang": 3, "ketenangan": 3, "takut": 3, "harapan": 2,
    "hidayah": 4, "insaf": 4, "rindu": 3, "sedih": 2, "derita": 3, "ujian": 3,
    "musibah": 3, "bahagia": 2,
    # Kehidupan
    "dunia": 2, "ibu": 3, "ayah": 3, "mak": 2, "anak": 2, "keluarga": 2,
    "rezeki": 3, "harta": 2, "masa": 2, "umur": 3, "muda": 2, "tua": 2,
    "nikmat": 3, "hidup": 2, "nyawa": 3,
    # Ilmu, institusi & infak
    "ilmu": 3, "agama": 3, "madrasah": 3, "zawiyah": 3, "pondok": 3, "guru": 3,
    "pelajar": 2, "ustaz": 2, "mengajar": 3, "belajar": 2, "dakwah": 3,
    "infak": 4, "penginfak": 4, "istiqamah": 4, "sumbangan": 3, "bantu": 3,
    "membantu": 3, "rm150": 4, "warga": 2, "emas": 2, "yaman": 3, "pautan": 3,
    "beribadah": 3, "ibadah": 3, "amalkan": 3, "berkembang": 2, "bulanan": 3,
}

# Frasa yang kuat untuk hook (soalan/kejutan).
HOOK_CUES = [
    "bayangkan", "tahukah", "pernahkah", "kenapa", "mengapa", "apa akan",
    "bagaimana", "kalau esok", "jika esok", "siapa", "sedarkah", "ingat",
    "demi allah", "wallahi", "sungguh", "jangan",
]

# Perkataan pengisi / gagap yang dibuang.
FILLERS = {
    "em", "emm", "emmm", "erm", "err", "er", "aa", "aaa", "ah", "ahh", "eh",
    "ehh", "hmm", "hm", "uh", "um", "umm", "ha", "haa", "aah",
}

# Visual sinematik (prompt AI, dalam Bahasa Inggeris kerana kebanyakan
# penjana imej AI lebih tepat dengan prompt Inggeris).
VISUALS = {
    "syurga": "lush paradise garden with crystal rivers and golden light, heavenly clouds",
    "neraka": "dark fiery abyss, glowing embers and smoke, ominous red sky",
    "akhirat": "vast endless plain under a blazing sky, crowds of silhouettes, epic scale",
    "kiamat": "cracking earth and collapsing mountains, dramatic stormy sky, apocalyptic",
    "kubur": "lonely grave in a quiet cemetery under moonlight, mist, frangipani tree",
    "mati": "empty hospital bed by a window at dusk, soft light, quiet and somber",
    "kematian": "white shroud and lantern in a dark room, solemn atmosphere",
    "maut": "hourglass with the last grains of sand falling, dark background",
    "umur": "hourglass with sand falling, warm candle light, time passing",
    "masa": "old clock face with moving hands, dust particles in light beams",
    "dosa": "man sitting alone in the rain at night, head bowed, city lights bokeh",
    "taubat": "man kneeling on prayer mat at night crying, single lamp, emotional",
    "bertaubat": "man kneeling on prayer mat at night crying, single lamp, emotional",
    "ampun": "hands raised in prayer toward a glowing sky, light rays breaking through clouds",
    "doa": "close-up of hands raised in dua, warm backlight, tasbih beads",
    "berdoa": "close-up of hands raised in dua, warm backlight, tasbih beads",
    "solat": "silhouette of a man praying on a prayer mat at dawn, sunlight through window",
    "sembahyang": "silhouette of a man praying on a prayer mat at dawn, sunlight through window",
    "sujud": "man in sujud on a prayer mat, soft volumetric light from above",
    "tahajud": "man praying alone at night in a dim room, moonlight through window",
    "masjid": "grand mosque at golden hour, minarets, birds flying, cinematic wide shot",
    "quran": "open Quran on a wooden stand, glowing light, dust particles",
    "al-quran": "open Quran on a wooden stand, glowing light, dust particles",
    "allah": "light rays piercing through clouds over a calm ocean, majestic sky",
    "rahmat": "gentle rain falling on green fields, sunlight and rainbow",
    "hidayah": "single beam of light shining into a dark room, a man looking up",
    "hati": "glowing light inside a human chest silhouette, soft particles",
    "tenang": "calm lake at sunrise with mist, mountains reflection, serene",
    "ketenangan": "calm lake at sunrise with mist, mountains reflection, serene",
    "sabar": "lone tree standing in a storm, wind and rain, resilient",
    "ujian": "man walking alone through a desert storm, determined",
    "musibah": "flooded village street under a grey sky, dramatic",
    "syukur": "family sharing a simple meal together, warm light, smiles",
    "nikmat": "golden wheat field at sunset, wind, abundance",
    "rezeki": "farmer harvesting rice paddy at sunrise, golden light",
    "ibu": "elderly mother's wrinkled hands holding her child's hand, warm light",
    "mak": "elderly mother's wrinkled hands holding her child's hand, warm light",
    "ayah": "elderly father walking with his son on a village road at sunset",
    "anak": "child running in a green field toward a parent, golden hour",
    "keluarga": "family praying together in congregation at home, warm lamp light",
    "dunia": "busy city timelapse at night, people rushing, neon lights",
    "harta": "pile of gold coins and money slowly turning to dust",
    "sedekah": "hand giving food to a poor person on a street, warm light",
    "menangis": "close-up of a tear rolling down a cheek, shallow depth of field",
    "tangis": "close-up of a tear rolling down a cheek, shallow depth of field",
    "rindu": "man looking out a rainy window at night, longing",
    "kasih": "two hands holding each other, soft sunset backlight",
    "cinta": "two hands holding each other, soft sunset backlight",
    "hidup": "time-lapse of a seed growing into a tree, life cycle",
    "nyawa": "candle flame flickering and slowly fading out in darkness",
    "nabi": "ancient desert caravan at sunset, sand dunes, golden light (no faces)",
    "rasulullah": "Masjid an-Nabawi green dome at dusk, pilgrims, cinematic",
    "zikir": "hand moving tasbih prayer beads, macro shot, warm bokeh",
    "puasa": "dates and water on a table at iftar, golden sunset light",
    "pahala": "light particles rising into the night sky, glowing",
    "azab": "storm with lightning over dark ocean waves, terrifying",
}

DEFAULT_VISUAL = "cinematic sky with light rays through clouds, Islamic atmosphere, serene"

PROMPT_STYLE = (
    "cinematic, photorealistic, vertical 9:16, 35mm film look, volumetric light, "
    "shallow depth of field, moody color grade, no text, no faces of prophets"
)


def norm(word: str) -> str:
    w = unicodedata.normalize("NFKC", word).lower().strip()
    w = re.sub(r"[^\w\-']", "", w)
    return w.strip("-'")


def keyword_of(word: str):
    """Pulangkan kata kunci dasar jika perkataan ini kata kunci (termasuk
    imbuhan ringkas seperti 'syurga-nya', 'kesyurgaan', 'neraka')."""
    w = norm(word)
    if not w:
        return None
    if KEYWORD_WEIGHTS.get(w, 0) > 0:
        return w
    for suffix in ("nya", "lah", "kah", "mu", "ku", "kan", "an"):
        if w.endswith(suffix) and KEYWORD_WEIGHTS.get(w[: -len(suffix)], 0) > 0:
            return w[: -len(suffix)]
    for prefix in ("ke", "di", "ber", "men", "mem", "pe", "se"):
        base = w[len(prefix):]
        if w.startswith(prefix) and KEYWORD_WEIGHTS.get(base, 0) > 0 and len(base) >= 4:
            return base
    return None
