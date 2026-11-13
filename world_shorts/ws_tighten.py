"""Shorten narrator pauses: every silence over 0.4 s (silencedetect, -38 dB) is cut down to 0.28 s, and the word
timings are shifted to match, then the clip is sped up by TEMPO. Originals stay as r*_orig.mp3/json, so it is safe to re-run."""
import json, pathlib, re, shutil, subprocess
MIN_SIL, KEEP = 0.4, 0.28
TEMPO = 1.07  # a touch quicker overall (pitch kept) so the short lands around 42 s
for js in sorted(pathlib.Path("reels_audio").glob("r1_*.json")):
    if js.stem.endswith("_orig"): continue
    mp3 = js.with_suffix(".mp3")
    oj, om = js.with_name(js.stem + "_orig.json"), js.with_name(js.stem + "_orig.mp3")
    if not oj.exists(): shutil.copy(js, oj); shutil.copy(mp3, om)
    log = subprocess.run(["ffmpeg", "-v", "info", "-i", str(om), "-af", f"silencedetect=n=-38dB:d={MIN_SIL}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    total = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(om)]))
    cuts = [(s + KEEP / 2, e - KEEP / 2) for s, e in zip(starts, ends) if s > 0.05 and e < total - 0.05]  # inner pauses only
    def shift(t):
        return t - sum(min(b, max(a, t)) - a for a, b in cuts)
    words = [(w, shift(s) / TEMPO, shift(e) / TEMPO) for w, s, e in json.loads(oj.read_text())]
    keep, t0 = [], 0.0
    for a, b in cuts: keep.append((t0, a)); t0 = b
    keep.append((t0, None))
    parts = "".join(f"[0]atrim={a}" + (f":{b}" if b else "") + f",asetpts=PTS-STARTPTS[p{i}];" for i, (a, b) in enumerate(keep))
    fc = parts + "".join(f"[p{i}]" for i in range(len(keep))) + f"concat=n={len(keep)}:v=0:a=1,atempo={TEMPO}[o]"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(om), "-filter_complex", fc, "-map", "[o]", "-b:a", "192k", str(mp3)], check=True)
    js.write_text(json.dumps(words)); print(js.stem, f"-{sum(b - a for a, b in cuts):.2f}s")
