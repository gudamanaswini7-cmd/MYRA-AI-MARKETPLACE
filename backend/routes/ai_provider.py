"""Server-side Gemini integration for MYRA's creator and brief workflows.

Set GEMINI_API_KEY in the deployment environment. The key is never sent to the browser.
Without a key, the endpoint returns an explicitly labelled local demo fallback.
"""
import json
import os
import urllib.error
import urllib.request

from flask import Blueprint, jsonify, request

ai_provider_bp = Blueprint("ai_provider", __name__)


def _fallback(task, data):
    if task == "portfolio":
        profile = data.get("profile") or {}
        projects = data.get("projects") or []
        name = str(profile.get("name") or "This creator")[:100]
        headline = str(profile.get("headline") or "independent creator")[:160]
        skills = str(profile.get("skills") or "skills not yet listed")[:600]
        project_titles = [str(p.get("title", ""))[:100] for p in projects[:8] if isinstance(p, dict) and p.get("title")]
        highlights = ", ".join(project_titles) if project_titles else "no portfolio projects added yet"
        return f"{name} is a {headline}. Their listed skills include {skills}. Portfolio highlights: {highlights}. This demo summary is based only on the profile information provided; review work samples and verify claims before hiring."
    title = str(data.get("title") or "Untitled project")[:150]
    description = str(data.get("description") or "")[:2500]
    return (f"Project: {title}. Goal: {description} "
            f"Deliverable: {data.get('contentType', 'Any')}; aspect ratio: {data.get('aspectRatio', 'Not applicable')}; "
            f"format: {data.get('outputFormat', 'Flexible')}; commercial use: {data.get('commercialUse', 'Discuss with creator')}; "
            f"budget: {data.get('budget', 'not specified')} USD. Confirm scope, revision count, deadlines, licensing, ownership, and source-file delivery with the selected creator.")


def _gemini_generate(prompt):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.4, "maxOutputTokens": 700}}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gemini could not complete the request. Check GEMINI_API_KEY, GEMINI_MODEL, network access, and quota.") from exc


@ai_provider_bp.post("/api/ai/generate")
def generate_ai_content():
    data = request.get_json(silent=True) or {}
    task = str(data.get("task", "")).strip().lower()
    if task not in {"portfolio", "brief"}:
        return jsonify(error="Supported tasks are 'portfolio' and 'brief'."), 400
    if task == "portfolio":
        profile = data.get("profile") or {}
        projects = data.get("projects") or []
        if not isinstance(profile, dict) or not isinstance(projects, list):
            return jsonify(error="Profile must be an object and projects must be a list."), 400
        prompt = ("Write a concise, professional creator portfolio summary in 3-5 sentences. "
                  "Use only supplied facts, do not invent credentials, results, clients, or skills, and mention when experience is self-reported. "
                  "Return plain text only.\nPROFILE: " + json.dumps(profile, ensure_ascii=False) + "\nPROJECTS: " + json.dumps(projects[:12], ensure_ascii=False))
    else:
        title = str(data.get("title", "")).strip()[:150]
        description = str(data.get("description", "")).strip()[:3000]
        if not title or len(description) < 12:
            return jsonify(error="Enter a project title and a description of at least 12 characters."), 400
        prompt = ("Improve this creative/technical project brief. Use headings Goal, Deliverables, Acceptance criteria, "
                  "Open questions, and Licensing checklist. Do not invent facts; mark assumptions as questions. "
                  "Explicitly preserve the requested type, aspect ratio, format, commercial-use preference, and budget. "
                  "Remind the user to confirm licensing/ownership in writing. Return plain text.\nBRIEF: " + json.dumps({k: data.get(k) for k in ("title", "description", "contentType", "aspectRatio", "outputFormat", "commercialUse", "budget")}, ensure_ascii=False))
    try:
        generated = _gemini_generate(prompt)
        if generated:
            return jsonify(text=generated, provider="gemini")
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 502
    return jsonify(text=_fallback(task, data), provider="demo-fallback")
