# AFTER THE HUM (Ashlight Stories)

Daily 5-minute dark anime survival episodes for YouTube, plus 4 vertical reels per episode for Instagram, TikTok and
YouTube Shorts. Planned run: 180 episodes, city → collapse → mountains → sanctuary. Series bible: `series.json`.

## Decisions already made (don't re-ask)
- Images: Qwen-Image 3.0 Pro (DashScope API), dark gritty seinen style matched to `style_ref/dark_gritty_qwen.png`.
- Writing: OpenAI `gpt-5.6-sol`, reasoning effort high.
- Audio: ElevenLabs. Narrator = V1 "husky" (voice id in `voices.json` → `narrator`), score style = M1 dark ambient.
- Channel: Ashlight Stories, suggested handle @ashlightanime (not confirmed). Logo not picked yet (`brand/logo2_*`).
- Local LoRA fallback (Animagine + kohya in `~/lora/sd-scripts`) is postponed; the user installs the trainer venv.
- Keys live in `.env` (chmod 600). Never print them.

## Make episode N
**One command:** `python3 run_day.py` does every step below (resumable; state in Drive `_state/`). The unattended
daily routine follows `ROUTINE.md` (checks to do yourself, when to stop). Cloud setup: `cloud_setup.sh`.
Thumbnails: `make_thumb.py`; reel covers 1080x1920: `make_covers.py`; the day's kit + thumbnail: `write_kit.py`.

The steps it runs (by hand: from this folder with `.venv/bin/python`):
1. Move the last episode's working files into `ep{N-1:02d}/`: story.json STORY.md frames frames_v build audio reels
   reels.json reels_audio REELS.md and the episode mp4s. `refs/`, `voices.json`, `sfx_kit/` stay (shared).
2. `write_episode.py N` → story.json + STORY.md (continues from `ep{N-1}/story.json`, keeps character tags).
   Check no pose asks for a caption or title painted into the image; strip it if it does.
3. In parallel: `qwen_frames.py refs` (only new characters), `qwen_frames.py shots 1-25`, `audio.py`, `plan_reels.py`.
4. `reel_audio.py`, then `VERTICAL=1 qwen_frames.py shots $(make_reels.py shots)` once the wide frames are done
   (Qwen rate-limits at ~2 parallel calls; 429s retry on their own). About 190 images, roughly $8 an episode.
5. `assemble.py epNN_title.mp4`, `make_srt.py upload/epNN_subtitles_en.srt`, `make_reels.py`.
6. Thumbnail 1280x720: the strongest frame, a 2-3 word line in Arial Rounded Bold with the last word ember orange,
   "AFTER THE HUM | EP N" small. Phone copy under 30 MB (1280x720, ~520 kbps) for SendUserFile.
7. Copy to `~/Desktop/After the Hum/Episode N/` and write that day's upload kit as a Claude Doc. Also save the kit
   as `upload/epNN_upload_kit.pdf` (docs `export` with container kind "project", file = the tab id, format pdf;
   decode the base64 from the saved result).
8. `python3 upload_drive.py N` → Google Drive `My Drive/After the Hum/<YYYY-MM-DD> - Episode NN/` with every
   `upload/epNN_*` file. Stdlib only, re-runnable (skips files already there). Auth: `GOOGLE_CLIENT_ID`,
   `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` in `.env` (one-time `google_auth.py`); `DRIVE_ROOT_ID` is set
   automatically. Scope is drive.file, so the app only sees the folders it made.
9. Notion: write the kit as `upload/epNN_upload_kit.md` (a Drive-folder callout on top, a to-do checklist at the end),
   then `notion.page("Day N · YYYY-MM-DD · Episode N upload kit", md, icon="🎬")`. If CLAUDE.md changed,
   `python3 notion.py page "Production Guide" CLAUDE.md` (same title replaces the page's contents). Integration
   "inferaform"; `NOTION_TOKEN` and `NOTION_ROOT_PAGE` in `.env`.

Don't use `pgrep -f` with a pattern that also matches the waiting shell's own command line; use `"[q]wen_frames"`.

## Rules learned from the user's reference reels
- Kallaway Triple Hook: spoken + visual + on-screen hook in the first 3 s, then lock-in, body, rehook (~1:40),
  body, rehook (~3:20), body, cliffhanger + CTA (`hooks.py`, fed to every writer prompt).
- Kallaway Illusion of Novelty in body blocks and rehooks: new reveal → contrast framing → urgency → bullseye proof.
- Proven hook shapes said with tension: tonality per shot (`delivery`: calm/tense/whisper/urgent → TTS settings).
- Motion graphics: hook, rehook and CTA text pop in word by word, last word ember orange (`motion.py`).
- Sound design on the exact frame (no silent edits): boom under the hook, whoosh on every reel cut, riser + hit into
  each rehook and the CTA (`sfx_kit.py` once, used by `mix.py` and `make_reels.py`). Kit is ElevenLabs-made, so no
  licence checks; if outside sounds are ever used (e.g. Openverse), check each licence.
- Reels always carry burned-in captions: narrator word by word (yellow active word), character lines in blue.

## Reference reels (required)
Before writing or reviewing any reel, read REFERENCE_REELS.md and apply its rules and scoring in the three-way review.
