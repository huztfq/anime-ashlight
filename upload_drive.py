"""Upload one episode's files to Google Drive: My Drive/After the Hum/<date> - Episode NN/.
Uploads every upload/epNN_* file (full video, 4 reels, thumbnail, subtitles, upload kit guide).
Usage: python3 upload_drive.py N [YYYY-MM-DD]   (date defaults to today; safe to re-run, skips files already there)"""
import datetime, pathlib, sys
from gdrive import Drive

n = int(sys.argv[1])
day = sys.argv[2] if len(sys.argv) > 2 else datetime.date.today().isoformat()
files = sorted(pathlib.Path(__file__).with_name("upload").glob(f"ep{n:02d}_*"))
if not files:
    raise SystemExit(f"No upload/ep{n:02d}_* files found.")

d = Drive()
folder = d.folder(f"{day} - Episode {n:02d}", d.root())
for f in files:
    print(f"{f.name} ({f.stat().st_size / 1e6:.1f} MB): {d.upload(f, folder)}", flush=True)
print(f"Done: https://drive.google.com/drive/folders/{folder}")
