"""Film frames with Qwen-Image 3.0 Pro (dark gritty anime look).

character sheets:  qwen_frames.py refs
shot frames:       qwen_frames.py shots 1-15      (VERTICAL=1 for 9:16 reel frames; "9:3" = shot 9, poses 1-3 only)
Pose 1 of each shot is drawn with the on-screen characters' sheets as references; poses 2-4 are edits of pose 1
(same framing, background and light), so only the characters move. Frames are saved at 1920x1080 / 1080x1920."""
import base64, json, os, pathlib, re, sys, time
from concurrent.futures import ThreadPoolExecutor
import requests
from PIL import Image

for line in pathlib.Path(".env").read_text().splitlines():
    k, _, v = line.partition("=")
    os.environ[k] = v

MODEL = "qwen-image-3.0-pro"
HOST = os.environ["DASHSCOPE_BASE_URL"].removesuffix("/compatible-mode/v1")
H = {"Authorization": f"Bearer {os.environ['DASHSCOPE_API_KEY']}", "Content-Type": "application/json"}
VERTICAL = os.environ.get("VERTICAL") == "1"
SIZE, OUT_WH = ("928*1664", (1080, 1920)) if VERTICAL else ("1664*928", (1920, 1080))
STORY = json.loads(pathlib.Path("story.json").read_text())
CHARS = {c["id"]: c for c in STORY["characters"] if c.get("on_screen", True)}
STYLE_REF = pathlib.Path("style_ref/dark_gritty_qwen.png")
REFS = pathlib.Path("refs"); FRAMES = pathlib.Path("frames_v" if VERTICAL else "frames")
STYLE = ("Dark mature seinen anime style, heavy black shadows, rough ink lines, muted desaturated palette, "
         "grim cinematic mood, faces still clearly readable.")
RULES = "All faces fully inside the frame. No captions, no subtitles, no watermark."


def data_url(path):
    return "data:image/png;base64," + base64.b64encode(pathlib.Path(path).read_bytes()).decode()


def call(images, text, size, dest, what, retries=8):
    """One generation; retries with backoff on the account's rate limit."""
    content = [{"image": data_url(p)} for p in images] + [{"text": text}]
    body = {"model": MODEL, "input": {"messages": [{"role": "user", "content": content}]},
            "parameters": {"size": size, "n": 1, "watermark": False, "prompt_extend": False}}
    for i in range(retries):
        try:
            r = requests.post(f"{HOST}/api/v1/services/aigc/multimodal-generation/generation", headers=H, json=body, timeout=300)
            j = r.json()
            if r.status_code >= 400:
                raise RuntimeError(f"{r.status_code} {j.get('code')} {j.get('message')}")
            url = j["output"]["choices"][0]["message"]["content"][0]["image"]
            dest.write_bytes(requests.get(url, timeout=120).content)
            with open("costs.jsonl", "a") as f:
                f.write(json.dumps({"service": "qwen-image", "what": what, "model": MODEL, "usage": j.get("usage")}) + "\n")
            return dest
        except Exception as e:
            print(f"{what} attempt {i+1}: {str(e)[:160]}", flush=True)
            time.sleep(min(60, 10 * (i + 1)))
    raise RuntimeError(f"{what} failed")


def fit(path, wh):
    """Resize + center-crop to exact 16:9 / 9:16 so the ffmpeg zoom math in assemble/make_reels holds."""
    im = Image.open(path).convert("RGB")
    s = max(wh[0] / im.width, wh[1] / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - wh[0]) // 2, (im.height - wh[1]) // 2
    im.crop((x, y, x + wh[0], y + wh[1])).save(path)


def refs():
    REFS.mkdir(exist_ok=True)
    for cid, c in CHARS.items():
        out = REFS / f"{cid}.png"
        if out.exists():
            continue
        text = (f"{STYLE} Character reference sheet: one character, full body, standing, front view, neutral "
                f"expression, plain dark grey background. {c['name']}: {c['tags']}. {c['bio']} No text.")
        text += " Match the art style of the reference image exactly; do not copy its characters or scene."
        call([STYLE_REF], text, "928*1664", out, f"ref_{cid}")
        print(f"ref {cid}: done", flush=True)


def overlay_text(s):
    """Words the script wants written on a prop (chalkboard, notebook): Qwen can draw them in the scene."""
    m = re.search(r"overlay on (\w+):\s*'([^']+)'", s["sfx"])
    return f' The {m.group(1)} shows the handwritten words "{m.group(2)}".' if m else ""


def shot(s, n_poses=4):
    cids = [c for c in s["characters"] if c in CHARS]
    who = " ".join(f"{CHARS[c]['name']} ({CHARS[c]['tags']})." for c in cids)
    refnote = ("Use the reference image(s) only for each character's face, hair and clothes; do not copy their pose "
               "or background. " if cids else "")
    shape = "Vertical 9:16 composition." if VERTICAL else "Wide 16:9 cinematic composition."
    base = (f"{STYLE} {shape} {refnote}Scene: {s['location']}. Camera: {s['framing']}. Background: {s['background']}. "
            f"Characters: {who or 'no named characters'}")
    first = FRAMES / f"s{s['id']:02d}_1.png"
    if not first.exists():
        call([REFS / f"{c}.png" for c in cids], f"{base} Action: {s['poses'][0]}.{overlay_text(s)} {RULES}",
             SIZE, first, f"{FRAMES.name}_s{s['id']}_1")
        fit(first, OUT_WH)

    def pose(i):
        out = FRAMES / f"s{s['id']:02d}_{i+1}.png"
        if not out.exists():
            text = (f"Edit this image: keep the exact same scene, camera framing, background, lighting, art style and "
                    f"the same characters with identical faces, hair and clothes. Change only their pose and "
                    f"expression to: {s['poses'][i]}. {RULES}")
            call([first], text, SIZE, out, f"{FRAMES.name}_s{s['id']}_{i+1}")
            fit(out, OUT_WH)
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(pose, range(1, min(n_poses, len(s["poses"])))))
    return f"shot {s['id']}: done"


def shots(ids):
    """ids: {shot id: how many poses to draw}."""
    FRAMES.mkdir(exist_ok=True)
    todo = [s for s in STORY["shots"] if s["id"] in ids]
    with ThreadPoolExecutor(max_workers=2) as ex:
        for res in ex.map(lambda s: shot(s, ids[s["id"]]), todo):
            print(res, flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "refs":
        refs()
    else:
        ids = {}
        for part in filter(None, sys.argv[2].split(",")):
            part, _, n = part.partition(":")
            a, _, b = part.partition("-")
            ids.update({i: int(n or 4) for i in range(int(a), int(b or a) + 1)})
        shots(ids)
