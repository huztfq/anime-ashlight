"""One-time kit of editing sound effects (whoosh, hit, riser, boom, tick) made with ElevenLabs, so every cut and
text pop lands on a real sound on the exact frame. Writes sfx_kit/*.mp3; reused by every episode and reel."""
import pathlib
from concurrent.futures import ThreadPoolExecutor
from audio import post

OUT = pathlib.Path("sfx_kit"); OUT.mkdir(exist_ok=True)
KIT = {  # name -> (prompt, seconds)
    "whoosh": ("Fast cinematic air whoosh transition, short and clean, dark trailer style, no music", 0.8),
    "hit": ("Single deep cinematic impact hit with a short metallic tail, dark trailer style, no music", 1.5),
    "riser": ("Tense cinematic riser building for two seconds into silence, dark low strings and metallic noise, no music", 2.5),
    "boom": ("Huge low sub boom with a distant rumble tail, horror trailer opening, no music", 3.0),
    "tick": ("Single soft clock tick with a little room echo, no music", 0.5),
}

if __name__ == "__main__":
    jobs = [lambda n=n, p=p, s=s: post("sound-generation?output_format=mp3_44100_192", OUT / f"{n}.mp3", f"kit-{n}",
                                       text=p, duration_seconds=s, prompt_influence=0.7) for n, (p, s) in KIT.items()]
    with ThreadPoolExecutor(max_workers=5) as ex:
        for res in ex.map(lambda f: f(), jobs):
            print(res, flush=True)
