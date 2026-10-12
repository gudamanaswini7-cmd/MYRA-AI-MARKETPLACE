
function getProfileForm() {
  return document.getElementById("profile-form");
}

function getMatchForm() {
  return document.getElementById("match-form");
}

function getNotice() {
  return document.getElementById("notice");
}

function showNotice(message, isError = false) {
  const notice = getNotice();
  if (!notice) return;

  notice.textContent = message;
  notice.classList.toggle("error", isError);
  notice.classList.add("show");
}

function clearNotice() {
  const notice = getNotice();
  if (!notice) return;

  notice.textContent = "";
  notice.classList.remove("show", "error");
}

async function apiRequest(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || "Something went wrong.");
  }

  return data;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (!element) return;
  element.textContent = value ?? "";
}

function renderSkills(containerId, skills, type = "") {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.replaceChildren();

  if (!skills || skills.length === 0) {
    const empty = document.createElement("span");
    empty.className = "empty-text";
    empty.textContent = type === "missing"
      ? "No missing skills in this comparison."
      : "No skills listed yet.";
    container.appendChild(empty);
    return;
  }

  skills.forEach((skill) => {
    const tag = document.createElement("span");
    tag.className = `skill-tag ${type}`;
    tag.textContent = skill;
    container.appendChild(tag);
  });
}

function renderBrandMatches(brands = []) {
  const container = document.getElementById("brand-opportunities");
  container.replaceChildren();

  if (!brands || brands.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-text";
    empty.textContent = "No direct brand matches yet. Update your skills or campaign brief.";
    container.appendChild(empty);
    return;
  }

  brands.forEach((brand) => {
    const card = document.createElement("div");
    card.className = "brand-card";

    const header = document.createElement("div");
    header.className = "brand-header";

    const name = document.createElement("strong");
    name.textContent = brand.brand_name;

    const score = document.createElement("span");
    score.className = "brand-score";
    score.textContent = `${brand.match_score}% fit`;

    header.appendChild(name);
    header.appendChild(score);

    const industry = document.createElement("p");
    industry.className = "brand-industry";
    industry.textContent = brand.industry;

    const brief = document.createElement("p");
    brief.className = "brand-brief";
    brief.textContent = brand.brief;

    const skillRow = document.createElement("div");
    skillRow.className = "brand-skills";

    (brand.matched_skills || []).forEach((skill) => {
      const tag = document.createElement("span");
      tag.className = "skill-tag matched";
      tag.textContent = skill;
      skillRow.appendChild(tag);
    });

    if (brand.missing_skills && brand.missing_skills.length) {
      const note = document.createElement("small");
      note.className = "brand-note";
      note.textContent = `Also needed: ${brand.missing_skills.join(", ")}`;
      skillRow.appendChild(note);
    }

    card.appendChild(header);
    card.appendChild(industry);
    card.appendChild(brief);
    card.appendChild(skillRow);
    container.appendChild(card);
  });
}

function getInitials(name) {
  const words = (name || "").trim().split(/\s+/).filter(Boolean);

  if (!words.length) return "AI";

  return words.slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join("");
}

function renderProfile(profile) {
  const form = getProfileForm();
  if (!form) return;

  form.elements.name.value = profile.name || "";
  form.elements.title.value = profile.title || "";
  form.elements.skills.value =
    (profile.skills || []).join(", ");
  form.elements.experience.value = profile.experience ?? 0;
  form.elements.portfolio.value = profile.portfolio || "";

  const name = profile.name || "Your creator name";
  const title = profile.title || "Your creative specialty";
  const initials = getInitials(profile.name) || "AI";

  setText("display-name", name);
  setText("display-title", title);
  setText("large-avatar", initials);

  setText(
    "summary-text",
    profile.summary ||
      "Save your profile to generate your AI creator summary."
  );

  renderSkills("skill-list", profile.skills || []);
  setText(
    "profile-status",
    profile.name ? "Saved locally" : "Not saved"
  );

  const profilePanel = document.getElementById("profile");
  const summaryPanel = document.getElementById("summary");
  const matcherPanel = document.getElementById("matcher");
  const hasProfile = Boolean(profile && profile.name && profile.skills && profile.skills.length);

  document.body.classList.toggle("summary-view", hasProfile);
  document.body.classList.toggle("profile-view", !hasProfile);
  if (profilePanel) profilePanel.hidden = hasProfile;
  if (summaryPanel) summaryPanel.hidden = !hasProfile;
  if (matcherPanel) matcherPanel.hidden = true;
}

async function loadProfile() {
  try {
    const profile = await apiRequest("/api/profile");
    renderProfile(profile);
  } catch (error) {
    showNotice(
      "Could not load your profile. Check that the Flask server is running.",
      true
    );
  }
}

function ensureProfileVisible() {
  if (!profileForm) return;

  const hasProfile = Boolean(
    profileForm.elements.name.value.trim() &&
    profileForm.elements.skills.value.trim()
  );

  if (!hasProfile) {
    const summaryPanel = document.getElementById("summary");
    const matcherPanel = document.getElementById("matcher");

    if (summaryPanel) summaryPanel.hidden = true;
    if (matcherPanel) matcherPanel.hidden = true;
  }
}

const profileForm = getProfileForm();
const matchForm = getMatchForm();

if (profileForm) {
  profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearNotice();
    ensureProfileVisible();

    const button = profileForm.querySelector('button[type="submit"]');
    if (button) {
      button.disabled = true;
      button.textContent = "Saving...";
    }

    const payload = {
      name: profileForm.elements.name.value,
      title: profileForm.elements.title.value,
      skills: profileForm.elements.skills.value,
      experience: profileForm.elements.experience.value,
      portfolio: profileForm.elements.portfolio.value,
    };

    try {
      const result = await apiRequest("/api/profile", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      renderProfile(result.profile);
      const profilePanel = document.getElementById("profile");
      const summaryPanel = document.getElementById("summary");
      const matcherPanel = document.getElementById("matcher");

      if (profilePanel) profilePanel.hidden = true;
      if (summaryPanel) summaryPanel.hidden = false;
      if (matcherPanel) matcherPanel.hidden = true;

      if (summaryPanel) {
        summaryPanel.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }

      window.location.hash = "#summary";
      showNotice("Your creator profile was saved successfully.");
    } catch (error) {
      showNotice(error.message, true);
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = "Next →";
      }
    }
  });
}

if (matchForm) {
  matchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearNotice();

    const button = matchForm.querySelector('button[type="submit"]');
    if (button) {
      button.disabled = true;
      button.textContent = "Analyzing...";
    }

  const payload = {
    title: document.getElementById("project-title").value,
    skills: document.getElementById("project-skills").value,
    description:
      document.getElementById("project-description").value,
  };

  try {
    const result = await apiRequest("/api/match", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    setText("match-verdict", result.verdict);
    setText("score-value", `${result.score}%`);
    setText("match-explanation", result.explanation);

    renderSkills(
      "matched-skills",
      result.matched_skills,
      "matched"
    );

    renderSkills(
      "missing-skills",
      result.missing_skills,
      "missing"
    );
    renderBrandMatches(result.brands || []);

    document.getElementById("score-circle").style.borderColor =
      result.score >= 80
        ? "#8ce4b0"
        : result.score >= 50
          ? "#d6b66a"
          : "#e38b9a";

    document.getElementById("match-result").hidden = false;
    document.getElementById("matcher").scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
    showNotice(`Analysis completed for "${result.project}".`);
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = "Analyze creator fit →";
  }
  });
}

loadProfile();
ensureProfileVisible();
