"""One local render per style (Animagine XL 4.0 via ComfyUI), same scene and seed as the Qwen style test.
Usage: local_styles.py   -> styles_local/{NN}_{key}.png"""
import pathlib, time
from comfy import graph, run

OUT = pathlib.Path("styles_local"); OUT.mkdir(exist_ok=True)
SEED = 7302
QUALITY = "masterpiece, best quality, very aesthetic, absurdres"
BASE_NEG = ("lowres, worst quality, low quality, bad anatomy, bad hands, extra fingers, missing fingers, deformed, "
            "blurry, jpeg artifacts, watermark, signature, logo, text, gore, nsfw, crowd, extra people, cropped head")
# kept short: SDXL's text encoder reads ~75 tokens per chunk, and tags past it lose weight, so style goes first
SCENE = ("2people, 1girl, 1boy, wide shot, full body, sitting side by side on ruined rooftop at dusk, "
         "girl with short white bob hair and yellow raincoat holding candle, "
         "boy with orange hair, red earmuffs and green hoodie, ash falling, radio tower in distance")

# key: (name, style tags, extra negative tags)
STYLES = {
    "anime_screencap": ("Modern anime (current film look)", "anime screencap, anime coloring, cinematic lighting, detailed background", "3d, realistic"),
    "dark_gritty": ("Dark gritty anime", "anime coloring, dark, muted desaturated palette, heavy shadows, grim, film grain, dramatic lighting", "bright colors, 3d"),
    "retro_90s": ("1990s retro anime", "retro artstyle, 1990s (style), cel animation, vhs artifacts, muted colors", "3d, realistic, modern"),
    "watercolor": ("Watercolor", "watercolor (medium), traditional media, soft colors, paper texture", "3d, lineart heavy"),
    "manga_ink": ("Black-and-white manga", "monochrome, greyscale, manga, screentones, ink, hatching, high contrast", "color, colorful"),
    "oil_painting": ("Painterly / oil painting", "oil painting (medium), impasto, painterly, brush strokes, dramatic lighting", "flat color, lineart"),
    "pencil_sketch": ("Pencil sketch", "sketch, graphite (medium), traditional media, rough lines, monochrome", "color, clean lineart"),
    "flat_color": ("Flat color / minimal", "flat color, no lineart, limited palette, simple shading, graphic", "detailed shading, 3d"),
    "semi_realistic": ("Semi-realistic", "semi-realistic, realistic, detailed face, detailed skin, cinematic lighting", "chibi, flat color"),
    "chibi": ("Chibi", "chibi, cute, big head, simple background shapes", "realistic"),
}



if __name__ == "__main__":
    for i, (key, (name, tags, neg)) in enumerate(STYLES.items(), 1):
        out = OUT / f"{i:02d}_{key}.png"
        if out.exists():
            continue
        g = graph(f"{tags}, {SCENE}, {QUALITY}", SEED)
        g["neg"]["inputs"]["text"] = f"{BASE_NEG}, {neg}"
        t = time.time()
        run(g, out)
        print(f"{i}. {name}: {time.time()-t:.0f}s", flush=True)
