// ===================================================
// VIRALREEL AI — CLIENT-SIDE JAVASCRIPT
// ===================================================

let currentVideoInfo = null;
let currentMoments = [];
let loadingInterval = null;

let currentModalReel = null;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  checkApiStatus();
  checkYouTubeStatus();
  loadReelsGallery();

  // Escape key closes open modals
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeVideoModal();
      closeYouTubeSetupModal();
    }
  });

  // Handle redirect from Google OAuth
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("youtube") === "connected") {
    showToast("🎉 YouTube Studio linked successfully!");
    window.history.replaceState({}, document.title, window.location.pathname);
  } else if (urlParams.get("youtube") === "error") {
    showToast(`OAuth Error: ${urlParams.get("detail") || "Authorization failed"}`, "error");
    window.history.replaceState({}, document.title, window.location.pathname);
  }
});

// Toast notification helper
function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${type === "success" ? "✓" : "⚠️"}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Format seconds into mm:ss
function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

// 1. Check API Key Status
async function checkApiStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();

    const geminiBadge = document.getElementById("gemini-status-badge");
    const anthropicBadge = document.getElementById("anthropic-status-badge");

    if (data.gemini_connected) {
      geminiBadge.classList.add("status-active");
      geminiBadge.querySelector(".status-dot").style.backgroundColor = "var(--accent-green)";
    } else {
      geminiBadge.querySelector(".status-dot").style.backgroundColor = "var(--text-dim)";
      geminiBadge.title = "GEMINI_API_KEY missing in .env";
    }

    if (data.anthropic_connected) {
      anthropicBadge.classList.add("status-active");
      anthropicBadge.querySelector(".status-dot").style.backgroundColor = "var(--accent-green)";
    } else {
      anthropicBadge.querySelector(".status-dot").style.backgroundColor = "var(--text-dim)";
      anthropicBadge.title = "ANTHROPIC_API_KEY missing in .env";
    }
  } catch (err) {
    console.warn("Could not check API status:", err);
  }
}

// 2. Clipboard Paste Helper
async function handlePasteClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      document.getElementById("youtube-url-input").value = text.trim();
      showToast("Pasted link from clipboard!");
    }
  } catch (err) {
    showToast("Clipboard access denied. Please paste manually.", "error");
  }
}

// 3. Analyze Video & Find Viral Moments
async function handleAnalyze() {
  const url = document.getElementById("youtube-url-input").value.trim();
  if (!url) {
    showToast("Please enter a valid YouTube video URL", "error");
    return;
  }

  const engine = document.getElementById("engine-select").value;
  const count = parseInt(document.getElementById("clips-count-select").value, 10);
  const minDuration = parseFloat(document.getElementById("min-duration-input").value) || 20;
  const maxDuration = parseFloat(document.getElementById("max-duration-input").value) || 60;

  // Show loading UI
  const loadingSection = document.getElementById("loading-section");
  const analyzeBtn = document.getElementById("analyze-btn");
  const momentsSection = document.getElementById("moments-section");
  const overviewSection = document.getElementById("video-overview-section");

  loadingSection.classList.remove("hidden");
  momentsSection.classList.add("hidden");
  overviewSection.classList.add("hidden");
  analyzeBtn.disabled = true;

  // Progressive loading steps
  const loadingMessages = [
    { title: "Fetching Video & Transcripts...", desc: "Extracting timestamps and high-quality captions from YouTube." },
    { title: "Analyzing 3-Second Hooks...", desc: "Scanning opening lines for curiosity gaps and pattern interrupts." },
    { title: "Evaluating Retention Curves...", desc: "Measuring emotional pacing and standalone completeness with Gemini 3.8." },
    { title: "Ranking Viral Moments...", desc: "Selecting the top scoring segments for 9:16 vertical reels." }
  ];
  let msgIndex = 0;
  const loadingTitle = document.getElementById("loading-title");
  const loadingDesc = document.getElementById("loading-desc");

  loadingInterval = setInterval(() => {
    msgIndex = (msgIndex + 1) % loadingMessages.length;
    loadingTitle.textContent = loadingMessages[msgIndex].title;
    loadingDesc.textContent = loadingMessages[msgIndex].desc;
  }, 2600);

  loadingSection.scrollIntoView({ behavior: "smooth" });

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        count,
        engine,
        min_duration: minDuration,
        max_duration: maxDuration
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Virality analysis failed.");
    }

    currentVideoInfo = data.video_info;
    currentMoments = data.viral_moments;

    // Render Overview
    document.getElementById("video-thumb").src = currentVideoInfo.thumbnail || "";
    document.getElementById("video-title").textContent = currentVideoInfo.title;
    document.getElementById("video-channel").textContent = currentVideoInfo.uploader;
    document.getElementById("video-duration").textContent = formatTime(currentVideoInfo.duration);
    document.getElementById("video-transcript-words").textContent = `${data.transcript_segment_count} transcript segments`;
    document.getElementById("video-summary").textContent = data.summary || "High-retention segments detected.";

    overviewSection.classList.remove("hidden");

    // Render Moments
    renderMomentsList(currentMoments);
    momentsSection.classList.remove("hidden");
    momentsSection.scrollIntoView({ behavior: "smooth" });

    showToast(`Found ${currentMoments.length} high-potential viral moments!`);
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    clearInterval(loadingInterval);
    loadingSection.classList.add("hidden");
    analyzeBtn.disabled = false;
  }
}

