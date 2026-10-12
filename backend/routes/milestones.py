def build_risk_list(scenario, team_size):
    scenario_lower = scenario.lower()
    risks = []
    if "unavailable" in scenario_lower or "leave" in scenario_lower:
        risks.append("A critical dependency may slip if key team members become unavailable.")
    if "budget" in scenario_lower or "cost" in scenario_lower:
        risks.append("Budget pressure may delay data preparation, testing, or hiring support.")
    if team_size <= 2:
        risks.append("The team is lean, so workload bottlenecks may slow delivery.")
    else:
        risks.append("Delivery risk is moderate unless task ownership is clearly assigned.")
    risks.append("Late-stage QA and release validation could compress the final delivery window.")
    return risks[:3]


def build_recommendations(scenario, team_size, deadline_days):
    recommendations = []
    if team_size <= 3:
        recommendations.append("Assign a backup owner for every critical task to reduce single-point failure risk.")
    if deadline_days <= 30:
        recommendations.append("Prioritize the MVP scope first and defer lower-impact improvements to a later sprint.")
    if "unavailable" in scenario.lower() or "leave" in scenario.lower():
        recommendations.append("Create a contingency plan and reassign blockers early before they reach the critical path.")
    else:
        recommendations.append("Set milestone checkpoints for team review so risks are identified before they become blockers.")
    recommendations.append("Increase QA coverage and schedule a release readiness review before launch.")
    return recommendations[:4]