"""Narrator VO per section with word timings (reel_audio.py settings, a touch faster for short-form pacing)."""
import base64, json, pathlib, sys, requests
sys.path.insert(0, "/workspace/ashlight/prod/anime-ashlight")
from audio import API, H, log
from reel_audio import words, NARRATOR, REELS, OUT
SPEED = 1.12
for r in REELS:
    for i, sec in enumerate(r["sections"]):
        if not sec["vo"]: continue
        base = OUT / f"r{r['id']}_{i}"
        if base.with_suffix(".json").exists(): continue
        resp = requests.post(f"{API}/text-to-speech/{NARRATOR}/with-timestamps?output_format=mp3_44100_192", headers=H, timeout=300,
            json={"text": sec["vo"], "model_id": "eleven_multilingual_v2",
                  "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.4, "speed": SPEED}})
        resp.raise_for_status(); log(f"ws_vo{i}", resp); j = resp.json()
        base.with_suffix(".mp3").write_bytes(base64.b64decode(j["audio_base64"]))
        base.with_suffix(".json").write_text(json.dumps(words(j["alignment"])))
        print(i, "done", flush=True)
