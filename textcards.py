"""Pillow text rendering shared by the film and reels (this ffmpeg build has no drawtext/libass)."""
from PIL import Image, ImageDraw, ImageFont

BOLD = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
SERIF = "/System/Library/Fonts/Supplemental/Didot.ttc"


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)


def wrap(draw, text, f, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if draw.textlength(t, font=f) <= max_w:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + [cur] if cur else lines


def banner(text, size, out, w, h, y_frac, path=BOLD, fill="white", stroke=8, box=False, highlight=None):
    """Transparent PNG with centered, wrapped, outlined text. `highlight` = index of a word to color yellow."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(path, size)
    lines = wrap(d, text, f, w * 0.86)
    lh = size * 1.18
    y = h * y_frac - lh * len(lines) / 2
    if box:
        widest = max(d.textlength(l, font=f) for l in lines)
        d.rounded_rectangle([(w - widest) / 2 - 30, y - 18, (w + widest) / 2 + 30, y + lh * len(lines) + 12],
                            radius=24, fill=(0, 0, 0, 150))
    idx = 0
    for line in lines:
        x = (w - d.textlength(line, font=f)) / 2
        for word in line.split():
            color = "#FFD84D" if highlight is not None and idx == highlight else fill
            d.text((x, y), word, font=f, fill=color, stroke_width=stroke, stroke_fill="black")
            x += d.textlength(word + " ", font=f); idx += 1
        y += lh
    img.save(out)
    return out
