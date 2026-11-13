# Daily routine: make today's AFTER THE HUM episode

You are running unattended (usually in the cloud, no Mac, nobody to ask). Read `CLAUDE.md` first: every rule there
applies. The goal each day: Episode N (5:09 film), its 4 reels, thumbnail and reel covers, subtitles and the Day N
upload kit, all in Google Drive (`After the Hum/<date> - Episode NN`) and a Notion page "Day N · date · Episode N
upload kit". Posting to YouTube, Instagram and TikTok is done by the user, never by you.

## 1. Run it

```bash
cd anime   # if the repo root is not already this folder
nohup python3 run_day.py > run_day.out 2>&1 &
```

It is resumable and takes 1–2 hours (about 190 Qwen images at ~2 at a time). Check progress with
`tail -5 run_day.log` every few minutes; don't sleep-loop on it. If it stops with `FAILED`, read the end of
`run_day.log`, fix the cause, and start it again: finished steps are skipped. Retry a failing step at most 3 times.
`--until write` stops after the script so you can review it first.

## 2. Review before it continues (do these checks yourself)

After `write` (story.json exists for episode N):
- Continuity with `epNN-1/story.json` and `series.json`: same names, injuries, supplies, open threads; the episode
  follows `series.json → episodes[n]` (title, logline, cliffhanger) when it is there.
- Hook rules from `hooks.py`: shot 1 hook is spoken + visual + on-screen at once (max 6 words); rehooks around shot
  9 and 17; CTA on the last shot; every body block has a new reveal, contrast, urgency and a concrete proof.
- No pose asks for text, captions or titles to be painted into the image. Remove any that do.
- No gore, corpses or weapons (see the story's `negative`). If the script fails these, fix story.json by hand
  (keep 25 shots, 4 poses each) or delete it and re-run (it rewrites).

After `frames`: open 6–8 frames across the episode (`frames/sNN_1.png`). Same faces as `refs/`, no painted text,
no extra fingers or broken faces on the main characters. Delete a bad pose PNG and re-run to redraw it.

After it finishes (the CHECKS list at the end):
- Thumbnail: open it. The words must not cover a face and must read at phone size. If they do cover a face, re-run
  `python3 make_thumb.py N <other shot> "<text>" [pose]` and update `thumbnail_shot`/`thumbnail_text` in kit.json.
- Reel covers: open all 4; hook text readable, faces visible.
- Film: `ffprobe` duration about 5:09; spot-check frames at 0:01 (hook text), ~1:40 and ~3:20 (rehooks), the end (CTA).
- Reels: 4 files, each 30–70 s, captions burned in.
- Kit (`upload/epNN_upload_kit.md`): 3 titles with "AFTER THE HUM", chapters starting 0:00, reel captions present.
- Drive folder and Notion page links open and list everything.
If you changed the thumbnail or the kit after the upload, re-run `python3 upload_drive.py N <date>` and
`python3 -c "import notion; notion.page('Day N · <date> · Episode N upload kit', open('upload/epNN_upload_kit.md').read(), icon='🎬')"`.

## 3. When to stop instead of shipping

Don't upload something broken. If after 3 attempts a step still fails (API down, keys rejected, out of credit),
create the Notion page `Day N · <date> · ⚠️ needs attention` with what failed, the last 30 lines of `run_day.log`,
and what you already tried. Never print or commit keys. Never `git push` (the routine has read-only access; state
lives in Drive `_state/`).

## 4. Report

End with a short summary: episode title, Drive link, Notion link, the thumbnail text, anything you fixed by hand,
and the day's API cost if `costs.jsonl` shows it.
