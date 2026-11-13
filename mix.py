"""Mix score (ducked under voices) + per-shot SFX + narration + character lines. Usage: mix.py out.m4a [lo-hi]"""
import json, pathlib, subprocess, sys

TITLE_S, SHOT_S, END_S = 0, 12, 9  # hook-first: no title card before shot 1
SCORE_OFFSET = 6  # the score was composed with a 6s intro; start on the music
STORY = json.loads(pathlib.Path("story.json").read_text())
A = pathlib.Path("audio")


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]))


def mix(out, lo=1, hi=None):
    hi = hi or len(STORY["shots"])
    shots = [s for s in STORY["shots"] if lo <= s["id"] <= hi]
    total = TITLE_S + SHOT_S * len(shots) + END_S
    full = TITLE_S + SHOT_S * len(STORY["shots"]) + END_S
    # the score is capped at the music model's max length, so loop it under longer episodes
    ins, parts, sfx, voice = ["-stream_loop", "-1", "-i", str(A / "score.mp3")], [], [], []

    def add(path, start, label, extra=""):
        ins.extend(["-i", str(path)])
        ms = int(start * 1000)
        parts.append(f"[{sum(a == '-i' for a in ins) - 1}]{extra}adelay={ms}|{ms}[{label}]")

    for s in shots:
        t0 = TITLE_S + SHOT_S * (s["id"] - lo)
        add(A / f"sfx{s['id']:02d}.mp3", t0, f"s{s['id']}",
            f"atrim=0:{SHOT_S},afade=in:d=0.4,afade=out:st={SHOT_S-0.6}:d=0.6,")
        sfx.append(f"[s{s['id']}]")
        t = t0 + 0.6
        vo = A / f"vo{s['id']:02d}.mp3"
        if vo.exists():
            add(vo, t, f"v{s['id']}"); voice.append(f"[v{s['id']}]")
            t += dur(vo) + 0.4
        line = A / f"line{s['id']:02d}.mp3"
        if line.exists():
            add(line, min(t, t0 + SHOT_S - dur(line) - 0.2), f"l{s['id']}"); voice.append(f"[l{s['id']}]")
    # sound design on the text cards (same times as assemble.py): boom under the hook, riser + hit into each rehook and the CTA
    fx, kit = [], pathlib.Path("sfx_kit")
    cues = [("boom", 0, 0.8)]
    for sid in (9, 17):
        if lo <= sid <= hi:
            t = SHOT_S * (sid - lo) + 0.4
            cues += [("riser", t - 2.5, 0.45), ("hit", t, 0.7)]
    if hi == len(STORY["shots"]):
        cues += [("riser", SHOT_S * (len(shots) - 1) + 3.5, 0.45), ("hit", SHOT_S * (len(shots) - 1) + 6, 0.7)]
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