// 4. Render Moments Cards
function renderMomentsList(moments) {
  const grid = document.getElementById("moments-grid");
  grid.innerHTML = "";

  moments.forEach((m, idx) => {
    const card = document.createElement("article");
    card.className = "moment-card glass-panel";
    card.id = `moment-card-${idx}`;

    card.innerHTML = `
      <div class="moment-top-row">
        <span class="rank-badge">REEL #${idx + 1}</span>
        <div class="score-badge" title="Viral Potential Score">
          <span>🔥</span>
          <span>${m.viral_score}/100</span>
        </div>
      </div>

      <div class="hook-banner-preview">
        <span class="hook-preview-label">HOOK TEXT BANNER</span>
        <h4 class="hook-headline">"${escapeHtml(m.hook)}"</h4>
      </div>

      <h3 class="moment-title">${escapeHtml(m.title)}</h3>

      <p class="moment-quote">"${escapeHtml(m.key_quote)}"</p>
      <p class="moment-reason">${escapeHtml(m.reason)}</p>

      <div class="time-adjuster-box">
        <div class="time-inputs">
          <label class="control-label">START</label>
          <input type="number" id="start-time-${idx}" class="time-input-field" value="${m.start_time.toFixed(1)}" step="0.5" onchange="updateDuration(${idx})" />
          <label class="control-label">END</label>
          <input type="number" id="end-time-${idx}" class="time-input-field" value="${m.end_time.toFixed(1)}" step="0.5" onchange="updateDuration(${idx})" />
        </div>
        <span id="duration-badge-${idx}" class="duration-pill">${m.duration.toFixed(1)}s</span>
      </div>

      <button id="render-btn-${idx}" class="render-btn" onclick="handleRenderSingle(${idx})">
        <span class="btn-icon">⚡</span>
        <span class="btn-text">Render 9:16 Reel</span>
      </button>
    `;

    grid.appendChild(card);
  });
}

function updateDuration(idx) {
  const start = parseFloat(document.getElementById(`start-time-${idx}`).value) || 0;
  const end = parseFloat(document.getElementById(`end-time-${idx}`).value) || 0;
  const dur = Math.max(0, end - start);
  document.getElementById(`duration-badge-${idx}`).textContent = `${dur.toFixed(1)}s`;
}

// 5. Render a Single Reel
async function handleRenderSingle(idx) {
  const btn = document.getElementById(`render-btn-${idx}`);
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="cyber-spinner" style="width:20px;height:20px;border-width:2px;"></span> Rendering...`;

  const m = currentMoments[idx];
  const customStart = parseFloat(document.getElementById(`start-time-${idx}`).value);
  const customEnd = parseFloat(document.getElementById(`end-time-${idx}`).value);

  const momentToRender = {
    ...m,
    start_time: customStart,
    end_time: customEnd,
    duration: customEnd - customStart
  };

  const withSubtitles = document.getElementById("subtitles-toggle").checked;
  const withBanner = document.getElementById("banner-toggle").checked;

  try {
    const res = await fetch("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: currentVideoInfo.webpage_url,
        video_id: currentVideoInfo.id,
        moment: momentToRender,
        with_subtitles: withSubtitles,
        with_banner: withBanner
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Rendering failed.");
    }

    showToast(`Reel rendered successfully (${data.size_mb} MB)!`);
    loadReelsGallery();

    // Open video preview modal
    openVideoModal({
      url: data.url,
      title: momentToRender.title,
      hook: momentToRender.hook,
      duration: momentToRender.duration,
      score: momentToRender.viral_score
    });

  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
}

// 6. Render All Reels Sequentially
async function handleRenderAll() {
  const renderAllBtn = document.getElementById("render-all-btn");
  renderAllBtn.disabled = true;
  renderAllBtn.textContent = "Rendering in progress...";

  for (let i = 0; i < currentMoments.length; i++) {
    showToast(`Rendering Reel #${i + 1} of ${currentMoments.length}...`);
    await handleRenderSingle(i);
  }

  renderAllBtn.disabled = false;
  renderAllBtn.textContent = "🎬 Render All Reels";
  showToast("All reels rendered and added to library!");
}

