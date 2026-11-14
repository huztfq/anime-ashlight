# Handoff: AFTER THE HUM daily routine

For the Claude agent picking this up from a different Claude account. Read this, then `CLAUDE.md` (rules and
pipeline) and `ROUTINE.md` (the daily playbook). Written 2026-11-13.

## What this project is

**AFTER THE HUM** is an original dark anime survival series for the YouTube channel **Ashlight Stories**. The
suggested handle @ashlightanime isn't confirmed yet.
- **Cadence:** one 5-minute episode every day, plus 4 vertical reels per episode for Instagram, TikTok and YouTube
  Shorts.
- **Plan:** about 180 episodes, with the arc city → collapse → mountains → sanctuary.
- **Series bible:** `series.json` (cast, world, locations, episode outlines).

The owner (call them "the user") posts to the platforms by hand. Our job is to produce everything else, every day,
unattended:
- the episode video;
- 4 reels;
- a YouTube thumbnail and 4 reel covers;
- subtitles;
- an upload guide;
- a Google Drive folder and a Notion page.

## Your task

**Set up a daily scheduled routine (Claude Code cloud) that runs `ROUTINE.md` every morning.** Then do one test run
and confirm it finishes.

1. **Repo:** `huztfq/anime-ashlight` (public, branch `main`). Your GitHub connection only needs to read it.
   - **Never `git push`.** The day-to-day state lives in Google Drive, not git.
   - If your account can't see the repo in the routine's repo picker, the GitHub owner (huztfq) has to install the
     Claude GitHub App on that repo and/or add your GitHub account as a collaborator. Ask the user.
2. **Cloud environment:**
   - **Setup script:** the contents of `cloud_setup.sh`. It installs ffmpeg, requests and Pillow, and the
     M PLUS Rounded 1c ExtraBold title font.
   - **Network:** allow package managers, and these hosts:
     - `api.openai.com`
     - the DashScope host in `DASHSCOPE_BASE_URL` (normally `dashscope-intl.aliyuncs.com`)
     - `api.elevenlabs.io`
     - `oauth2.googleapis.com`
     - `www.googleapis.com`
     - `api.notion.com`
     - `github.com` and `raw.githubusercontent.com` (for the font)
   - **Environment variables:** the user pastes them from their local `anime/.env`. Never ask them to paste keys into
     chat, and never print them. The names:
     `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL`, `GOOGLE_CLIENT_ID`,
     `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `DRIVE_ROOT_ID`, `NOTION_TOKEN`, `NOTION_ROOT_PAGE`.
     (`ANTHROPIC_API_KEY` is not needed.) `run_day.py` writes them into a local `.env` at start, because every
     script reads `.env`.
3. **Schedule:** daily, about 6:00 AM in the user's time zone, so files are ready before the first 9 AM post.
4. **Prompt:**
   `Read CLAUDE.md, HANDOFF.md and ROUTINE.md, then make today's episode by following ROUTINE.md exactly. Do not git push.`
5. **Test:** use Run now and watch it.
   - A day takes 1–2 hours, mostly about 190 Qwen images at ~2 parallel calls.
   - Claude's docs list no total time limit for routines. Each command is capped at about 10 minutes in the
     foreground, so `run_day.py` runs in the background with `nohup` and is resumable.
   - If the session ends early, the next run continues from where it stopped (steps skip finished work).
   - Report back how long it took and whether it finished.

## Where things are (no secrets here)

