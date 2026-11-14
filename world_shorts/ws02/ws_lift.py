"""Lift dark frames (ws01 reviewer fix): every frames_v png is kept unlifted in raw/ and re-written from it with a
per-frame gamma that brings mean luminance up to ~TARGET (gamma clamped 0.55-0.9), so the night look stays but
faces read on a phone. Re-runnable: a frame newer than its raw copy is treated as a new raw frame."""
import glob, os, pathlib, shutil, numpy as np
from PIL import Image
TARGET = 44
raw = pathlib.Path("raw"); raw.mkdir(exist_ok=True)
for f in sorted(glob.glob("frames_v/*.png")):
    r = raw / pathlib.Path(f).name
    if not r.exists() or os.path.getmtime(f) > os.path.getmtime(r) + 1:
        shutil.copy2(f, r); os.utime(r)
    a = np.asarray(Image.open(r).convert("RGB")).astype(float) / 255
    lum = a.mean()
    g = 0.9 if lum * 255 >= TARGET else float(np.clip(np.log(TARGET / 255) / np.log(max(lum, 1e-3)), 0.55, 0.9))
    Image.fromarray((255 * a ** g).clip(0, 255).astype(np.uint8)).save(f)
    os.utime(r)  # raw stays newer than the lifted frame
    print(pathlib.Path(f).name, round(lum * 255), "->", round(255 * (a ** g).mean()), f"g={g:.2f}")