// Utility to format raw reel filenames into clean display titles
function cleanFilenameTitle(filename) {
  if (!filename) return "Viral Reel";
  let title = filename;
  title = title.replace(/^reel_[^_]+_/, "");
  title = title.replace(/^s\d+_e\d+_/, "");
  title = title.replace(/^score\d+_/, "");
  title = title.replace(/\.mp4$/i, "");
  title = title.replace(/[_-]+/g, " ").trim();
  return title.replace(/\b\w/g, c => c.toUpperCase()) || "Viral Reel";
}

let galleryReelsList = [];

// 7. Load Previously Generated Reels Gallery
async function loadReelsGallery() {
  const grid = document.getElementById("gallery-grid");
  const empty = document.getElementById("gallery-empty");

  try {
    const res = await fetch("/api/reels");
    const data = await res.json();
    const reels = data.reels || [];
    galleryReelsList = reels;

    if (reels.length === 0) {
      grid.innerHTML = "";
      empty.classList.remove("hidden");
      return;
    }

    empty.classList.add("hidden");
    grid.innerHTML = "";

    reels.forEach((r, idx) => {
      const card = document.createElement("div");
      card.className = "gallery-card glass-panel";
      card.style.cursor = "pointer";

      const niceTitle = cleanFilenameTitle(r.filename);

      card.innerHTML = `
        <div class="gallery-preview-wrapper" onclick="openGalleryItemByIndex(${idx})" title="Click to preview & upload">
          <video class="gallery-video-preview" src="${r.url}#t=0.5" preload="metadata" muted playsinline loop></video>
          <div class="preview-play-overlay">▶</div>
        </div>
        <div class="gallery-card-title" title="${escapeHtml(niceTitle)}">${escapeHtml(niceTitle)}</div>
        <div class="gallery-card-meta">
          <span>${r.size_mb} MB</span>
          <span>9:16 Vertical</span>
        </div>
        <div class="gallery-actions">
          <button type="button" class="preview-reel-btn" onclick="openGalleryItemByIndex(${idx})">▶ Preview</button>
          <a class="download-reel-btn" href="${r.url}" download="${r.filename}">⬇ Save</a>
        </div>
      `;

      // Entire card opens the preview unless clicking the Save download link
      card.addEventListener("click", (e) => {
        if (e.target.closest(".download-reel-btn")) return;
        e.preventDefault();
        openGalleryItemByIndex(idx);
      });

      const videoElem = card.querySelector(".gallery-video-preview");
      card.addEventListener("mouseenter", () => {
        if (videoElem) videoElem.play().catch(() => {});
      });
      card.addEventListener("mouseleave", () => {
        if (videoElem) {
          videoElem.pause();
          videoElem.currentTime = 0.5;
        }
      });

      grid.appendChild(card);
    });
  } catch (err) {
    console.warn("Could not load reels gallery:", err);
  }
}

function openGalleryItemByIndex(idx) {
  const r = galleryReelsList[idx];
  if (!r) return;
  const niceTitle = cleanFilenameTitle(r.filename);
  openVideoModal({
    url: r.url,
    title: niceTitle,
    hook: niceTitle.toUpperCase(),
    duration: 30.0,
    score: 95
  });
}

