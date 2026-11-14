"""Turn one episode of series.json into a 25-shot production script (story.json + STORY.md) with OpenAI.
Usage: write_episode.py <episode number>"""
import json, os, pathlib, sys
import requests
from hooks import RULES

for line in pathlib.Path(".env").read_text().splitlines():
    k, _, v = line.partition("=")
    os.environ[k] = v

MODEL = "gpt-5.6-sol"
N = int(sys.argv[1])
SERIES = json.loads(pathlib.Path("series.json").read_text())


def in_range(spec, n):
    """'15-21' or '7' contains n?"""
    a, _, b = str(spec).partition("-")
    return int(a) <= n <= int(b or a)


def arc_outline(n):
    """series.json only outlines the first episodes; past them, brief the writer from the week and month arcs."""
    week = next((w for w in SERIES.get("weeks", []) if in_range(w["episodes"], n)), None)
    month = next((m for m in SERIES.get("months", []) if in_range(m["episodes"], n)), None)
    pts = month.get("turning_points", []) if month else []
    tagged = lambda p: int(p.split(":")[0].split()[-1]) if p.startswith("Episode ") else 0
    return {"n": n, "title": None, "logline": None, "cliffhanger": None,
            "note": ("No outline exists for this episode. Invent its title, logline and cliffhanger so it continues "
                     "straight from the previous episode, advances this week's arc by one clear step and does not "
                     "jump ahead of later turning points."),
            "week_arc": week and week["arc"], "month": month and f"{month['name']}: {month['summary']}",
            "turning_point_this_episode": [p for p in pts if tagged(p) == n],
            "next_turning_points": [p for p in pts if tagged(p) > n][:2],
            "cast_available": [c["name"] for c in SERIES["cast"] if c["joins_episode"] <= n]}


EP = next((e for e in SERIES["episodes"] if e["n"] == N), None) or arc_outline(N)
BEATS = SERIES["episode1"] if N == 1 else None
PREV = pathlib.Path(f"ep{N-1:02d}/story.json")
PREV = json.loads(PREV.read_text()) if PREV.exists() else None
# the chosen narrator voice (V1) and score style (M1) stay the same across the series
NARRATOR_VOICE = ("A young woman in her mid-twenties narrating a dark survival story. Low, slightly husky, calm and tired, "
                  "speaking close to the microphone like a late-night confession. American accent, natural, never theatrical.")
MUSIC_STYLE = ("Five-minute dark ambient survival score: deep low drones, distant metallic textures, faint rain, almost no "
               "melody, slow heavy tension that sits quietly under narration.")
KNOWN = {c["id"]: c for c in PREV["characters"]} if PREV else {}

