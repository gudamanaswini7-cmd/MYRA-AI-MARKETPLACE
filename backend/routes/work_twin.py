from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from backend.routes.match_score import build_job_matches, normalize_skills

work_twin_bp = Blueprint("work_twin", __name__)


def empty_profile():
    return {"id": 1, "name": "", "title": "", "skills": [], "experience": 0, "portfolio": "", "summary": "", "updated_at": ""}


def build_summary(profile):
    name = profile["name"].strip() or "This freelancer"
    title = profile["title"].strip() or "independent professional"
    skills = ", ".join(profile["skills"]) if profile["skills"] else "skills not yet listed"
    return (
        f"{name} is an AI creator focusing on {title} with "
        f"{profile['experience']} year(s) of hands-on experience. Their "
        f"creative toolkit includes {skills}. Review the portfolio and work examples "
        "before making creative or project-fit decisions. This summary is generated from self-reported information."
    )


def read_profile():
    profile = session.get("creator_profile")
    if not profile:
        return empty_profile()
    normalized = dict(empty_profile(), **profile)
    normalized["skills"] = list(normalized.get("skills", []) or [])
    normalized["summary"] = normalized.get("summary") or build_summary(normalized)
    return normalized


@work_twin_bp.get("/work-twin/")
@work_twin_bp.get("/work-twin")
def work_twin_home():
    return render_template("work-twin/index.html")


@work_twin_bp.get("/work-twin/jobs")
def suitable_jobs():
    profile = read_profile()
    if not profile.get("name"):
        return redirect(url_for("work_twin.work_twin_home"))
    return render_template("work-twin/jobs.html", jobs=build_job_matches(profile), creator=profile["name"])


@work_twin_bp.get("/api/profile")
def get_profile():
    return jsonify(read_profile())


@work_twin_bp.post("/api/profile")
def save_profile():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()[:100]
    title = str(data.get("title", "")).strip()[:120]
    portfolio = str(data.get("portfolio", "")).strip()[:3000]
    try:
        experience = int(data.get("experience", 0))
    except (TypeError, ValueError):
        return jsonify(error="Experience must be a whole number."), 400
    if not name:
        return jsonify(error="Please enter your name."), 400
    if not 0 <= experience <= 60:
        return jsonify(error="Experience must be between 0 and 60."), 400
    skills = sorted(normalize_skills(data.get("skills", "")))
    if len(skills) > 50:
        return jsonify(error="Please enter no more than 50 skills."), 400
    profile = {"name": name, "title": title, "skills": skills, "experience": experience, "portfolio": portfolio}
    profile["summary"] = build_summary(profile)
    session["creator_profile"] = profile
    return jsonify(message="Work Twin profile saved.", profile=read_profile())