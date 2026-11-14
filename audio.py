"""ElevenLabs: narrator VO, character lines, 12s SFX per shot, and the score. Writes into audio/."""
import base64, json, os, pathlib
from concurrent.futures import ThreadPoolExecutor
import requests

for line in pathlib.Path(".env").read_text().splitlines():
    k, _, v = line.partition("=")
    os.environ[k] = v

API = "https://api.elevenlabs.io/v1"
H = {"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}
OUT = pathlib.Path("audio"); OUT.mkdir(exist_ok=True)
STORY = json.loads(pathlib.Path("story.json").read_text())
TITLE_S, SHOT_S, END_S = 6, 12, 9
VOICES_FILE = pathlib.Path("voices.json")
# narrator tonality per shot (stability, style): lower stability + more style = more tension in the read
TONE = {"calm": (0.6, 0.2), "whisper": (0.55, 0.3), "tense": (0.45, 0.4), "urgent": (0.38, 0.5)}
# stock voices to fall back on when designing one is refused (e.g. child voices)
FALLBACK = {"narrator": "pFZP5JQG7iQjIQuC4Bku", "female": "EXAVITQu4vr4xnSDxMaL", "male": "JBFqnCBsd6RMkjVDRZzb"}


def log(what, r):
    with open("costs.jsonl", "a") as f:
        f.write(json.dumps({"service": "elevenlabs", "what": what,
                            "character_cost": r.headers.get("character-cost")}) + "\n")


DRY = (" Recorded dry in a treated studio on a close microphone: no reverb, no echo, no room sound, no background "
       "noise.")
MAX_FLOOR_DB = -48  # quietest 5% of the audio vs its peak; above this the voice carries audible room echo


def noise_floor(mp3_bytes):
    """dB of the quietest 5% of 10 ms frames relative to the peak. Dry voices sit near -55; reverb lifts it."""
    import array, math, subprocess
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         input=mp3_bytes, capture_output=True, check=True).stdout
    a, fr = array.array("h", raw), 160
    db = sorted(10 * math.log10(sum(x * x for x in a[i:i + fr]) / fr + 1e-9) for i in range(0, len(a) - fr, fr))
    return db[len(db) // 20] - db[-1]


def design_voice(name, description, sample):
    """Create a voice from a text description (for characters no stock voice fits). Of the previews ElevenLabs
    returns, keep the driest one (no baked-in reverb); refuse if every preview still has room echo."""
    description = (description.rstrip() + DRY)[:1000]
    best = None
    for attempt in range(2):
        r = requests.post(f"{API}/text-to-voice/design", headers=H, timeout=300, json={
            "voice_description": description, "text": sample, "model_id": "eleven_multilingual_ttv_v2"})
        r.raise_for_status(); log(f"design-{name}", r)
        for p in r.json()["previews"]:
            fl = noise_floor(base64.b64decode(p["audio_base_64"]))
            print(f"voice {name}: preview floor {fl:.0f} dB", flush=True)
            if best is None or fl < best[0]:
                best = (fl, p["generated_voice_id"])
        if best[0] <= MAX_FLOOR_DB:
            break
    if best[0] > MAX_FLOOR_DB:
        raise RuntimeError(f"voice design for {name}: every preview has room echo (best {best[0]:.0f} dB)")
    gid = best[1]
    r = requests.post(f"{API}/text-to-voice", headers=H, timeout=120, json={
        "voice_name": f"{STORY['title']} - {name}", "voice_description": description, "generated_voice_id": gid})
    r.raise_for_status()
    return r.json()["voice_id"]


def voices():
    """One designed voice per speaker, from the voice descriptions in story.json; cached in voices.json."""
    v = json.loads(VOICES_FILE.read_text()) if VOICES_FILE.exists() else {}
    speakers = [("narrator", "Narrator", STORY["narrator_voice"], next(s["narration"] for s in STORY["shots"] if s["narration"]))]
    for c in STORY["characters"]:
        if c["id"] == STORY.get("narrator_character"):
            continue
        sample = " ".join(s["line"]["text"] for s in STORY["shots"] if (s.get("line") or {}).get("character") == c["id"])
        speakers.append((c["id"], c["name"], c["voice"], sample))
    for key, name, desc, sample in speakers:
        if key in v:
            continue
        sample = (sample + " " + STORY["logline"])[:500]  # the design endpoint wants 100+ characters of sample text
        try:
            v[key] = design_voice(name, desc[:1000], sample)
        except (requests.HTTPError, RuntimeError) as e:
            why = f"{e.response.status_code}: {e.response.text[:200]}" if isinstance(e, requests.HTTPError) else str(e)
            print(f"voice design failed for {name} ({why}); using a stock voice", flush=True)
            v[key] = FALLBACK["narrator" if key == "narrator" else "female" if "girl" in desc.lower() or "woman" in desc.lower() else "male"]
        VOICES_FILE.write_text(json.dumps(v, indent=2))
    if STORY.get("narrator_character"):  # a first-person narrator speaks her own lines in the same voice
        v[STORY["narrator_character"]] = v["narrator"]
    return v


def post(path, dest, what, **body):
    if dest.exists():
        return f"{what}: exists"
    r = requests.post(f"{API}/{path}", headers=H, json=body, timeout=900)
    if r.status_code >= 400:
        return f"{what}: ERROR {r.status_code} {r.text[:300]}"
    dest.write_bytes(r.content); log(what, r)
    return f"{what}: done"


def tts(voice, text, dest, what, stability=0.5, style=0.3):
    return post(f"text-to-speech/{voice}?output_format=mp3_44100_192", dest, what, text=text,
                model_id="eleven_multilingual_v2",
                voice_settings={"stability": stability, "similarity_boost": 0.8, "style": style})


if __name__ == "__main__":
    v = voices()
    jobs = []
    for s in STORY["shots"]:
        i = s["id"]
        if s["narration"]:
            stab, style = TONE.get(s.get("delivery"), TONE["calm"])
            jobs.append(lambda s=s, i=i, a=stab, b=style: tts(v["narrator"], s["narration"], OUT / f"vo{i:02d}.mp3", f"vo{i}", a, b))
        line = s.get("line") or {}
        if line.get("text") and line.get("character") in v:
            jobs.append(lambda s=s, i=i, line=line: tts(v[line["character"]], line["text"], OUT / f"line{i:02d}.mp3", f"line{i}"))
        jobs.append(lambda s=s, i=i: post("sound-generation?output_format=mp3_44100_192", OUT / f"sfx{i:02d}.mp3",
                                          f"sfx{i}", text=f"Ambience only, no music: {s['sfx']}",
                                          duration_seconds=SHOT_S, prompt_influence=0.5))
    total = TITLE_S + SHOT_S * len(STORY["shots"]) + END_S
    jobs.append(lambda: post("music?output_format=mp3_44100_192", OUT / "score.mp3", "score",
                             prompt=f"{STORY['music']} Total length {total} seconds: a quiet {TITLE_S}-second opening "
                                    f"under a title card and a soft {END_S}-second ending under the end card. "
                                    "Instrumental only, no vocals.",
                             music_length_ms=min(total, 300) * 1000, model_id="music_v1"))
    with ThreadPoolExecutor(max_workers=5) as ex:
        for res in ex.map(lambda f: f(), jobs):
            print(res, flush=True)
