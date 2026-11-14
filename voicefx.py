"""Voice clean-up and the narration/dialogue treatments (viewer feedback 2026-11-14).

- Every voice clip: gentle high-pass, light FFT denoise, a little warmth and presence, de-ess, then loudness-matched
  (two-pass EBU R128, linear gain) so male and female voices sit at the same level and clarity.
- Narration (Nara's inner voice): warmer, with a soft short room tail, so it reads as "voice-over".
- Dialogue (lines spoken in the scene): dry and present, a touch brighter.

process(path, kind) returns the path of a cached .wav next to the input (audio/fx/<name>.wav). On ANY failure it
returns the original path, so the mix falls back to the old behaviour. Set VOICEFX=0 to switch it off entirely.
Usage (by hand): voicefx.py <in.mp3> narration|dialogue <out.wav>"""
import json, os, pathlib, subprocess, sys

TARGET_LUFS = -19.0
CLEAN = ("highpass=f=75,afftdn=nf=-50:tn=1,equalizer=f=200:t=q:w=1:g=1.5,"
         "equalizer=f=3500:t=q:w=1.2:g=2,highshelf=f=9000:g=1.5,deesser=i=0.25")
NARR_EQ = "equalizer=f=250:t=q:w=1:g=1.5,highshelf=f=7000:g=-1"   # warmer, softer top: an inner voice
DIAL_EQ = "equalizer=f=4500:t=q:w=1.5:g=1"                          # dry, present, in the scene
REVERB_WET = 0.16                                                   # narration room tail, kept subtle
HERE = pathlib.Path(__file__).resolve().parent


def _ff(*a):
    return subprocess.run(["ffmpeg", "-hide_banner", "-y", "-nostdin", *a], check=True, capture_output=True, text=True)


def _ir():
    """A soft 0.7 s room impulse response, made once with ffmpeg alone (no numpy needed)."""
    ir = HERE / "sfx_kit" / "narration_room_ir.wav"
    if not ir.exists():
        ir.parent.mkdir(exist_ok=True)
        _ff("-f", "lavfi", "-i", "anoisesrc=d=0.7:c=pink:a=0.5:r=44100:s=7",
            "-af", "afade=t=out:st=0:d=0.7:curve=exp,highpass=f=250,lowpass=f=4500", "-ac", "1", str(ir))
    return ir


def _chain(src, dst, kind):
    if kind == "narration":
        fc = (f"[0:a]aformat=sample_rates=44100:channel_layouts=mono,{CLEAN},{NARR_EQ},asplit[d][w];"
              f"[w][1:a]afir=dry=10:wet=10[r];[d][r]amix=inputs=2:weights='1 {REVERB_WET}':normalize=0[o]")
        _ff("-i", str(src), "-i", str(_ir()), "-filter_complex", fc, "-map", "[o]", "-ar", "44100", str(dst))
    else:
        _ff("-i", str(src), "-af", f"aformat=sample_rates=44100:channel_layouts=mono,{CLEAN},{DIAL_EQ}",
            "-ar", "44100", str(dst))


def _loudnorm(src, dst):
    out = _ff("-i", str(src), "-af", f"loudnorm=I={TARGET_LUFS}:TP=-2:LRA=11:print_format=json", "-f", "null", "-").stderr
    m = json.loads(out[out.rindex("{"):out.rindex("}") + 1])
    if float(m["input_i"]) < -70:  # silence: nothing to normalise
        _ff("-i", str(src), "-c", "copy", str(dst)); return
    _ff("-i", str(src), "-af",
        f"loudnorm=I={TARGET_LUFS}:TP=-2:LRA=11:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
        f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}",
        "-ar", "44100", str(dst))


def treat(src, kind, dst):
    src, dst = pathlib.Path(src), pathlib.Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.stem + ".tmp.wav")
    _chain(src, tmp, kind)
    _loudnorm(tmp, dst)
    tmp.unlink(missing_ok=True)
    return dst


def process(path, kind):
    """Cached treated copy of a voice clip; the original path if disabled or anything goes wrong."""
    path = pathlib.Path(path)
    if os.environ.get("VOICEFX", "1") == "0" or not path.exists():
        return path
    dst = path.parent / "fx" / f"{path.stem}.{kind}.wav"
    try:
        if not dst.exists() or dst.stat().st_mtime < path.stat().st_mtime:
            treat(path, kind, dst)
        return dst
    except Exception as e:  # never break the episode over polish
        print(f"voicefx: {path.name} untreated ({type(e).__name__}: {str(e)[:200]})", file=sys.stderr, flush=True)
        return path


if __name__ == "__main__":
    print(treat(sys.argv[1], sys.argv[2], sys.argv[3]))
