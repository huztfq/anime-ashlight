"""Mix score (ducked under voices) + per-shot SFX + narration + character lines. Usage: mix.py out.m4a [lo-hi]"""
import json, pathlib, subprocess, sys

TITLE_S, SHOT_S, END_S = 0, 12, 9  # hook-first: no title card before shot 1
SCORE_OFFSET = 6  # the score was composed with a 6s intro; start on the music
STORY = json.loads(pathlib.Path("story.json").read_text())
A = pathlib.Path("audio")


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]))


LEAD, GAP, TAIL = 0.6, 0.4, 0.6  # silence before the narrator, between narrator and line, after the last voice


def layout(lo=1, hi=None):
    """{shot id: {start, len, vo, line}} in seconds from the start of shot `lo`. A shot lasts SHOT_S unless its
    narration plus character line need longer; then it stretches, so a line never plays over the narrator.
    Shared by mix.py, assemble.py, make_srt.py and write_kit.py so picture, sound, subtitles and chapters agree."""
    hi = hi or len(STORY["shots"])
    out, t = {}, TITLE_S
    for s in STORY["shots"]:
        if not lo <= s["id"] <= hi:
            continue
        vo, line = A / f"vo{s['id']:02d}.mp3", A / f"line{s['id']:02d}.mp3"
        tv = end = t + LEAD
        if vo.exists():
            end = tv + dur(vo)
        tl = None
        if line.exists():
            tl = end + GAP if vo.exists() else tv
            end = tl + dur(line)
        out[s["id"]] = {"start": t, "len": max(SHOT_S, round(end - t + TAIL, 2)), "vo": tv, "line": tl}
        t += out[s["id"]]["len"]
    return out


def total_len(L):
    return sum(x["len"] for x in L.values()) + END_S


def mix(out, lo=1, hi=None):
    hi = hi or len(STORY["shots"])
    L = layout(lo, hi)
    total = total_len(L)
    # the score is capped at the music model's max length, so loop it under longer episodes
    ins, parts, sfx, voice = ["-stream_loop", "-1", "-i", str(A / "score.mp3")], [], [], []

    def add(path, start, label, extra=""):
        ins.extend(["-i", str(path)])
        ms = int(start * 1000)
        parts.append(f"[{sum(a == '-i' for a in ins) - 1}]{extra}adelay={ms}|{ms}[{label}]")

    for sid, x in L.items():
        n = x["len"]  # ambience was made 12 s long; pad with silence under a stretched shot
        add(A / f"sfx{sid:02d}.mp3", x["start"], f"s{sid}",
            f"apad,atrim=0:{n},afade=in:d=0.4,afade=out:st={n - 0.6}:d=0.6,")
        sfx.append(f"[s{sid}]")
        if (A / f"vo{sid:02d}.mp3").exists():
            add(A / f"vo{sid:02d}.mp3", x["vo"], f"v{sid}"); voice.append(f"[v{sid}]")
        if x["line"] is not None:
            add(A / f"line{sid:02d}.mp3", x["line"], f"l{sid}"); voice.append(f"[l{sid}]")
    # sound design on the text cards (same times as assemble.py): boom under the hook, riser + hit into each rehook and the CTA
    fx, kit = [], pathlib.Path("sfx_kit")
    cues = [("boom", 0, 0.8)]
    for sid in (9, 17):
        if sid in L:
            t = L[sid]["start"] + 0.4
            cues += [("riser", t - 2.5, 0.45), ("hit", t, 0.7)]
    if hi == len(STORY["shots"]):
        cues += [("riser", L[hi]["start"] + 3.5, 0.45), ("hit", L[hi]["start"] + 6, 0.7)]
    for name, t, vol in cues:
        if (kit / f"{name}.mp3").exists():
            add(kit / f"{name}.mp3", t, f"k{len(fx)}", f"volume={vol},"); fx.append(f"[k{len(fx)}]")
    # score was composed for the full film: play it from this range's start, with the title section first
    start = SCORE_OFFSET + (layout()[lo]["start"] if lo > 1 else 0)
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
