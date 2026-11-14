"""Build the 9:16 reels from reels.json: vertical pose frames with quick cuts, narrator VO, reused character
lines, word-by-word captions, on-screen hook (0-3s) and CTA, ducked score + shot ambience.
Usage: make_reels.py [reel ids...]"""
import json, pathlib, re, subprocess, sys
from PIL import Image
from mix import dur, SCORE_OFFSET, SHOT_S, voice_fx
from textcards import banner
from motion import kinetic


WEAK = {"THE", "A", "AN", "AND", "OR", "TO", "OF", "FOR", "WITH", "AT", "FROM", "IN", "ON",
        "BY", "AS", "BUT", "THEN", "THAN", "THAT", "THIS", "ITS", "OUR", "YOUR", "MY",
        "BEFORE", "AFTER", "INTO", "OVER", "UNDER"}


def group_words(words):
    """Group caption words into 2-5 word beats, breaking on punctuation instead of mid-phrase."""
    items = [w if isinstance(w, (list, tuple)) else (w, 0, 0) for w in words]
    n, i, groups = len(items), 0, []

    def core(tok):
        return re.sub(r"[^A-Za-z0-9']+$", "", tok).upper()

    def punct(tok):
        return bool(re.search(r"[.?!;:—]$", tok)) or tok.endswith("...")

    while i < n:
        best, found = min(i + 3, n), False
        for j in range(i + 1, min(i + 6, n + 1)):
            tok = items[j - 1][0]
            if punct(tok) or (tok.endswith(",") and j - i >= 2):
                best, found = j, True
                break
        if not found:
            for length in (4, 3, 5, 2):
                j = i + length
                if j <= n and core(items[j - 1][0]) not in WEAK:
                    best = j
                    break
            else:
                best = min(i + 3, n)
        if n - best == 1 and best - i < 5:
            best = n
        groups.append(items[i:best])
        i = best
    return groups


W, H, FPS = 1080, 1920, 30
STORY = json.loads(pathlib.Path("story.json").read_text())
REELS = json.loads(pathlib.Path("reels.json").read_text())["reels"]
RA, A, FV = pathlib.Path("reels_audio"), pathlib.Path("audio"), pathlib.Path("frames_v")
KIT = pathlib.Path("sfx_kit")
LINE_IN = 0.35  # a reused character line starts this long into its shot, and its shot runs this long after it, so
                # it never touches the narrator (2026-11-14 lesson: never overlap two voices; min gap 0.25 s)
OUT = pathlib.Path("reels"); OUT.mkdir(exist_ok=True)


def ff(*a):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)


def timeline(r):
    """Resolve each section to absolute times: list of (start, length, section, [(shot, start, length, use_line)])."""
    t, out = 0.0, []
    for i, sec in enumerate(r["sections"]):
        vo = RA / f"r{r['id']}_{i}.mp3"
        vo_len = dur(vo) + 0.35 if vo.exists() else 0
        shots = sec["shots"] or [{"shot": 1, "seconds": 2, "use_line": False}]
        lens = [max(1.2, sh["seconds"]) for sh in shots]
        for k, sh in enumerate(shots):  # a reused character line needs its shot long enough to finish
            line = A / f"line{sh['shot']:02d}.mp3"
            if sh.get("use_line") and line.exists():
                if vo.exists():  # a narrated section can't also carry a character line: they would overlap
                    print(f"reel {r['id']} section {i}: dropping line{sh['shot']:02d} (section has narration)", flush=True)
                    sh["use_line"] = False
                    continue
                lens[k] = max(lens[k], dur(voice_fx(line, "dialogue")) + 2 * LINE_IN)
        total = max(sum(lens), vo_len)
        lens = [l * total / sum(lens) for l in lens]
        segs, st = [], t
        for sh, l in zip(shots, lens):
            segs.append((sh["shot"], st, l, bool(sh.get("use_line")))); st += l
        out.append((t, total, sec, segs, vo if vo.exists() else None))
        t += total
    return out, t