| What | Where |
| --- | --- |
| Code + rules | GitHub `huztfq/anime-ashlight` (also on the user's Mac at `~/Documents/Projects/Inferaform/anime`) |
| Daily output | Google Drive → My Drive → `After the Hum/<YYYY-MM-DD> - Episode NN/` |
| State between days | Drive `After the Hum/_state/`: `state.json` (`last_episode`), `epNN_story.json`, `epNN_reels.json`, `ref_<character>.png`, `voices.json` (every designed voice id, so a character keeps one voice) |
| Upload guides | Notion page "After the Hum · Ashlight Stories" → "Day N · date · Episode N upload kit" sub-pages |
| Rules for you | Notion "Production Guide" (= CLAUDE.md) and "🤖 Daily Routine Playbook" (= ROUTINE.md) |

**Access details:**
- **Drive:** the Google OAuth client is a Desktop-app client in the user's Google Cloud project "inferaform"
  (published, so the refresh token doesn't expire). Its scope is `drive.file`: the app only sees files it created
  itself, which is everything under "After the Hum".
- **Notion:** internal integration "inferaform", connected to the root page.

## Status on 2026-11-13

| Episode | Status |
| --- | --- |
| **1** "Three Seconds at 7:17" | Done and in Drive (2026-11-11 folder), with the Day 1 Notion page |
| **2** "The Morning Without Birds" | Done and in Drive (2026-11-13 folder), with the Day 2 Notion page. Its 4 reels and covers are ready to post on Day 3 |
| **Next: 3** "The Water Is Listening" | `_state/state.json` says `last_episode: 2`, so the first routine run makes Episode 3 |

**Posting rhythm:** Day N = Episode N on YouTube at 5 PM, plus Episode N-1's four reels at 9 AM, 1 PM, 6 PM and
9 PM. The kit and the Notion page follow that rhythm automatically (`write_kit.py`).

## How a day is made (`run_day.py`, resumable)

1. **state:** Download yesterday's story, reels and character sheets from Drive `_state` and decide N.
2. **archive:** Move yesterday's working files into `epNN-1/`.
3. **write:** `write_episode.py N`, using OpenAI `gpt-5.6-sol`, writes a 25-shot script (`story.json`). It
   continues from yesterday and follows the hook rules in `hooks.py`.
4. **frames:** Qwen-Image 3.0 Pro (DashScope). The `refs` step draws character sheets, then 25 shots × 4 poses
   (pose 1 drawn from the references, poses 2–4 as edits of pose 1). ElevenLabs makes the narrator, lines,
   effects and score. `plan_reels.py` plans the 4 reels.
5. **reels_plan:** Reel narration with word timings, then vertical 9:16 frames for the shots the reels use.
6. **assemble:** The film (about 5:10; shots stretch past 12 s so voices never overlap), then `upload/epNN_full_quality.mp4` and `epNN_subtitles_en.srt`.
7. **reels:** 4 reels with burned-in captions, then `upload/epNN_reel1-4.mp4`.
8. **covers:** `make_covers.py`: 1080×1920 reel covers with the hook text in the centre-safe area.
9. **kit:** `write_kit.py` uses OpenAI to write titles, description, chapters, tags, reel captions and Shorts titles,
   the pinned comment, the story and a poll. It also picks the thumbnail frame and text, then `make_thumb.py`
   renders the 1280×720 thumbnail.
10. **drive, notion, save_state:** Upload everything, create the Notion page, then save state for tomorrow.

The dated Drive folder gets every `upload/epNN_*` file, plus yesterday's reel covers.

## Decisions the user already made (don't re-ask)

- **Images:** Qwen-Image 3.0 Pro, dark gritty seinen style matched to `style_ref/dark_gritty_qwen.png`. Same faces
  every episode, via `refs/`.
- **Writing:** OpenAI `gpt-5.6-sol`.
- **Audio:**
  - Narrator: ElevenLabs voice V1 "husky" (the id is in `voices.json`).
  - Music: M1 dark ambient.
- **Structure:**
  - Kallaway triple hook: spoken, visual and on-screen hook in the first 3 s.
  - Rehooks around 1:40 and 3:20, then a CTA.
  - Illusion of Novelty in every body block.
  - Sound on every cut: boom under the hook, whoosh on reel cuts, riser + hit into rehooks and the CTA.
- **On-screen text:** words pop in one by one, last word ember orange `#FF963C`. Reels always carry burned-in
  captions: the narrator in yellow, character lines in blue.
- **Thumbnails:** 2–3 words, last word ember orange, "AFTER THE HUM | EP N" small. The text must never cover a face.
- **Fonts:** Arial Rounded Bold on the Mac. In the cloud, M PLUS Rounded 1c ExtraBold, because the Apple font
  can't be redistributed.
- **Platforms:** label everything as AI-generated.
- **Secrets:** never print keys, never commit `.env`. Keys live only in `.env` and the cloud environment.

## Reels and short-form rules (must follow; learned from the user's reference reels)

The user gave five Instagram reels as must-follow techniques: `instagram.com/reel/Db-zJhiuXP3`, `DfRouHKyJvy`,
`DfiDTGiS7cO`, `DfaaI9aBqRH` (hooks and structure) and `De9yxpuIG6X` (sound design). Instagram blocks logged-out
viewing, so the lessons are already written into `hooks.py` (fed to every writer prompt), `motion.py`,
`sfx_kit.py`, `mix.py` and `make_reels.py`. Keep them all.

**Structure of every video (episode and reel)**
1. **Triple hook in the first 1–3 s.** The spoken hook (voice-over), the visual hook (the most striking frame) and
   the on-screen text hook (max 6 words) all point at the same idea at the same moment. Open a curiosity gap. Never
   start with setup, a title card or a logo.
2. **Proven hook shapes, said with tension.** Tonality matters more than wording; each shot's `delivery`
   (calm, tense, whisper, urgent) maps to ElevenLabs stability and style. The shapes:
   - the shocking specific fact ("At 7:17, every phone screamed.")
   - the "nobody noticed" reveal
   - the countdown ("We had nine minutes of water left.")
   - the contrarian warning ("Boiling it would have killed us.")
   - the confession
   - a cold-open line of dialogue
   - the impossible detail
   - the direct question
   - the "this is the moment…" flash-forward
   - before/after contrast
3. **Lock-in zone:** 2–3 short sentences right after the hook that raise the stakes and promise the payoff.
4. **Body → rehook → body → rehook → body.** A rehook is one line that re-opens curiosity ("But that wasn't the
   strange part."). In episodes the rehooks land around 1:40 and 3:20 (shots 9 and 17); reels have them at section
   starts.
5. **Illusion of Novelty (Kallaway)** in every body block and rehook:
   - a new reveal, presented as just discovered;
   - contrast framing ("Everyone filled bottles. That was the mistake.");
   - urgency (a clock or cost right now);
   - bullseye proof (one concrete visible thing: a gauge reading, a filament under a magnet, a number, a sound).
6. **The CTA matches what the viewer just felt.** Send them to the full episode ("Full episode on our channel, link
   in bio") or ask for a comment keyword or theory.
7. **Plain words:** the audience's own language, short sentences, emotional and specific, no filler.

**Reel specifics**
- **Four reels per episode, one angle each:** Cliffhanger, Survival skill, Moral choice, Mystery clue. They come
  from `plan_reels.py`; keep these angles because the posting schedule keys off them.
- **Format and length:** 1080×1920 vertical frames (made with `VERTICAL=1`), quick cuts. Aim for 30–50 s; the
  current reels run 53–70 s.
- **Hook card:** the on-screen hook pops in word by word at the top (about 20% down, size 100, 3 s), last word ember
  orange `#FF963C` on a dark rounded box.
- **CTA card:** at the end in the same style.
- **Captions are always burned in:**
  - narrator word by word, in groups of about 3 words, with the active word in yellow;
  - reused character lines in blue `#9FD8FF`.

  Never upload a reel without captions.
- **Sound on the exact frame, never a silent edit:**
  - a boom under the hook at 0 s;
  - a whoosh 0.2 s before every cut;
  - a riser and hit into each rehook and the CTA;
  - the score ducked under the voice.

  The effects come from the ElevenLabs-made kit in `sfx_kit/`, so no licence checks are needed. If you ever use
  outside sounds, check each licence.
- **Cover:** `epNN_reelK_cover.jpg`, 1080×1920, from the reel's opening frame without captions. The hook text sits
  in the lower-middle so faces stay visible, inside the centre 3:4 area that Instagram's profile grid keeps, with
  "AFTER THE HUM | EP N · PART K OF 4" underneath.
- **Same file everywhere:** one reel file goes to Instagram Reels, TikTok and YouTube Shorts. Only the text changes:
  - **Instagram:** a caption ending in "link in bio" (links don't work in captions) and 4–5 hashtags. Set the cover
    from the camera roll, turn on "Also share to feed", and add the "AI info" label.
  - **TikTok:** a shorter caption with 3 hashtags. Upload the cover, and turn on "AI-generated content" under
    More options.
  - **YouTube Shorts:** a Shorts title instead of a caption. Set "Related video" to the full episode (a one-tap
    link), mark altered or synthetic content, and add the AFTER THE HUM playlist. A custom cover can only be
    uploaded from the phone app, so otherwise pick the frame.
- **Posting order** (Day N, the user's local time):
  - 9 AM: Survival reel (the widest appeal, so it goes first).
  - 1 PM: Mystery reel (comments and theories).
  - 5 PM: Episode N on YouTube. Upload at 4 PM and schedule it, so it's processed in HD.
  - 6 PM: Cliffhanger reel (lands right after the new episode).
  - 9 PM: Moral-choice reel (night viewers comment most).
  - All four are Episode N-1's reels.

**YouTube episode specifics**
- **Title:** under 70 characters and always containing "AFTER THE HUM". The kit offers three to choose from.
- **Description:**
  - The first two lines carry the hook, since they show above "more".
  - Chapters start at 0:00, at least 10 s apart, using shot starts (12 s each).
  - A link to Episode 1 and the playlist.
  - "Subscribe so you don't miss Episode N+1: <title>."
  - "Survival notes are part of the story, not safety advice."
  - 3–5 hashtags.
- **Tags:** 15–20.
- **Settings:**
  - Not made for kids.
  - Altered or synthetic content: Yes.
  - Category: Film & Animation.
  - English subtitles from the `.srt`.
  - Playlist: AFTER THE HUM, at position N.
  - End screen: Subscribe plus the previous episode, swapped to the next episode the following day.
- **Pinned comment:** a question that tomorrow's episode answers, with "best theory gets pinned".
- **Instagram story at 5 PM:** an episode frame with a link sticker and a poll.
- **Never** paint captions or titles into the generated images; all text is added in editing. **No** gore, corpses,
  weapons or zombies.

## Changes from viewer feedback (2026-11-14)

- **Premise recap:** `write_episode.py` makes shot 2 a fresh narrated recap (what the Hum is, how far the city has
  fallen, where the characters are now) and keeps the world state clear in the episode. The YouTube description in the
  kit has a "The story so far" line plus "New episode every day. Voices and visuals are AI-generated." Don't add a
  season length or episode count (the user said no).
- **Voices:** Jun (a 17-year-old girl in the bible) had a low, lo-fi designed voice and Lio's was band-limited, which
  viewers heard as "a bad mic". Both now use premade ElevenLabs voices (Jessica, Liam); `audio.py` retries a line
  with the previous voice if one fails. ElevenLabs refuses to design under-18 voices, so pick premade voices for teens.
- **Narration vs dialogue:** `voicefx.py` (narration warm with a soft room tail, dialogue dry and present, all clips
  loudness-matched); narration subtitles in italics. Reels already colour narrator vs lines.
- **Cliffhangers are unchanged** on purpose.

## Lesson: voices never overlap, character voices are premade (Ep3 feedback, 2026-11-14)

The user: "male voice still feels weird, it starts when she's already speaking, and sounds like an echo voice".
- **Overlap cause:** `mix.py` placed a line at `min(after narration, 12 s - line)`, so when narration + line didn't
  fit a 12 s shot the line was pulled back on top of the narration. Ep3 had 11 overlapping lines (worst 3.1 s,
  shot 21), and shot 2's 14.2 s recap ran into shot 3's narration. **Rule:** speech is strictly sequential.
  `mix.plan()` puts narration at +0.5 s, then a 0.35 s gap, then the line, and **extends the shot** (last poses held
  longer) when it doesn't fit. `assemble.py`, `make_srt.py` and the mix all use the same plan, and `mix.check_gaps()`
  stops the build if two voices are closer than 0.25 s. Reels: `make_reels.py` starts a reused line 0.35 s into its
  shot, drops a line from a narrated section, and refuses to render if two speakers are under 0.25 s apart.
  Shots can now be longer than 12 s, so chapter times in the kit should come from `mix.plan()` (they were made
  from 12 s steps; small drift is OK, the chapters stay in order).
- **Echo cause:** Soren's *designed* ElevenLabs voice had a room/reverb baked into every take: the quiet 10% of each
  clip sat only ~37 dB under the peak (premade voices: ~-70 to -77 dB). The voicefx chain is dry for dialogue, so
  the echo came from the voice itself. **Rule:** design voices for the narrator only; every on-screen character gets
  a premade voice (`audio.PREMADE`, chosen by gender, first unused). Soren kept a redesigned voice that measures dry (-80 dB),
  because the fixed Ep3 uses it ("Brian" is the fallback). `audio.line_tts` prints a WARNING when a line's floor is above -48 dB (`audio.room_db`), so check the log for "sounds roomy".

## Known gaps and what to watch

- **`series.json` only outlines episodes 1–14.** From Episode 15 `write_episode.py` briefs the writer from the
  `weeks` / `months` arcs instead (`arc_outline`), so it no longer crashes; the titles and loglines are invented
  each day. Proper outlines (`plan_series.py`) would still give tighter plotting.
- **Reels run 53–70 s,** against a 30–50 s target the user liked. It's acceptable but could be tightened in
  `plan_reels.py`.
- **The thumbnail auto-pick can put the text over a face.** ROUTINE.md tells you to check visually and re-run
  `make_thumb.py` with another shot or pose.
- **Cost:** about $8 a day for images, plus OpenAI and ElevenLabs. `costs.jsonl` logs each call.
- **Still waiting on the user:** the logo choice (drafts under `brand/`, not in the repo), handle confirmation, and
  the playlist and Episode 1 links for the descriptions (placeholders say `[link to Episode 1]`).
- **Not in scope:** posting to YouTube, Instagram or TikTok. The user does that by hand from the Notion checklist.

## How the user likes to work

- Keep messages short and plain.
- Send finished files rather than describing them.
- Don't re-ask settled decisions.
- When something fails unattended, leave a "Day N · date · ⚠️ needs attention" Notion page explaining what
  happened, instead of shipping something broken.
