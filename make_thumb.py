"""YouTube thumbnail 1280x720: one film frame, a 2-3 word line on top (last word ember orange), "AFTER THE HUM | EP N"
small at the bottom right. Usage: make_thumb.py N SHOT "TEXT" [pose]  -> upload/epNN_thumbnail_1280x720.jpg"""
import pathlib, sys
from PIL import Image, ImageDraw
from textcards import BOLD, font

W, H = 1280, 720
EMBER = (255, 150, 60)


def thumb(n, shot, text, pose=1):
    src = pathlib.Path("frames") / f"s{int(shot):02d}_{pose}.png"
    im = Image.open(src).convert("RGB").resize((W, H), Image.LANCZOS)
    shade = Image.new("L", (1, H))
    for y in range(H):  # dark at the top for the words, lighter in the middle, dark again for the tag
        shade.putpixel((0, y), int(175 * max(0, 1 - y / (H * 0.42), (y - H * 0.78) / (H * 0.22))))
    im = Image.composite(Image.new("RGB", (W, H), "black"), im, shade.resize((W, H)))
    d = ImageDraw.Draw(im)
    words = text.upper().split()
    size = 132
    while size > 70:
        f = font(BOLD, size)
        if d.textlength(" ".join(words), font=f) <= W * 0.9:
            break
        size -= 6
    x = (W - d.textlength(" ".join(words), font=f)) / 2
    for i, w in enumerate(words):
        d.text((x, 40), w, font=f, fill=EMBER if i == len(words) - 1 else "white",
               stroke_width=max(5, size // 14), stroke_fill="black")
        x += d.textlength(w + " ", font=f)
    tag = font(BOLD, 38)
    label = f"AFTER THE HUM  |  EP {n}"
    d.text((W - 36 - d.textlength(label, font=tag), H - 70), label, font=tag, fill="white",
           stroke_width=3, stroke_fill="black")
    out = pathlib.Path("upload") / f"ep{n:02d}_thumbnail_1280x720.jpg"
    out.parent.mkdir(exist_ok=True)
    im.save(out, quality=92)
    return out


if __name__ == "__main__":
    print(thumb(int(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 1))
