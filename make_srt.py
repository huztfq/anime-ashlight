"""YouTube subtitles for the episode, timed the same way mix.py places the voices. Usage: make_srt.py out.srt"""
import json, pathlib, sys
from mix import dur, layout

STORY = json.loads(pathlib.Path("story.json").read_text())
A = pathlib.Path("audio")
names = {c["id"]: c["name"].split()[0] for c in STORY["characters"]}


def ts(t):
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(t * 1000 % 1000):03d}"


cues = []
L = layout()
for s in STORY["shots"]:
    x = L[s["id"]]
    t = x["vo"]
    vo = A / f"vo{s['id']:02d}.mp3"
    if vo.exists():
        d = dur(vo)
        words = s["narration"].split()
        half = len(words)
        if len(words) > 12:  # long lines split into two cues, at the punctuation nearest the middle
            breaks = [i + 1 for i, w in enumerate(words[:-1]) if w[-1] in ".,;:?!—"] or [(len(words) + 1) // 2]
            half = min(breaks, key=lambda i: abs(i - len(words) / 2))
        for k, chunk in enumerate([words[:half], words[half:]]):
            if chunk:
                a = t + d * (0 if k == 0 else half / len(words))
                b = t + d * (half / len(words) if k == 0 else 1)
                cues.append((a, b, " ".join(chunk)))
    line = A / f"line{s['id']:02d}.mp3"
    if x["line"] is not None:
        a = x["line"]
        cues.append((a, a + dur(line), f"{names.get(s['line']['character'], '')}: {s['line']['text']}"))
pathlib.Path(sys.argv[1]).write_text("".join(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n" for i, (a, b, txt) in enumerate(cues, 1)))
print(len(cues), "cues")
