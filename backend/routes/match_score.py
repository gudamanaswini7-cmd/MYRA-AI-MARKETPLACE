import re

from flask import Blueprint, jsonify, request

match_score_bp = Blueprint("match_score", __name__)

SKILL_ALIASES = {
    "js": "javascript",
    "html5": "html",
    "css3": "css",
    "py": "python",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "flask": "python",
    "reactjs": "react",
}

BRAND_OPPORTUNITIES = [
    {"brand_name": "NovaLabs AI", "industry": "AI SaaS", "brief": "Needs a creator to design AI onboarding flows and launch demo assets.", "required_skills": ["python", "prompt design", "branding", "ai video"]},
    {"brand_name": "PixelForge Studio", "industry": "Creative technology", "brief": "Hiring for visual storytelling, product mockups, and AI-driven ad creatives.", "required_skills": ["midjourney", "branding", "video editing", "prompt design"]},
    {"brand_name": "Aster Growth", "industry": "Marketing automation", "brief": "Looking for AI creators who can build landing-page graphics and campaign assets.", "required_skills": ["branding", "python", "ai video", "javascript"]},
    {"brand_name": "EchoLoop Media", "industry": "Content studio", "brief": "Needs creators who can script, edit, and package AI-powered content at scale.", "required_skills": ["video editing", "prompt design", "branding", "content strategy"]},
]


def normalize_skills(value):
    parts = value if isinstance(value, list) else re.split(r"[,;\n]", str(value or ""))
    skills = set()
    for part in parts:
        skill = re.sub(r"\s+", " ", str(part).strip().lower())
        if skill:
            skills.add(SKILL_ALIASES.get(skill, skill))
    return skills


def build_job_matches(profile):
    available = set(profile.get("skills", []))
    jobs = [
        {"company": "Northstar Labs", "title": "AI Content Strategist", "industry": "Marketing tech", "location": "Remote", "description": "Hiring an AI creator to shape content systems, creative briefs, and launch assets for product growth.", "required_skills": ["prompt design", "branding", "content strategy", "video editing"]},
        {"company": "SignalLoop Studio", "title": "AI Video Producer", "industry": "Media production", "location": "Hybrid", "description": "Looking for a creator who can design launch edits, storyboards, and AI-driven brand visuals.", "required_skills": ["ai video", "video editing", "storytelling", "branding"]},
        {"company": "LumaForge", "title": "AI Brand Designer", "industry": "Design systems", "location": "Remote", "description": "Need a visual designer fluent in AI workflows, concept development, and campaign mockups.", "required_skills": ["midjourney", "branding", "prompt design", "visual design"]},
        {"company": "NovaWave AI", "title": "AI Automation Creator", "industry": "Automation", "location": "Remote", "description": "Seeking a technical creator who can build AI workflows, automation playbooks, and demo systems.", "required_skills": ["python", "javascript", "prompt design", "ai automation"]},
        {"company": "BrightLoop", "title": "Growth Creative Partner", "industry": "Performance marketing", "location": "Remote", "description": "Create campaign concepts, motion assets, and narrative loops for client content funnels.", "required_skills": ["branding", "video editing", "ai video", "content strategy"]},
        {"company": "OrbitFrame", "title": "AI Campaign Designer", "industry": "Creative tech", "location": "Remote", "description": "This team needs a creator who understands AI ad concepts, storytelling systems, and visual testing.", "required_skills": ["branding", "prompt design", "midjourney", "video editing"]},
    ]
    for job in jobs:
        required = normalize_skills(job["required_skills"])
        matched = sorted(required & available)
        job["matched_skills"] = matched
        job["missing_skills"] = sorted(required - available)
        job["match_score"] = round(len(matched) / len(required) * 100) if required else 0
    return sorted(jobs, key=lambda item: (-item["match_score"], item["company"]))


@match_score_bp.post("/api/match")
def match_project():
    data = request.get_json(silent=True) or {}
    project_title = str(data.get("title", "")).strip()[:150]
    description = str(data.get("description", "")).strip()[:5000]
    required = normalize_skills(data.get("skills", ""))
    if not project_title:
        return jsonify(error="Enter a project title."), 400
    if not required:
        return jsonify(error="Enter at least one required project skill."), 400

    from flask import session
    profile = session.get("creator_profile", {})
    available = set(profile.get("skills", [])) or required
    matched = sorted(required & available)
    missing = sorted(required - available)
    score = round(len(matched) / len(required) * 100)
    verdict = "Strong creator fit" if score >= 80 else "Solid creator fit" if score >= 50 else "Potential fit"

    brands = []
    for brand in BRAND_OPPORTUNITIES:
        brand_required = normalize_skills(brand["required_skills"])
        overlap = sorted(brand_required & available)
        if overlap:
            brands.append({
                "brand_name": brand["brand_name"],
                "industry": brand["industry"],
                "brief": brand["brief"],
                "match_score": round(len(overlap) / len(brand_required) * 100),
                "matched_skills": overlap,
                "missing_skills": sorted(brand_required - available),
            })
    brands.sort(key=lambda item: (-item["match_score"], item["brand_name"]))
    return jsonify(
        project=project_title,
        description=description,
        score=score,
        verdict=verdict,
        matched_skills=matched,
        missing_skills=missing,
        brands=brands,
        explanation=f"{len(matched)} of {len(required)} required skills match your creator profile. We also surfaced brands that are likely to hire based on overlapping skills.",
    )