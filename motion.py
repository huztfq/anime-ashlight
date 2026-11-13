"""Motion-graphic text: words pop in one by one (scale overshoot + fade), hold, then fade out.
Rendered frame by frame with Pillow into an alpha .mov that ffmpeg overlays (this ffmpeg has no drawtext)."""
import pathlib, shutil, subprocess
from PIL import Image, ImageDraw
from textcards import BOLD, font, wrap

EMBER = (255, 150, 60, 255)


def ease_out_back(x):
    c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def kinetic(text, out, w, h, y_frac, size, secs, fps, stagger=0.11, pop=0.28, accent=-1, box=True):
    """Alpha video of `text` building word by word; the `accent` word (default last) glows ember orange."""
    out = pathlib.Path(out)
    if out.exists():
        return out
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    f = font(BOLD, size)
    lines = wrap(probe, text, f, w * 0.84)
    lh = size * 1.2
    top = h * y_frac - lh * len(lines) / 2
    words = []  # (word, x, y) of each word at full size
    for li, line in enumerate(lines):
        x = (w - probe.textlength(line, font=f)) / 2
        for word in line.split():
            words.append((word, x, top + li * lh)); x += probe.textlength(word + " ", font=f)
    accent = accent % len(words)
    sprites = []
    for i, (word, _, _) in enumerate(words):
        pad = 12
        tw, th = int(probe.textlength(word, font=f)) + 2 * pad, int(size * 1.3) + 2 * pad
        im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((pad, pad), word, font=f, fill=EMBER if i == accent else "white",
                                stroke_width=max(4, size // 12), stroke_fill="black")
        sprites.append((im, pad))
    widest = max(probe.textlength(l, font=f) for l in lines)
    tmp = out.with_suffix(".frames"); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
    n = round(secs * fps)
    for k in range(n):
        t = k / fps
        fade = min(1, max(0, (secs - t) / 0.3))  # fade the whole card out over the last 0.3s
        frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if box:
            a = min(1, t / 0.2) * fade
            ImageDraw.Draw(frame).rounded_rectangle(
                [(w - widest) / 2 - 34, top - 20, (w + widest) / 2 + 34, top + lh * len(lines) + 14],
                radius=26, fill=(0, 0, 0, int(150 * a)))
        for i, ((word, x, y), (im, pad)) in enumerate(zip(words, sprites)):
            p = (t - i * stagger) / pop
            if p <= 0:
                continue
            p = min(1, p)
            s = 0.4 + 0.6 * ease_out_back(p)  # 0.4 -> overshoot -> 1.0
            spr = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
            alpha = spr.getchannel("A").point(lambda v: int(v * min(1, p * 2) * fade))
            spr.putalpha(alpha)
            cx, cy = x - pad + im.width / 2, y - pad + im.height / 2
            frame.alpha_composite(spr, (round(cx - spr.width / 2), round(cy - spr.height / 2)))
        frame.save(tmp / f"{k:04d}.png")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(fps), "-i", str(tmp / "%04d.png"),
                    "-c:v", "png", "-pix_fmt", "rgba", str(out)], check=True)
    shutil.rmtree(tmp)
    return out
