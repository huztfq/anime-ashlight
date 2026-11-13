"""Narrator voice and music-style samples to pick from. Writes samples/voice_*.mp3 and samples/music_*.mp3."""
import base64, json, pathlib
from concurrent.futures import ThreadPoolExecutor
import requests
from audio import API, H, log

OUT = pathlib.Path("samples"); OUT.mkdir(exist_ok=True)
LINE = ("At 7:17, every phone in Meridian screamed. It lasted three seconds. By lunch, the birds were gone. "
        "By dark, a dead woman would say my name.")

DESIGNS = {  # name -> description; each design call returns several previews, the first two are kept
    "husky": "A young woman in her mid-twenties narrating a dark survival story. Low, slightly husky, calm and tired, "
             "speaking close to the microphone like a late-night confession. American accent, natural, never theatrical.",
    "cool": "A young woman in her mid-twenties narrating a tense thriller. Clear, cool and controlled voice with quiet "
            "intensity, measured pace and crisp delivery. Neutral American accent, cinematic but restrained.",
}
STOCK = {"lily": "pFZP5JQG7iQjIQuC4Bku", "sarah": "EXAVITQu4vr4xnSDxMaL"}
MUSIC = {
    "1_dark_ambient": "Dark ambient survival score: deep low drones, distant metallic textures, faint rain, almost no "
                      "melody, slow and heavy tension that sits quietly under narration. Instrumental, no vocals.",
    "2_acoustic_melancholy": "Melancholic post-apocalyptic score: sparse fingerpicked acoustic guitar, soft ambient "
                             "strings, lonely and emotional, slow tempo, lots of space. Instrumental, no vocals.",
    "3_dark_synth": "Dark retro synth score: pulsing analog synth bass, cold arpeggios, eerie pads, mysterious and "
                    "suspenseful, steady slow pulse. Instrumental, no vocals.",
    "4_cinematic_tension": "Cinematic survival thriller score: low string ostinato, deep taiko hits, rising brass "
                           "swells, urgent and dramatic but not loud. Instrumental, no vocals.",
}


def design(name, desc):
    r = requests.post(f"{API}/text-to-voice/design", headers=H, timeout=300, json={
        "voice_description": desc, "text": LINE, "model_id": "eleven_multilingual_ttv_v2"})
    r.raise_for_status(); log(f"sample-design-{name}", r)
    out = []
    for i, p in enumerate(r.json()["previews"][:2], 1):
        f = OUT / f"voice_{name}_{i}.mp3"
        f.write_bytes(base64.b64decode(p["audio_base_64"]))
        out.append((f.name, p["generated_voice_id"]))
    return out


def stock(name, vid):
    f = OUT / f"voice_{name}.mp3"
    r = requests.post(f"{API}/text-to-speech/{vid}?output_format=mp3_44100_192", headers=H, timeout=300,
                      json={"text": LINE, "model_id": "eleven_multilingual_v2",
                            "voice_settings": {"stability": 0.55, "similarity_boost": 0.8, "style": 0.2}})
    r.raise_for_status(); log(f"sample-{name}", r)
    f.write_bytes(r.content)
    return [(f.name, vid)]


def music(name, prompt):
    f = OUT / f"music_{name}.mp3"
    r = requests.post(f"{API}/music?output_format=mp3_44100_192", headers=H, timeout=600,
                      json={"prompt": prompt, "music_length_ms": 30000, "model_id": "music_v1"})
    r.raise_for_status(); log(f"sample-music-{name}", r)
    f.write_bytes(r.content)
    return [(f.name, None)]


if __name__ == "__main__":
    jobs = [lambda n=n, d=d: design(n, d) for n, d in DESIGNS.items()]
    jobs += [lambda n=n, v=v: stock(n, v) for n, v in STOCK.items()]
    jobs += [lambda n=n, p=p: music(n, p) for n, p in MUSIC.items()]
    ids = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for res in ex.map(lambda f: f(), jobs):
            for fname, vid in res:
                print(fname, flush=True)
                if vid:
                    ids[fname] = vid
    (OUT / "voice_ids.json").write_text(json.dumps(ids, indent=2))  # generated ids are needed to save the pick
