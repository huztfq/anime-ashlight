"""Poses 2-4 for shots with no characters: edit pose 1 with a no-people prompt (the stock edit prompt invites figures)."""
import sys, json
sys.path.insert(0, "/workspace/ashlight/prod/anime-ashlight")
import os; os.environ["VERTICAL"] = "1"
import qwen_frames as Q
from concurrent.futures import ThreadPoolExecutor
ids = [int(x) for x in sys.argv[1:]]
for s in Q.STORY["shots"]:
    if s["id"] in ids and not (Q.FRAMES / f"s{s['id']:02d}_1.png").exists():
        Q.shot({**s, "poses": s["poses"][:1]})
def pose(args):
    s, i = args
    out = Q.FRAMES / f"s{s['id']:02d}_{i+1}.png"
    if out.exists(): return
    text = (f"Edit this image: keep the exact same scene, camera framing, background, lighting and art style. "
            f"There are no people in this image: do not add any person, face, figure or silhouette. "
            f"Change only this detail: {s['poses'][i]}. No captions, no subtitles, no watermark.")
    Q.call([Q.FRAMES / f"s{s['id']:02d}_1.png"], text, Q.SIZE, out, f"ws_fix_s{s['id']}_{i+1}"); Q.fit(out, Q.OUT_WH)
jobs = [(s, i) for s in Q.STORY["shots"] if s["id"] in ids for i in range(1, 4)]
with ThreadPoolExecutor(max_workers=2) as ex: list(ex.map(pose, jobs))
print("done")
