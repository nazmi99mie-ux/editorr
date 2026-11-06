"""Jana gambar B-roll AI secara tempatan dengan SD-Turbo (Stable Diffusion).

    python -m dakwah_editor.aigen prompts.json broll/ [--steps 2] [--seeds 1]

prompts.json: {"style": "...", "images": {"nama": "prompt", ...}}
Setiap imej disimpan sebagai broll/<nama>.jpg (potret 576x1024).
"""

import argparse
import json
import os


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("prompts")
    ap.add_argument("outdir")
    ap.add_argument("--model", default="stabilityai/sd-turbo")
    ap.add_argument("--steps", type=int, default=2)
    ap.add_argument("--width", type=int, default=576)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--only", nargs="*", help="hanya jana nama-nama ini")
    ap.add_argument("--force", action="store_true", help="tulis ganti fail sedia ada")
    a = ap.parse_args(argv)

    import torch
    from diffusers import AutoPipelineForText2Image

    cfg = json.load(open(a.prompts, encoding="utf-8"))
    style = cfg.get("style", "")
    os.makedirs(a.outdir, exist_ok=True)
    torch.set_num_threads(os.cpu_count() or 4)
    pipe = AutoPipelineForText2Image.from_pretrained(a.model, torch_dtype=torch.float32)
    pipe.set_progress_bar_config(disable=True)
    for i, (name, prompt) in enumerate(cfg["images"].items()):
        if a.only and name not in a.only:
            continue
        out = os.path.join(a.outdir, f"{name}.jpg")
        if os.path.exists(out) and not a.force:
            continue
        g = torch.Generator().manual_seed(a.seed + i)
        img = pipe(f"{prompt}, {style}", num_inference_steps=a.steps, guidance_scale=0.0,
                   width=a.width, height=a.height, generator=g).images[0]
        img.save(out, quality=95)
        print(f"[aigen] {out}", flush=True)


if __name__ == "__main__":
    main()
