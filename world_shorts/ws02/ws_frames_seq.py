"""Vertical frames for a world short, ONE Qwen call at a time (the daily episode run has Qwen priority).
Usage: python3 ws_frames_seq.py first|poses [ids...]
Shots listed in REUSE only draw the distinct poses and copy the rest, so a recurring object (phone tray, wall,
watch) stays in exactly the same position across every pose."""
import os, shutil, sys
sys.path.insert(0, "/workspace/ashlight/prod/anime-ashlight")
os.environ["VERTICAL"] = "1"
import qwen_frames as Q
REUSE = {2: [1, 2, 1, 2], 5: [1, 2, 1, 2], 9: [1, 2, 1, 2]}   # pose k uses drawn pose REUSE[k]
NO_PEOPLE = {2, 5, 9}
mode, ids = sys.argv[1], [int(x) for x in sys.argv[2:]]
Q.FRAMES.mkdir(exist_ok=True)
for s in Q.STORY["shots"]:
    if ids and s["id"] not in ids: continue
    first = Q.FRAMES / f"s{s['id']:02d}_1.png"
    if not first.exists():
        Q.shot({**s, "poses": s["poses"][:1]}); print("first", s["id"], flush=True)
    if mode != "poses": continue
    plan = REUSE.get(s["id"], [1, 2, 3, 4])
    for k, src in enumerate(plan, 1):
        out = Q.FRAMES / f"s{s['id']:02d}_{k}.png"
        if out.exists(): continue
        if src != k:
            shutil.copy(Q.FRAMES / f"s{s['id']:02d}_{src}.png", out); continue
        if s["id"] in NO_PEOPLE:
            text = (f"Edit this image: keep the exact same scene, camera framing, background, object positions, lighting and art style. "
                    f"There are no people in this image: do not add any person, face, figure or silhouette. "
                    f"Change only this detail: {s['poses'][k-1]}. No captions, no subtitles, no watermark.")
        else:
            text = (f"Edit this image: keep the exact same scene, camera framing, background, lighting, art style and "
                    f"the same characters with identical faces, hair and clothes. Change only their pose and "
                    f"expression to: {s['poses'][k-1]}. {Q.RULES}")
        Q.call([first], text, Q.SIZE, out, f"ws02_s{s['id']}_{k}"); Q.fit(out, Q.OUT_WH); print("pose", s["id"], k, flush=True)
print("done")
