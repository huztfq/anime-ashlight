"""Ask OpenAI's flagship model for the series bible of a daily 5-minute survival anime. Saves series.json."""
import json, os, pathlib, time
import requests
from hooks import RULES

for line in pathlib.Path(".env").read_text().splitlines():
    k, _, v = line.partition("=")
    os.environ[k] = v

MODEL = "gpt-5.6-sol"

BRIEF = f"""You are the showrunner of an ORIGINAL anime survival series for YouTube.

FORMAT: one 5-minute episode every day for 6 months (about 180 episodes, 26 weeks), plus 3-5 vertical reels/Shorts
cut from each episode that drive viewers to the full episode. Each episode = 25 shots of 12 seconds, told mostly by a
narrator voice-over plus short character lines. Visual style: dark, gritty, mature seinen anime.

STORY: it starts in the NORMAL world (ordinary life, small signs something is wrong), then the collapse, then
surviving in the city, the escape from the city through the foothills into the forests and mountains, and finally
building a sanctuary in the mountains, defending it, and growing a community. Tone and appeal like The Walking Dead,
The Last of Us, The Maze Runner, The 100 and Silo: a real threat, scarce supplies, hard moral choices, distrust
between survivors, found family, factions, and a slow-burn MYSTERY about what really caused the collapse that pays off
over the 6 months. Fully original: do not reuse any of those shows' characters, creatures, places, groups or plot
points. PG-13 for YouTube (danger and tension, no gore). Make survival craft real and specific (water, fire, shelter,
food, medicine, weather, winter) so each episode teaches or shows something.

PRODUCTION LIMITS (plan for them):
- Images are AI-generated stills with consistency from fixed character sheets. Give each main character a distinctive
  look that stays the same (hair, one signature clothing item/accessory) and list it as fixed visual tags.
  Costume changes only at clear story moments.
- At most 3 named characters on screen per shot. The threat must work as silhouettes, shadows, sounds, eyes in the dark,
  or aftermath - no crowd fight scenes.
- Core cast of 5-7 for the first months; new characters join slowly. Keep recurring locations few and memorable.

HOOK RULES for every episode and reel:
{RULES}
Every episode: a cold-open hook in the first 3 seconds, a lock-in, rehooks around 1:40 and 3:20, and a cliffhanger
ending that makes tomorrow's episode a must-watch. End with a CTA aligned with the cliffhanger.

Return ONLY JSON:
{{"title": str, "tagline": str, "logline": str,
 "world": {{"normal_life": str, "the_collapse": str, "the_threat": str, "threat_rules": [str],
            "the_mystery": str, "mystery_payoff": str, "journey": str, "sanctuary": str}},
 "cast": [{{"id": str, "name": str, "age": int, "role": str, "look_tags": str, "personality": str,
            "arc": str, "voice": str, "joins_episode": int}}],
 "locations": [{{"name": str, "look_tags": str, "episodes": str}}],
 "months": [{{"month": int, "name": str, "episodes": str, "summary": str, "turning_points": [str]}}],
 "weeks": [{{"week": int, "episodes": str, "arc": str}}],
 "episode_format": [{{"segment": str, "time": str, "purpose": str}}],
 "reels": {{"per_episode": int, "angles": [str], "cta": str}},
 "episodes": [{{"n": int, "title": str, "logline": str, "cliffhanger": str}}],
 "episode1": {{"title": str, "hook_text": str, "beats": [{{"time": str, "beat": str}}]}}}}
"weeks" covers all 26 weeks. "episodes" covers episodes 1-14 only. "episode1.beats" has 10-14 beats over 0:00-5:00.
"""

t = time.time()
r = requests.post("https://api.openai.com/v1/responses", timeout=1800,
                  headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                  json={"model": MODEL, "input": BRIEF, "reasoning": {"effort": "high"},
                        "text": {"format": {"type": "json_object"}}})
j = r.json()
if r.status_code >= 400:
    raise SystemExit(json.dumps(j)[:800])
text = next(c["text"] for o in j["output"] if o["type"] == "message" for c in o["content"] if c["type"] == "output_text")
series = json.loads(text)
pathlib.Path("series.json").write_text(json.dumps(series, indent=2))
u = j.get("usage", {})
with open("costs.jsonl", "a") as f:
    f.write(json.dumps({"service": "openai", "what": "series_bible", "model": MODEL, "input_tokens": u.get("input_tokens"),
                        "output_tokens": u.get("output_tokens")}) + "\n")
print(series["title"], "|", len(series["cast"]), "cast |", len(series["weeks"]), "weeks |", u, "|", round(time.time() - t), "s")
