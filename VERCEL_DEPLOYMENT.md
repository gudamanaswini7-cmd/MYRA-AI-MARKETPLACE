# Deploying AI Marketplace on Vercel

## Included changes
- `vercel.json` configures two Flask services: the public `app` service at the repository root and the internal-only `reelsly` service under `reelsly/`.
- The catch-all public rewrite targets `app`, preserving existing paths and output. The main app already serves the Reelsly feature; the standalone `reelsly` service is not publicly routed.
- Neither service calls the other, so no service bindings are required.
- If the Reels feed has no records, it is seeded from the MP4s bundled in `reelsly/static/videos/`. On Vercel, the temporary JSON feed file is kept under `/tmp`; this supports demo playback but is not durable storage.
- `public/static/` contains CSS, JavaScript, and image assets served by Vercel's CDN at `/static/...`.
- `backend/database.py` uses `/tmp/marketplace_challenge.db` when running on Vercel. This is only for demos: the database is ephemeral and records can disappear between instances/deployments.
- The legacy project-simulator JavaScript now calls the same-origin `/api/simulator/simulate` endpoint instead of a local port.

## Deploy
1. Extract this ZIP. Copy the files and folders inside it into your GitHub repository, preserving the directory structure, and commit/push the changes.
2. In Vercel, import or open the project connected to that repository.
3. Keep the Vercel project root at the repository root so it can read `vercel.json`. The service roots and Flask framework are configured per service in that file; do not set the project root to `frontend` or `reelsly`.
4. Leave Build Command, Output Directory, and Install Command at their defaults/blank.
5. In Project Settings -> Environment Variables, add `SECRET_KEY` with a long, random private value. Redeploy after adding it.
6. Deploy and test `/`, `/health`, `/marketplace`, `/work-twin/`, `/simulator/`, and the API interactions.

## Persistent Reels storage

Reels uploaded to a local development server are stored in local files and are not
shared with other devices. For a deployed app, Reels media must be uploaded to
Cloudinary and reel metadata must be stored in managed PostgreSQL.

1. Create a managed PostgreSQL database (Neon or Supabase are supported through
   `DATABASE_URL`).
2. Create a Cloudinary account and copy its cloud name, API key, and API secret.
3. In Vercel Project Settings → Environment Variables, set `DATABASE_URL`,
   `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, and
   `SECRET_KEY` for Production (and Preview if needed). Keep the API secret private.
4. Redeploy. New Reels uploads go directly from the browser to Cloudinary; metadata
   and hire requests go to PostgreSQL. Video playback URLs request H.264/AAC MP4
   delivery for broad browser compatibility. If shared storage is not configured,
   `/api/reels/storage` reports `mode: "unavailable"` and deployed uploads fail
   with a clear error instead of appearing to succeed temporarily. Bundled MP4s
   still play as starter reels, but new uploads need both services to persist.
5. To migrate existing local Reels and media, configure those same environment
   variables in PowerShell and run:

   ```powershell
   .venv\Scripts\python.exe scripts\migrate_reels_to_cloudinary.py
   ```

   Run this from the project root on a machine that still has the old
   `reelsly\data\db.json` and media files. The script preserves reel IDs and
   existing hire requests, uploads local media to Cloudinary, and stores updated
   URLs in PostgreSQL. It leaves already-migrated Cloudinary media unchanged.

The `Scroll` control is rendered inside the Reels iframe because Reels uses its own
scrollable feed. Its visibility and next/previous action are based on that feed,
not the outer marketplace page scrollbar.

## Other persistence notes
- The included SQLite setup is not durable on Vercel. Persistent creator submissions
  and other saved records also require managed PostgreSQL.
- Gemini-backed portfolio summaries and brief enhancement are available through `/api/ai/generate`. Set `GEMINI_API_KEY` to enable live Gemini calls; without it the app labels the response as a demo fallback. Creator matching remains explainable rule-based scoring, not an AI claim.
- Never put private API keys in frontend JavaScript.

## Persistent database (recommended for production)

The app supports both local SQLite and managed PostgreSQL. To persist creator submissions on Vercel:

1. Create a PostgreSQL database with a provider such as Neon or Supabase.
2. Copy its pooled/standard PostgreSQL connection string. Keep it private.
3. In Vercel, open Project Settings → Environment Variables and add `DATABASE_URL` with that connection string for Production (and Preview if needed).
4. Keep `SECRET_KEY` configured as a private environment variable.
5. Redeploy. On startup, the app creates the required tables if they do not exist.

If `DATABASE_URL` is absent, the app falls back to SQLite. On Vercel this fallback uses `/tmp` and is temporary; it is only suitable for a demo. Existing SQLite data is not automatically migrated to PostgreSQL.
