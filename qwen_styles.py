"""One Qwen-Image render per animation style, same scene (shot 2), for picking the film's look.
Usage: qwen_styles.py [model]   -> styles/{key}.png + styles/board.jpg"""
import json, os, pathlib, sys, time
from concurrent.futures import ThreadPoolExecutor
import requests
from PIL import Image
from textcards import font, BOLD

for line in pathlib.Path(".env").read_text().splitlines():
    k, _, v = line.partition("=")
    os.environ[k] = v

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen-image-3.0-pro"
HOST = os.environ["DASHSCOPE_BASE_URL"].removesuffix("/compatible-mode/v1")
H = {"Authorization": f"Bearer {os.environ['DASHSCOPE_API_KEY']}", "Content-Type": "application/json"}
OUT = pathlib.Path("styles"); OUT.mkdir(exist_ok=True)

SCENE = ("Post-apocalyptic city at dusk. On the rooftop of a ruined apartment building, under a tarp shelter, "
         "a 16-year-old girl kneels beside her 8-year-old brother. She holds a small candle stub, melting wax to plug "
         "his ears, and looks protectively toward the horizon. "
         "The girl: short choppy white bob haircut, blue eyes, small scar on her left cheek, oversized mustard yellow "
         "raincoat, small black chalkboard hanging from her neck on a string, fingerless gloves. "
         "The boy: messy orange hair, freckles, big red earmuffs, oversized green hoodie, patched knees. "
         "Background: tin cans, a laundry line, grey ash falling like snow, flooded streets far below, and on a distant "
         "hill a tall radio tower with a blinking red light. Both faces fully visible, wide 16:9 cinematic shot, "
         "no text, no watermark.")

STYLES = {
    "tv_anime": ("Japanese TV anime", "Modern Japanese TV anime style, clean line art, flat cel shading, vivid colors, crisp highlights."),
    "seinen": ("Dark gritty anime", "Dark mature seinen anime style, heavy black shadows, rough ink lines, muted desaturated palette, grim cinematic mood."),
    "painted_anime": ("Hand-painted anime film", "Hand-painted 2D anime feature film style, soft watercolor-gouache painted backgrounds, warm gentle light, simple expressive characters."),
    "painterly_3d": ("Painterly 3D", "Stylized painterly 3D animation, hand-painted textures with visible brush strokes, dramatic rim lighting, graphic shapes, cinematic."),
    "pixar_3d": ("3D animated movie", "Polished 3D animated feature film style, soft global illumination, expressive appealing characters, subsurface skin, detailed materials."),
    "graphic_novel": ("Graphic novel ink", "Black-and-white graphic novel comic art, bold ink lines, cross-hatching, heavy spotted blacks, gritty survival-horror comic, one accent color: the red light."),
    "halftone_comic": ("Comic pop / halftone", "Animated comic-book style, bold outlines, halftone dot shading, offset print misregistration, graphic color blocks, dynamic look."),
    "webtoon": ("Korean webtoon", "Korean webtoon digital illustration style, clean thin line art, soft gradient shading, glowing atmospheric light, polished modern finish."),
    "concept_art": ("Cinematic concept art", "Semi-realistic cinematic digital painting, video-game concept art, realistic proportions, moody volumetric light, detailed environment."),
    "storybook": ("Watercolor storybook", "Watercolor and colored pencil storybook illustration, paper texture, soft bleeding edges, gentle muted palette."),
}


def render(key):
    dest = OUT / f"{key}.png"
    if dest.exists():
        return key, "exists"
    body = {"model": MODEL,
            "input": {"messages": [{"role": "user", "content": [{"text": f"{STYLES[key][1]} {SCENE}"}]}]},
            "parameters": {"size": "1664*928", "n": 1, "watermark": False, "prompt_extend": False}}
    for i in range(3):
        try:
            r = requests.post(f"{HOST}/api/v1/services/aigc/multimodal-generation/generation", headers=H, json=body, timeout=300)
            j = r.json()
            if r.status_code >= 400:
                raise RuntimeError(f"{r.status_code} {j.get('code')} {j.get('message')}")
            url = j["output"]["choices"][0]["message"]["content"][0]["image"]
            dest.write_bytes(requests.get(url, timeout=120).content)
            with open("costs.jsonl", "a") as f:
                f.write(json.dumps({"service": "qwen-image", "what": f"style_{key}", "model": MODEL, "usage": j.get("usage")}) + "\n")
            return key, "done"
        except Exception as e:
            print(f"{key} attempt {i+1}: {e}", flush=True)
            time.sleep(5)
    return key, "FAILED"


def board():
    """2-column contact sheet with numbered style labels, sized for a phone."""
    keys = [k for k in STYLES if (OUT / f"{k}.png").exists()]
    tw, th, lab = 800, 446, 56
    sheet = Image.new("RGB", (tw * 2, (th + lab) * ((len(keys) + 1) // 2)), "black")
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for i, k in enumerate(keys):
        x, y = (i % 2) * tw, (i // 2) * (th + lab)
        sheet.paste(Image.open(OUT / f"{k}.png").convert("RGB").resize((tw, th)), (x, y + lab))
        d.text((x + 16, y + 10), f"{list(STYLES).index(k) + 1}. {STYLES[k][0]}", font=font(BOLD, 34), fill="white")
    sheet.save(OUT / "board.jpg", quality=88)


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=5) as ex:
        for key, res in ex.map(render, STYLES):
            print(key, res, flush=True)
    board()
