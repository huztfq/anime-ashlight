"""Ask OpenAI to plan 4 vertical reels cut from the film, following the user's reference reels. Saves reels.json + REELS.md."""
import json, os, pathlib
import requests

for line in pathlib.Path(".env").read_text().splitlines():
    k, _, v = line.partition("=")
    os.environ[k] = v

STORY = json.loads(pathlib.Path("story.json").read_text())
SERIES = json.loads(pathlib.Path("series.json").read_text())

from hooks import RULES

BRIEF = f"""You are a short-form video editor. Cut 4 different vertical reels (30-50 seconds each) from this anime
episode, one per angle below, so they don't feel repetitive. Every reel drives viewers to the full 5-minute episode.
ANGLES: {json.dumps(SERIES["reels"]["angles"])}
CTA STYLE: {SERIES["reels"]["cta"]}

{RULES}

Footage available: the episode's {len(STORY['shots'])} shots, each with 4 poses (pose images p1-p4 of the same framing, the character moving).
Reels will be re-rendered vertically (9:16) from the same shot descriptions, so any shot can be used.
Each segment shows ONE shot for 2-8 seconds, cycling through its poses. Prefer quick cuts (2-4s) in the hook and
rehooks, longer holds (4-8s) in body blocks. A shot may appear in several reels.
Voice-over is the film's narrator ({STORY["narrator_voice"]}). You may also reuse a character's original line from the
film by setting "use_line": true on that segment (the line plays over that shot).

FILM:
{json.dumps(STORY, indent=1)}

Return ONLY JSON:
{{"reels": [{{"id": int, "angle": str, "hook_text": str,          // on-screen hook, max 6 words
  "cta_text": str,                                               // on-screen CTA, max 8 words
  "sections": [{{"part": "hook"|"lock_in"|"body1"|"rehook1"|"body2"|"rehook2"|"body3"|"closing"|"cta",
                 "vo": str,                                      // narrator text for this section ("" allowed)
                 "shots": [{{"shot": int, "seconds": number, "use_line": bool}}]}}],
  "caption": str, "hashtags": [str]}}]}}
The sum of seconds in a section should roughly match how long its vo takes to say (~2.6 words per second),
and each reel's total should be 30-50 seconds.
"""

r = requests.post("https://api.openai.com/v1/responses", timeout=1800,
                  headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                  json={"model": "gpt-5.6-sol", "input": BRIEF, "reasoning": {"effort": "high"},
                        "text": {"format": {"type": "json_object"}}})
j = r.json()
if r.status_code >= 400:
    raise SystemExit(json.dumps(j)[:800])
text = next(c["text"] for o in j["output"] if o["type"] == "message" for c in o["content"] if c["type"] == "output_text")
reels = json.loads(text)
pathlib.Path("reels.json").write_text(json.dumps(reels, indent=2))
u = j.get("usage", {})
with open("costs.jsonl", "a") as f:
    f.write(json.dumps({"service": "openai", "what": "plan_reels", "input_tokens": u.get("input_tokens"),
                        "output_tokens": u.get("output_tokens")}) + "\n")

md = [f"# Reels for {STORY['title']}", ""]
for r in reels["reels"]:
    secs = sum(sh["seconds"] for sec in r["sections"] for sh in sec["shots"])
    md += [f"## Reel {r['id']}: {r['angle']} ({secs:.0f}s)", f"**On-screen hook:** {r['hook_text']}  ",
           f"**CTA:** {r['cta_text']}", ""]
    for sec in r["sections"]:
        shots = ", ".join(f"shot {sh['shot']}" + (" (with line)" if sh.get("use_line") else "") for sh in sec["shots"])
        md.append(f"- **{sec['part']}** — {sec['vo'] or '(no voice)'}  \n  _{shots}_")
    md += ["", f"Caption: {r['caption']} {' '.join('#' + h.lstrip('#') for h in r['hashtags'])}", ""]
pathlib.Path("REELS.md").write_text("\n".join(md))
print(len(reels["reels"]), "reels planned;", u.get("output_tokens"), "tokens")
