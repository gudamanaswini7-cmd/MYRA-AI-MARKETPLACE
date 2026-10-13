const feed = document.getElementById("feed");
const scrollNext = document.getElementById("scrollNext");
const emptyEl = document.getElementById("empty");
const toastEl = document.getElementById("toast");
const isBrandDashboard = () => new URLSearchParams(window.location.search).get("view") === "brand" || document.body.dataset.dashboard === "brand";
const accountEmail = document.body.dataset.accountEmail || "";
const accountName = document.body.dataset.accountName || "";
let tab = "all", muted = true, sourceReels = [];

const toast = (m) => { toastEl.textContent = m; toastEl.classList.add("show");
  setTimeout(() => toastEl.classList.remove("show"), 1600); };
const esc = (s) => s.replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const api = (url, opts) => fetch(url, opts).then(r => r.json());

function showPlaybackMessage(button, message, canRetry) {
  button.textContent = message;
  button.disabled = !canRetry;
  button.hidden = false;
}

// Autoplay the reel that occupies most of the feed viewport.
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    const v = e.target.querySelector("video");
    const audio = e.target.querySelector("audio");
    if (audio && !e.isIntersecting) audio.pause();
    if (!v) return;
    if (e.intersectionRatio >= 0.5) {
      v.muted = muted;
      v.play().catch(error => {
        if (error.name === "NotAllowedError") {
          showPlaybackMessage(e.target.querySelector(".playback-message"), "Tap to play", true);
        }
      });
    }
    else { v.pause(); v.currentTime = 0; }
  });
}, { root: feed, threshold: [0, 0.5] });

function appendReelBatch() {
  sourceReels.forEach(r => { const el = buildReel(r); feed.appendChild(el); observer.observe(el); });
  updateScrollButton();
}

function updateScrollButton() {
  const reels = feed.querySelectorAll(".reel");
  const canScroll = reels.length > 1 || (tab === "all" && sourceReels.length > 0);
  const currentIndex = Math.round(feed.scrollTop / Math.max(feed.clientHeight, 1));
  const atSavedEnd = tab === "saved" && currentIndex >= reels.length - 1;
  scrollNext.hidden = !canScroll;
  scrollNext.textContent = atSavedEnd ? "↑" : "↓";
  scrollNext.setAttribute("aria-label", atSavedEnd ? "Return to first reel" : "Scroll to next reel");
  scrollNext.title = atSavedEnd ? "Return to first reel" : "Scroll to next reel";
}

scrollNext.addEventListener("click", () => {
  const reels = feed.querySelectorAll(".reel");
  if (!reels.length) return;
  const currentIndex = Math.min(reels.length - 1, Math.round(feed.scrollTop / Math.max(feed.clientHeight, 1)));
  let nextIndex = currentIndex + 1;
  if (nextIndex >= reels.length) {
    if (tab === "saved") nextIndex = 0;
    else {
      appendReelBatch();
      nextIndex = reels.length;
    }
  }
  feed.scrollTo({ top: nextIndex * feed.clientHeight, behavior: "smooth" });
  updateScrollButton();
});

let pendingReelIndex = null, pendingReelTimer;
feed.addEventListener("wheel", (event) => {
  if (!event.deltaY) return;
  const reels = [...feed.querySelectorAll(".reel")];
  if (!reels.length) return;
  event.preventDefault();
  const currentIndex = pendingReelIndex ?? Math.round(feed.scrollTop / feed.clientHeight);
  const steps = Math.max(1, Math.round(Math.abs(event.deltaY) / 120));
  pendingReelIndex = Math.max(0, currentIndex + Math.sign(event.deltaY) * steps);
  if (tab === "all") while (pendingReelIndex >= feed.querySelectorAll(".reel").length) appendReelBatch();
  else pendingReelIndex = Math.min(reels.length - 1, pendingReelIndex);
  feed.scrollTop = pendingReelIndex * feed.clientHeight;
  clearTimeout(pendingReelTimer);
  pendingReelTimer = setTimeout(() => { pendingReelIndex = null; }, 500);
}, { passive: false });
feed.addEventListener("scroll", () => {
  if (tab === "all" && sourceReels.length && feed.scrollHeight - feed.scrollTop - feed.clientHeight < feed.clientHeight / 2) appendReelBatch();
  updateScrollButton();
}, { passive: true });

