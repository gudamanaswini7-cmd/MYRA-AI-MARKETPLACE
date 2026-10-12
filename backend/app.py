import json
import mimetypes
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from backend.database import init_db
from backend.routes.marketplace import marketplace_bp
from backend.routes.ai_provider import ai_provider_bp
from backend.routes.match_score import match_score_bp
from backend.routes.proof_of_skill import proof_of_skill_bp
from backend.routes.simulator import simulator_bp
from backend.routes.work_twin import work_twin_bp

BASE_DIR = Path(__file__).resolve().parent.parent
REELSLY_DIR = BASE_DIR / "reelsly"
REELSLY_STATIC = REELSLY_DIR / "static"
REELSLY_DB = REELSLY_DIR / "data" / "db.json"
REELSLY_UPLOADS = REELSLY_STATIC / "uploads"
REELSLY_VIDEOS = REELSLY_STATIC / "videos"
REELSLY_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}
REELSLY_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
REELSLY_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".aac"}
REELSLY_FILE_EXTENSIONS = {".pdf", ".txt", ".md", ".rtf", ".csv", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip"}
REELSLY_ALLOWED = REELSLY_VIDEO_EXTENSIONS | REELSLY_IMAGE_EXTENSIONS | REELSLY_AUDIO_EXTENSIONS | REELSLY_FILE_EXTENSIONS
REELSLY_SEED = [
    ("sample1.mp4", "sunsetloop", "Warm gradients to start the day #chill", 128),
    ("sample2.mp4", "nightwave", "Ocean-to-midnight colour drift #vibes", 342),
    ("sample3.mp4", "testpattern", "Retro signal check #glitch #art", 905),
    ("sample4.mp4", "greenroom", "Fresh lime energy #minimal", 57),
]


def load_reels_db():
    if not REELSLY_DB.exists():
        reels = []
        for i, (fname, creator, caption, likes) in enumerate(REELSLY_SEED):
            if (REELSLY_VIDEOS / fname).exists():
                reels.append({
                    "id": f"seed{i}",
                    "video_url": f"/reels-static/videos/{fname}",
                    "creator": creator,
                    "caption": caption,
                    "likes": likes,
                    "liked": False,
                    "saved": False,
                    "created": datetime.now().isoformat(),
                })
        REELSLY_DB.parent.mkdir(exist_ok=True)
        REELSLY_DB.write_text(json.dumps({"reels": reels}, indent=2), encoding="utf-8")

    db = json.loads(REELSLY_DB.read_text(encoding="utf-8"))
    changed = False
    for reel in db.get("reels", []):
        if reel.get("video_url", "").startswith("/static/"):
            reel["video_url"] = reel["video_url"].replace("/static/", "/reels-static/")
            changed = True
    if changed:
        REELSLY_DB.write_text(json.dumps(db, indent=2), encoding="utf-8")
    return db


def save_reels_db(db):
    REELSLY_DB.parent.mkdir(exist_ok=True)
    REELSLY_DB.write_text(json.dumps(db, indent=2), encoding="utf-8")


def find_reel(db, reel_id):
    return next((r for r in db["reels"] if r["id"] == reel_id), None)


def normalized_identity(value):
    return "".join(character for character in str(value or "").casefold() if character.isalnum())


def matches_creator_account(hire_request, email, name):
    email = str(email or "").strip().casefold()
    creator_email = str(hire_request.get("creator_email") or "").strip().casefold()
    if email and creator_email and email == creator_email:
        return True
    creator_key = normalized_identity(hire_request.get("creator_name"))
    account_keys = {
        normalized_identity(name),
        normalized_identity(email.partition("@")[0]),
    }
    return bool(creator_key and creator_key in account_keys)


def public_hire_request(hire_request):
    return {key: value for key, value in hire_request.items() if key != "creator_email"}


def sanitize_creator_profile(raw_profile, creator_name):
    try:
        profile = json.loads(raw_profile or "{}")
    except (TypeError, ValueError):
        profile = {}
    if not isinstance(profile, dict):
        profile = {}

    def value(key, limit, fallback=""):
        return str(profile.get(key) or fallback).strip()[:limit]

    return {
        "name": value("creatorName", 80, creator_name),
        "headline": value("headline", 160),
        "skills": value("skills", 500),
        "tools": value("tools", 500),
        "formats": value("formats", 300),
        "portfolio": value("portfolio", 500),
    }


def create_app(test_config=None):
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "frontend"),
        static_folder=str(BASE_DIR / "frontend"),
        static_url_path="/static",
    )
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "myra-local-development-key"),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,
        TEMPLATES_AUTO_RELOAD=True,
    )
    if test_config:
        app.config.update(test_config)

    app.config["REELSLY_LOCK"] = threading.Lock()
    init_db()
    app.register_blueprint(marketplace_bp)
    app.register_blueprint(ai_provider_bp)
    app.register_blueprint(match_score_bp)
    app.register_blueprint(proof_of_skill_bp)
    app.register_blueprint(simulator_bp)
    app.register_blueprint(work_twin_bp)

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.get("/marketplace")
    def marketplace_page():
        return render_template("marketplace.html")

    @app.get("/simulator")
    @app.get("/simulator/")
    def simulator_page():
        return render_template("simulator/index.html")

    @app.get("/project-simulator/index.html")
    def legacy_simulator_page():
        return redirect(url_for("simulator_page"))

    def reelsly_page(dashboard):
        if request.args.get("embedded") != "1":
            return redirect(url_for("marketplace_page"))
        return render_template(
            "reelsly.html",
            dashboard=dashboard,
            account_email=request.args.get("account_email", ""),
            account_name=request.args.get("account_name", ""),
        )

    @app.get("/creator")
    @app.get("/creator/")
    def creator_dashboard():
        return reelsly_page("creator")

    @app.get("/brand")
    @app.get("/brand/")
    def brand_dashboard():
        return reelsly_page("brand")

    @app.get("/reels")
    @app.get("/reels/")
    def reels_dashboard():
        return reelsly_page("creator")

    @app.route("/reels-static/<path:filename>")
    def reels_static(filename):
        if not (REELSLY_STATIC / filename).exists():
            return jsonify(error="Not found"), 404
        return send_from_directory(str(REELSLY_STATIC), filename)

    @app.get("/api/reels")
    def list_reels():
        with app.config["REELSLY_LOCK"]:
            reels = load_reels_db()["reels"]
        if request.args.get("saved") == "1":
            reels = [r for r in reels if r["saved"]]
        public_reels = [{key: value for key, value in reel.items() if key != "creator_email"} for reel in reels]
        return jsonify(sorted(public_reels, key=lambda r: r["created"], reverse=True))

    @app.post("/api/reels/<reel_id>/like")
    def toggle_like(reel_id):
        with app.config["REELSLY_LOCK"]:
            db = load_reels_db(); r = find_reel(db, reel_id)
            if not r:
                return jsonify(error="Not found"), 404
            r["liked"] = not r["liked"]
            r["likes"] = max(0, r["likes"] + (1 if r["liked"] else -1))
            save_reels_db(db)
        return jsonify(liked=r["liked"], likes=r["likes"])

    @app.post("/api/reels/<reel_id>/save")
    def toggle_save(reel_id):
        with app.config["REELSLY_LOCK"]:
            db = load_reels_db(); r = find_reel(db, reel_id)
            if not r:
                return jsonify(error="Not found"), 404
            r["saved"] = not r["saved"]
            save_reels_db(db)
        return jsonify(saved=r["saved"])

    @app.post("/api/hire-requests")
    def create_hire_request():
        data = request.get_json(silent=True) or {}
        reel_id = str(data.get("reel_id", "")).strip()
        brand_email = str(data.get("brand_email", "")).strip().casefold()
        if not reel_id or not brand_email:
            return jsonify(error="A reel and signed-in brand account are required."), 400

        with app.config["REELSLY_LOCK"]:
            db = load_reels_db()
            reel = find_reel(db, reel_id)
            if not reel:
                return jsonify(error="Creator reel not found."), 404
            hire_request = {
                "id": uuid.uuid4().hex,
                "reel_id": reel_id,
                "creator_name": reel.get("creator", "Creator"),
                "creator_email": reel.get("creator_email", ""),
                "brand_email": brand_email,
                "brand_name": str(data.get("brand_name") or brand_email.split("@", 1)[0]).strip()[:80],
                "caption": reel.get("caption", ""),
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            }
            db.setdefault("hire_requests", []).append(hire_request)
            save_reels_db(db)
        return jsonify(public_hire_request(hire_request)), 201

    @app.get("/api/notifications")
    def list_notifications():
        email = str(request.args.get("email", "")).strip().casefold()
        name = str(request.args.get("name", "")).strip()
        role = request.args.get("role", "creator")
        if not email or role not in {"brand", "creator"}:
            return jsonify(error="A signed-in brand or creator account is required."), 400

        with app.config["REELSLY_LOCK"]:
            hire_requests = load_reels_db().get("hire_requests", [])
        if role == "brand":
            notifications = [item for item in hire_requests if item.get("brand_email", "").casefold() == email]
        else:
            notifications = [item for item in hire_requests if matches_creator_account(item, email, name)]
        visible_notifications = [public_hire_request(item) for item in notifications]
        return jsonify(sorted(visible_notifications, key=lambda item: item["created_at"], reverse=True))

    @app.post("/api/notifications/<notification_id>/respond")
    def respond_to_hire_request(notification_id):
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip().casefold()
        name = str(data.get("name", "")).strip()
        decision = data.get("decision")
        if not email or decision not in {"accept", "decline"}:
            return jsonify(error="Choose accept or decline with a signed-in creator account."), 400

        with app.config["REELSLY_LOCK"]:
            db = load_reels_db()
            hire_request = next((item for item in db.get("hire_requests", []) if item["id"] == notification_id), None)
            if not hire_request or not matches_creator_account(hire_request, email, name):
                return jsonify(error="Notification not found."), 404
            if hire_request["status"] != "pending":
                return jsonify(error="This hire request already has a response."), 409
            hire_request["status"] = "accepted" if decision == "accept" else "declined"
            hire_request["responded_at"] = datetime.now().isoformat()
            save_reels_db(db)
        return jsonify(public_hire_request(hire_request))

    @app.post("/api/upload")
    def upload_reel():
        f = request.files.get("media") or request.files.get("video")
        if not f or not f.filename:
            return jsonify(error="Choose an image, video, audio, or document file."), 400
        ext = Path(f.filename).suffix.lower()
        if ext not in REELSLY_ALLOWED:
            return jsonify(error="This file type is not supported."), 400
        media_kind = (
            "video" if ext in REELSLY_VIDEO_EXTENSIONS else
            "image" if ext in REELSLY_IMAGE_EXTENSIONS else
            "audio" if ext in REELSLY_AUDIO_EXTENSIONS else
            "file"
        )
        REELSLY_UPLOADS.mkdir(parents=True, exist_ok=True)
        name = secure_filename(f"{uuid.uuid4().hex}{ext}")
        f.save(REELSLY_UPLOADS / name)
        media_url = f"/reels-static/uploads/{name}"
        creator_name = (request.form.get("creator") or "you").strip()[:30]
        reel = {
            "id": uuid.uuid4().hex[:10],
            "video_url": media_url,
            "media_url": media_url,
            "media_kind": media_kind,
            "media_type": mimetypes.guess_type(name)[0] or "application/octet-stream",
            "media_name": secure_filename(f.filename),
            "creator": creator_name,
            "creator_profile": sanitize_creator_profile(request.form.get("creator_profile"), creator_name),
            "creator_email": str(request.form.get("creator_email", "")).strip().casefold(),
            "caption": (request.form.get("caption") or "").strip()[:200],
            "likes": 0,
            "liked": False,
            "saved": False,
            "created": datetime.now().isoformat(),
        }
        with app.config["REELSLY_LOCK"]:
            db = load_reels_db(); db["reels"].append(reel); save_reels_db(db)
        return jsonify(reel), 201

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5001")), debug=False)