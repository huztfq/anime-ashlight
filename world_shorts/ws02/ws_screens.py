"""Recurring objects drawn ONCE by Qwen, then switched on/off in code so they never move between poses:
shot 2 (tray of phones: ON shows 7:17, OFF is black), shot 5 (watch: glow on/off), shot 9 (wall of screens on/off)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from blobs import blobs
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
O = "old/orig_frames/"

def screens_off(a, mask, level=0.06):
    m = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(3))
    m = np.asarray(m).astype(float)[..., None] / 255
    dark = np.full_like(a, 0); dark[..., 0] = 10; dark[..., 1] = 12; dark[..., 2] = 16
    return a * (1 - m) + (dark + a * level) * m

# shot 2: phone tray
im = Image.open(O + "s02_1.png").convert("RGB"); a = np.asarray(im).astype(float)
g = a.mean(2); boxes = [b for b in blobs(g > 190, 4, 5000)]
on = im.copy(); d = ImageDraw.Draw(on)
for y0, y1, x0, x1, _ in boxes:
    w = x1 - x0; f = ImageFont.truetype(FONT, int(w * 0.30))
    d.text(((x0 + x1) / 2, y0 + (y1 - y0) * 0.27), "7:17", font=f, fill=(28, 30, 36), anchor="mm")
on = Image.blend(im, on, 0.92)
on.save("frames_v/s02_1.png"); on.save("frames_v/s02_3.png")
mask = np.zeros(g.shape)
for y0, y1, x0, x1, _ in boxes: mask[y0:y1, x0:x1] = (g[y0:y1, x0:x1] > 120)
off = screens_off(a, mask)
Image.fromarray(off.clip(0, 255).astype(np.uint8)).save("frames_v/s02_2.png"); Image.fromarray(off.clip(0, 255).astype(np.uint8)).save("frames_v/s02_4.png")
print("s02 screens:", len(boxes))

# shot 5: the watch glow drops (whole frame dimmer, watch face greyer)
im = Image.open(O + "s05_1.png").convert("RGB"); im.save("frames_v/s05_1.png"); im.save("frames_v/s05_3.png")
dim = Image.fromarray((np.asarray(im).astype(float) * 0.62).astype(np.uint8))
dim.save("frames_v/s05_2.png"); dim.save("frames_v/s05_4.png")

# shot 9: wall of screens dark
im = Image.open(O + "s09_1.png").convert("RGB"); a = np.asarray(im).astype(float); g = a.mean(2)
im.save("frames_v/s09_1.png"); im.save("frames_v/s09_3.png")
mask = (g > 150).astype(float)
off = screens_off(a, mask, 0.15)
Image.fromarray(off.clip(0, 255).astype(np.uint8)).save("frames_v/s09_2.png"); Image.fromarray(off.clip(0, 255).astype(np.uint8)).save("frames_v/s09_4.png")
print("done")

# shot 12: the street clock (Qwen-edited to 7:17) flares cold white on the tone; same picture, so the clock never moves
from PIL import ImageEnhance
im = Image.open(O + "s12_1.png").convert("RGB"); im.save("frames_v/s12_1.png"); im.save("frames_v/s12_3.png")
glow = ImageEnhance.Brightness(im).enhance(1.35).filter(ImageFilter.GaussianBlur(18))
flare = Image.blend(ImageEnhance.Brightness(im).enhance(1.25), glow, 0.35)
flare = Image.fromarray(np.clip(np.asarray(flare).astype(float) * [0.95, 1.0, 1.08], 0, 255).astype(np.uint8))
flare.save("frames_v/s12_2.png"); flare.save("frames_v/s12_4.png")
