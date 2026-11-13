"""Make one day of AFTER THE HUM end to end. Resumable: every step skips work that is already done, so re-running
after a failure continues where it stopped. Works on the Mac and in the cloud routine (Linux).

Usage: python3 run_day.py [N] [--date YYYY-MM-DD] [--until STEP]
  N defaults to the next episode after the last finished one (Drive "_state/state.json", else local state.json).
Steps: state, archive, write, frames, reels_plan, assemble, reels, covers, kit, drive, notion, save_state, desktop
Log: run_day.log. Ends by printing CHECKS for Claude (see ROUTINE.md) to review before the day is called done."""
import datetime, json, os, pathlib, re, shutil, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
os.chdir(HERE)
PY = str(HERE / ".venv/bin/python") if (HERE / ".venv/bin/python").exists() else sys.executable
KEYS = ["OPENAI_API_KEY", "ELEVENLABS_API_KEY", "DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL", "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN", "DRIVE_ROOT_ID", "NOTION_TOKEN", "NOTION_ROOT_PAGE"]
WORK = ["story.json", "STORY.md", "frames", "frames_v", "build", "audio", "reels", "reels.json", "reels_audio",
        "REELS.md", "kit.json"]
LOG = open(HERE / "run_day.log", "a")


def log(*a):
    msg = " ".join(map(str, a))
    print(msg, flush=True)
    LOG.write(f"{datetime.datetime.now():%H:%M:%S} {msg}\n"); LOG.flush()


def run(*cmd, env=None):
    log("$", " ".join(cmd))
    p = subprocess.run(cmd, env={**os.environ, **(env or {})}, stdout=LOG, stderr=subprocess.STDOUT)
    if p.returncode:
        raise SystemExit(f"FAILED: {' '.join(cmd)} (see run_day.log)")


def parallel(*cmds):
    procs = []
    for cmd in cmds:
        log("$ (bg)", " ".join(cmd))
        procs.append((cmd, subprocess.Popen(cmd, stdout=LOG, stderr=subprocess.STDOUT)))
    bad = [c for c, p in procs if p.wait()]
    if bad:
        raise SystemExit(f"FAILED: {bad} (see run_day.log)")


def ensure_env():
    """In the cloud the keys arrive as environment variables; the scripts read .env, so write it (gitignored, 600)."""
    env = HERE / ".env"
    have = env.read_text() if env.exists() else ""
    add = [f"{k}={os.environ[k]}" for k in KEYS if os.environ.get(k) and f"{k}=" not in have]
    if add:
        env.write_text(have + ("\n" if have and not have.endswith("\n") else "") + "\n".join(add) + "\n")
        os.chmod(env, 0o600)
    missing = [k for k in KEYS if k != "DRIVE_ROOT_ID" and f"{k}=" not in env.read_text()]
    if missing:
        raise SystemExit(f"Missing keys: {', '.join(missing)}")


def story_ep():
    p = HERE / "story.json"
    return int(json.loads(p.read_text())["episode"]) if p.exists() else None


