"""Channel branding: logo options (profile picture for YouTube, Instagram, TikTok) and YouTube banner options.
Art from Qwen in the dark gritty style; the channel name is set with Pillow so it stays crisp and inside safe areas.
Usage: brand.py ["Channel Name"] ["tagline"]   -> brand/"""
import pathlib, sys
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from qwen_frames import call, STYLE_REF

NAME = sys.argv[1] if len(sys.argv) > 1 else "Ashlight Stories"
TAGLINE = sys.argv[2] if len(sys.argv) > 2 else "DARK ANIME STORIES  ·  NEW EPISODES DAILY"
OUT = pathlib.Path("brand"); OUT.mkdir(exist_ok=True)
FONT = "/System/Library/Fonts/Avenir Next Condensed.ttc"
STYLE = ("Dark mature seinen anime illustration, heavy black shadows, rough ink lines, muted desaturated palette with "
         "one warm ember-orange accent. Match the art style of the reference image; do not copy its characters.")

LOGOS = {
    "logo_A_ember": "Minimal emblem logo, centered on a pure black background: a single glowing ember floating inside a "
                    "thin rough ink circle, grey ash flakes drifting around it. Bold, simple, readable at tiny sizes. No text.",
    "logo_B_monogram": "Minimal monogram logo, centered on a pure black background: a bold brush-ink letter A whose "
                       "crossbar is a glowing ember-orange spark, ash flakes falling. Bold, simple, readable at tiny sizes. "
                       "No other text.",
    "logo_C_lantern": "Minimal emblem logo, centered on a pure black background: a small old lantern held up in a "
                      "silhouetted hand, its warm ember light the only color, ash falling. Bold, simple, readable at tiny "
                      "sizes. No text.",
}
BANNERS = {
    "banner_A_city_to_mountains": "Ultra-wide panorama at dusk: a ruined rain-dark city on the left fading into black pine "
        "forests and snowy mountains on the right, one tiny warm light glowing on a distant mountain peak, grey ash "
        "falling. The middle third is calm, dark open sky with no objects. No people, no text.",
    "banner_B_survivors_ridge": "Ultra-wide panorama: four small silhouetted survivors walking along a ridge at the "
        "bottom edge, a vast dark sky above them, a ruined city skyline far behind and mountains ahead, one warm ember "
        "glow on the horizon, ash falling. The middle of the sky is calm and empty. No text.",
}


def font(size):
    return ImageFont.truetype(FONT, size, index=2)  # Avenir Next Condensed Demi Bold


def spaced(draw, xy, text, f, fill, spacing, anchor_w):
    """Draw letter-spaced text centered on anchor_w (x center)."""
    widths = [draw.textlength(c, font=f) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x, y = anchor_w - total / 2, xy
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=f, fill=fill)
        x += w + spacing
    return total


def logo(key, prompt):
    raw = OUT / f"{key}_raw.png"
    if not raw.exists():
        call([STYLE_REF], f"{STYLE} {prompt}", "1328*1328", raw, f"brand_{key}")
    im = Image.open(raw).convert("RGB").resize((1024, 1024), Image.LANCZOS)
    im.save(OUT / f"{key}_1024.png")
    # preview of how the platforms crop it: a circle
    mask = Image.new("L", im.size, 0); ImageDraw.Draw(mask).ellipse((0, 0, 1023, 1023), fill=255)
    prev = Image.new("RGB", im.size, (24, 24, 24)); prev.paste(im, (0, 0), mask)
    prev.resize((320, 320), Image.LANCZOS).save(OUT / f"{key}_circle_preview.png")
    return key


def banner(key, prompt):
    raw = OUT / f"{key}_raw.png"
    if not raw.exists():
        call([STYLE_REF], f"{STYLE} {prompt}", "1664*928", raw, f"brand_{key}")
    W, H = 2560, 1440
    im = Image.open(raw).convert("RGB")
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    im = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))
    # darken the centre band so the name reads; YouTube's always-visible safe area is 1546x423 in the middle
    shade = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shade).rectangle((0, H // 2 - 260, W, H // 2 + 260), fill=150)
    im = Image.composite(Image.new("RGB", (W, H), "black"), im, shade.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(im)
    spaced(d, H // 2 - 120, NAME.upper(), font(150), (236, 230, 220), 22, W / 2)
    spaced(d, H // 2 + 60, TAGLINE, font(46), (214, 140, 60), 10, W / 2)
    im.save(OUT / f"{key}_2560x1440.png")
    return key


if __name__ == "__main__":
    jobs = [lambda k=k, p=p: logo(k, p) for k, p in LOGOS.items()] + [lambda k=k, p=p: banner(k, p) for k, p in BANNERS.items()]
    with ThreadPoolExecutor(max_workers=2) as ex:
        for k in ex.map(lambda f: f(), jobs):
            print(k, "done", flush=True)
