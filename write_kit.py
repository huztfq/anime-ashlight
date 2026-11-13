"""Day N upload kit: Episode N on YouTube plus Episode N-1's four reels, written with OpenAI and rendered as
upload/epNN_upload_kit.md (titles, description with chapters, tags, settings, thumbnail and cover table, reel
captions and Shorts titles, schedule, pinned comment, story, checklist). Also makes the YouTube thumbnail.
Usage: write_kit.py N [drive_folder_url]   (run after the episode, reels and covers exist)"""
import json, os, pathlib, sys
import requests
from make_thumb import thumb

for line in pathlib.Path(".env").read_text().splitlines():
    k, _, v = line.partition("=")
    if k.strip():
        os.environ[k.strip()] = v.strip()

MODEL = "gpt-5.6-sol"
N = int(sys.argv[1])
DRIVE = sys.argv[2] if len(sys.argv) > 2 else ""
SHOT_S = 12
STORY = json.loads(pathlib.Path("story.json").read_text())
PREV = pathlib.Path(f"ep{N - 1:02d}/reels.json")
PREV_REELS = json.loads(PREV.read_text())["reels"] if PREV.exists() else []
NEXT_TITLE = ""
series = json.loads(pathlib.Path("series.json").read_text())
for e in series.get("episodes", []):
    if int(e.get("n", e.get("number", 0))) == N + 1:
        NEXT_TITLE = e.get("title", "")


def mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


shots = [{"shot": s["id"], "start": mmss(SHOT_S * (s["id"] - 1)), "part": s["part"], "narration": s["narration"]}
         for s in STORY["shots"]]
BRIEF = f"""You write the YouTube and social upload kit for Episode {N} of AFTER THE HUM, an original dark anime survival
series by the channel Ashlight Stories (daily 5-minute episodes; arc: city -> collapse -> mountains -> sanctuary).
Episode {N}: "{STORY['title']}". Logline: {STORY['logline']}
On-screen hook: {STORY['hook_text']}. Next episode: "{NEXT_TITLE or 'Episode ' + str(N + 1)}".
Shots with start times (each 12 s; the film is about 5:09):
{json.dumps(shots, indent=0)}

Yesterday's episode (Episode {N - 1}) has 4 reels to post today on Instagram, TikTok and YouTube Shorts:
{json.dumps([{k: r.get(k) for k in ('id', 'angle', 'hook_text', 'caption', 'hashtags')} for r in PREV_REELS], indent=0)}

Rules: plain, emotional, specific words; short sentences; curiosity gaps, no spoilers of the final twist. Titles under
70 characters and always contain "AFTER THE HUM". Links don't work in Instagram/TikTok captions, so they say
"link in bio". Every survival tip is part of the story, not advice.

Return ONLY JSON:
{{"titles": [str, str, str],
 "description_hook": str,            // first 2 lines, shown above "more"
 "description_body": str,            // 2-4 sentences about the episode
 "chapters": [{{"start": "m:ss", "label": str}}],   // 7-10, first is 0:00, use only the start times above, >= 10 s apart
 "tags": [str],                      // 15-20
 "hashtags": str,                    // 3-5 for the description
 "thumbnail_shot": int,              // the most striking, readable frame (faces visible, one clear object or event)
 "thumbnail_text": str,              // 2-3 words, a curiosity gap, NOT the same as the on-screen hook
 "pinned_comment": str,              // a question tomorrow's episode answers
 "story_text": str,                  // Instagram story line at release
 "poll": {{"question": str, "options": [str, str]}},
 "reels": [{{"id": str, "shorts_title": str, "instagram": str, "tiktok": str}}]}}   // one per reel above
"""

r = requests.post("https://api.openai.com/v1/responses", timeout=900,
                  headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                  json={"model": MODEL, "input": BRIEF, "reasoning": {"effort": "medium"},
                        "text": {"format": {"type": "json_object"}}})
j = r.json()
if r.status_code >= 400:
    raise SystemExit(json.dumps(j)[:800])
kit = json.loads(next(c["text"] for o in j["output"] if o["type"] == "message"
                      for c in o["content"] if c["type"] == "output_text"))
pathlib.Path("kit.json").write_text(json.dumps(kit, indent=2))
thumb(N, kit["thumbnail_shot"], kit["thumbnail_text"])

E, P = f"ep{N:02d}", f"ep{N - 1:02d}"
by_angle = {}
for rr in PREV_REELS:
    a = rr.get("angle", "").lower()
    by_angle["cliff" if "cliff" in a else "moral" if "moral" in a else "mystery" if "myster" in a else "survival"] = rr
order = [("9:00 AM", by_angle.get("survival")), ("1:00 PM", by_angle.get("mystery")), ("5:00 PM", "EP"),
         ("6:00 PM", by_angle.get("cliff")), ("9:00 PM", by_angle.get("moral"))]
order = [(t, x) for t, x in order if x]
rk = {str(x["id"]): x for x in kit.get("reels", [])}

md = []
if DRIVE:
    md += [f"> 📁 All files: [Google Drive → After the Hum → Episode {N:02d}]({DRIVE})", ""]
