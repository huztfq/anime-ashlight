"""Local image generation through a running ComfyUI (Animagine XL 4.0 + IP-Adapter).

reference sheets:  comfy.py refs
shot frames:       comfy.py shots 1-5        (VERTICAL=1 for 9:16 reel frames)
Each shot: pose 1 is drawn from scratch (with the character reference via IP-Adapter); poses 2-4 are img2img
from pose 1 with the same seed, so background and framing stay put and only the pose/expression changes."""
import json, os, pathlib, sys, time, uuid
import requests
from PIL import Image

URL = "http://127.0.0.1:8188"
COMFY_INPUT = pathlib.Path.home() / "ComfyUI/input"
CKPT = "animagine-xl-4.0.safetensors"
VERTICAL = os.environ.get("VERTICAL") == "1"  # 9:16 frames for reels
W, H = (768, 1344) if VERTICAL else (1344, 768)  # SDXL buckets
STORY = json.loads(pathlib.Path("story.json").read_text())
CHARS = {c["id"]: c for c in STORY["characters"]}
REFS = pathlib.Path("refs"); FRAMES = pathlib.Path("frames_v" if VERTICAL else "frames")
QUALITY = "masterpiece, high score, great score, absurdres"
NEG = ("lowres, bad anatomy, bad hands, extra digits, missing fingers, cropped, head out of frame, worst quality, "
       "low quality, jpeg artifacts, signature, watermark, text, logo, ") + STORY["negative"]


def run(graph, out):
    """Queue a workflow, wait for it, save the single output image to `out`."""
    pid = requests.post(f"{URL}/prompt", json={"prompt": graph, "client_id": str(uuid.uuid4())}).json()
    if "prompt_id" not in pid:
        raise RuntimeError(json.dumps(pid)[:800])
    pid = pid["prompt_id"]
    while True:
        h = requests.get(f"{URL}/history/{pid}").json().get(pid)
        if h and h.get("status", {}).get("completed"):
            break
        if h and h.get("status", {}).get("status_str") == "error":
            raise RuntimeError(json.dumps(h["status"])[:800])
        time.sleep(1)
    img = next(i for o in h["outputs"].values() for i in o.get("images", []))
    r = requests.get(f"{URL}/view", params={"filename": img["filename"], "subfolder": img["subfolder"], "type": img["type"]})
    out.write_bytes(r.content)
    return out


def graph(prompt, seed, width=W, height=H, ref=None, ref_weight=0.6, init=None, denoise=1.0,
          preset="PLUS FACE (portraits)", end_at=0.7, regions=()):
    g = {
        "ckpt": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["ckpt", 1]}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["ckpt", 1]}},
        "dec": {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": ["ckpt", 2]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": "film"}},
    }
    model = ["ckpt", 0]
    positive = ["pos", 0]
    if regions:
        # each character's tags and face only act inside their half of the frame, so attributes don't bleed
        g["ipl"] = {"class_type": "IPAdapterUnifiedLoader", "inputs": {"model": model, "preset": preset}}
        model, cond = ["ipl", 0], ["pos", 0]
        for k, (face_ref, tags, mask) in enumerate(regions):
            g[f"m{k}"] = {"class_type": "LoadImageMask", "inputs": {"image": mask, "channel": "red"}}
            g[f"r{k}"] = {"class_type": "LoadImage", "inputs": {"image": face_ref}}
            g[f"ipa{k}"] = {"class_type": "IPAdapterAdvanced", "inputs": {
                "model": model, "ipadapter": ["ipl", 1], "image": [f"r{k}", 0], "weight": ref_weight,
                "weight_type": "linear", "combine_embeds": "concat", "start_at": 0.0, "end_at": end_at,
                "embeds_scaling": "V only", "attn_mask": [f"m{k}", 0]}}
            model = [f"ipa{k}", 0]
            g[f"t{k}"] = {"class_type": "CLIPTextEncode", "inputs": {"text": tags, "clip": ["ckpt", 1]}}
            g[f"tm{k}"] = {"class_type": "ConditioningSetMask", "inputs": {
                "conditioning": [f"t{k}", 0], "mask": [f"m{k}", 0], "strength": 1.0, "set_cond_area": "default"}}
            g[f"cc{k}"] = {"class_type": "ConditioningCombine", "inputs": {
                "conditioning_1": cond, "conditioning_2": [f"tm{k}", 0]}}
            cond = [f"cc{k}", 0]
        positive = cond
    if ref:
        g["refimg"] = {"class_type": "LoadImage", "inputs": {"image": ref}}
        g["ipl"] = {"class_type": "IPAdapterUnifiedLoader", "inputs": {"model": model, "preset": preset}}
        g["ipa"] = {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["ipl", 0], "ipadapter": ["ipl", 1], "image": ["refimg", 0], "weight": ref_weight,
            "weight_type": "linear", "combine_embeds": "concat",
            "start_at": 0.0, "end_at": end_at, "embeds_scaling": "V only"}}
        model = ["ipa", 0]
    if init:
        g["init"] = {"class_type": "LoadImage", "inputs": {"image": init}}
        g["enc"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["init", 0], "vae": ["ckpt", 2]}}
        latent = ["enc", 0]
    else:
        g["lat"] = {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}}
        latent = ["lat", 0]
    g["ks"] = {"class_type": "KSampler", "inputs": {
        "model": model, "positive": positive, "negative": ["neg", 0], "latent_image": latent, "seed": seed,
        "steps": 28, "cfg": 5.0, "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": denoise}}
    return g


