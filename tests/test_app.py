import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import create_app


class MarketplaceAppTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})
        self.client = self.app.test_client()

    def test_health_and_marketplace(self):
        self.assertEqual(self.client.get("/health").get_json(), {"status": "ok"})
        response = self.client.get("/api/marketplace")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["name"], "MYRA")
        self.assertTrue(response.get_json()["tools"])

    def test_work_twin_profile_and_match(self):
        profile = self.client.post("/api/profile", json={
            "name": "Maya Chen",
            "title": "AI Creator",
            "skills": "python, prompt design",
            "experience": 2,
        })
        self.assertEqual(profile.status_code, 200)
        match = self.client.post("/api/match", json={
            "title": "AI launch campaign",
            "skills": "python, prompt design",
        })
        self.assertEqual(match.status_code, 200)
        self.assertEqual(match.get_json()["score"], 100)
        self.assertEqual(self.client.get("/work-twin/jobs").status_code, 200)

    def test_proof_of_skill_upload(self):
        response = self.client.post(
            "/api/creator/submit",
            data={
                "creator_name": "Maya Chen",
                "file": (io.BytesIO(b"sample work"), "creator_demo.mp4", "video/mp4"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["allowed_to_dashboard"])

    def test_ai_endpoint_demo_fallback_and_validation(self):
        response = self.client.post("/api/ai/generate", json={
            "task": "portfolio",
            "profile": {"name": "Maya", "headline": "AI Designer", "skills": "Python, design"},
            "projects": [{"title": "Support Assistant"}],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["provider"], "demo-fallback")
        self.assertIn("Maya", response.get_json()["text"])
        invalid = self.client.post("/api/ai/generate", json={"task": "unknown"})
        self.assertEqual(invalid.status_code, 400)

    def test_brief_ai_endpoint_requires_description(self):
        response = self.client.post("/api/ai/generate", json={"task": "brief", "title": "Campaign", "description": "short"})
        self.assertEqual(response.status_code, 400)

    def test_project_simulation(self):
        response = self.client.post("/api/simulator", json={
            "project_name": "AI Support Assistant",
            "description": "A chatbot for product questions.",
            "budget": 20000,
            "deadline_days": 30,
            "team_size": 3,
            "technology_stack": "Python, Flask, SQLite",
            "scenario": "One developer becomes unavailable",
        })
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn(payload["risk_level"], {"Low", "Medium", "High"})
        self.assertTrue(payload["recommendations"])

    def test_workspace_pages_and_assets(self):
        for path in ("/", "/dashboard", "/marketplace", "/work-twin/", "/simulator/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        for path in (
            "/static/styles.css",
            "/static/site-background.css",
            "/static/assets/ai-background.svg",
            "/static/work-twin/styles.css",
            "/static/work-twin/app.js",
            "/static/simulator/styles.css",
            "/static/simulator/app.js",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                response.close()

    def test_reelsly_only_renders_as_myra_embed(self):
        for path in ("/creator", "/brand", "/reels"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers["Location"], "/marketplace")

                embedded = self.client.get(f"{path}?embedded=1&account_email=maya%40example.com&account_name=Maya+Chen")
                self.assertEqual(embedded.status_code, 200)
                self.assertIn(b'data-account-email="maya@example.com"', embedded.data)
                self.assertIn(b'data-account-name="Maya Chen"', embedded.data)
                self.assertIn(b'id="scrollNext"', embedded.data)

    def test_creator_upload_binds_reel_to_signed_in_account(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "reels.json"
            static_path = Path(temp_dir) / "static"
            uploads_path = static_path / "uploads"
            db_path.write_text(json.dumps({"reels": []}), encoding="utf-8")

            with patch("backend.app.REELSLY_DB", db_path), patch("backend.app.REELSLY_STATIC", static_path), patch("backend.app.REELSLY_UPLOADS", uploads_path):
                response = self.client.post(
                    "/api/upload",
                    data={
                        "creator_email": "maya@example.com",
                        "creator": "Maya Chen",
                        "creator_profile": json.dumps({
                            "creatorName": "Maya Chen",
                            "headline": "AI designer",
                            "skills": "Python, design",
                            "tools": "Figma",
                            "formats": "PNG, PDF",
                            "portfolio": "https://example.com/portfolio",
                        }),
                        "caption": "My creator reel",
                        "video": (io.BytesIO(b"video data"), "maya.mp4", "video/mp4"),
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(response.status_code, 201)
                saved_reel = json.loads(db_path.read_text(encoding="utf-8"))["reels"][0]
                self.assertEqual(saved_reel["creator_email"], "maya@example.com")
                self.assertEqual(saved_reel["creator_profile"]["headline"], "AI designer")
                self.assertEqual(saved_reel["creator_profile"]["skills"], "Python, design")
                public_post = self.client.get("/api/reels").get_json()[0]
                self.assertEqual(public_post["creator_profile"]["tools"], "Figma")
                self.assertNotIn("creator_email", public_post)

    def test_creator_upload_supports_media_and_safe_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "reels.json"
            static_path = Path(temp_dir) / "static"
            uploads_path = static_path / "uploads"
            db_path.write_text(json.dumps({"reels": []}), encoding="utf-8")

            with patch("backend.app.REELSLY_DB", db_path), patch("backend.app.REELSLY_STATIC", static_path), patch("backend.app.REELSLY_UPLOADS", uploads_path):
                for filename, expected_kind in (
                    ("photo.png", "image"),
                    ("clip.mp4", "video"),
                    ("voice.mp3", "audio"),
                    ("brief.pdf", "file"),
                ):
                    with self.subTest(filename=filename):
                        response = self.client.post(
                            "/api/upload",
                            data={
                                "creator": "Maya Chen",
                                "media": (io.BytesIO(b"sample content"), filename),
                            },
                            content_type="multipart/form-data",
                        )
                        self.assertEqual(response.status_code, 201)
                        post = response.get_json()
                        self.assertEqual(post["media_kind"], expected_kind)
                        self.assertTrue(Path(uploads_path, Path(post["media_url"]).name).exists())
                        asset = self.client.get(post["media_url"])
                        self.assertEqual(asset.status_code, 200)
                        asset.close()

                rejected = self.client.post(
                    "/api/upload",
                    data={
                        "creator": "Maya Chen",
                        "media": (io.BytesIO(b"<script>alert(1)</script>"), "unsafe.html"),
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(rejected.status_code, 400)

    def test_hire_request_notifies_creator_and_accept_or_decline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "reels.json"
            db_path.write_text(json.dumps({"reels": [{
                "id": "creator-reel",
                "creator": "Maya Chen",
                "creator_email": "maya@example.com",
                "caption": "AI design reel",
                "likes": 0,
                "liked": False,
                "saved": False,
                "created": "2026-10-13T00:00:00",
            }]}), encoding="utf-8")

            with patch("backend.app.REELSLY_DB", db_path):
                response = self.client.post("/api/hire-requests", json={
                    "reel_id": "creator-reel",
                    "brand_email": "brand@example.com",
                    "brand_name": "Acme Brand",
                })
                self.assertEqual(response.status_code, 201)
                self.assertNotIn("creator_email", response.get_json())
                notification_id = response.get_json()["id"]
                public_reel = self.client.get("/api/reels").get_json()[0]
                self.assertNotIn("creator_email", public_reel)

                creator_notifications = self.client.get(
                    "/api/notifications?role=creator&email=maya%40example.com&name=Maya+Chen"
                ).get_json()
                self.assertEqual(len(creator_notifications), 1)
                self.assertEqual(creator_notifications[0]["status"], "pending")

                unauthorized = self.client.post(
                    f"/api/notifications/{notification_id}/respond",
                    json={"email": "other@example.com", "name": "Other", "decision": "accept"},
                )
                self.assertEqual(unauthorized.status_code, 404)

                accepted = self.client.post(
                    f"/api/notifications/{notification_id}/respond",
                    json={"email": "maya@example.com", "name": "Maya Chen", "decision": "accept"},
                )
                self.assertEqual(accepted.get_json()["status"], "accepted")

                second_request = self.client.post("/api/hire-requests", json={
                    "reel_id": "creator-reel",
                    "brand_email": "brand@example.com",
                    "brand_name": "Acme Brand",
                }).get_json()
                declined = self.client.post(
                    f"/api/notifications/{second_request['id']}/respond",
                    json={"email": "maya@example.com", "name": "Maya Chen", "decision": "decline"},
                )
                self.assertEqual(declined.get_json()["status"], "declined")

                brand_notifications = self.client.get(
                    "/api/notifications?role=brand&email=brand%40example.com&name=Acme+Brand"
                ).get_json()
                self.assertEqual({item["status"] for item in brand_notifications}, {"accepted", "declined"})
                self.assertTrue(all("creator_email" not in item for item in brand_notifications))


if __name__ == "__main__":
    unittest.main()