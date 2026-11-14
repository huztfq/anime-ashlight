"""Three-way review packet: Claude + OpenAI score the short against REFERENCE_REELS.md (Grok Bot scores by hand)."""
import base64, json, os, pathlib, subprocess, sys, requests
sys.path.insert(0, "/workspace/ashlight/prod/anime-ashlight")
import ws_build as B
REPO = pathlib.Path("/workspace/ashlight/prod/anime-ashlight")
for l in pathlib.Path('.env').read_text().splitlines():
    k, _, v = l.partition('='); os.environ[k] = v
video = sys.argv[1]
tl, total = B.timeline(B.M.REELS[0])
story = json.loads(pathlib.Path("story.json").read_text())
lines = []
for st, ln, sec, segs, vo in tl:
    shots = ", ".join(f"shot {s} ({next(x['framing'] for x in story['shots'] if x['id']==s)[:70]}...)" for s, *_ in segs)
    said = sec["vo"] or " / ".join(f"JUN (character line, blue caption): {next(x['line']['text'] for x in story['shots'] if x['id']==s)}" for s, _, _, u in segs if u)
    lines.append(f"{st:5.1f}-{st+ln:5.1f}s [{sec['part']}] {said}   | visuals: {shots}")
packet = f"""You are reviewing a 9:16 short for YouTube Shorts and Instagram Reels: a standalone "From the world of AFTER THE HUM"
mini story (an AI anime series). It must make complete sense to someone who never saw an episode.

REFERENCE RULES AND SCORING:
{(REPO/'REFERENCE_REELS.md').read_text()}

WORLD SHORT RULES:
{(REPO/'WORLD_SHORTS.md').read_text().split('## Format')[0]}

SERIES CANON (short): Meridian is a rain-dark city. Jun Arai (17, auburn curls, teal headphones, yellow rain shell,
analog wristwatch) is an electronics apprentice with a tiny repair kiosk. Before the collapse ("Quietfall"), small
failures pile up: phones heat up without power, public speakers run unexplained tests, pipes pulse every seventeen
seconds. In the series, at 7:17 one morning every phone in Meridian emitted the same three-second tone (already aired).
The narrator voice is Nara's (a courier who narrates the series).

THE SHORT ({total:.1f} s). On-screen from frame 0: small label "FROM THE WORLD OF AFTER THE HUM" + hook card
"{story['hook_text']}" (3.2 s). Narrator captions word by word (yellow active word), Jun's lines in blue, low-centre.
End card: "{story['cta_text']}" + "Voices and visuals are AI-generated". Each shot cycles 4 drawn poses (~1.3 s each)
with a slow push-in, whoosh on cuts, boom at 0, riser+hit into rehooks and CTA, ambient score.
Timeline:
""" + "\n".join(lines) + """

The attached image is a contact sheet of the actual render, one frame every 1.5 s (timestamps under each).

Score each item 1-5: hook_0_2s, story_loop_rehook, payoff, visual_change_rate, text_readability_placement,
comment_cta, shareability, makes_sense_standalone, canon_and_content_safety. Return ONLY JSON:
{"scores": {item: int}, "top_issues": [str], "fixes": [str]}  (be concrete and brief)."""
img = base64.b64encode(pathlib.Path("ws02_contact.jpg").read_bytes()).decode()
pathlib.Path("review_packet.txt").write_text(packet)
out = {}
r = requests.post("https://api.anthropic.com/v1/messages", timeout=600,
    headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
    json={"model": "claude-opus-5-5", "max_tokens": 6000, "messages": [{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img}}, {"type": "text", "text": packet}]}]})
j = r.json(); out["claude"] = "".join(c.get("text","") for c in j["content"] if c.get("type")=="text") if r.ok else str(j)[:500]
r = requests.post("https://api.openai.com/v1/responses", timeout=900,
    headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
    json={"model": "gpt-5.6-sol", "reasoning": {"effort": "high"}, "input": [{"role": "user", "content": [
        {"type": "input_text", "text": packet}, {"type": "input_image", "image_url": f"data:image/jpeg;base64,{img}"}]}]})
j = r.json()
out["openai"] = next((c["text"] for o in j.get("output", []) if o["type"] == "message" for c in o["content"] if c["type"] == "output_text"), str(j)[:500])
pathlib.Path(sys.argv[2]).write_text(json.dumps(out, indent=1))
for k, v in out.items(): print("==", k, "\n", v)