// 8. Video Modal Handlers
function openVideoModal(reel) {
  if (!reel || !reel.url) return;
  currentModalReel = reel;
  const modal = document.getElementById("video-modal");
  const player = document.getElementById("modal-video-player");

  // Reset upload drawer & status
  const drawer = document.getElementById("modal-upload-drawer");
  if (drawer) drawer.classList.add("hidden");
  const statusBox = document.getElementById("yt-upload-status");
  if (statusBox) statusBox.classList.add("hidden");

  player.src = reel.url;
  player.load();
  player.play().catch(e => console.log("Autoplay deferred:", e));

  document.getElementById("modal-reel-title").textContent = reel.title || "Viral Reel";
  document.getElementById("modal-hook-text").textContent = reel.hook ? `"${reel.hook}"` : `"${reel.title || 'VIRAL REEL'}"`;
  document.getElementById("modal-score-badge").textContent = `${reel.score || 95}/100`;

  const durText = (typeof reel.duration === "number") ? `${reel.duration.toFixed(1)}s` : "9:16 Vertical";
  document.getElementById("modal-duration-badge").textContent = durText;

  const downloadBtn = document.getElementById("modal-download-btn");
  downloadBtn.href = reel.url;
  downloadBtn.download = reel.url.split("/").pop();

  modal.classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function openVideoModalDirect(url, title) {
  const filename = url ? url.split("/").pop() : "";
  const cleanTitle = title || cleanFilenameTitle(filename);
  openVideoModal({
    url,
    title: cleanTitle,
    hook: cleanTitle.toUpperCase(),
    duration: 30.0,
    score: 95
  });
}

function closeVideoModal() {
  const modal = document.getElementById("video-modal");
  const player = document.getElementById("modal-video-player");
  if (player) {
    player.pause();
    player.src = "";
  }
  if (modal) {
    modal.classList.add("hidden");
  }
  document.body.style.overflow = "";
}

// Expose modal handlers to window for reliable inline and dynamic access
window.openGalleryItemByIndex = openGalleryItemByIndex;
window.openVideoModal = openVideoModal;
window.openVideoModalDirect = openVideoModalDirect;
window.closeVideoModal = closeVideoModal;
window.cleanFilenameTitle = cleanFilenameTitle;

function copyHookToClipboard() {
  const hook = document.getElementById("modal-hook-text").textContent.replace(/"/g, "");
  navigator.clipboard.writeText(hook).then(() => {
    showToast("Hook headline copied to clipboard!");
  });
}

// ===================================================
// YOUTUBE STUDIO OAUTH & DIRECT UPLOAD
// ===================================================

let youtubeState = {
  has_client_secrets: false,
  is_authenticated: false,
  channel: null
};

async function checkYouTubeStatus() {
  try {
    const res = await fetch("/api/youtube/status");
    const data = await res.json();
    youtubeState = data;

    const btn = document.getElementById("youtube-connect-btn");
    const label = document.getElementById("youtube-account-label");

    if (data.is_authenticated && data.channel) {
      btn.classList.add("connected");
      btn.title = `Connected to ${data.channel.title}. Click to disconnect.`;
      label.textContent = `🔴 ${data.channel.title}`;
    } else {
      btn.classList.remove("connected");
      btn.title = "Click to link your YouTube channel";
      label.textContent = "Connect YouTube Studio";
    }
  } catch (err) {
    console.warn("Could not check YouTube status:", err);
  }
}

async function handleYouTubeConnectClick() {
  if (youtubeState.is_authenticated && youtubeState.channel) {
    if (confirm(`Connected to YouTube channel "${youtubeState.channel.title}". Do you want to disconnect?`)) {
      await fetch("/api/youtube/disconnect", { method: "POST" });
      showToast("YouTube Studio disconnected.");
      checkYouTubeStatus();
    }
    return;
  }

  if (!youtubeState.has_client_secrets) {
    const setupModal = document.getElementById("youtube-setup-modal");
    if (setupModal) {
      setupModal.classList.remove("hidden");
      document.body.style.overflow = "hidden";
    }
  } else {
    initiateGoogleOAuth();
  }
}

function closeYouTubeSetupModal() {
  const setupModal = document.getElementById("youtube-setup-modal");
  if (setupModal) {
    setupModal.classList.add("hidden");
  }
  document.body.style.overflow = "";
}

window.closeYouTubeSetupModal = closeYouTubeSetupModal;

async function handleSaveClientSecrets() {
  const content = document.getElementById("secrets-json-input").value.trim();
  if (!content) {
    showToast("Please paste your client_secrets.json content", "error");
    return;
  }

  try {
    const res = await fetch("/api/youtube/secrets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to save client secrets");

    showToast("Credentials saved! Redirecting to Google Login...");
    closeYouTubeSetupModal();
    initiateGoogleOAuth();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function initiateGoogleOAuth() {
  try {
    const res = await fetch("/api/youtube/auth-url");
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to get authorization URL");
    window.location.href = data.auth_url;
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function generateViralCopy() {
  if (!currentModalReel) return;

  const rewriteBtn = document.querySelector(".ai-rewrite-btn");
  if (rewriteBtn) rewriteBtn.textContent = "⏳ Thinking...";

  const rawTitle = currentModalReel.title || currentModalReel.url.split("/").pop();
  const hook = currentModalReel.hook || "";
  const quote = currentModalReel.key_quote || "";

  try {
    const res = await fetch("/api/youtube/suggest-copy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_title: rawTitle, hook, quote })
    });
    const data = await res.json();

    document.getElementById("yt-upload-title").value = data.catchy_title;
    document.getElementById("yt-upload-desc").value = data.catchy_description;

    const suggestionsBox = document.getElementById("yt-title-suggestions");
    if (data.alternative_titles && data.alternative_titles.length > 0) {
      suggestionsBox.innerHTML = `
        <span style="font-size:0.7rem;color:var(--text-dim);font-weight:700;">CLICK TO USE ALTERNATIVE TITLE:</span>
      `;
      data.alternative_titles.forEach(alt => {
        const pill = document.createElement("div");
        pill.className = "suggestion-pill";
        pill.textContent = alt;
        pill.onclick = () => {
          document.getElementById("yt-upload-title").value = alt;
          showToast("Title updated!");
        };
        suggestionsBox.appendChild(pill);
      });
      suggestionsBox.classList.remove("hidden");
    }
  } catch (err) {
    console.warn("Could not generate viral copy:", err);
  } finally {
    if (rewriteBtn) rewriteBtn.textContent = "✨ AI Rewrite";
  }
}

function toggleUploadDrawer() {
  if (!youtubeState.is_authenticated) {
    handleYouTubeConnectClick();
    return;
  }

  const drawer = document.getElementById("modal-upload-drawer");
  const isHidden = drawer.classList.contains("hidden");

  if (isHidden && currentModalReel) {
    const cleanTitle = cleanFilenameTitle(currentModalReel.title || currentModalReel.url.split("/").pop());
    document.getElementById("yt-upload-title").value = `${cleanTitle} 🤯 #Shorts`;
    document.getElementById("yt-upload-desc").value = `Wait till the end... 👀\n\nWhat would you do in this situation? Drop a comment below! 👇\n\n#Shorts #Viral #Trending #Gaming #Clips`;
    drawer.classList.remove("hidden");

    // Automatically generate AI viral hooks & alternative titles
    generateViralCopy();
  } else {
    drawer.classList.add("hidden");
  }
}

async function executeYouTubeUpload() {
  if (!currentModalReel) {
    showToast("No active reel selected", "error");
    return;
  }

  const title = document.getElementById("yt-upload-title").value.trim();
  const description = document.getElementById("yt-upload-desc").value.trim();
  const privacy = document.getElementById("yt-upload-privacy").value;
  const filename = currentModalReel.url.split("/").pop();

  const submitBtn = document.getElementById("yt-confirm-upload-btn");
  const originalHtml = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span class="cyber-spinner" style="width:14px;height:14px;border-width:2px;display:inline-block;"></span> Uploading...`;

  const statusBox = document.getElementById("yt-upload-status");
  statusBox.className = "upload-status-box";
  statusBox.textContent = "Uploading video to YouTube Studio...";
  statusBox.classList.remove("hidden");

  try {
    const res = await fetch("/api/youtube/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename,
        title,
        description,
        privacy
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Upload failed");

    showToast("🎉 Video successfully uploaded to YouTube Shorts!");
    statusBox.innerHTML = `
      <strong>✓ Upload Complete!</strong><br>
      Published as <strong>${privacy.toUpperCase()}</strong>.<br>
      <a href="${data.url}" target="_blank" style="color:#67E8F9;font-weight:700;text-decoration:underline;margin-top:6px;display:inline-block;">
        ▶ Watch Short on YouTube (${data.video_id})
      </a>
    `;
  } catch (err) {
    showToast(err.message, "error");
    statusBox.className = "upload-status-box";
    statusBox.style.background = "rgba(239, 68, 68, 0.2)";
    statusBox.style.borderColor = "rgba(239, 68, 68, 0.5)";
    statusBox.style.color = "#FCA5A5";
    statusBox.textContent = `Upload failed: ${err.message}`;
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalHtml;
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
