"""Render a world short with make_reels.py, plus the "From the world of AFTER THE HUM" label and an AI-generated line."""
import pathlib, sys
sys.path.insert(0, "/workspace/ashlight/prod/anime-ashlight")
import make_reels as M
from motion import kinetic
from textcards import banner

GAP = 0.15  # tighter than episode reels (0.35) for a 30-45 s short


def timeline(r):
    t, out = 0.0, []
    for i, sec in enumerate(r["sections"]):
        vo = M.RA / f"r{r['id']}_{i}.mp3"
        vo_len = M.dur(vo) + GAP if vo.exists() else 0
        shots = sec["shots"]
        lens = [max(1.2, sh["seconds"]) for sh in shots]
        for k, sh in enumerate(shots):
            line = M.A / f"line{sh['shot']:02d}.mp3"
            if sh.get("use_line") and line.exists():
                lens[k] = max(lens[k], M.dur(line) + 0.4)
        total = max(sum(lens), vo_len)
        lens = [l * total / sum(lens) for l in lens]
        segs, st = [], t
        for sh, l in zip(shots, lens):
            segs.append((sh["shot"], st, l, bool(sh.get("use_line")))); st += l
        out.append((t, total, sec, segs, vo if vo.exists() else None))
        t += total
    return out, t


def chunks(words, n=3):
    """Caption groups of up to n words that never run across a sentence end (n+1 if that completes it) (".", "?", "!");
    a comma also closes a group once it has 2+ words (ws02 review: no 'KIOSK, AND SHE')."""
    def ends(w):
        return w[0].rstrip('"\u201d').endswith((".", "?", "!"))
    out, cur = [], []
    for k, w in enumerate(words):
        cur.append(w)
        nxt = words[k + 1] if k + 1 < len(words) else None
        if ends(w) or (w[0].endswith(",") and len(cur) >= 2) or (len(cur) >= n and not (len(cur) == n and nxt and ends(nxt))):  # one more word may finish a sentence
            out.append(cur); cur = []
    return out + [cur] if cur else out


def captions(tl, total, work):
    """make_reels.captions with sentence-aware groups."""
    from PIL import Image
    import json
    W, H, FPS = M.W, M.H, M.FPS
    blank = work / "blank.png"; Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(blank)
    events, n = [], 0
    for st, _, _, _, vo in tl:
        if not vo:
            continue
        for group in chunks(json.loads(vo.with_suffix(".json").read_text())):
            text = " ".join(w for w, _, _ in group).upper()
            for j, (_, ws, we) in enumerate(group):
                end = group[j + 1][1] if j + 1 < len(group) else we + 0.15
                png = banner(text, 92, work / f"cap{n:04d}.png", W, H, 0.7, box=True, highlight=j); n += 1
                events.append((st + ws, st + end, png))
    for _, _, _, segs, _ in tl:
        for shot, s0, _, use_line in segs:
            line = M.A / f"line{shot:02d}.mp3"
            if not (use_line and line.exists()):
                continue
            words = next(x["line"]["text"] for x in M.STORY["shots"] if x["id"] == shot).upper().split()
            per = M.dur(line) / max(1, len(words))
            k = 0
            for g in chunks([(w, 0, 0) for w in words], 4):
                png = banner(" ".join(w for w, _, _ in g), 92, work / f"cap{n:04d}.png", W, H, 0.7, fill="#9FD8FF", box=True); n += 1
                events.append((s0 + 0.2 + k * per, s0 + 0.2 + (k + len(g)) * per, png)); k += len(g)
    events.sort(key=lambda e: e[0])
    lines, t = [], 0.0
    for s, e, png in events:
        if s > t + 0.02:
            lines += [f"file '{blank.name}'", f"duration {s - t:.3f}"]
        lines += [f"file '{png.name}'", f"duration {max(0.04, e - max(s, t)):.3f}"]
        t = max(t, e)
    lines += [f"file '{blank.name}'", f"duration {max(0.1, total - t):.3f}", f"file '{blank.name}'"]
    (work / "caps.txt").write_text("\n".join(lines) + "\n")
    M.ff("-f", "concat", "-safe", "0", "-i", str(work / "caps.txt"), "-vf", f"fps={FPS},format=rgba",
         "-c:v", "png", str(work / "caps.mov"))
    return work / "caps.mov"


def build(r, out):
    W, H, FPS = M.W, M.H, M.FPS
    work = M.OUT / f"work{r['id']}"; work.mkdir(exist_ok=True)
    tl, total = timeline(r)
    # no low caption while a card already shows the same words: the spoken label (section 0) and the CTA
    norm = lambda x: "".join(ch for ch in x.upper() if ch.isalnum() or ch == " ").split()
    same_as_card = lambda sec: norm(sec["vo"]) == norm(r["hook_text"])  # spoken hook already on the hook card
    caps_tl = [(st, ln, sec, segs, None if (i == 0 or sec["part"] == "cta" or same_as_card(sec)) else vo) for i, (st, ln, sec, segs, vo) in enumerate(tl)]
    v, caps, a = M.video(r, tl, work), captions(caps_tl, total, work), M.audio(r, tl, total, work)
    hook_end = next((st for st, _, sec, _, _ in tl if sec["part"] == "lock_in"), 3.2)  # hook card stays up through the spoken hook
    label = kinetic("FROM THE WORLD OF AFTER THE HUM", work / "k_label.mov", W, H, 0.085, 42, 3.2, FPS, stagger=0.05, box=True)
    hook = kinetic(r["hook_text"].upper(), work / "k_hook.mov", W, H, 0.2, 100, hook_end, FPS)
    cta_start = next((st for st, _, sec, _, _ in tl if sec["part"] == "cta"), total - 3)
    cta = kinetic(r["cta_text"].upper(), work / "k_cta.mov", W, H, 0.2, 84, total - cta_start + 0.5, FPS)
    ai = banner("Voices and visuals are AI-generated", 38, work / "ai.png", W, H, 0.31, stroke=4)
    M.ff("-i", str(v), "-i", str(caps), "-i", str(label), "-i", str(hook), "-itsoffset", f"{cta_start:.2f}", "-i", str(cta),
         "-loop", "1", "-i", str(ai), "-i", str(a),
         "-filter_complex",
         f"[0][1]overlay[a];[a][2]overlay=eof_action=pass[b];[b][3]overlay=eof_action=pass[c];"
         f"[c][4]overlay=eof_action=pass[d];[d][5]overlay=enable='gte(t,{cta_start + 0.6:.2f})':shortest=1[v]",
         "-map", "[v]", "-map", "6:a", "-t", f"{total:.2f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(out))
    print(f"{total:.1f}s -> {out}", flush=True)


if __name__ == "__main__":
    build(M.REELS[0], pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "draft.mp4"))