function buildReel(r) {
  const el = document.createElement("section");
  el.className = "reel";
  const mediaKind = r.media_kind || "video";
  const mediaUrl = esc(r.media_url || r.video_url || "");
  const mediaName = esc(r.media_name || "Creator file");
  const mediaContent = mediaKind === "image"
    ? `<img class="post-media" src="${mediaUrl}" alt="${esc(r.caption || mediaName)}">`
    : mediaKind === "audio"
      ? `<div class="file-card audio-card"><span class="file-icon" aria-hidden="true">♪</span><strong>${mediaName}</strong><audio controls preload="metadata" src="${mediaUrl}"></audio></div>`
      : mediaKind === "file"
        ? `<a class="file-card" href="${mediaUrl}" download="${mediaName}"><span class="file-icon" aria-hidden="true">↧</span><strong>${mediaName}</strong><small>Download file</small></a>`
        : `<video src="${mediaUrl}" autoplay loop playsinline webkit-playsinline muted preload="auto"></video><button class="playback-message" type="button" hidden></button>`;
  el.innerHTML = `
    ${mediaContent}
    <div class="shade"></div>
    <div class="burst">🔥</div>
    <div class="info"><div class="creator"><button class="creator-profile-trigger" type="button" aria-label="View @${esc(r.creator)} creator profile">@${esc(r.creator)}</button></div><div class="caption">${esc(r.caption)}</div></div>
    <div class="actions">
      <button class="act like ${r.liked ? "on" : ""}" title="${r.liked ? "Remove fire" : "Fire"}" aria-label="${r.liked ? "Remove fire from this reel" : "Fire this reel"}" aria-pressed="${r.liked}">${r.liked ? "❤️‍🔥" : "🔥"}</button>
      <div class="count">${r.likes}</div>
      ${isBrandDashboard() ? '<button class="act hire" type="button" title="Hire Startup" aria-label="Hire Startup"><img class="hire-art" src="/reels-static/hire-startup.svg" alt="Thumbs up"></button>' : ""}
      <button class="act save ${r.saved ? "on" : ""}" title="Save">${r.saved ? "★" : "☆"}</button>
      ${mediaKind === "video" ? `<button class="act mute" title="Sound">${muted ? "🔇" : "🔊"}</button>` : ""}
    </div>`;
  const video = el.querySelector("video");
  const playbackMessage = el.querySelector(".playback-message");
  if (video) {
    video.addEventListener("error", () => {
      showPlaybackMessage(playbackMessage, "Video unavailable — upload MP4 (H.264)", false);
    });
    video.addEventListener("playing", () => { playbackMessage.hidden = true; });
    playbackMessage.onclick = () => {
      video.muted = muted;
      video.play().catch(error => {
        showPlaybackMessage(
          playbackMessage,
          error.name === "NotAllowedError" ? "Tap to allow playback" : "Unsupported video — upload MP4 (H.264)",
          error.name === "NotAllowedError"
        );
      });
    };
  }
  const likeBtn = el.querySelector(".like"), saveBtn = el.querySelector(".save");
  const hireBtn = el.querySelector(".hire");
  const count = el.querySelector(".count"), burst = el.querySelector(".burst");
  el.querySelector(".creator-profile-trigger").onclick = () => {
    const profile = r.creator_profile || {};
    const creatorName = profile.name || r.creator || "Creator";
    const initials = creatorName.split(/\s+/).map(part => part[0]).join("").slice(0, 2).toUpperCase();
    const details = [
      ["Headline", profile.headline],
      ["Skills", profile.skills],
      ["Tools", profile.tools],
      ["Formats", profile.formats],
    ].filter(([, value]) => value);
    const portfolioUrl = safeProfileUrl(profile.portfolio);
    profileContent.innerHTML = `
      <div class="profile-head"><span class="profile-avatar">${esc(initials || "C")}</span><div><h2 id="creatorProfileTitle">${esc(creatorName)}</h2><p>@${esc(r.creator)}</p></div></div>
      ${details.length ? details.map(([label, value]) => `<section class="profile-detail"><h3>${label}</h3><p>${esc(value)}</p></section>`).join("") : '<p class="profile-empty">This creator has not added profile details yet.</p>'}
      ${portfolioUrl ? `<a class="profile-link" href="${esc(portfolioUrl)}" target="_blank" rel="noopener noreferrer">View portfolio ↗</a>` : ""}`;
    profileModal.showModal();
  };

  const like = async () => {
    const d = await api(`/api/reels/${r.id}/like`, { method: "POST" });
    likeBtn.classList.toggle("on", d.liked); likeBtn.textContent = d.liked ? "❤️‍🔥" : "🔥";
    likeBtn.title = d.liked ? "Remove fire" : "Fire";
    likeBtn.setAttribute("aria-label", d.liked ? "Remove fire from this reel" : "Fire this reel");
    likeBtn.setAttribute("aria-pressed", String(d.liked)); count.textContent = d.likes;
  };
  likeBtn.onclick = like;
  if (hireBtn) hireBtn.onclick = async () => {
    if (!accountEmail) return toast("Sign in to MYRA before sending a hire request.");
    hireBtn.disabled = true;
    try {
      const response = await fetch("/api/hire-requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reel_id: r.id, brand_email: accountEmail, brand_name: accountName }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not send hire request.");
      hireBtn.title = "Hire request sent";
      hireBtn.setAttribute("aria-label", "Hire request sent");
      toast(`Hire request sent to @${r.creator}.`);
    } catch (error) {
      hireBtn.disabled = false;
      toast(error.message || "Could not send hire request.");
    }
  };
  saveBtn.onclick = async () => {
    const d = await api(`/api/reels/${r.id}/save`, { method: "POST" });
    saveBtn.classList.toggle("on", d.saved); saveBtn.textContent = d.saved ? "★" : "☆";
    toast(d.saved ? "Saved" : "Removed from saved");
    if (tab === "saved" && !d.saved) { el.remove(); if (!feed.children.length) showEmpty(); }
  };
  const muteBtn = el.querySelector(".mute");
  if (muteBtn) muteBtn.onclick = () => {
    muted = !muted;
    document.querySelectorAll(".reel video").forEach(v => v.muted = muted);
    document.querySelectorAll(".mute").forEach(b => b.textContent = muted ? "🔇" : "🔊");
  };
  // single tap = pause/play, double tap = like (never unlikes)
  let last = 0;
  if (video) video.onclick = async () => {
    const now = Date.now();
    if (now - last < 300) {
      if (!likeBtn.classList.contains("on")) await like();
      burst.classList.remove("go"); void burst.offsetWidth; burst.classList.add("go");
    } else setTimeout(() => { if (Date.now() - last >= 300) video.paused ? video.play() : video.pause(); }, 310);
    last = now;
  };
  return el;
}

