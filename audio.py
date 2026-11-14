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
# 2026-11-14: viewers said "the male voice" sounded like a bad mic. The designed Jun/Lio voices were thin and
# band-limited (Lio rolled off near 4 kHz) with an audible noise floor, and Jun (a 17-year-old girl in series.json)
# had been designed with a low, male-sounding voice. ElevenLabs refuses to design voices for under-18 characters, so
# both moved to clean, full-band premade voices in voices.json (Jun: "Jessica", young bright American female;
# Lio: "Liam", young American male). If a voice ever fails, the line is retried with the previous voice below.
PREVIOUS = {"jun": "CxmVLC0zdI88j2zfLOeX", "lio": "1CuQEihJU6LyGS2focVP", "soren": "Ag1rBrmqwqZYr2m4S6H2"}
# 2026-11-14 (Ep3): the designed Soren voice had a room/reverb baked into every take (pauses sat only ~37 dB under
# the peaks, vs ~76 dB for premade voices); viewers heard it as "an echo voice". Designed voices are now used for the
# narrator only. Every on-screen character gets a clean premade voice from this pool (first unused one that fits the
# character's gender/age in series.json); Soren = "Brian" (deep, calm, close-mic).
PREMADE = {
    "male": ["nPczCjzI2devNBz1zQrb",    # Brian: deep, calm, resonant (Soren)
             "TX3LPaxmHKxFdv7VOQHJ",    # Liam: young, energetic (Lio)
             "iP95p4xoKVk53GoZ742B",    # Chris: down-to-earth
             "CwhRBWXzGAHq8TQ4Fs17",    # Roger: laid-back
             "bIHbv24MWmeRgasZH58o",    # Will: young, relaxed
             "pqHfZKP75CvOlQylNhV4"],   # Bill: older, crisp
    "female": ["cgSgspJ2msm6clMCkdW9",  # Jessica: young, bright (Jun)
               "EXAVITQu4vr4xnSDxMaL",  # Sarah
               "XrExE9yKIg1WjnnlVkGX",  # Matilda
               "Xb7hH8MSUJpSbSDYk0k2",  # Alice
               "pFZP5JQG7iQjIQuC4Bku"],  # Lily
}
ROOM_MAX_DB = -50  # a clean close-mic clip's quiet frames sit below peak-50 dB; above that it carries room/reverb


def room_db(path):
    """How far the quiet 10% of a voice clip sits below its peak (dB, negative). Near -37 = roomy/echoey take."""
    import subprocess, numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    fr = x[:len(x) // 160 * 160].reshape(-1, 160)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)
    return float(np.percentile(db, 10) - db.max())


def premade_for(c, used):
    tags = (c.get("tags", "") + " " + c.get("voice", "")).lower()
    gender = "female" if any(w in tags for w in ("woman", "girl", "female", "feminine")) else "male"
    pool = PREMADE[gender]
    return next((x for x in pool if x not in used), pool[0])
# appended to every designed voice: without it the design model often returns lo-fi, "phone mic" audio
QUALITY = " Perfect studio audio quality: crisp, clear, full-bandwidth close-mic recording, no background noise."


def log(what, r):
    with open("costs.jsonl", "a") as f:
        f.write(json.dumps({"service": "elevenlabs", "what": what,
                            "character_cost": r.headers.get("character-cost")}) + "\n")


def design_voice(name, description, sample):
    """Create a voice from a text description (for characters no stock voice fits)."""
    r = requests.post(f"{API}/text-to-voice/design", headers=H, timeout=300, json={
        "voice_description": description[:1000 - len(QUALITY)] + QUALITY, "text": sample,
        "model_id": "eleven_multilingual_ttv_v2"})
    r.raise_for_status(); log(f"design-{name}", r)
    gid = r.json()["previews"][0]["generated_voice_id"]
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
        if key != "narrator":  # characters: clean premade voice, never a designed one (see PREMADE)
            c = next(c for c in STORY["characters"] if c["id"] == key)
            v[key] = premade_for(c, set(v.values()))
            VOICES_FILE.write_text(json.dumps(v, indent=2))
            continue
        sample = (sample + " " + STORY["logline"])[:500]  # the design endpoint wants 100+ characters of sample text
        try:
            v[key] = design_voice(name, desc[:1000], sample)
        except requests.HTTPError as e:
            print(f"voice design refused for {name} ({e.response.status_code}: {e.response.text[:200]}); using a stock voice", flush=True)
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


def line_tts(v, line, dest, what):
    """A character line; if the character's voice errors, retry once with their previous voice."""
    res = tts(v[line["character"]], line["text"], dest, what, stability=0.55, style=0.15)
    if dest.exists() and room_db(dest) > ROOM_MAX_DB:  # roomy/echoey take: say so loudly, the mix still runs
        print(f"WARNING {what}: voice {v[line['character']]} sounds roomy ({room_db(dest):.0f} dB floor); "
              f"switch {line['character']} to a premade voice in voices.json", flush=True)
    old = PREVIOUS.get(line["character"])
    if "ERROR" in res and old and old != v[line["character"]]:
        res = f"{res} | retry with previous voice: " + tts(old, line["text"], dest, what)
    return res


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
            jobs.append(lambda s=s, i=i, line=line: line_tts(v, line, OUT / f"line{i:02d}.mp3", f"line{i}"))
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