md += ["## Today's schedule", "",
       f"Episode {N} on YouTube plus Episode {N - 1}'s four reels, spread across the day so each one points back to the "
       "channel. Times are your audience's local time; shift them once analytics show when followers are online.", "",
       "| Time | Platform | File | Notes |", "| --- | --- | --- | --- |"]
for t, x in order:
    if x == "EP":
        md.append(f"| {t} | YouTube | {E}_full_quality.mp4 | Episode {N}. Upload at 4 PM, schedule for 5 PM so it is HD |")
    else:
        md.append(f"| {t} | Instagram, TikTok, YouTube Shorts | {P}_reel{x['id']}.mp4 | {x.get('angle', '')} |")
md += ["", "## Thumbnails and covers", "", "| Post | File | Where to set it |", "| --- | --- | --- |",
       f"| Episode {N} (YouTube) | {E}_thumbnail_1280x720.jpg | YouTube Studio → Details → Thumbnail → Upload file |"]
for t, x in order:
    if x != "EP":
        md.append(f"| {t} · Ep {N - 1} reel {x['id']} | {P}_reel{x['id']}_cover.jpg | Instagram: Edit cover → Add from "
                  "camera roll · TikTok: Edit cover → Upload · Shorts: pick the frame |")
md += ["", f"Episode {N}'s own reel covers ({E}_reel1-4_cover.jpg) are in today's folder, ready for tomorrow.", "",
       f"## YouTube: Episode {N}", "",
       f"Upload `{E}_full_quality.mp4`, add it to the AFTER THE HUM playlist after Episode {N - 1}, and make it the end "
       f"screen target on Episode {N - 1}.", "", "**Title** (pick one)", ""]
md += [f"- {t}" for t in kit["titles"]]
chap = "\n".join(f"{c['start']} {c['label']}" for c in kit["chapters"])
md += ["", "**Description**", "", "```", kit["description_hook"], "", kit["description_body"], "",
       "AFTER THE HUM is an original dark anime survival series. A new 5-minute episode every day: from a normal city, "
       "through the collapse, into the mountains and the fight to build a sanctuary.", "",
       "▶ Start from Episode 1: [link to Episode 1]", "▶ Full series playlist: [playlist link]", "", "Chapters", chap, "",
       f"New episode every day. Subscribe so you don't miss Episode {N + 1}" + (f": {NEXT_TITLE}." if NEXT_TITLE else "."),
       "", "Survival notes in this series are part of the story, not safety advice.", "", kit["hashtags"], "```", "",
       f"**Tags:** {', '.join(kit['tags'])}", "",
       "| Setting | Value |", "| --- | --- |",
       f"| Thumbnail | {E}_thumbnail_1280x720.jpg (text: {kit['thumbnail_text'].upper()}) |",
       f"| Subtitles | Upload {E}_subtitles_en.srt as English (already timed) |",
       f"| Playlist | AFTER THE HUM, position {N} |", "| Audience | Not made for kids |",
       "| Altered or synthetic content | Yes: AI-generated visuals and voices |", "| Category | Film & Animation |",
       f"| End screen | Subscribe button + Episode {N - 1} now, swap to Episode {N + 1} tomorrow |",
       "| Visibility | Schedule for 5:00 PM |", ""]
if PREV_REELS:
    md += [f"## Episode {N - 1} reels", "",
           "Same file on Instagram, TikTok and YouTube Shorts. Captions are burned in. Mark each as AI-generated "
           "(Instagram \"AI info\", TikTok \"AI-generated content\", YouTube \"altered or synthetic\") and set the Shorts "
           f"related video to Episode {N - 1}.", ""]
    for t, x in order:
        if x == "EP":
            continue
        k = rk.get(str(x["id"]), {})
        md += [f"### Reel {x['id']}: {x.get('angle', '')} ({t})", "", f"On-screen hook: {x['hook_text']}", "",
               "Instagram caption:", "", "```", k.get("instagram", x.get("caption", "")), "```", "",
               "TikTok caption:", "", "```", k.get("tiktok", ""), "```", "",
               "Shorts title:", "", "```", k.get("shorts_title", ""), "```", ""]
md += ["## Pinned comment and story", "", f"Pin this under Episode {N} on YouTube:", "", "```", kit["pinned_comment"],
       "```", "", "Instagram story at 5:00 PM: a frame from the episode with a link sticker to the video.", "", "```",
       kit["story_text"], "```", "",
       f"Poll sticker: \"{kit['poll']['question']}\" with {' / '.join(kit['poll']['options'])}.", "", "## Checklist", ""]
for t, x in order:
    md.append(f"- [ ] {t} — " + (f"Episode {N} on YouTube (upload at 4 PM, thumbnail, subtitles, playlist, end screen)"
                                 if x == "EP" else f"Ep {N - 1} reel {x['id']} on Instagram, TikTok, Shorts (with cover)"))
md += ["- [ ] 5:00 PM — Pin the comment, post the Instagram story", ""]
out = pathlib.Path("upload") / f"{E}_upload_kit.md"
out.write_text("\n".join(md))
print(out, "| thumbnail:", kit["thumbnail_text"], "shot", kit["thumbnail_shot"])
