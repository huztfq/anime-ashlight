"""Reel cover thumbnails (1080x1920): the reel's opening frame, no burned captions, with its hook text in the same
look as the on-screen hook (white, last word ember orange, dark rounded box) plus a small series tag.
Text stays inside the centre 3:4 area so Instagram's profile-grid crop keeps it.
Usage: make_covers.py N [episode_dir]   (episode_dir holds reels.json and frames_v/; default: this folder)
Writes upload/epNN_reelK_cover.jpg."""
import json, pathlib, sys
from PIL import Image, ImageDraw, ImageFilter
from textcards import BOLD, font, wrap

W, H = 1080, 1920
EMBER = (255, 150, 60)


def cover(frame, hook, n, k, out):
    im = Image.open(frame).convert("RGB")
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x0 = (im.width - W) // 2
    if im.width > W:  # wide frame: centre the crop on the most detailed part of the upper half (usually faces)
        e = im.convert("L").filter(ImageFilter.FIND_EDGES).crop((0, 0, im.width, im.height // 2)).resize((im.width // 8, 1))
        cols = list(e.get_flattened_data())
        win = W // 8
        best = max(range(len(cols) - win + 1), key=lambda i: sum(cols[i:i + win]))
        x0 = min(max(0, best * 8), im.width - W)
    im = im.crop((x0, (im.height - H) // 2, x0 + W, (im.height - H) // 2 + H))
    # darken the lower half so the text reads on any frame (faces stay clear up top)
    shade = Image.new("L", (1, H))
    for y in range(H):
        t = max(0, (y - H * 0.48) / (H * 0.32))
        shade.putpixel((0, y), int(165 * min(1, t)))
    im = Image.composite(Image.new("RGB", (W, H), "black"), im, shade.resize((W, H)))
    d = ImageDraw.Draw(im, "RGBA")

    size = 104
    f = font(BOLD, size)
    lines = wrap(d, hook.upper(), f, W * 0.84)
    while len(lines) > 3 and size > 70:
        size -= 8; f = font(BOLD, size); lines = wrap(d, hook.upper(), f, W * 0.84)
    lh = size * 1.2
    top = H * 0.64 - lh * len(lines) / 2   # inside the 3:4 grid crop (y 240..1680)
    widest = max(d.textlength(l, font=f) for l in lines)
    d.rounded_rectangle([(W - widest) / 2 - 36, top - 22, (W + widest) / 2 + 36, top + lh * len(lines) + 14],
                        radius=28, fill=(0, 0, 0, 150))
    words = hook.upper().split()
    last = len(words) - 1
    i = 0
    for li, line in enumerate(lines):
        x = (W - d.textlength(line, font=f)) / 2
        for w in line.split():
            d.text((x, top + li * lh), w, font=f, fill=EMBER if i == last else "white",
                   stroke_width=max(4, size // 12), stroke_fill="black")
            x += d.textlength(w + " ", font=f); i += 1

    tag = font(BOLD, 46)
    label = f"AFTER THE HUM  |  EP {n}"
    d.text(((W - d.textlength(label, font=tag)) / 2, H * 0.80), label, font=tag, fill="white",
           stroke_width=3, stroke_fill="black")
    sub = font(BOLD, 34)
    s2 = f"PART {k} OF 4"
    d.text(((W - d.textlength(s2, font=sub)) / 2, H * 0.80 + 62), s2, font=sub, fill=EMBER,
           stroke_width=3, stroke_fill="black")
    im.save(out, quality=92)
    return out


if __name__ == "__main__":
    n = int(sys.argv[1])
    ep = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else ".")
    here = pathlib.Path(__file__).parent
    reels = json.loads((ep / "reels.json").read_text())["reels"]
    for k, r in enumerate(reels, 1):
        shot = r["sections"][0]["shots"][0]["shot"]
        name = f"s{int(shot):02d}_1.png"  # vertical frame if made, else the wide one centre-cropped
        frame = ep / "frames_v" / name if (ep / "frames_v" / name).exists() else ep / "frames" / name
        out = here / "upload" / f"ep{n:02d}_reel{r['id']}_cover.jpg"
        print(cover(frame, r["hook_text"], n, r["id"], out))
