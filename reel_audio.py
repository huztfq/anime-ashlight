"""Narrator VO for every reel section, with word timings for burned-in captions. Writes reels_audio/r{N}_{i}.mp3 + .json"""
import base64, json, pathlib
from concurrent.futures import ThreadPoolExecutor
import requests
from audio import API, H, log

OUT = pathlib.Path("reels_audio"); OUT.mkdir(exist_ok=True)
REELS = json.loads(pathlib.Path("reels.json").read_text())["reels"]
NARRATOR = json.loads(pathlib.Path("voices.json").read_text())["narrator"]


def words(al):
    """Collapse ElevenLabs character alignment into [(word, start, end)]."""
    out, cur, st = [], "", None
    for ch, s, e in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        if ch.isspace():
            if cur:
                out.append((cur, st, end))
            cur, st = "", None
            continue
        if st is None:
            st = s
        cur += ch; end = e
    if cur:
        out.append((cur, st, end))
    return out


def vo(r, i, text):
    base = OUT / f"r{r}_{i}"
    if base.with_suffix(".json").exists() or not text:
        return f"r{r}_{i}: skip"
    resp = requests.post(f"{API}/text-to-speech/{NARRATOR}/with-timestamps?output_format=mp3_44100_192", headers=H,
                         timeout=300, json={"text": text, "model_id": "eleven_multilingual_v2",
                                            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.35}})
    resp.raise_for_status(); log(f"reel{r}_{i}", resp)
    j = resp.json()
    base.with_suffix(".mp3").write_bytes(base64.b64decode(j["audio_base64"]))
    base.with_suffix(".json").write_text(json.dumps(words(j["alignment"])))
    return f"r{r}_{i}: done"


if __name__ == "__main__":
    jobs = [(r["id"], i, sec["vo"]) for r in REELS for i, sec in enumerate(r["sections"])]
    with ThreadPoolExecutor(max_workers=5) as ex:
        for res in ex.map(lambda a: vo(*a), jobs):
            print(res, flush=True)
