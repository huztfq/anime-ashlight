"""Second round of logo directions, each filling the frame so it survives the round profile crop. -> brand/logo2_*"""
import pathlib
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont
from qwen_frames import call

OUT = pathlib.Path("brand")
FILL = " The design fills most of the square and stays inside a centered circle. Pure black background."
LOGOS = {
    "1_character": "Anime channel logo: close-up portrait of a young hooded survivor girl, half her face in deep shadow, "
                   "one eye lit by a warm ember glow, ash falling, dark gritty seinen anime ink style. No text.",
    "2_hanko_seal": "Logo in the style of a Japanese hanko seal stamp: a bold square vermilion-red seal with the kanji "
                    "灰光 carved in white, slightly rough ink-stamp texture, centered on black. No other text.",
    "3_wordmark": "Bold text logo: the word \"ASHLIGHT\" stacked as \"ASH\" above \"LIGHT\" in heavy brush-calligraphy "
                  "letters, off-white ink with a glowing ember-orange spark on the letter I, ash particles. No other text.",
    "4_minimal_mountain": "Clean minimal flat vector logo: a sharp black-and-white mountain peak inside a circle with a "
                          "single small ember-orange dot glowing at the summit, crisp geometric lines, modern and simple. No text.",
    "5_eye_reflection": "Anime logo: an extreme close-up of a single anime eye, the iris reflecting a burning city skyline "
                        "in ember orange, dark ink lines, dramatic and striking. No text.",
    "6_crest_badge": "Circular crest badge logo: the words \"ASHLIGHT STORIES\" curved around the rim in clean capitals, "
                     "in the center a mountain silhouette with a small lantern glow, off-white and ember orange on black, "
                     "vintage emblem style. No other text.",
}


def make(key):
    raw = OUT / f"logo2_{key}_raw.png"
    if not raw.exists():
        call([], LOGOS[key] + FILL, "1328*1328", raw, f"brand_logo2_{key}")
    im = Image.open(raw).convert("RGB").resize((1024, 1024), Image.LANCZOS)
    im.save(OUT / f"logo2_{key}_1024.png")
    raw.unlink()
    return key


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=2) as ex:
        keys = list(ex.map(make, LOGOS))
    f = ImageFont.truetype("/System/Library/Fonts/Avenir Next Condensed.ttc", 26, index=2)
    sheet = Image.new("RGB", (3 * 340, 2 * 380), (40, 40, 40)); d = ImageDraw.Draw(sheet)
    for i, k in enumerate(keys):
        im = Image.open(OUT / f"logo2_{k}_1024.png").resize((320, 320), Image.LANCZOS)
        m = Image.new("L", (320, 320), 0); ImageDraw.Draw(m).ellipse((0, 0, 319, 319), fill=255)
        x, y = (i % 3) * 340 + 10, (i // 3) * 380 + 10
        sheet.paste(im, (x, y), m)
        d.text((x + 4, y + 326), k.replace("_", " ").upper(), font=f, fill=(230, 225, 215))
    sheet.save(OUT / "logo2_options_preview.png")
    print(keys)