def to_input(path):
    """Copy an image into ComfyUI's input folder and return the name ComfyUI knows it by."""
    name = f"film_{path.parent.name}_{path.name}"
    (COMFY_INPUT / name).write_bytes(path.read_bytes())
    return name


def refs():
    REFS.mkdir(exist_ok=True)
    for cid, c in CHARS.items():
        out = REFS / f"{cid}.png"
        if out.exists():
            continue
        prompt = (f"{c['tags']}, full body, standing, front view, looking at viewer, gentle smile, simple background, "
                  f"white background, {STORY['look']}, {QUALITY}")
        t = time.time()
        run(graph(prompt, seed=1000 + len(cid), width=896, height=1152), out)
        print(f"ref {cid}: {time.time()-t:.0f}s", flush=True)


def face(cid):
    """Head-and-shoulders crop of a character sheet: the face adapter then copies the face, not the pose or layout."""
    out = REFS / f"{cid}_face.png"
    if not out.exists():
        im = Image.open(REFS / f"{cid}.png")
        side = int(im.width * 0.62)
        x = (im.width - side) // 2
        im.crop((x, 0, x + side, side)).save(out)
    return out


def masks():
    """Left/right half masks (with a soft overlap) in ComfyUI's input folder."""
    names = []
    for side in ("left", "right"):
        name = f"film_mask_{side}_{W}x{H}.png"
        if not (COMFY_INPUT / name).exists():
            m = Image.new("RGB", (W, H), "black")
            box = (0, 0, int(W * 0.55), H) if side == "left" else (int(W * 0.45), 0, W, H)
            m.paste((255, 255, 255), box)
            m.save(COMFY_INPUT / name)
        names.append(name)
    return names


def shot_ref(s):
    """Face reference for single-character shots. Two-character shots rely on the fixed tags alone:
    a combined reference leaks its side-by-side layout into the scene."""
    ids = [c for c in s["characters"] if (REFS / f"{c}.png").exists()]
    if len(ids) != 1:
        return None, 0
    return to_input(face(ids[0])), 0.55


def shots(ids):
    FRAMES.mkdir(exist_ok=True)
    for s in STORY["shots"]:
        if s["id"] not in ids:
            continue
        cids = [c for c in s["characters"] if c in CHARS]
        regions = ()
        if len(cids) == 2:
            regions = tuple((to_input(face(c)), f"{CHARS[c]['tags']}, on {side} side", m)
                            for c, side, m in zip(cids, ("left", "right"), masks()))
            cast = f"{CHARS[cids[0]]['name']} on the left, {CHARS[cids[1]]['name']} on the right"
        else:
            cast = ", ".join(CHARS[c]["tags"] for c in cids)
        count = {0: "no humans", 1: "solo"}.get(len(s["characters"]), "2people")
        # framing first, cast next, background last; the pose goes right after framing so it carries weight
        head, tail = f"{count}, {s['framing']}", f"{cast}, {s['background']}"
        ref, w = shot_ref(s)
        seed = 7000 + s["id"]
        first = None
        for i, pose in enumerate(s["poses"]):
            out = FRAMES / f"s{s['id']:02d}_{i+1}.png"
            prompt = f"{head}, {pose}, {tail}, {STORY['look']}, {QUALITY}"
            t = time.time()
            if not out.exists():
                if i == 0:
                    run(graph(prompt, seed, ref=ref, ref_weight=w or 0.45, regions=regions), out)
                else:
                    run(graph(prompt, seed, ref=ref, ref_weight=w or 0.45, regions=regions, init=first, denoise=0.62), out)
            if i == 0:
                first = to_input(out)
            print(f"shot {s['id']} pose {i+1}: {time.time()-t:.0f}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "refs":
        refs()
    else:
        ids = set()
        for part in sys.argv[2].split(","):  # "1-5" or "1,3,7-9"
            a, _, b = part.partition("-")
            ids.update(range(int(a), int(b or a) + 1))
        shots(ids)
