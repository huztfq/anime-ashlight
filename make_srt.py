"""YouTube subtitles for the episode, timed the same way mix.py places the voices. Usage: make_srt.py out.srt
Narration (Nara's voice-over) is in <i>italics</i>; spoken lines are upright and start with the speaker's name, so
viewers can tell the two apart (YouTube renders <i> in uploaded .srt files)."""
import json, pathlib, sys
from mix import plan

STORY = json.loads(pathlib.Path("story.json").read_text())
A = pathlib.Path("audio")
names = {c["id"]: c["name"].split()[0] for c in STORY["characters"]}


def ts(t):
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(t * 1000 % 1000):03d}"


cues = []
for p in plan():  # same speech plan as mix.py: narration, a gap, then the line; never overlapping
    s = next(x for x in STORY["shots"] if x["id"] == p["id"])
    if p["vo"]:
        _, t, end = p["vo"]; d = end - t
        words = s["narration"].split()
        half = len(words)
        if len(words) > 12:  # long lines split into two cues, at the punctuation nearest the middle
            breaks = [i + 1 for i, w in enumerate(words[:-1]) if w[-1] in ".,;:?!—"] or [(len(words) + 1) // 2]
            half = min(breaks, key=lambda i: abs(i - len(words) / 2))
        for k, chunk in enumerate([words[:half], words[half:]]):
            if chunk:
                a = t + d * (0 if k == 0 else half / len(words))
                b = t + d * (half / len(words) if k == 0 else 1)
                cues.append((a, b, f"<i>{' '.join(chunk)}</i>"))  # narration in italics, dialogue upright with a name
    if p["line"]:
        _, a, b = p["line"]
        cues.append((a, b, f"{names.get(s['line']['character'], '')}: {s['line']['text']}"))
pathlib.Path(sys.argv[1]).write_text("".join(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n" for i, (a, b, txt) in enumerate(cues, 1)))
print(len(cues), "cues")
