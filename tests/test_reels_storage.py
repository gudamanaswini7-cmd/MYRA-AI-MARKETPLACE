import hashlib
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote
from unittest.mock import patch

from backend.app import REELSLY_VIDEOS, create_app
from backend.reels_storage import (
    cloudinary_delivery_url,
    create_upload_signature,
    validate_cloudinary_asset,
)


class ReelsStorageTests(unittest.TestCase):
    def test_bundled_mp4_videos_are_served_with_range_requests(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "reels.json"
            expected_videos = sorted(
                video.name
                for video in REELSLY_VIDEOS.glob("*.mp4")
            )
            with (
                patch("backend.app.USE_POSTGRES", False),
                patch("backend.app.REELSLY_DB", database_path),
            ):
                client = create_app({"TESTING": True}).test_client()
                reels = client.get("/api/reels").get_json()
                served_videos = []
                for reel in reels:
                    response = client.get(
                        reel["video_url"],
                        headers={"Range": "bytes=0-31"},
                    )
                    served_videos.append((
                        Path(unquote(reel["video_url"].split("?")[0])).name,
                        response.status_code,
                        response.mimetype,
                        response.headers.get("Content-Range", ""),
                        len(response.data),
                    ))
                    response.close()

            self.assertEqual(
                sorted(name for name, *_ in served_videos),
                expected_videos,
            )
            self.assertTrue(all(
                status == 206
                and mimetype == "video/mp4"
                and content_range.startswith("bytes 0-31/")
                and byte_count == 32
                for _, status, mimetype, content_range, byte_count in served_videos
            ))

    def test_empty_feed_seeds_bundled_videos_and_serves_them(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_dir = root / "static"
            videos_dir = static_dir / "videos"
            videos_dir.mkdir(parents=True)
            video_path = videos_dir / "creator clip.mp4"
            video_path.write_bytes(b"sample video")
            database_path = root / "data" / "reels.json"

            with (
                patch("backend.app.USE_POSTGRES", False),
                patch("backend.app.REELSLY_DB", database_path),
                patch("backend.app.REELSLY_STATIC", static_dir),
                patch("backend.app.REELSLY_VIDEOS", videos_dir),
            ):
                client = create_app({"TESTING": True}).test_client()
                reels = client.get("/api/reels").get_json()
                self.assertEqual(len(reels), 1)
                self.assertEqual(
                    reels[0]["video_url"],
                    "/reels-static/videos/creator%20clip.mp4",
                )
                video_response = client.get(reels[0]["video_url"])
                ranged_response = client.get(
                    reels[0]["video_url"],
                    headers={"Range": "bytes=0-3"},
                )
                video_status = video_response.status_code
                video_data = video_response.data
                video_mimetype = video_response.mimetype
                video_response.close()
                ranged_status = ranged_response.status_code
                ranged_data = ranged_response.data
                ranged_response.close()

            self.assertEqual(video_status, 200)
            self.assertEqual(video_data, b"sample video")
            self.assertEqual(video_mimetype, "video/mp4")
            self.assertEqual(ranged_status, 206)
            self.assertEqual(ranged_data, b"samp")

    def test_signed_upload_is_scoped_to_reels_folder(self):
        with patch.dict("os.environ", {
            "CLOUDINARY_CLOUD_NAME": "test-cloud",
            "CLOUDINARY_API_KEY": "test-key",
            "CLOUDINARY_API_SECRET": "test-secret",
        }):
            upload = create_upload_signature(
                "my clip.mp4",
                {".mp4", ".png", ".pdf"},
                {".png"},
                set(),
                {".pdf"},
            )

        self.assertTrue(upload["public_id"].startswith("myra/reels/"))
        self.assertEqual(upload["resource_type"], "video")
        self.assertEqual(
            upload["signature"],
            hashlib.sha1(
                f"public_id={upload['public_id']}&timestamp={upload['timestamp']}test-secret".encode()
            ).hexdigest(),
        )

    def test_rejects_unsupported_upload_type(self):
        with patch.dict("os.environ", {
            "CLOUDINARY_CLOUD_NAME": "test-cloud",
            "CLOUDINARY_API_KEY": "test-key",
            "CLOUDINARY_API_SECRET": "test-secret",
        }):
            with self.assertRaisesRegex(ValueError, "not supported"):
                create_upload_signature("script.exe", {".mp4"}, set(), set(), set())

    def test_validates_cloudinary_url_and_signed_public_id(self):
        public_id = "myra/reels/" + ("a" * 32)
        asset = {
            "public_id": public_id,
            "resource_type": "video",
            "secure_url": f"https://res.cloudinary.com/test-cloud/video/upload/v123/{public_id}.mp4",
            "format": "mp4",
        }
        with patch.dict("os.environ", {"CLOUDINARY_CLOUD_NAME": "test-cloud"}):
            result = validate_cloudinary_asset(asset, "clip.mp4")
        self.assertEqual(result["secure_url"], asset["secure_url"])

    def test_video_delivery_transcodes_to_browser_compatible_mp4(self):
        public_id = "myra/reels/" + ("a" * 32)
        asset = {
            "public_id": public_id,
            "secure_url": f"https://res.cloudinary.com/test-cloud/video/upload/v123/{public_id}.mov",
        }

        self.assertEqual(
            cloudinary_delivery_url(asset, "video"),
            f"https://res.cloudinary.com/test-cloud/video/upload/f_mp4,vc_h264,ac_aac/v123/{public_id}.mp4",
        )

    def test_rejects_untrusted_or_wrong_folder_asset(self):
        public_id = "myra/reels/" + ("a" * 32)
        asset = {
            "public_id": public_id,
            "resource_type": "video",
            "secure_url": f"https://example.com/test-cloud/video/upload/v123/{public_id}.mp4",
            "format": "mp4",
        }
        with patch.dict("os.environ", {"CLOUDINARY_CLOUD_NAME": "test-cloud"}):
            with self.assertRaisesRegex(ValueError, "trusted Cloudinary"):
                validate_cloudinary_asset(asset, "clip.mp4")

    def test_shared_upload_endpoint_persists_cloud_asset_metadata(self):
        with (
            patch.dict("os.environ", {
                "CLOUDINARY_CLOUD_NAME": "test-cloud",
                "CLOUDINARY_API_KEY": "test-key",
                "CLOUDINARY_API_SECRET": "test-secret",
            }),
            patch("backend.app.USE_POSTGRES", True),
            patch("backend.app.load_reels_db", return_value={"reels": [], "hire_requests": []}),
            patch("backend.app.save_reels_db") as save_reels,
        ):
            client = create_app({"TESTING": True}).test_client()
            self.assertEqual(client.get("/api/reels/storage").get_json()["mode"], "shared")
            signature = client.post(
                "/api/reels/upload-signature",
                json={"filename": "clip.mp4"},
            ).get_json()
            public_id = signature["public_id"]
            asset = {
                "public_id": public_id,
                "resource_type": "video",
                "secure_url": f"https://res.cloudinary.com/test-cloud/video/upload/v123/{public_id}.mp4",
                "format": "mp4",
            }
            response = client.post("/api/reels", json={
                "asset": asset,
                "filename": "clip.mp4",
                "creator": "Maya",
                "creator_email": "maya@example.com",
                "caption": "A shared reel",
            })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.get_json()["media_url"],
            cloudinary_delivery_url(asset, "video"),
        )
        self.assertEqual(response.get_json()["media_kind"], "video")
        self.assertEqual(save_reels.call_count, 1)


if __name__ == "__main__":
    unittest.main()
