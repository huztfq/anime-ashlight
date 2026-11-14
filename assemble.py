"""Build the 16:9 film: each shot cycles its 4 poses (3s each) with a slow push-in and soft dissolves,
on-screen hook text over the first 3s, CTA text over the last shot, an end card, then the audio mix.
Usage: assemble.py out.mp4 [lo-hi]"""
import json, pathlib, subprocess, sys
from PIL import Image
from mix import mix, layout, total_len, END_S
from textcards import banner, SERIF
from motion import kinetic

W, H, FPS = 1920, 1080, 25
XF = 0.35
STORY = json.loads(pathlib.Path("story.json").read_text())
B = pathlib.Path("build"); B.mkdir(exist_ok=True)


def ff(*a):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)


def pose_clip(png, dest, secs, i):
    """One pose held `secs`, with a gentle 4% push-in (direction alternates so cuts don't feel mechanical)."""
    if dest.exists():
        return dest
    n = round(secs * FPS)
    z = f"1.04-0.04*on/{n}" if i % 2 else f"1+0.04*on/{n}"
    ff("-loop", "1", "-i", str(png), "-vf",
       f"scale=7680:-2,crop=7680:4320,zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={n}:s={W}x{H}:fps={FPS}",
       "-frames:v", str(n), "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", str(dest))
    return dest


def shot_clip(s, length):
    """The shot's 4 poses spread evenly over `length` (12 s, or longer when its voices need it; see mix.layout)."""
    dest = B / f"shot{s['id']:02d}.mp4"
    if dest.exists():
        return dest
    pngs = [pathlib.Path(f"frames/s{s['id']:02d}_{i}.png") for i in range(1, 5)]
    pngs = [p if p.exists() else pngs[0] for p in pngs]
    pose_s = length / 4
    secs = pose_s + XF  # each clip overlaps the next by XF
    clips = [pose_clip(p, B / f"s{s['id']:02d}_{i}.mp4", secs if i < 4 else pose_s, i) for i, p in enumerate(pngs, 1)]
    fc, last = [], "[0]"
    for i in range(1, 4):
        fc.append(f"{last}[{i}]xfade=transition=fade:duration={XF}:offset={i * pose_s:.3f}[x{i}]"); last = f"[x{i}]"
    args = sum((["-i", str(c)] for c in clips), [])
    ff(*args, "-filter_complex", ";".join(fc) + f";{last}vignette=PI/6[v]", "-map", "[v]", "-t", str(length),
       "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", str(dest))
    return dest


def end_card():
    dest = B / "end.mp4"
    img = Image.new("RGB", (W, H), "black"); img.save(B / "end_bg.png")
    banner(STORY["title"].upper(), 110, B / "end_title.png", W, H, 0.42, path=SERIF, stroke=0)
    banner(STORY.get("cta_text", ""), 54, B / "end_cta.png", W, H, 0.62, stroke=0, fill="#cfcfcf")
    ff("-loop", "1", "-i", str(B / "end_bg.png"), "-loop", "1", "-i", str(B / "end_title.png"),
       "-loop", "1", "-i", str(B / "end_cta.png"), "-filter_complex",
       "[0][1]overlay[a];[a][2]overlay,fade=in:d=1,fade=out:st=" + str(END_S - 1.5) + ":d=1.5,format=yuv420p[v]",
       "-map", "[v]", "-t", str(END_S), "-r", str(FPS), "-c:v", "libx264", "-crf", "17", str(dest))
    return dest


def build(out, lo=1, hi=None):
    hi = hi or len(STORY["shots"])
    shots = [s for s in STORY["shots"] if lo <= s["id"] <= hi]
    L = layout(lo, hi)
    vids = [shot_clip(s, L[s["id"]]["len"]) for s in shots] + [end_card()]
    (B / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in vids))
    ff("-f", "concat", "-safe", "0", "-i", str(B / "list.txt"), "-c", "copy", str(B / "video.mp4"))
    total = total_len(L)
    # motion-graphic text: hook (0-3.2s), the two rehooks (shots 9 and 17), CTA over the last shot
    cards = [(kinetic(STORY.get("hook_text", "").upper(), B / "k_hook.mov", W, H, 0.8, 92, 3.2, FPS), 0)]
    for k, (sid, txt) in enumerate(zip((9, 17), STORY.get("rehook_texts", []))):
        if sid in L:
            cards.append((kinetic(txt.upper(), B / f"k_rehook{k}.mov", W, H, 0.8, 84, 3.4, FPS), L[sid]["start"] + 0.4))
    if hi == len(STORY["shots"]):
        cards.append((kinetic(STORY.get("cta_text", ""), B / "k_cta.mov", W, H, 0.82, 70, 5.6, FPS), L[hi]["start"] + 6))
    audio = mix(str(B / "mix.m4a"), lo, hi)
    args, fc, last = ["-i", str(B / "video.mp4")], [], "[0]"
    for i, (mov, t0) in enumerate(cards, 1):
        args += ["-itsoffset", f"{t0:.2f}", "-i", str(mov)]
        fc.append(f"{last}[{i}]overlay=eof_action=pass[o{i}]"); last = f"[o{i}]"
    args += ["-i", audio]
    ff(*args, "-filter_complex", ";".join(fc), "-map", last, "-map", f"{len(cards) + 1}:a", "-t", str(total),
       "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
       "-c:a", "copy", "-movflags", "+faststart", out)
    return out


if __name__ == "__main__":
    lo, hi = map(int, (sys.argv[2] if len(sys.argv) > 2 else f"1-{len(STORY['shots'])}").split("-"))
    print(build(sys.argv[1], lo, hi))
