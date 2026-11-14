"""One consistent 'star' for shot 2: remove the extra high light from pose 1, then derive OFF and FLARE frames from it
so the blink is the same light in the same spot (Qwen edits moved and duplicated it)."""
import numpy as np
from PIL import Image, ImageFilter
src = Image.open("old/orig_frames/s02_1.png").convert("RGB")
a = np.asarray(src).astype(float)

def light_layer(a, cy, cx, r):
    box = (cx - r, cy - r, cx + r, cy + r)
    crop = Image.fromarray(a[cy - r:cy + r, cx - r:cx + r].astype(np.uint8))
    bg = np.asarray(crop.filter(ImageFilter.MedianFilter(41)).filter(ImageFilter.GaussianBlur(6))).astype(float)
    layer = np.clip(a[cy - r:cy + r, cx - r:cx + r] - bg, 0, None)
    yy, xx = np.mgrid[-r:r, -r:r]; mask = np.clip(1.4 - np.hypot(yy, xx) / r * 1.4, 0, 1)[..., None]
    return layer * mask

def remove(a, cy, cx, r, k=1.0):
    a = a.copy(); a[cy - r:cy + r, cx - r:cx + r] -= k * light_layer(a, cy, cx, r); return a

def glow(a, cy, cx, r, amp):
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    d = np.hypot(yy - cy, xx - cx)
    g = amp * (np.exp(-(d / (r * 0.25)) ** 2) + 0.35 * np.exp(-(d / r) ** 2))
    return np.clip(a + g[..., None] * np.array([0.92, 0.97, 1.0]), 0, 255)

def patch(a, cy, cx, r, dx):
    """Cover a light with feathered sky copied from dx pixels to the side."""
    a = a.copy(); yy, xx = np.mgrid[-r:r, -r:r]
    m = np.clip((r - np.hypot(yy, xx)) / (r * 0.35), 0, 1)[..., None]
    a[cy - r:cy + r, cx - r:cx + r] = a[cy - r:cy + r, cx - r + dx:cx + r + dx] * m + a[cy - r:cy + r, cx - r:cx + r] * (1 - m)
    return a

base = patch(a, 404, 542, 120, -300)          # the extra high light goes
on = base
off = remove(base, 1129, 552, 46, 0.93)       # the ridge light nearly out
flare = glow(base, 1129, 552, 140, 120)       # the ridge light pulses bright
def save(x, name):
    im = Image.fromarray(np.clip(x, 0, 255).astype(np.uint8))
    im = im.point(lambda v: round(255 * ((v / 255) ** 0.78)))  # same midtone lift as the other frames
    im.save(f"frames_v/{name}")
save(on, "s02_1.png"); save(off, "s02_2.png"); save(flare, "s02_3.png"); save(on, "s02_4.png")
