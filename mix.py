"""Mix score (ducked under voices) + per-shot SFX + narration + character lines. Usage: mix.py out.m4a [lo-hi]"""
import json, math, pathlib, subprocess, sys
try:  # cleaned + loudness-matched voices (voicefx.py); returns the raw file on any failure
    from voicefx import process as voice_fx
except Exception:  # keep the old behaviour if the module is missing or broken
    def voice_fx(path, kind):
        return path

TITLE_S, SHOT_S, END_S = 0, 12, 9  # hook-first: no title card before shot 1
SCORE_OFFSET = 6  # the score was composed with a 6s intro; start on the music
STORY = json.loads(pathlib.Path("story.json").read_text())
A = pathlib.Path("audio")


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]))


# Speech timeline (viewer feedback 2026-11-14, Ep3: "the male voice starts while she's still speaking").
# The old placement put a character line at min(after narration, end of shot - line), so whenever narration + line
# didn't fit in 12 s the line was pulled back on top of the narration (up to 3.1 s of overlap in Ep3), and a
# narration longer than 12 s ran into the next shot's narration. Now speech is strictly sequential: narration,
# then a GAP of silence, then the line, and a shot is EXTENDED (its last pose held longer) when the speech doesn't
# fit. Durations are measured on the treated clips that are actually mixed. make_srt.py and assemble.py use the
# same plan, so subtitles, text cards and video stay in sync.
LEAD = 0.5   # silence at the start of a shot before the first voice
GAP = 0.35   # minimum silence between two voices (narration has a short room tail, so a bit more than 0.25 s)
TAIL = 0.45  # silence after the last voice before the shot cuts
FPS_GRID = 0.04  # shot lengths are rounded up to whole 25 fps frames


def plan(lo=1, hi=None):
    """[{id, t0, len, vo: (path, start, end) | None, line: (path, start, end) | None}] for shots lo..hi."""
    hi = hi or len(STORY["shots"])
    out, t0 = [], TITLE_S
    for s in STORY["shots"]:
        if not lo <= s["id"] <= hi:
            continue
        p = {"id": s["id"], "t0": t0, "vo": None, "line": None}
        t = t0 + LEAD
        vo = A / f"vo{s['id']:02d}.mp3"
        if vo.exists():
            f = voice_fx(vo, "narration"); d = dur(f)
            p["vo"] = (f, t, t + d); t += d + GAP
        line = A / f"line{s['id']:02d}.mp3"
        if line.exists():
            f = voice_fx(line, "dialogue"); d = dur(f)
            p["line"] = (f, t, t + d); t += d + GAP
        need = (t - GAP if (p["vo"] or p["line"]) else t0) + TAIL - t0
        p["len"] = max(SHOT_S, math.ceil(round(need / FPS_GRID, 6)) * FPS_GRID)
        out.append(p); t0 += p["len"]
    return out


def speech_spans(pl):
    """(start, end, who) for every voice in the plan, in order: used by the overlap check."""
    sp = []
    for p in pl:
        if p["vo"]:
            sp.append((p["vo"][1], p["vo"][2], "narrator"))
        if p["line"]:
            ch = next(s for s in STORY["shots"] if s["id"] == p["id"])["line"]["character"]
            sp.append((p["line"][1], p["line"][2], ch))
    return sp


def check_gaps(pl, min_gap=0.25):
    """Raise if any two voices overlap or sit closer than min_gap (never ship overlapping speakers)."""
    sp = speech_spans(pl)
    worst = min((b[0] - a[1] for a, b in zip(sp, sp[1:])), default=99)
    if worst < min_gap:
        raise SystemExit(f"speech overlap/too close: min gap {worst:.2f}s < {min_gap}s")
    return worst


def mix(out, lo=1, hi=None):
    hi = hi or len(STORY["shots"])
    pl = plan(lo, hi)
    check_gaps(pl)
    starts = {p["id"]: p["t0"] for p in pl}
    total = sum(p["len"] for p in pl) + END_S
    # the score is capped at the music model's max length, so loop it under longer episodes
    ins, parts, sfx, voice = ["-stream_loop", "-1", "-i", str(A / "score.mp3")], [], [], []

    def add(path, start, label, extra=""):
        ins.extend(["-i", str(path)])
        ms = int(round(start * 1000))
        parts.append(f"[{sum(a == '-i' for a in ins) - 1}]{extra}adelay={ms}|{ms}[{label}]")

    for p in pl:
        i, t0, L = p["id"], p["t0"], p["len"]
        # ambience is 12 s; an extended shot loops it so the room doesn't drop out
        ins.extend(["-stream_loop", "-1"])
        add(A / f"sfx{i:02d}.mp3", t0, f"s{i}", f"atrim=0:{L},afade=in:d=0.4,afade=out:st={L-0.6}:d=0.6,")
        sfx.append(f"[s{i}]")
        if p["vo"]:
            add(p["vo"][0], p["vo"][1], f"v{i}"); voice.append(f"[v{i}]")
        if p["line"]:
            add(p["line"][0], p["line"][1], f"l{i}"); voice.append(f"[l{i}]")
    # sound design on the text cards (same times as assemble.py): boom under the hook, riser + hit into each rehook and the CTA
    fx, kit = [], pathlib.Path("sfx_kit")
    cues = [("boom", 0, 0.8)]
    for sid in (9, 17):
        if lo <= sid <= hi:
            t = starts[sid] + 0.4
            cues += [("riser", t - 2.5, 0.45), ("hit", t, 0.7)]
    if hi == len(STORY["shots"]):
        cues += [("riser", pl[-1]["t0"] + 3.5, 0.45), ("hit", pl[-1]["t0"] + 6, 0.7)]
    for name, t, vol in cues:
        if (kit / f"{name}.mp3").exists():
            add(kit / f"{name}.mp3", t, f"k{len(fx)}", f"volume={vol},"); fx.append(f"[k{len(fx)}]")
    # score was composed for the full film: play it from this range's start, with the title section first
    start = SCORE_OFFSET + SHOT_S * (lo - 1)
    fc = ";".join(parts + [
        f"[0]atrim={start}:{start + total},asetpts=PTS-STARTPTS,volume=0.6,afade=out:st={total-4}:d=4[mus]",
        f"{''.join(sfx)}amix=inputs={len(sfx)}:normalize=0,volume=0.4[sfx]",
        f"{''.join(voice)}amix=inputs={len(voice)}:normalize=0,apad,atrim=0:{total},volume=1.3,asplit[vo][key]",
        "[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=600[duck]",
        f"{''.join(fx)}amix=inputs={len(fx)}:normalize=0[fx]",
        "[duck][sfx][vo][fx]amix=inputs=4:normalize=0,alimiter=limit=0.95[out]"])
    subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", fc, "-map", "[out]",
                    "-t", str(total), "-c:a", "aac", "-b:a", "256k", out], check=True)
    return out


if __name__ == "__main__":
    lo, hi = map(int, (sys.argv[2] if len(sys.argv) > 2 else f"1-{len(STORY['shots'])}").split("-"))
    print(mix(sys.argv[1], lo, hi))
