const API_URL = "/api/simulator/simulate";

const projectForm = document.getElementById("projectForm");
const projectSummaryName = document.getElementById("projectSummaryName");
const readinessScore = document.getElementById("readinessScore");
const readinessBar = document.getElementById("readinessBar");
const completionTime = document.getElementById("completionTime");
const budgetImpact = document.getElementById("budgetImpact");
const riskLevel = document.getElementById("riskLevel");
const riskBadge = document.getElementById("riskBadge");
const summaryText = document.getElementById("summaryText");
const riskList = document.getElementById("riskList");
const recommendationList = document.getElementById("recommendationList");

function renderList(listElement, items) {
    listElement.innerHTML = "";
    items.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        listElement.appendChild(li);
    });
}

function renderResults(result) {
    projectSummaryName.textContent = result.project_name;
    readinessScore.textContent = `${result.readiness_score}%`;
    readinessBar.style.width = `${result.readiness_score}%`;
    completionTime.textContent = `${result.completion_time_days} days`;
    budgetImpact.textContent = `₹${result.budget_impact.toLocaleString()}`;
    riskLevel.textContent = result.risk_level;
    riskBadge.textContent = result.risk_level;
    summaryText.textContent = result.summary;

    const badgeColor = result.risk_level === "Low" ? "#78f0b3" : result.risk_level === "Medium" ? "#fbbf24" : "#f87171";
    riskBadge.style.background = badgeColor;
    riskBadge.style.color = "#07141d";

    renderList(riskList, result.risk_list);
    renderList(recommendationList, result.recommendations);
}

projectForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const payload = {
        project_name: document.getElementById("projectName").value,
        description: document.getElementById("projectDescription").value,
        budget: Number(document.getElementById("budget").value || 0),
        deadline_days: Number(document.getElementById("deadlineDays").value || 30),
        team_size: Number(document.getElementById("teamSize").value || 1),
        technology_stack: document.getElementById("technologyStack").value,
        scenario: document.getElementById("scenario").value
    };

    const button = document.getElementById("simulateButton");
    button.disabled = true;
    button.innerHTML = "⏳ Simulating...";

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`Backend returned HTTP ${response.status}`);
        }

        const result = await response.json();
        renderResults(result);
    } catch (error) {
        summaryText.textContent = "Could not connect to the simulator API. Please try again or check the deployment logs.";
        riskList.innerHTML = "";
        recommendationList.innerHTML = "";
        riskBadge.textContent = "ERROR";
        riskBadge.style.background = "#f87171";
        riskBadge.style.color = "#07141d";
    } finally {
        button.disabled = false;
        button.innerHTML = '<span>▶</span> Run Simulation <span class="button-arrow">↗</span>';
    }
});

renderResults({
    project_name: "AI Customer Support Chatbot",
    readiness_score: 0,
    risk_level: "READY",
    completion_time_days: "--",
    budget_impact: 0,
    risk_list: ["Add project details and run the simulation to review risks."],
    recommendations: ["Use the simulator to test delivery pressure before building."],
    summary: "Your simulation summary will appear here."
});