def main():
    args = sys.argv[1:]
    date = args[args.index("--date") + 1] if "--date" in args else datetime.date.today().isoformat()
    until = args[args.index("--until") + 1] if "--until" in args else None
    nums = [a for a in args if a.isdigit()]
    ensure_env()
    sys.path.insert(0, str(HERE))
    from gdrive import Drive
    d = Drive()
    root = d.root()
    state_dir = d.folder("_state", root)

    # --- state: which episode is next; fetch yesterday's story/reels and character sheets if missing
    st = HERE / "state.json"
    remote = d.find("state.json", state_dir)
    if remote:
        d.download(remote["id"], st)
    last = json.loads(st.read_text())["last_episode"] if st.exists() else 2
    n = int(nums[0]) if nums else last + 1
    E, P = f"ep{n:02d}", f"ep{n - 1:02d}"
    log(f"=== Day {n} ({date}): Episode {n} ===")
    files = {f["name"]: f for f in d.list(state_dir)}
    for name in (f"{P}_story.json", f"{P}_reels.json"):
        dest = HERE / P / name.split("_", 1)[1]
        if not dest.exists() and story_ep() != n - 1 and name in files:
            d.download(files[name]["id"], dest)
    (HERE / "refs").mkdir(exist_ok=True)
    for name, f in files.items():
        if name.startswith("ref_") and not (HERE / "refs" / name[4:]).exists():
            d.download(f["id"], HERE / "refs" / name[4:])
    if until == "state":
        return

    # --- archive: yesterday's working files go into epNN-1/
    if story_ep() == n - 1:
        (HERE / P).mkdir(exist_ok=True)
        for w in WORK + [p.name for p in HERE.glob(f"{P}_*.mp4")]:
            if (HERE / w).exists():
                shutil.move(str(HERE / w), str(HERE / P / w))
        log(f"archived Episode {n - 1} into {P}/")

    # --- write: the script (story.json), then strip any text the writer put into the image prompts
    if story_ep() != n:
        run(PY, "write_episode.py", str(n))
        s = json.loads((HERE / "story.json").read_text())
        bad = re.compile(r"\b(caption|title card|subtitle|on-screen text|text reads|words? .{0,20}(appear|written))\b", re.I)
        for sh in s["shots"]:
            sh["poses"] = [bad.sub("", p) for p in sh["poses"]]
        (HERE / "story.json").write_text(json.dumps(s, indent=2))
    if until == "write":
        return

    # --- frames + audio + reel plan in parallel (Qwen allows ~2 calls at once; 429s retry on their own)
    if not (HERE / "frames" / "s25_4.png").exists() or not (HERE / "audio").exists() or not (HERE / "reels.json").exists():
        run(PY, "qwen_frames.py", "refs")
        parallel([PY, "qwen_frames.py", "shots", "1-25"], [PY, "audio.py"], [PY, "plan_reels.py"])
    if until == "frames":
        return

    # --- reels: narrator audio with word timings, then the vertical frames the reels use
    if not (HERE / "reels_audio").exists() or len(list((HERE / "reels_audio").glob("*.json"))) == 0:
        run(PY, "reel_audio.py")
    shots = subprocess.check_output([PY, "make_reels.py", "shots"], text=True).strip()
    run(PY, "qwen_frames.py", "shots", shots, env={"VERTICAL": "1"})
    if until == "reels_plan":
        return

    # --- the film, subtitles and reels
    title = re.sub(r"[^a-z0-9]+", "_", json.loads((HERE / "story.json").read_text())["title"].lower()).strip("_")
    film = HERE / f"{E}_{title}.mp4"
    up = HERE / "upload"; up.mkdir(exist_ok=True)
    if not film.exists():
        run(PY, "assemble.py", film.name)
    shutil.copy(film, up / f"{E}_full_quality.mp4")
    run(PY, "make_srt.py", f"upload/{E}_subtitles_en.srt")
    if until == "assemble":
        return
    if not all((HERE / "reels" / f"reel{k}.mp4").exists() for k in range(1, 5)):
        run(PY, "make_reels.py")
    for k in range(1, 5):
        shutil.copy(HERE / "reels" / f"reel{k}.mp4", up / f"{E}_reel{k}.mp4")
    if until == "reels":
        return

    # --- covers, then the kit (titles, descriptions, captions, thumbnail) into the dated Drive folder
    run(PY, "make_covers.py", str(n))
    folder = d.folder(f"{date} - Episode {n:02d}", root)
    url = f"https://drive.google.com/drive/folders/{folder}"
    if not (up / f"{E}_upload_kit.md").exists():
        run(PY, "write_kit.py", str(n), url)
    if until == "kit":
        return
    run(PY, "upload_drive.py", str(n), date)
    for k in range(1, 5):  # yesterday's reel covers are posted today; keep them next to today's guide
        c = up / f"{P}_reel{k}_cover.jpg"
        if c.exists():
            d.upload(c, folder)
    import notion
    pid = notion.page(f"Day {n} · {date} · Episode {n} upload kit", (up / f"{E}_upload_kit.md").read_text(), icon="🎬")
    log("notion:", "https://www.notion.so/" + pid.replace("-", ""))

    # --- save state for tomorrow
    for src, name in ((HERE / "story.json", f"{E}_story.json"), (HERE / "reels.json", f"{E}_reels.json")):
        tmp = HERE / name; shutil.copy(src, tmp); d.replace(tmp, state_dir); tmp.unlink()
    for ref in (HERE / "refs").glob("*.png"):
        if f"ref_{ref.name}" not in files:
            tmp = HERE / f"ref_{ref.name}"; shutil.copy(ref, tmp); d.upload(tmp, state_dir); tmp.unlink()
    st.write_text(json.dumps({"last_episode": n, "date": date}))
    d.replace(st, state_dir)

    # --- on the Mac, also drop the files on the Desktop
    desk = pathlib.Path.home() / "Desktop"
    if sys.platform == "darwin" and desk.exists():
        dest = desk / "After the Hum" / f"Episode {n}"
        dest.mkdir(parents=True, exist_ok=True)
        for f in up.glob(f"{E}_*"):
            shutil.copy(f, dest / f.name)

    kit = json.loads((HERE / "kit.json").read_text()) if (HERE / "kit.json").exists() else {}
    log("=== DONE ===")
    print("CHECKS (look at each before reporting the day as done):")
    print(f"  thumbnail: upload/{E}_thumbnail_1280x720.jpg  text={kit.get('thumbnail_text')!r} shot={kit.get('thumbnail_shot')}")
    print(f"  covers:    upload/{E}_reel1-4_cover.jpg")
    print(f"  film:      upload/{E}_full_quality.mp4  (hook 0-3s, rehooks ~1:40 and ~3:20, CTA at the end)")
    print(f"  reels:     upload/{E}_reel1-4.mp4  (captions, hook, 30-70 s)")
    print(f"  drive:     {url}")
    print(f"  notion:    https://www.notion.so/{pid.replace('-', '')}")


if __name__ == "__main__":
    main()
