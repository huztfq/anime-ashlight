# World shorts: "From the world of AFTER THE HUM" (from Huzaifa, 2026-11-14)

Standalone 30-45 s vertical mini stories set in the AFTER THE HUM world, posted to YouTube Shorts and Instagram
Reels alongside the episode reels. Someone who has never seen an episode must understand each one completely.
Same anime style, same pipeline, same voices. Read REFERENCE_REELS.md first; everything there applies.

## Story rules
- **One small moment, one side character (or a main character on a side moment), one twist.** It must not
  contradict `series.json` or anything already aired, and it must not spoil major upcoming plot (who is behind the
  Hum, Greyglass, the Held, Sela). Hint, never explain.
- **Self-contained:** name the character and give one line of who they are. No "as you saw in episode N", no
  episode numbers, no season length or episode count.
- **Story loop:** care (who they are, what they want) -> curious (an impossible detail) -> surprise (a reveal with
  one concrete piece of proof: a number, a sound, a light) -> rehook (a last line that reframes it, e.g. "That was
  the night before the city went quiet.").
- **Pay off the hook.** The hook's question is answered or clearly advanced by the end.
- **Shareable moment:** one eerie beat worth sending to a friend.
- **Content:** no gore, corpses, weapons or zombies. The Held, if shown at all, only as silhouettes, sounds or
  reflections.

## Format
- 1080x1920, full 9:16 frame, 30-45 s (aim ~42 s), captions burned in.
- **0-2 s:** the spoken line "From the world of After the Hum." finishes by ~2.1 s (generate it as its own section
  and keep the take that does: stability ~0.7, speed ~1.15) while two cards are on screen from frame 0: a small
  label "FROM THE WORLD OF AFTER THE HUM" (top, y 0.085) and the hook card (max 6 words, y 0.2).
  The first frame is the character's face, never an empty establishing shot.
- **Visual change every 2-4 s:** 10-12 shots, 4 poses each (make_reels cycles ~1.3 s per pose with a push-in).
- **Text:** narrator captions word by word (yellow active word), character lines in blue, at y 0.7. Compose every
  shot with the face in the middle third so neither the hook card nor captions cover it.
- **End:** comment CTA card ("<A> or <B>? Comment your theory." / "Comment <WORD> if ..."), spoken and on screen,
  over a shot with no face, plus a small line "Voices and visuals are AI-generated". No link or DM promises.

## Voices and sound
- Narrator: `voices.json` -> `narrator` (Nara's voice; she can tell a side character's story in third person),
  ElevenLabs speed ~1.12. Jun = "Jessica", Lio = "Liam". All voices go through `voicefx.py` (narration warm with a
  room tail, dialogue dry) via make_reels.
- Sound kit on the exact frame: boom at 0, whoosh on cuts, riser + hit into rehooks and the CTA, score ducked.

## How to make one (worked example + scripts: `world_shorts/` in this repo; run them from a work folder)
1. Make a work folder and symlink `.env refs style_ref sfx_kit voices.json series.json` from the repo.
2. Write `story.json` (title, logline, hook_text, cta_text, characters with the canonical tags, 10-12 shots with
   4 poses, `line` for 1-2 character lines, `sfx`) and `reels.json` (one reel, sections hook / hook2 / lock_in /
   body1 / rehook1 / body2 / rehook2 / body3 / closing / cta; a section with empty `vo` + `use_line` plays a line).
   Empty-sky shots must say "no people" or Qwen adds a figure.
3. `VERTICAL=1 python3 <repo>/qwen_frames.py shots 1-12` (new side characters: `qwen_frames.py refs` first).
4. Lines, per-shot ambience, score: `ws_audio.py`; narrator sections with word timings: `ws_vo.py`, then `ws_tighten.py` (cuts long pauses, 1.07x tempo).
5. `python3 ws_build.py wsNN.mp4` (make_reels.py with a 0.15 s VO gap, the world label and the AI line).
6. Three-way review (Claude + OpenAI + Grok Bot) with REFERENCE_REELS.md scoring on a contact sheet of frames
   every 2 s + the script; fix anything two reviewers score 2 or below, re-render.
7. Caption: one punchy line, the CTA question, "Full episodes on YouTube, link in bio", "New episode every day.",
   "Voices and visuals are AI-generated.", #AfterTheHum + up to 4 trending tags. Shorts title under 70 characters
   with "AFTER THE HUM". Save `/workspace/ashlight/world_shorts/wsNN.mp4` + `wsNN_caption.md`.
8. Posting: AI label on every platform; Shorts "Related video" = latest episode.

## Lessons from ws02 (2026-11-14; scripts in `world_shorts/ws02/`)
- While `run_day.py` runs, Qwen belongs to the episode: draw world-short frames one call at a time (`ws_frames_seq.py`).
- Recurring props (phone tray, wall of screens, watch, clock) are drawn once by Qwen and switched on/off in code
  (`ws_screens.py`) so they never move between poses; on-screen numbers are drawn in code, not left to Qwen.
- `ws_lift.py`: per-frame gamma lift to mean luma ~44 (unlifted copies in `raw/`), so night frames read on a phone.
- If Qwen puts the opening face under the hook card (y 0.2), shift that shot down (`ws_shift.py`).
- `ws_build.py`: captions on a dark box, groups close at sentence ends and commas, character lines in 4-word groups,
  and no low caption while the spoken hook repeats the hook card.
- Name the character and what they do in the first narrated line; keep times consistent (the reviewers catch it).
