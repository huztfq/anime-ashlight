"""Rewrite story.json so the 3-minute film itself follows the hook / lock-in / rehook / CTA structure.
Keeps the cast, look and schema; backs up the previous version to story_v1.json, then rebuilds STORY.md."""
import json, os, pathlib, shutil, subprocess
import anthropic
from hooks import RULES

for line in pathlib.Path(".env").read_text().splitlines():
    k, _, v = line.partition("=")
    os.environ[k] = v

old = json.loads(pathlib.Path("story.json").read_text())
if not pathlib.Path("story_v1.json").exists():
    shutil.copy("story.json", "story_v1.json")

BRIEF = f"""Here is a 3-minute anime short film (JSON). Rewrite it so the FILM ITSELF is structured like a
high-retention short-form script, while keeping the same story, cast, emotional payoff, look and production method.

{RULES}

Apply it to a 3-minute film:
- Shot 1 (0:00-0:12) is a COLD OPEN triple hook: open on the most striking moment from later in the story
  (a flash-forward), with a narrator hook line that opens a curiosity gap, and an on-screen hook text (max 6 words)
  saying the same thing. Then the story begins from the start.
- Lock-in (shot 2): 2-3 sentences that raise the stakes and promise the payoff.
- Body block 1 -> rehook 1 (around 1:00) -> body block 2 -> rehook 2 (around 2:00) -> body block 3 -> closing.
  Rehooks are single narrator lines that re-open curiosity.
- Final shot ends with a soft CTA spoken by the narrator and shown as on-screen text (e.g. follow for the next
  story / comment a keyword), aligned with the feeling of the ending.
- Narration: max 22 words per shot (it must fit in 12s alongside any character line), simple emotional words.
- Keep exactly 15 shots of 12 seconds, same schema, same character ids and tags, same "look" and "negative".
  Update "music" so the score's arc matches the new structure (including the cold open).
- Add to each shot a "part" field: "hook" | "lock_in" | "body1" | "rehook1" | "body2" | "rehook2" | "body3" | "closing" | "cta".
- Add top-level "hook_text" (on-screen, max 6 words, shown 0-3s) and "cta_text" (on-screen, max 8 words, last shot).

Return ONLY the full JSON.

FILM:
{json.dumps(old, indent=1)}
"""

client = anthropic.Anthropic()
with client.messages.stream(model="claude-opus-5-5", max_tokens=32000, output_config={"effort": "high"},
                            messages=[{"role": "user", "content": BRIEF}]) as s:
    msg = s.get_final_message()
text = next(b.text for b in msg.content if b.type == "text")
new = json.loads(text[text.find("{"): text.rfind("}") + 1])
assert len(new["shots"]) == 15
pathlib.Path("story.json").write_text(json.dumps(new, indent=2))
with open("costs.jsonl", "a") as f:
    f.write(json.dumps({"service": "anthropic", "what": "rewrite_story", "input_tokens": msg.usage.input_tokens,
                        "output_tokens": msg.usage.output_tokens}) + "\n")

names = {c["id"]: c["name"] for c in new["characters"]}
md = [f"# {new['title']}", "", f"*{new['logline']}*", "",
      f"**On-screen hook (0:00–0:03):** {new['hook_text']}  ", f"**On-screen CTA (end):** {new['cta_text']}", "",
      "## Cast"]
md += [f"- **{c['name']}** — {c['bio']}" for c in new["characters"]]
md += ["", f"**Score:** {new['music']}", "", "## Shots"]
for s in new["shots"]:
    t0 = (s["id"] - 1) * 12
    md += ["", f"### {s['id']}. [{s['part'].upper()}] {s['location']} — {t0 // 60}:{t0 % 60:02d}",
           f"On screen: {', '.join(names.get(c, c) for c in s['characters']) or 'nobody'}  ",
           "Motion: " + " → ".join(p.split(",")[0] for p in s["poses"]), ""]
    if s["narration"]:
        md.append(f"> *Narrator:* {s['narration']}")
    if s.get("line") and s["line"].get("text"):
        md.append(f"> **{names.get(s['line']['character'], s['line']['character'])}:** \"{s['line']['text']}\"")
    md.append(f"\nSound: {s['sfx']}")
pathlib.Path("STORY.md").write_text("\n".join(md))
print(new["title"], "| parts:", [s["part"] for s in new["shots"]])
