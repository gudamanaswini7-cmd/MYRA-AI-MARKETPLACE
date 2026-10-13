"""Reelsly - basic short-video app prototype (Flask backend + vanilla JS frontend)."""
import json, threading, uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

BASE = Path(__file__).parent
DB_FILE = BASE / "data" / "db.json"
UPLOADS = BASE / "static" / "uploads"
VIDEOS = BASE.parent / "public" / "static" / "reels" / "videos"
ALLOWED = {".mp4", ".webm", ".mov"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB
lock = threading.Lock()

SEED_META = [
    ("sample1.mp4", "sunsetloop", "Warm gradients to start the day #chill", 128),
    ("sample2.mp4", "nightwave", "Ocean-to-midnight colour drift #vibes", 342),
    ("sample3.mp4", "testpattern", "Retro signal check #glitch #art", 905),
    ("sample4.mp4", "greenroom", "Fresh lime energy #minimal", 57),
]


def load_db():
    """Load the JSON 'database'; create it from sample videos on first run."""
    if not DB_FILE.exists():
        reels = []
        for i, (fname, creator, caption, likes) in enumerate(SEED_META):
            if (VIDEOS / fname).exists():
                reels.append({"id": f"seed{i}", "video_url": f"/static/videos/{fname}",
                              "creator": creator, "caption": caption, "likes": likes,
                              "liked": False, "saved": False,
                              "created": datetime.now().isoformat()})
        save_db({"reels": reels})
    return json.loads(DB_FILE.read_text(encoding="utf-8"))


def save_db(db):
    DB_FILE.parent.mkdir(exist_ok=True)
    DB_FILE.write_text(json.dumps(db, indent=2), encoding="utf-8")


def find(db, reel_id):
    return next((r for r in db["reels"] if r["id"] == reel_id), None)


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/reels")
def list_reels():
    with lock:
        reels = load_db()["reels"]
    if request.args.get("saved") == "1":
        reels = [r for r in reels if r["saved"]]
    return jsonify(sorted(reels, key=lambda r: r["created"], reverse=True))


@app.post("/api/reels/<reel_id>/like")
def toggle_like(reel_id):
    with lock:
        db = load_db(); r = find(db, reel_id)
        if not r:
            return jsonify(error="Not found"), 404
        r["liked"] = not r["liked"]
        r["likes"] = max(0, r["likes"] + (1 if r["liked"] else -1))
        save_db(db)
    return jsonify(liked=r["liked"], likes=r["likes"])


@app.post("/api/reels/<reel_id>/save")
def toggle_save(reel_id):
    with lock:
        db = load_db(); r = find(db, reel_id)
        if not r:
            return jsonify(error="Not found"), 404
        r["saved"] = not r["saved"]
        save_db(db)
    return jsonify(saved=r["saved"])


@app.post("/api/upload")
def upload():
    """Creators post a reel: multipart form with video, creator, caption."""
    f = request.files.get("video")
    if not f or not f.filename:
        return jsonify(error="Choose a video file."), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED:
        return jsonify(error="Use .mp4, .webm or .mov"), 400
    UPLOADS.mkdir(parents=True, exist_ok=True)
    name = secure_filename(f"{uuid.uuid4().hex}{ext}")
    f.save(UPLOADS / name)
    reel = {"id": uuid.uuid4().hex[:10], "video_url": f"/static/uploads/{name}",
            "creator": (request.form.get("creator") or "you").strip()[:30],
            "caption": (request.form.get("caption") or "").strip()[:200],
            "likes": 0, "liked": False, "saved": False,
            "created": datetime.now().isoformat()}
    with lock:
        db = load_db(); db["reels"].append(reel); save_db(db)
    return jsonify(reel), 201


if __name__ == "__main__":
    raise SystemExit("Reelsly is integrated into MYRA. Start the MYRA app instead.")