function showEmpty() {
  emptyEl.hidden = false;
  emptyEl.textContent = tab === "saved" ? "Nothing saved yet. Tap ☆ on a reel to keep it here."
                                        : "No reels yet. Tap ＋ to post the first one!";
}

function safeProfileUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : "";
  } catch {
    return "";
  }
}

async function load() {
  const reels = await api(`/api/reels${tab === "saved" ? "?saved=1" : ""}`);
  sourceReels = reels;
  observer.disconnect(); feed.innerHTML = "";
  emptyEl.hidden = reels.length > 0;
  if (!reels.length) showEmpty();
  else appendReelBatch();
  feed.scrollTop = 0;
  pendingReelIndex = null;
  updateScrollButton();
}

document.querySelectorAll(".tab").forEach(b => b.onclick = () => {
  document.querySelector(".tab.active").classList.remove("active");
  b.classList.add("active"); tab = b.dataset.tab; load();
});

// Creator upload
const modal = document.getElementById("uploadModal"), form = document.getElementById("uploadForm");
const profileModal = document.getElementById("creatorProfileModal"), profileContent = document.getElementById("creatorProfileContent");
document.getElementById("openUpload").onclick = () => modal.showModal();
document.getElementById("cancelUpload").onclick = () => modal.close();
document.getElementById("closeCreatorProfile").onclick = () => profileModal.close();
form.onsubmit = async (e) => {
  e.preventDefault();
  const btn = document.getElementById("submitUpload"); btn.disabled = true; btn.textContent = "Posting…";
  const postData = new FormData(form);
  let creatorProfile = {};
  try { creatorProfile = JSON.parse(localStorage.getItem(`forma:creator-profile:${accountEmail}`) || "{}"); } catch {}
  postData.set("creator_profile", JSON.stringify(creatorProfile));
  try {
    const storageResponse = await fetch("/api/reels/storage");
    const storage = await storageResponse.json();
    if (!storageResponse.ok || storage.mode === "unavailable") {
      throw new Error(storage.error || "Persistent reel storage is not configured.");
    }

    if (storage.mode === "shared") {
      const file = form.elements.media.files[0];
      const signatureResponse = await fetch("/api/reels/upload-signature", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: file.name }),
      });
      const signature = await signatureResponse.json();
      if (!signatureResponse.ok) throw new Error(signature.error || "Could not prepare the cloud upload.");

      btn.textContent = "Uploading…";
      const cloudForm = new FormData();
      cloudForm.append("file", file);
      for (const key of ["api_key", "timestamp", "signature", "public_id"]) {
        cloudForm.append(key, signature[key]);
      }
      const cloudResponse = await fetch(signature.upload_url, { method: "POST", body: cloudForm });
      const asset = await cloudResponse.json();
      if (!cloudResponse.ok) throw new Error(asset.error?.message || "Cloud media upload failed.");

      btn.textContent = "Saving…";
      const saveResponse = await fetch("/api/reels", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          asset,
          filename: file.name,
          creator: postData.get("creator"),
          creator_email: postData.get("creator_email"),
          caption: postData.get("caption"),
          creator_profile: creatorProfile,
        }),
      });
      const savedReel = await saveResponse.json();
      if (!saveResponse.ok) throw new Error(savedReel.error || "Could not save the reel record.");
    } else {
      const response = await fetch("/api/upload", { method: "POST", body: postData });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Upload failed.");
    }

    modal.close(); form.reset(); form.elements.creator_email.value = accountEmail; toast("Post shared!");
    document.querySelector('[data-tab="all"]').click();
  } catch (error) {
    toast(error.message || "Upload failed.");
  } finally {
    btn.disabled = false;
    btn.textContent = "Post";
  }
};

load();
