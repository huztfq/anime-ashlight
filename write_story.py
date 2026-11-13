"""Ask Claude for an original 3-minute anime short, planned for local SDXL limited animation. Saves story.json + STORY.md."""
import json, os, pathlib, time
import anthropic

for line in pathlib.Path(".env").read_text().splitlines():
    k, _, v = line.partition("=")
    os.environ[k] = v

BRIEF = """Write an ORIGINAL 3-minute anime short film. Surprise me: pick a fresh premise with heart, a clear
beginning-middle-end, a small cast (2-4 characters), and a satisfying emotional payoff. Nothing derivative of
existing franchises. Suitable for YouTube (PG).

Production method (plan the shots for it):
- Images are made locally with Animagine XL 4.0 (an SDXL anime model). It responds best to comma-separated
  Danbooru-style tags (e.g. "1girl, solo, short black hair, red scarf, school uniform, smiling, looking at viewer,
  night, city lights, rain"). Write all visual prompts that way.
- Characters stay consistent through a reference image per character plus a FIXED tag string per character that
  is pasted into every shot they appear in. Make each character visually distinctive (hair color/style, one signature
  clothing item or accessory). Use at most 2 characters on screen per shot - SDXL mixes up crowds.
- Motion is limited animation: each shot has 4 "poses" - the same framing and background, with only the
  character's pose/expression changing (e.g. hand reaching -> grabbing -> lifting -> smiling). Keep the camera framing
  identical across a shot's 4 poses so only the character moves.
- 15 shots, exactly 12 seconds each (180s).

Sound (made with ElevenLabs): a narrator voice-over (past tense, max 22 words per shot, may be empty),
optional one short spoken line per shot from a character (max 10 words, may be empty), an ambient sfx description,
and a music prompt for a 3-minute score that follows the story arc.

Return ONLY JSON:
{"title": str, "logline": str,
 "narrator_voice": str,                // e.g. "warm older female, gentle"
 "characters": [{"id": str, "name": str, "tags": str, "voice": str, "bio": str}],
 "look": str,                          // global quality/style tags appended to every prompt
 "negative": str,                      // negative prompt tags
 "music": str,
 "shots": [{"id": int, "location": str, "framing": str,   // framing tags, e.g. "medium shot, from side"
            "characters": [str],                          // character ids on screen (0-2)
            "background": str,                            // background tags, identical for all 4 poses
            "poses": [str, str, str, str],                // per-pose tags: action + expression
            "narration": str, "line": {"character": str, "text": str} | null, "sfx": str}]}
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
    f.write(json.dumps({"service": "anthropic", "what": "story", "input_tokens": msg.usage.input_tokens,
                        "output_tokens": msg.usage.output_tokens}) + "\n")

md = [f"# {story['title']}", "", f"*{story['logline']}*", "", "## Cast"]
md += [f"- **{c['name']}** — {c['bio']}  \n  Voice: {c['voice']}" for c in story["characters"]]
md += ["", f"**Narrator:** {story['narrator_voice']}", "", f"**Score:** {story['music']}", "", "## Shots"]
names = {c["id"]: c["name"] for c in story["characters"]}
for s in story["shots"]:
    t0 = (s["id"] - 1) * 12
    md += ["", f"### {s['id']}. {s['location']} — {t0 // 60}:{t0 % 60:02d}",
           f"On screen: {', '.join(names.get(c, c) for c in s['characters']) or 'nobody'}  ",
           "Motion: " + " → ".join(p.split(",")[0] for p in s["poses"]), ""]
    if s["narration"]:
        md.append(f"> *Narrator:* {s['narration']}")
    if s.get("line") and s["line"].get("text"):
        md.append(f"> **{names.get(s['line']['character'], s['line']['character'])}:** \"{s['line']['text']}\"")
    md.append(f"\nSound: {s['sfx']}")
pathlib.Path("STORY.md").write_text("\n".join(md))
print(story["title"], "|", len(story["shots"]), "shots |", msg.usage.output_tokens, "tokens |", round(time.time() - t), "s")
