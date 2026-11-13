"""Ask Claude for an original 3-minute post-apocalyptic anime short (hook structure), planned for local SDXL limited animation. Saves story.json + STORY.md."""
import json, os, pathlib, time
import anthropic
from hooks import RULES

for line in pathlib.Path(".env").read_text().splitlines():
    k, _, v = line.partition("=")
    os.environ[k] = v

BRIEF = f"""Write an ORIGINAL 3-minute anime short film in the post-apocalyptic survival genre: the tone of
The Maze Runner, The 100, The Walking Dead and The Last of Us (a ruined world, infected or monsters, scarce
supplies, hard choices, distrust between survivors, a bond worth protecting, a mystery about what happened).
Do NOT copy any of their characters, places, creatures or plot points - fresh premise, fresh world, fresh twist.
Small cast (2-4 characters), clear beginning-middle-end, tense and emotional with a gut-punch or hopeful twist
ending. PG-13 for YouTube: danger and threat, no gore.

{RULES}

Apply it to the 3-minute film:
- Shot 1 (0:00-0:12) is a COLD OPEN triple hook: open on the most striking moment from later in the story
  (a flash-forward), with a narrator hook line that opens a curiosity gap, and an on-screen hook text (max 6 words)
  saying the same thing. Then the story begins from the start.
- Lock-in (shot 2): 2-3 sentences that raise the stakes and promise the payoff.
- Body block 1 -> rehook 1 (around 1:00) -> body block 2 -> rehook 2 (around 2:00) -> body block 3 -> closing.
  Rehooks are single narrator lines that re-open curiosity.
- Final shot ends with a soft CTA spoken by the narrator and shown as on-screen text, aligned with the ending.

Production method (plan the shots for it):
- Images are made locally with an SDXL anime model. It responds best to comma-separated Danbooru-style tags
  (e.g. "1boy, solo, messy black hair, torn red jacket, holding flashlight, looking back, ruined subway, dark").
  Write all visual prompts that way.
- Characters stay consistent through a reference image per character plus a FIXED tag string per character that
  is pasted into every shot they appear in. Make each character visually distinctive (hair color/style, one signature
  clothing item or accessory). At most 2 named characters on screen per shot. Infected/monsters: show them as a
  single distant silhouette, shadows, eyes in the dark, or a shot with no named characters - never a crowd fight.
- Motion is limited animation: each shot has 4 "poses" - the same framing and background, with only the
  character's pose/expression changing. Keep framing identical across a shot's 4 poses.
- 15 shots, exactly 12 seconds each (180s).

Sound (made with ElevenLabs): a narrator voice-over (past tense, max 22 words per shot, may be empty),
optional one short spoken line per shot from a character (max 10 words, may be empty), an ambient sfx description,
and a music prompt for a 3-minute score that follows the story arc (including the cold open).

Return ONLY JSON:
{{"title": str, "logline": str, "hook_text": str, "cta_text": str,
 "narrator_voice": str,
 "characters": [{{"id": str, "name": str, "tags": str, "voice": str, "bio": str}}],
 "look": str,                          // global quality/style tags appended to every prompt
 "negative": str,
 "music": str,
 "shots": [{{"id": int, "part": "hook"|"lock_in"|"body1"|"rehook1"|"body2"|"rehook2"|"body3"|"closing"|"cta",
            "location": str, "framing": str, "characters": [str], "background": str,
            "poses": [str, str, str, str],
            "narration": str, "line": {{"character": str, "text": str}} | null, "sfx": str}}]}}
"""

client = anthropic.Anthropic()
t = time.time()
with client.messages.stream(model="claude-opus-5-5", max_tokens=32000, output_config={"effort": "high"},
                            messages=[{"role": "user", "content": BRIEF}]) as s:
    msg = s.get_final_message()
text = next(b.text for b in msg.content if b.type == "text")
story = json.loads(text[text.find("{"): text.rfind("}") + 1])
pathlib.Path("story.json").write_text(json.dumps(story, indent=2))
with open("costs.jsonl", "a") as f:
    f.write(json.dumps({"service": "anthropic", "what": "story_apocalypse", "input_tokens": msg.usage.input_tokens,
                        "output_tokens": msg.usage.output_tokens}) + "\n")

md = [f"# {story['title']}", "", f"*{story['logline']}*", "", f"**On-screen hook (0:00–0:03):** {story['hook_text']}  ",
      f"**On-screen CTA (end):** {story['cta_text']}", "", "## Cast"]
md += [f"- **{c['name']}** — {c['bio']}  \n  Voice: {c['voice']}" for c in story["characters"]]
md += ["", f"**Narrator:** {story['narrator_voice']}", "", f"**Score:** {story['music']}", "", "## Shots"]
names = {c["id"]: c["name"] for c in story["characters"]}
for s in story["shots"]:
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
print(story["title"], "|", len(story["shots"]), "shots |", msg.usage.output_tokens, "tokens |", round(time.time() - t), "s")
