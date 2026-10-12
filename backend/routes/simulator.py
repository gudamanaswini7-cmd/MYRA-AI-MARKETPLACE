from flask import Blueprint, jsonify, request

from backend.routes.milestones import build_recommendations, build_risk_list

simulator_bp = Blueprint("simulator", __name__)


def evaluate_project_plan(
    project_name,
    description,
    budget,
    deadline_days,
    team_size,
    technology_stack,
    scenario,
):
    team_size = max(1, int(team_size))
    deadline_days = max(7, int(deadline_days))
    budget = float(budget or 0)
    scenario_lower = scenario.lower()
    tech_count = max(1, len([item for item in technology_stack.split(",") if item.strip()]))
    description_words = max(1, len(description.split()))

    team_penalty = max(0, 12 - team_size) * 4
    deadline_penalty = max(0, 45 - deadline_days) * 0.7
    budget_penalty = 10 if budget < 20000 else 0
    scenario_penalty = (
        18 if "unavailable" in scenario_lower or "leave" in scenario_lower
        else 12 if "budget" in scenario_lower or "cost" in scenario_lower
        else 10
    )
    tech_penalty = max(0, tech_count - 4) * 4
    complexity_penalty = description_words / 30

    readiness_score = round(100 - (team_penalty + deadline_penalty + budget_penalty + scenario_penalty + tech_penalty + complexity_penalty), 0)
    readiness_score = max(25, min(96, int(readiness_score)))
    risk_level = "Low" if readiness_score >= 75 else "Medium" if readiness_score >= 50 else "High"
    completion_time_days = max(7, int(round(deadline_days * (1.1 + (100 - readiness_score) / 100 * 0.7))))
    budget_impact = round(max(0.0, budget * ((100 - readiness_score) / 100) * 0.18), 2)

    return {
        "project_name": project_name,
        "readiness_score": readiness_score,
        "risk_level": risk_level,
        "completion_time_days": completion_time_days,
        "budget_impact": budget_impact,
        "risk_list": build_risk_list(scenario, team_size),
        "recommendations": build_recommendations(scenario, team_size, deadline_days),
        "summary": (
            f"{project_name} is currently estimated at {readiness_score}% readiness. "
            f"The main risk is {scenario_lower}, which may affect delivery timing "
            "and resource planning if not managed early."
        ),
    }


@simulator_bp.get("/api/simulator/health")
def simulator_health():
    return jsonify(status="ok")


@simulator_bp.post("/api/simulator")
@simulator_bp.post("/api/simulator/simulate")
@simulator_bp.post("/api/project-simulator/simulate")
def simulate_project():
    payload = request.get_json(silent=True) or {}
    try:
        result = evaluate_project_plan(
            project_name=str(payload.get("project_name", "AI Customer Support Chatbot")),
            description=str(payload.get("description", "A customer support chatbot for a SaaS product.")),
            budget=float(payload.get("budget", 20000)),
            deadline_days=int(payload.get("deadline_days", 30)),
            team_size=int(payload.get("team_size", 3)),
            technology_stack=str(payload.get("technology_stack", "Python, Flask, SQLite")),
            scenario=str(payload.get("scenario", "One developer becomes unavailable")),
        )
    except (TypeError, ValueError):
        return jsonify(error="Budget, deadline, and team size must be valid numbers."), 400
    return jsonify(result)