BRIEF = f"""Write the production script for Episode {N} of the anime series "{SERIES['title']}".

SERIES BIBLE (JSON):
{json.dumps({k: SERIES[k] for k in ('title', 'logline', 'world', 'cast', 'locations', 'episode_format')}, indent=1)}

THIS EPISODE: {json.dumps(EP)}
{('APPROVED BEATS (follow them closely): ' + json.dumps(BEATS)) if BEATS else ''}
{('PREVIOUS EPISODE (continue straight from its cliffhanger; the viewer saw it yesterday): ' + json.dumps({
    "title": PREV["title"], "logline": PREV["logline"], "last_shots": [s["narration"] for s in PREV["shots"][-3:]]})) if PREV else ''}
{('EXISTING CHARACTER DESIGNS (reuse these ids and copy their tags exactly): ' + json.dumps(
    {k: c["tags"] for k, c in KNOWN.items()})) if KNOWN else ''}

{RULES}

PRODUCTION RULES:
- Exactly 25 shots, 12 seconds each (5:00), following the series episode format (hook, lock-in, body 1, rehook ~1:40,
  body 2, rehook ~3:20, body 3, cliffhanger + CTA). Give every shot a "part".
- The narrator is Nara, first person, past tense. Max 22 words of narration per shot (it must fit in 12 seconds next to
  any character line). Optional one short character line per shot, max 10 words. Narration and line together max
  26 words per shot: they play one after the other, never over each other, and must fit in the 12 seconds. Voices off screen (a tape, a radio) are
  fine as lines.
- Images are AI stills: each shot has 4 "poses" = the same camera framing and background, only the characters'
  pose/expression changes. At most 3 named characters on screen. Describe framing, background and poses in plain,
  concrete visual words. Keep the faces fully in frame. Any written words that must appear in the image (a label, a
  screen) go in the pose text in double quotes, max 6 words. Never put captions, titles or the hook/rehook/CTA text
  in the poses: on-screen text is added in editing.
- Include only characters who appear in this episode. Use the bible's ids lowercased by first name (e.g. "nara").
  An off-screen voice (e.g. Sela on a tape) is a character with "on_screen": false.
- "sfx" = ambience/sound effects only, no music, no speech.
- "delivery" = how Nara says this shot's narration: "calm", "tense", "whisper" or "urgent" (tonality sells the hooks).
- "rehook_texts" = the big on-screen words for rehook 1 (shot 9) and rehook 2 (shot 17), max 5 words each, matching
  what Nara says in that shot.

Return ONLY JSON:
{{"title": str, "logline": str, "hook_text": str, "rehook_texts": [str, str], "cta_text": str, "narrator_voice": str, "narrator_character": "nara",
 "characters": [{{"id": str, "name": str, "tags": str, "voice": str, "bio": str, "on_screen": bool}}],
 "negative": str, "look": str,
 "music": str,
 "shots": [{{"id": int, "part": str, "location": str, "framing": str, "characters": [str], "background": str,
            "poses": [str, str, str, str], "narration": str, "delivery": str, "line": {{"character": str, "text": str}} | null, "sfx": str}}]}}
"music" = a prompt for a 5-minute instrumental score following this episode's arc (no vocals).
"""

r = requests.post("https://api.openai.com/v1/responses", timeout=1800,
                  headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                  json={"model": MODEL, "input": BRIEF, "reasoning": {"effort": "high"},
                        "text": {"format": {"type": "json_object"}}})
j = r.json()
if r.status_code >= 400:
    raise SystemExit(json.dumps(j)[:800])
text = next(c["text"] for o in j["output"] if o["type"] == "message" for c in o["content"] if c["type"] == "output_text")
story = json.loads(text)
assert len(story["shots"]) == 25, len(story["shots"])
story["episode"] = N
story["narrator_voice"] = NARRATOR_VOICE
story["music"] = f"{MUSIC_STYLE} {story['music']}"
for c in story["characters"]:  # same faces every episode
    if c["id"] in KNOWN:
        c["tags"] = KNOWN[c["id"]]["tags"]
pathlib.Path("story.json").write_text(json.dumps(story, indent=2))
u = j.get("usage", {})
with open("costs.jsonl", "a") as f:
    f.write(json.dumps({"service": "openai", "what": f"episode{N}_script", "model": MODEL,
                        "input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens")}) + "\n")

names = {c["id"]: c["name"] for c in story["characters"]}
md = [f"# Episode {N}: {story['title']}", "", f"*{story['logline']}*", "",
      f"**On-screen hook (0:00–0:03):** {story['hook_text']}  ", f"**On-screen CTA (end):** {story['cta_text']}", ""]
for s in story["shots"]:
    t0 = (s["id"] - 1) * 12
    md += ["", f"### {s['id']}. [{s['part'].upper()}] {s['location']} — {t0 // 60}:{t0 % 60:02d}",
           f"On screen: {', '.join(names.get(c, c) for c in s['characters']) or 'nobody'}  ",
           "Motion: " + " → ".join(p.split(",")[0] for p in s["poses"]), ""]
    if s["narration"]:
        md.append(f"> *Nara:* {s['narration']}")
    if s.get("line") and s["line"].get("text"):
        md.append(f"> **{names.get(s['line']['character'], s['line']['character'])}:** \"{s['line']['text']}\"")
    md.append(f"\nSound: {s['sfx']}")
pathlib.Path("STORY.md").write_text("\n".join(md))
print(story["title"], "|", [c["id"] for c in story["characters"]], "|", u.get("output_tokens"), "tokens")
