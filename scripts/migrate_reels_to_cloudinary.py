"""Move local Reels metadata and media into the configured shared services.

Set DATABASE_URL and CLOUDINARY_* environment variables before running:
    .venv\\Scripts\\python.exe scripts\\migrate_reels_to_cloudinary.py
"""
import mimetypes
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from werkzeug.utils import secure_filename

from backend.database import USE_POSTGRES
from backend.app import (
    REELSLY_ALLOWED,
    REELSLY_AUDIO_EXTENSIONS,
    REELSLY_DB,
    REELSLY_FILE_EXTENSIONS,
    REELSLY_IMAGE_EXTENSIONS,
    REELSLY_STATIC,
    REELSLY_VIDEO_EXTENSIONS,
    load_reels_db,
    save_reels_db,
)
from backend.reels_storage import (
    cloudinary_configured,
    cloudinary_delivery_url,
    create_upload_signature,
    upload_local_media,
    validate_cloudinary_asset,
)


def local_media_path(media_url):
    parsed = urlparse(media_url)
    if parsed.scheme or not parsed.path.startswith("/reels-static/"):
        return None
    relative_path = unquote(parsed.path.removeprefix("/reels-static/"))
    candidate = (REELSLY_STATIC / relative_path).resolve()
    if not candidate.is_relative_to(REELSLY_STATIC.resolve()):
        raise ValueError(f"Unsafe local media path: {media_url}")
    return candidate


def main():
    if not USE_POSTGRES:
        raise RuntimeError("Set DATABASE_URL to the managed PostgreSQL connection string first.")
    if not cloudinary_configured():
        raise RuntimeError(
            "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET first."
        )

    database = load_reels_db()
    if REELSLY_DB.exists():
        legacy = json.loads(REELSLY_DB.read_text(encoding="utf-8"))
        known_ids = {reel["id"] for reel in database["reels"]}
        database["reels"].extend(
            reel for reel in legacy.get("reels", []) if reel["id"] not in known_ids
        )
        known_hires = {item["id"] for item in database["hire_requests"]}
        database["hire_requests"].extend(
            item for item in legacy.get("hire_requests", []) if item["id"] not in known_hires
        )

    migrated = 0
    for reel in database["reels"]:
        media_url = reel.get("media_url") or reel.get("video_url") or ""
        path = local_media_path(media_url)
        if path is None:
            continue
        if not path.is_file():
            raise FileNotFoundError(f"Missing media file for reel {reel['id']}: {path}")

        filename = secure_filename(reel.get("media_name") or path.name)
        signature = create_upload_signature(
            filename,
            REELSLY_ALLOWED,
            REELSLY_IMAGE_EXTENSIONS,
            REELSLY_AUDIO_EXTENSIONS,
            REELSLY_FILE_EXTENSIONS,
        )
        cloud_asset = upload_local_media(path, signature)
        asset = validate_cloudinary_asset(cloud_asset, filename)
        extension = Path(filename).suffix.lower()
        media_kind = (
            "video" if extension in REELSLY_VIDEO_EXTENSIONS else
            "image" if extension in REELSLY_IMAGE_EXTENSIONS else
            "audio" if extension in REELSLY_AUDIO_EXTENSIONS else
            "file"
        )
        reel.update({
            "video_url": cloudinary_delivery_url(asset, media_kind),
            "media_url": cloudinary_delivery_url(asset, media_kind),
            "media_kind": media_kind,
            "media_type": mimetypes.guess_type(filename)[0] or "application/octet-stream",
            "media_name": filename,
            "cloudinary_public_id": asset["public_id"],
        })
        migrated += 1

    save_reels_db(database)
    print(f"Saved {len(database['reels'])} reel records and {len(database['hire_requests'])} hire requests to PostgreSQL.")
    print(f"Uploaded {migrated} local media files to Cloudinary.")
    print("Run this again after adding new local-only reels; existing Cloudinary media is left unchanged.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Reels migration failed: {error}", file=sys.stderr)
        raise SystemExit(1)
