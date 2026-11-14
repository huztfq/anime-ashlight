"""Shot 1 opens under the hook card (y 0.2): move the picture down SHIFT px so Jun's face sits in the middle third.
The freed top band is the frame's own dark ceiling, mirrored and blurred. Reads old/orig_frames/ (unlifted originals), writes frames_v/ (re-lift after)."""
import sys
from PIL import Image, ImageFilter, ImageOps
SHIFT = 170
for k in range(1, 5):
    im = Image.open(f"old/orig_frames/s01_{k}.png").convert("RGB"); W, H = im.size
    out = Image.new("RGB", (W, H)); out.paste(im.crop((0, 0, W, H - SHIFT)), (0, SHIFT))
    top = ImageOps.flip(im.crop((0, 0, W, SHIFT))).filter(ImageFilter.GaussianBlur(6))
    out.paste(top, (0, 0)); out.save(f"frames_v/s01_{k}.png")