def pose_clip(png, dest, secs, push):
    n = max(2, round(secs * FPS))
    z = f"1+0.05*on/{n}" if push else f"1.05-0.05*on/{n}"
    if png.parent.name == "frames":
        # two-character shot: widescreen frame centered over a blurred, zoomed copy of itself
        ff("-loop", "1", "-i", str(png), "-filter_complex",
           f"[0]split[a][b];[a]scale=-2:{H},crop={W}:{H},boxblur=30:2,eq=brightness=-0.08[bg];"
           f"[b]scale=4320:-2,zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={n}:s={W}x{round(W*768/1344)//2*2}:fps={FPS}[fg];"
           f"[bg]fps={FPS}[bgf];[bgf][fg]overlay=(W-w)/2:(H-h)/2-80:shortest=1",
           "-frames:v", str(n), "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(dest))
        return dest
    ff("-loop", "1", "-i", str(png), "-vf",
       f"scale=-2:7680,crop=4320:7680,zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={n}:s={W}x{H}:fps={FPS}",
       "-frames:v", str(n), "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(dest))
    return dest


def video(r, tl, work):
    clips, k = [], 0
    for _, _, _, segs, _ in tl:
        for shot, _, l, _ in segs:
            # a true 9:16 frame when one was rendered, else the 16:9 frame over a blurred copy (see pose_clip)
            src = FV if (FV / f"s{shot:02d}_1.png").exists() else pathlib.Path("frames")
            poses = [src / f"s{shot:02d}_{i}.png" for i in range(1, 5)]
            poses = [p for p in poses if p.exists()] or [src / f"s{shot:02d}_1.png"]
            n = max(1, min(len(poses), round(l / 1.3)))  # ~1.3s per drawing: reads as limited animation
            for j in range(n):
                clips.append(pose_clip(poses[j], work / f"c{k:03d}.mp4", l / n, k % 2 == 0)); k += 1
    (work / "list.txt").write_text("".join(f"file '{c.name}'\n" for c in clips))
    ff("-f", "concat", "-safe", "0", "-i", str(work / "list.txt"), "-c", "copy", str(work / "video.mp4"))
    return work / "video.mp4"


def captions(tl, total, work):
    """Word-by-word captions as an alpha video: groups of up to 3 words, the spoken word in yellow."""
    blank = work / "blank.png"; Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(blank)
    events = []  # (start, end, png)
    n = 0
    for st, _, _, _, vo in tl:
        if not vo:
            continue
        words = json.loads(vo.with_suffix(".json").read_text())
        for group in group_words(words):
            text = " ".join(w for w, _, _ in group).upper()
            for j, (_, ws, we) in enumerate(group):
                end = group[j + 1][1] if j + 1 < len(group) else we + 0.15
                png = banner(text, 92, work / f"cap{n:04d}.png", W, H, 0.82, highlight=j); n += 1
                events.append((st + ws, st + end, png))
    for _, _, _, segs, _ in tl:  # reused character lines get captions too, in blue, timed evenly by word
        for shot, s0, _, use_line in segs:
            line = A / f"line{shot:02d}.mp3"
            if not (use_line and line.exists()):
                continue
            text = next(x["line"]["text"] for x in STORY["shots"] if x["id"] == shot).upper().split()
            per = dur(line) / max(1, len(text))
            offset = 0
            for group in group_words(text):
                png = banner(" ".join(w if isinstance(w, str) else w[0] for w in group), 92, work / f"cap{n:04d}.png", W, H, 0.82, fill="#9FD8FF"); n += 1
                events.append((s0 + LINE_IN + offset * per, s0 + LINE_IN + (offset + len(group)) * per, png))
                offset += len(group)
    events.sort(key=lambda e: e[0])
    lines, t = [], 0.0
    for s, e, png in events:
        if s > t + 0.02:
            lines += [f"file '{blank.name}'", f"duration {s - t:.3f}"]
        lines += [f"file '{png.name}'", f"duration {max(0.04, e - max(s, t)):.3f}"]
        t = max(t, e)
    lines += [f"file '{blank.name}'", f"duration {max(0.1, total - t):.3f}", f"file '{blank.name}'"]
    (work / "caps.txt").write_text("\n".join(lines) + "\n")
    ff("-f", "concat", "-safe", "0", "-i", str(work / "caps.txt"), "-vf", f"fps={FPS},format=rgba",
       "-c:v", "png", str(work / "caps.mov"))
    return work / "caps.mov"


def audio(r, tl, total, work):
    ins, parts, voice, amb = [], [], [], []

    def add(path, start, label, extra=""):
        ins.extend(["-i", str(path)]); ms = int(start * 1000)
        parts.append(f"[{len(ins)//2 - 1}]{extra}adelay={ms}|{ms}[{label}]")

    for i, (st, _, _, segs, vo) in enumerate(tl):
        if vo:
            add(voice_fx(vo, "narration"), st, f"v{i}"); voice.append(f"[v{i}]")
        for k, (shot, s0, l, use_line) in enumerate(segs):
            add(A / f"sfx{shot:02d}.mp3", s0, f"a{i}_{k}", f"atrim=0:{l},afade=in:d=0.15,afade=out:st={max(0, l-0.2)}:d=0.2,")
            amb.append(f"[a{i}_{k}]")
            line = A / f"line{shot:02d}.mp3"
            if use_line and line.exists():
                add(voice_fx(line, "dialogue"), s0 + LINE_IN, f"l{i}_{k}"); voice.append(f"[l{i}_{k}]")
    # sound design on the exact frame: boom under the hook, whoosh on every cut, riser into each rehook, hit on rehooks + CTA
    fx = []
    def kit(name, t, vol):
        if t >= 0 and (KIT / f"{name}.mp3").exists():
            add(KIT / f"{name}.mp3", t, f"k{len(fx)}", f"volume={vol},"); fx.append(f"[k{len(fx)}]")
    kit("boom", 0, 0.9)
    for st, _, sec, segs, _ in tl:
        for shot, s0, _, _ in segs:
            if s0 > 0.1:
                kit("whoosh", s0 - 0.2, 0.35)
        if sec["part"].startswith("rehook") or sec["part"] == "cta":
            kit("riser", st - 2.5, 0.5); kit("hit", st, 0.8)
    # score: start where the reel's first body shot sits in the film, so the mood roughly matches
    body = next((segs[0][0] for _, _, sec, segs, _ in tl if sec["part"].startswith("body")), 1)
    start = min(SCORE_OFFSET + SHOT_S * (body - 1), dur(A / "score.mp3") - total - 1)
    ins += ["-i", str(A / "score.mp3")]
    m = len(ins) // 2 - 1
    fc = ";".join(parts + [
        f"[{m}]atrim={start}:{start + total},asetpts=PTS-STARTPTS,volume=0.7,afade=in:d=0.3,afade=out:st={total-1.5}:d=1.5[mus]",
        f"{''.join(amb)}amix=inputs={len(amb)}:normalize=0,volume=0.3[amb]",
        f"{''.join(voice)}amix=inputs={len(voice)}:normalize=0,apad,atrim=0:{total},volume=1.4,asplit[vo][key]",
        "[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=30:release=400[duck]",
        f"{''.join(fx)}amix=inputs={len(fx)}:normalize=0[fx]",
        "[duck][amb][vo][fx]amix=inputs=4:normalize=0,alimiter=limit=0.95[out]"])
    ff(*ins, "-filter_complex", fc, "-map", "[out]", "-t", str(total), "-c:a", "aac", "-b:a", "192k", str(work / "mix.m4a"))
    return work / "mix.m4a"


def speech_spans(tl):
    """(start, end, who) of every voice in the reel, sorted."""
    sp = []
    for st, _, _, segs, vo in tl:
        if vo:
            sp.append((st, st + dur(voice_fx(vo, "narration")), "narrator"))
        for shot, s0, _, use_line in segs:
            line = A / f"line{shot:02d}.mp3"
            if use_line and line.exists():
                sp.append((s0 + LINE_IN, s0 + LINE_IN + dur(voice_fx(line, "dialogue")), f"line{shot:02d}"))
    return sorted(sp)


def build(r):
    work = OUT / f"work{r['id']}"; work.mkdir(exist_ok=True)
    tl, total = timeline(r)
    sp = speech_spans(tl)
    gaps = [(b[0] - a[1], a[2], b[2]) for a, b in zip(sp, sp[1:]) if a[2] != b[2]]
    bad = [g for g in gaps if g[0] < 0.25]
    if bad:  # never ship two speakers on top of each other
        raise SystemExit(f"reel {r['id']}: voices too close/overlapping: {bad}")
    v, caps, a = video(r, tl, work), captions(tl, total, work), audio(r, tl, total, work)
    hook_size, hook_y = (76, 0.075) if len(r["hook_text"].split()) >= 4 else (88, 0.09)
    hook = kinetic(r["hook_text"].upper(), work / "k_hook.mov", W, H, hook_y, hook_size, 3.0, FPS)
    cta_start = next((st for st, _, sec, _, _ in tl if sec["part"] == "cta"), total - 3)
    cta = kinetic(r["cta_text"].upper(), work / "k_cta.mov", W, H, 0.56, 76, total - cta_start + 0.5, FPS)
    out = OUT / f"reel{r['id']}.mp4"
    ff("-i", str(v), "-i", str(caps), "-i", str(hook), "-itsoffset", f"{cta_start:.2f}", "-i", str(cta), "-i", str(a),
       "-filter_complex", "[0][1]overlay[a];[a][2]overlay=eof_action=pass[b];[b][3]overlay=eof_action=pass[v]",
       "-map", "[v]", "-map", "4:a", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
       "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(out))
    print(f"reel {r['id']}: {total:.1f}s -> {out}", flush=True)
    return out


def shots_needed():
    return sorted({sh["shot"] for r in REELS for sec in r["sections"] for sh in sec["shots"]})


if __name__ == "__main__":
    if sys.argv[1:] == ["shots"]:
        print(",".join(map(str, shots_needed())))
    else:
        ids = set(map(int, sys.argv[1:])) or {r["id"] for r in REELS}
        for r in REELS:
            if r["id"] in ids:
                build(r)
