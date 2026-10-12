const BACKEND_URL = "";

async function runEvaluation() {
    console.warn("runEvaluation is disabled: /api/evaluate does not exist. Use /api/creator/submit or /api/project-simulator/simulate.");
    alert("Skills evaluation endpoint is not available in this build. Use Creator Upload or Project Simulator.");
    return;
    /* Disabled legacy implementation that called non-existent /api/evaluate
    const promptValue = document.getElementById("sys-prompt").value;
    const isChecked = document.getElementById("api-check").checked;

    try {
        const response = await fetch(`${BACKEND_URL}/api/evaluate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                api_key_configured: isChecked,
                custom_system_prompt: promptValue
            })
        });
        const data = await response.json();
        
        document.getElementById("results").classList.remove("hidden");
        document.getElementById("res-status").innerText = data.status;
        document.getElementById("res-score").innerText = data.final_score;
        
        const feedbackList = document.getElementById("res-feedback");
        feedbackList.innerHTML = "";
        data.feedback_summary.forEach(item => {
            feedbackList.innerHTML += `<li>${item}</li>`;
        });
    } catch (err) {
        alert("Unable to fetch skills verification metric. Confirm local server status.");
    }
    */
}

async function handleCreatorSubmission(event) {
    event.preventDefault();

    const form = document.getElementById("creator-form");
    const formData = new FormData(form);
    const fileInput = document.getElementById("creator-file");

    if (!fileInput.files || !fileInput.files[0]) {
        alert("Please select a file first.");
        return;
    }

    const resultBox = document.getElementById("creator-result");
    const dashboard = document.getElementById("creator-dashboard");
    const statusText = document.getElementById("creator-status");
    const scoreText = document.getElementById("creator-score");
    const feedbackList = document.getElementById("creator-feedback");
    const dashboardName = document.getElementById("dashboard-name");

    resultBox.classList.remove("hidden");
    statusText.innerText = "Checking...";
    scoreText.innerText = "...";
    feedbackList.innerHTML = "<li>AI is reviewing the uploaded file. Please wait...</li>";
    dashboard.classList.add("hidden");

    try {
        const response = await fetch(`${BACKEND_URL}/api/creator/submit`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        statusText.innerText = data.screening_status;
        scoreText.innerText = data.score;

        feedbackList.innerHTML = "";
        data.verification_notes.forEach((item) => {
            feedbackList.innerHTML += `<li>${item}</li>`;
        });

        if (data.allowed_to_dashboard) {
            dashboard.classList.remove("hidden");
            dashboardName.innerText = data.creator_name;
        } else {
            dashboard.classList.add("hidden");
        }
    } catch (err) {
        statusText.innerText = "ERROR";
        scoreText.innerText = "0";
        feedbackList.innerHTML = "<li>Unable to verify the uploaded creator file. Make sure the backend is running.</li>";
    }
}

document.getElementById("creator-form")?.addEventListener("submit", handleCreatorSubmission);
