"""Lines, per-shot ambience and the score for a world short (same ElevenLabs settings as audio.py)."""
import json, pathlib, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/workspace/ashlight/prod/anime-ashlight")
import audio as A
v = json.loads(pathlib.Path("voices.json").read_text())
jobs = []
for s in A.STORY["shots"]:
    i = s["id"]; line = s.get("line") or {}
    if line.get("text"):
        jobs.append(lambda s=s, i=i, line=line: A.line_tts(v, line, A.OUT / f"line{i:02d}.mp3", f"ws_line{i}"))
    jobs.append(lambda s=s, i=i: A.post("sound-generation?output_format=mp3_44100_192", A.OUT / f"sfx{i:02d}.mp3", f"ws_sfx{i}",
                text=f"Ambience only, no music: {s['sfx']}", duration_seconds=8, prompt_influence=0.5))
jobs.append(lambda: A.post("music?output_format=mp3_44100_192", A.OUT / "score.mp3", "ws_score",
            prompt=A.STORY["music"] + " Total length 70 seconds.", music_length_ms=70000, model_id="music_v1"))
with ThreadPoolExecutor(max_workers=5) as ex:
    for r in ex.map(lambda f: f(), jobs):
        print(r, flush=True)
