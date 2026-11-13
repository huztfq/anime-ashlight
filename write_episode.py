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
EP = next(e for e in SERIES["episodes"] if e["n"] == N)
BEATS = SERIES["episode1"] if N == 1 else None
PREV = pathlib.Path(f"ep{N-1:02d}/story.json")
PREV = json.loads(PREV.read_text()) if PREV.exists() else None
# the chosen narrator voice (V1) and score style (M1) stay the same across the series
NARRATOR_VOICE = ("A young woman in her mid-twenties narrating a dark survival story. Low, slightly husky, calm and tired, "
                  "speaking close to the microphone like a late-night confession. American accent, natural, never theatrical.")
MUSIC_STYLE = ("Five-minute dark ambient survival score: deep low drones, distant metallic textures, faint rain, almost no "
               "melody, slow heavy tension that sits quietly under narration.")
KNOWN = {c["id"]: c for c in PREV["characters"]} if PREV else {}


def world_state(n):
    """How far the collapse has gone at episode n, from the bible's week/month arcs (for the premise recap)."""
    import re
    def within(rng):
        a, _, b = str(rng).partition("-")
        return a.strip().isdigit() and int(a) <= n <= int((b or a).strip())
    week = next((w for w in SERIES.get("weeks", []) if within(w.get("episodes", ""))), None)
    month = next((m for m in SERIES.get("months", []) if within(m.get("episodes", ""))), None)
    fall = None  # the episode where Quietfall (the real collapse) happens, read from the turning points
    for m in SERIES.get("months", []):
        for tp in m.get("turning_points", []):
            hit = re.match(r"Episode (\d+):.*Quietfall", tp)
            if hit and fall is None:
                fall = int(hit.group(1))
    out = []
    if month:
        out.append(f"Month arc '{month.get('name')}': {month.get('summary')}")
    if week:
        out.append(f"This week's arc: {week.get('arc')}")
    if fall and n < fall:
        out.append(f"Quietfall (the full collapse) has NOT happened yet; it comes in Episode {fall}. Right now the city "
                   "still stands but is visibly failing since the Hum. Do not say the world has ended.")
    elif fall:
        out.append(f"Quietfall struck in Episode {fall}: power, water and order in Meridian have collapsed. Say so plainly.")
    return "\n".join(out)


try:  # never let the recap context break the script writer
    WORLD_STATE = world_state(N)
except Exception:
    WORLD_STATE = ""
PREMISE = f"""PREMISE CLARITY (viewers told us they could not tell what is happening, e.g. "has the world ended or are they
just homeless?"). Every episode must make the situation obvious to a first-time viewer:
- Shot 1 stays the triple hook exactly as the rules above say.
- Shot 2 (0:12-0:24) is a short narrated cold-open recap in Nara's voice, with NO character line in shot 2 and 16-24
  words of narration. In plain words it says (a) what the Hum is (the three-second tone that came out of every phone
  and speaker in Meridian at 7:17), (b) what has happened to the city since then, truthful to this point in the series
  (see WORLD STATE below), and (c) where Nara and the others are right now and what they need today. Write it fresh
  every episode: new wording and a new angle, never a copy of an earlier recap. Keep it tense, not a lecture. Shot 2's
  image is a clear establishing view of where they are now. Shot 3 then carries the lock-in stakes.
- Keep the world-state clear in the rest of the episode too: at least two more moments (narration or dialogue) show
  concretely what still works, what has failed, and why the characters are where they are. Never leave it ambiguous.
WORLD STATE AT EPISODE {N}:
{WORLD_STATE or "Follow the bible's world section and the previous episode."}
"""

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

{PREMISE}
PRODUCTION RULES:
- Exactly 25 shots, 12 seconds each (5:00), following the series episode format (hook, lock-in, body 1, rehook ~1:40,
  body 2, rehook ~3:20, body 3, cliffhanger + CTA), except that shot 2 is the premise recap above (part "recap").
  Give every shot a "part".
- The narrator is Nara, first person, past tense. Max 22 words of narration per shot (it must fit in 12 seconds next to
  any character line); only the shot 2 recap may use up to 24 because it has no line. Optional one short character line per shot, max 10 words. Voices off screen (a tape, a radio) are
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
if story["shots"][1].get("line"):  # shot 2 is the narrated recap: keep it free of dialogue so the VO fits 12 s
    story["shots"][1]["line"] = None
if len((story["shots"][1].get("narration") or "").split()) > 28:
    print("WARNING: shot 2 recap is over 28 words; check it fits 12 s", flush=True)
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
