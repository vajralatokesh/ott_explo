/* ============================================================
   PREMIUM OTT EXPLORER - INTERACTIVE STREAMING PLAYER ENGINE
   ============================================================ */

document.addEventListener("DOMContentLoaded", function () {
    const iframe = document.getElementById("player") || document.querySelector(".player-wrap iframe");
    const overlay = document.getElementById("playerOverlay") || document.querySelector(".custom-player-overlay");
    if (!iframe || !overlay) return;

    // Retrieve datasets from iframe
    const mediaId = iframe.dataset.contentId;
    const mediaType = iframe.dataset.contentType; // 'movie', 'tv', 'anime'
    const mediaTitle = iframe.dataset.title || "Untitled Video";
    const mediaPoster = iframe.dataset.poster || "";
    const currentSeason = iframe.dataset.season || null;
    const currentEpisode = iframe.dataset.episode || null;
    const imdbId = iframe.dataset.imdbId || "";

    // Internal State Variables
    let isPlaying = true;
    let playbackSpeed = 1.0;
    let savedVolume = parseFloat(localStorage.getItem("player_volume")) || 0.8;
    let isMuted = localStorage.getItem("player_muted") === "true";
    
    // Duration and Progress Simulation (CORS restriction fallback)
    let totalDuration = 7200; // 2 hours default for movies
    if (mediaType !== "movie") {
        totalDuration = 1440; // 24 mins default for shows/anime
    }
    let currentProgress = parseInt(iframe.dataset.savedProgress) || 0;
    if (currentProgress >= totalDuration) {
        currentProgress = 0;
    }

    // Server Fallback Management
    // Priority order: vidsrc.to -> vidsrc.me -> embed.su -> autoembed -> vidlink -> multiembed
    const serverPriority = [
        { name: "vidsrc.to", build: (id, s, e) => mediaType === "movie" ? `https://vidsrc.to/embed/movie/${id}` : `https://vidsrc.to/embed/tv/${id}/${s}/${e}` },
        { name: "vidsrc.me", build: (id, s, e) => mediaType === "movie" ? `https://vidsrc.me/embed/movie?tmdb=${id}` : `https://vidsrc.me/embed/tv?tmdb=${id}&season=${s}&episode=${e}` },
        { name: "embed.su", build: (id, s, e) => mediaType === "movie" ? `https://embed.su/embed/movie/${id}` : `https://embed.su/embed/tv/${id}/${s}/${e}` },
        { name: "autoembed", build: (id, s, e) => mediaType === "movie" ? `https://player.autoembed.cc/embed/movie/${id}` : `https://player.autoembed.cc/embed/tv/${id}/${s}/${e}` },
        { name: "vidlink",   build: (id, s, e) => mediaType === "movie" ? `https://vidlink.pro/movie/${id}` : `https://vidlink.pro/tv/${id}/${s}/${e}` },
        { name: "multiembed",build: (id, s, e) => mediaType === "movie" ? `https://multiembed.mov/?video_id=${id}&tmdb=1` : `https://multiembed.mov/?video_id=${id}&tmdb=1&s=${s}&e=${e}` }
    ];

    let currentServerIndex = 0;
    let selectedSubLanguage = "off";
    let loadWatchdogTimer = null;
    let progressTimer = null;
    let controlsHideTimer = null;
    let autoplayCountdownTimer = null;

    // Fetch DOM Controls
    const playPauseBtn = document.getElementById("playPauseBtn");
    const muteBtn = document.getElementById("muteBtn");
    const volumeSlider = document.getElementById("volumeSlider");
    const timeDisplay = document.getElementById("timeDisplay");
    const progressBar = document.getElementById("playerProgressBar");
    const progressContainer = document.querySelector(".player-progress-container");
    const skipIntroBtn = document.getElementById("skipIntroBtn");
    const theaterModeBtn = document.getElementById("theaterModeBtn");
    const fullscreenBtn = document.getElementById("fullscreenBtn");
    const nextEpBtn = document.getElementById("nextEpBtn");
    const nextDrawer = document.getElementById("nextDrawer");
    
    // Dropdowns
    const serverSelectorBtn = document.getElementById("serverSelectorBtn");
    const serverDropdownMenu = document.getElementById("serverDropdownMenu");
    const subtitleSelectorBtn = document.getElementById("subtitleSelectorBtn");
    const subtitleDropdownMenu = document.getElementById("subtitleDropdownMenu");
    const speedSelectorBtn = document.getElementById("speedSelectorBtn");
    const speedDropdownMenu = document.getElementById("speedDropdownMenu");

    // Initialize UI Elements
    initVolumeState();
    buildServerDropdown();
    buildSubtitleDropdown();
    setupDropdownTriggers();
    updateTimeDisplay();
    startProgressTracker();
    resetWatchdogTimer();
    showToast(`Initializing stream on ${serverPriority[currentServerIndex].name}`, "info");

    // ==========================================
    // 1. Core Controls (Play, Volume, Mute)
    // ==========================================
    if (playPauseBtn) {
        playPauseBtn.addEventListener("click", togglePlay);
    }

    function togglePlay() {
        isPlaying = !isPlaying;
        updatePlayBtnUI();
        if (isPlaying) {
            startProgressTracker();
            showToast("Playback Resumed", "info");
        } else {
            clearInterval(progressTimer);
            showToast("Playback Paused", "info");
        }
    }

    function updatePlayBtnUI() {
        if (!playPauseBtn) return;
        playPauseBtn.innerHTML = isPlaying 
            ? `<svg viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>`
            : `<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>`;
    }

    if (muteBtn) {
        muteBtn.addEventListener("click", toggleMute);
    }

    function toggleMute() {
        isMuted = !isMuted;
        localStorage.setItem("player_muted", isMuted);
        updateMuteUI();
        showToast(isMuted ? "Audio Muted" : `Volume restored to ${Math.round(savedVolume * 100)}%`, "info");
    }

    function initVolumeState() {
        if (volumeSlider) {
            volumeSlider.value = savedVolume * 100;
            volumeSlider.addEventListener("input", function() {
                savedVolume = parseFloat(this.value) / 100;
                isMuted = savedVolume === 0;
                localStorage.setItem("player_volume", savedVolume);
                localStorage.setItem("player_muted", isMuted);
                updateMuteUI();
            });
        }
        updateMuteUI();
    }

    function updateMuteUI() {
        if (!muteBtn) return;
        if (isMuted || savedVolume === 0) {
            muteBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.21.05-.42.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/></svg>`;
            if (volumeSlider) volumeSlider.value = 0;
        } else {
            if (volumeSlider) volumeSlider.value = savedVolume * 100;
            if (savedVolume < 0.4) {
                muteBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M7 9v6h4l5 5V4l-5 5H7zm11.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg>`;
            } else {
                muteBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>`;
            }
        }
    }

    // ==========================================
    // 2. Custom Progress Tracker & API Progress Logging
    // ==========================================
    function startProgressTracker() {
        clearInterval(progressTimer);
        progressTimer = setInterval(() => {
            if (!isPlaying) return;
            
            // Advance progress by playbackSpeed
            currentProgress += (1 * playbackSpeed);
            if (currentProgress > totalDuration) {
                currentProgress = totalDuration;
                triggerEpisodeComplete();
            }

            updateTimeDisplay();
            
            // Skip Intro Chip Logic: Intro usually active from 30s to 110s
            if (mediaType !== "movie" && currentProgress >= 20 && currentProgress <= 100) {
                if (skipIntroBtn) skipIntroBtn.classList.remove("hidden");
            } else {
                if (skipIntroBtn) skipIntroBtn.classList.add("hidden");
            }

            // Periodic database save every 10 seconds
            if (Math.round(currentProgress) % 10 === 0) {
                saveProgressToDatabase();
            }
        }, 1000);
    }

    function updateTimeDisplay() {
        if (!timeDisplay || !progressBar) return;
        const pct = (currentProgress / totalDuration) * 100;
        progressBar.style.width = `${pct}%`;

        const curFormatted = formatTime(currentProgress);
        const durFormatted = formatTime(totalDuration);
        timeDisplay.textContent = `${curFormatted} / ${durFormatted}`;
    }

    function formatTime(sec) {
        sec = Math.round(sec);
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        const s = sec % 60;
        const padS = s.toString().padStart(2, '0');
        
        if (h > 0) {
            const padM = m.toString().padStart(2, '0');
            return `${h}:${padM}:${padS}`;
        }
        return `${m}:${padS}`;
    }

    function saveProgressToDatabase() {
        fetch("/api/progress", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                content_id: mediaId,
                content_type: mediaType,
                title: mediaTitle,
                poster: mediaPoster,
                progress: Math.round(currentProgress),
                duration: totalDuration,
                season: currentSeason,
                episode: currentEpisode
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.completed) {
                clearInterval(progressTimer);
                triggerEpisodeComplete();
            }
        })
        .catch(err => console.error("Error saving progress:", err));
    }

    // Skip Intro action
    if (skipIntroBtn) {
        skipIntroBtn.addEventListener("click", () => {
            currentProgress = 110; // Jump past standard anime/tv intro
            updateTimeDisplay();
            skipIntroBtn.classList.add("hidden");
            showToast("Skipped intro", "success");
            saveProgressToDatabase();
        });
    }

    // Interactive seeking on visual progress bar
    if (progressContainer) {
        progressContainer.addEventListener("click", function (e) {
            const rect = this.getBoundingClientRect();
            const clickPos = (e.clientX - rect.left) / rect.width;
            currentProgress = clickPos * totalDuration;
            updateTimeDisplay();
            saveProgressToDatabase();
            showToast(`Jumped to ${formatTime(currentProgress)}`, "info");
        });
    }

    // ==========================================
    // 3. Dropdowns (Servers, Subtitles, Speed)
    // ==========================================
    function setupDropdownTriggers() {
        const triggers = document.querySelectorAll(".dropdown-trigger");
        
        triggers.forEach(trig => {
            trig.addEventListener("click", function(e) {
                e.stopPropagation();
                const container = this.parentElement;
                const menu = container.querySelector(".player-dropdown-menu");
                const isOpen = menu.classList.contains("open");
                
                closeAllMenus();
                
                if (!isOpen) {
                    menu.classList.add("open");
                }
            });
        });

        document.addEventListener("click", closeAllMenus);
    }

    function closeAllMenus() {
        document.querySelectorAll(".player-dropdown-menu").forEach(menu => {
            menu.classList.remove("open");
        });
    }

    function buildServerDropdown() {
        if (!serverDropdownMenu) return;
        serverDropdownMenu.innerHTML = "";
        
        serverPriority.forEach((srv, idx) => {
            const btn = document.createElement("button");
            btn.className = idx === currentServerIndex ? "active" : "";
            btn.innerHTML = `${srv.name} ${idx === currentServerIndex ? "✓" : ""}`;
            btn.addEventListener("click", () => {
                switchStreamServer(idx);
            });
            serverDropdownMenu.appendChild(btn);
        });
    }

    function switchStreamServer(idx) {
        currentServerIndex = idx;
        const srv = serverPriority[currentServerIndex];
        
        // Reload source URL
        let baseUrl = srv.build(mediaId, currentSeason || 1, currentEpisode || 1);
        
        // Append subtitles param if applicable (Server 1 & 2 support)
        if (selectedSubLanguage !== "off") {
            baseUrl += (baseUrl.includes("?") ? "&" : "?") + `ds_langs=${selectedSubLanguage}`;
        }
        
        iframe.src = baseUrl;
        buildServerDropdown();
        resetWatchdogTimer();
        showToast(`Switched server to ${srv.name}`, "info");
    }

    // Watchdog automatic fallback timer (7 seconds failure detection)
    function resetWatchdogTimer() {
        clearTimeout(loadWatchdogTimer);
        loadWatchdogTimer = setTimeout(triggerAutoFallback, 7000);
    }

    function triggerAutoFallback() {
        if (currentServerIndex + 1 < serverPriority.length) {
            const oldServer = serverPriority[currentServerIndex].name;
            currentServerIndex++;
            const newServer = serverPriority[currentServerIndex].name;
            showToast(`${oldServer} slow or unavailable. Switching to fallback: ${newServer}`, "warning");
            switchStreamServer(currentServerIndex);
        } else {
            showToast("All streaming links exhaustively checked. Please retry or adjust proxy settings.", "error");
        }
    }

    // Monitor visual loaded events
    iframe.addEventListener("load", function () {
        clearTimeout(loadWatchdogTimer);
        const serverName = serverPriority[currentServerIndex].name;
        showToast(`Connected successfully to ${serverName}`, "success");
    });

    function buildSubtitleDropdown() {
        if (!subtitleDropdownMenu) return;
        subtitleDropdownMenu.innerHTML = "";
        
        const languages = [
            { code: "off", name: "Off" },
            { code: "en", name: "🇬🇧 English" },
            { code: "hi", name: "🇮🇳 Hindi" },
            { code: "es", name: "🇪🇸 Spanish" },
            { code: "fr", name: "🇫🇷 French" },
            { code: "ja", name: "🇯🇵 Japanese" }
        ];

        languages.forEach(l => {
            const btn = document.createElement("button");
            btn.className = l.code === selectedSubLanguage ? "active" : "";
            btn.innerHTML = `${l.name} ${l.code === selectedSubLanguage ? "✓" : ""}`;
            btn.addEventListener("click", () => {
                selectedSubLanguage = l.code;
                buildSubtitleDropdown();
                switchStreamServer(currentServerIndex);
                showToast(`Subtitles set to: ${l.name}`, "info");
            });
            subtitleDropdownMenu.appendChild(btn);
        });
    }

    if (speedSelectorBtn && speedDropdownMenu) {
        const speedButtons = speedDropdownMenu.querySelectorAll(".speed-opt");
        speedButtons.forEach(btn => {
            btn.addEventListener("click", function() {
                speedButtons.forEach(b => b.classList.remove("active"));
                this.classList.add("active");
                playbackSpeed = parseFloat(this.dataset.speed);
                showToast(`Speed updated to ${playbackSpeed}x`, "info");
            });
        });
    }

    // ==========================================
    // 4. Autoplay Countdown / Next Drawer
    // ==========================================
    function triggerEpisodeComplete() {
        saveProgressToDatabase();
        
        // Autoplay is only relevant for episodic items (TV shows or Anime)
        if (mediaType === "movie" || !nextEpBtn) {
            showToast("Video completed!", "success");
            return;
        }

        openAutoplayCountdown();
    }

    function openAutoplayCountdown() {
        if (!nextDrawer) return;
        nextDrawer.classList.add("open");
        
        let counter = 5;
        const countNum = document.getElementById("countdownNum") || document.getElementById("countdownTimer");
        const countBar = document.querySelector(".countdown-circle-bar");
        
        if (countNum) countNum.textContent = counter;
        if (countBar) countBar.style.strokeDashoffset = "0";

        clearInterval(autoplayCountdownTimer);
        autoplayCountdownTimer = setInterval(() => {
            counter--;
            if (countNum) countNum.textContent = counter;
            
            if (countBar) {
                const fraction = (5 - counter) / 5;
                const offset = fraction * 176;
                countBar.style.strokeDashoffset = offset;
            }

            if (counter <= 0) {
                clearInterval(autoplayCountdownTimer);
                playNextNow();
            }
        }, 1000);
    }

    function playNextNow() {
        if (nextEpBtn) {
            nextEpBtn.click();
        }
    }

    // Cancel Autoplay Drawer
    const cancelNextBtn = document.getElementById("cancelNextBtn");
    if (cancelNextBtn) {
        cancelNextBtn.addEventListener("click", () => {
            clearInterval(autoplayCountdownTimer);
            if (nextDrawer) nextDrawer.classList.remove("open");
            showToast("Autoplay cancelled", "info");
        });
    }

    // Play Now Autoplay Drawer
    const playNextNowBtn = document.getElementById("playNextNowBtn");
    if (playNextNowBtn) {
        playNextNowBtn.addEventListener("click", () => {
            clearInterval(autoplayCountdownTimer);
            playNextNow();
        });
    }

    // ==========================================
    // 5. Theater Mode and Fullscreen System
    // ==========================================
    if (theaterModeBtn) {
        theaterModeBtn.addEventListener("click", toggleTheaterMode);
    }

    function toggleTheaterMode() {
        document.body.classList.toggle("theater-mode");
        const isActive = document.body.classList.contains("theater-mode");
        if (theaterModeBtn) {
            theaterModeBtn.classList.toggle("active", isActive);
        }
        showToast(isActive ? "Theater mode activated" : "Standard layout restored", "info");
    }

    if (fullscreenBtn) {
        fullscreenBtn.addEventListener("click", toggleFullscreen);
    }

    function toggleFullscreen() {
        const wrap = document.querySelector(".player-wrap");
        if (!wrap) return;

        if (!document.fullscreenElement) {
            wrap.requestFullscreen()
                .then(() => {
                    // Mobile orientation landscape locking
                    if (screen.orientation && screen.orientation.lock) {
                        screen.orientation.lock("landscape").catch(() => {});
                    }
                })
                .catch(err => {
                    console.error("Fullscreen lock failure:", err);
                });
        } else {
            document.exitFullscreen();
        }
    }

    document.addEventListener("fullscreenchange", () => {
        const isActive = document.fullscreenElement !== null;
        if (fullscreenBtn) {
            fullscreenBtn.classList.toggle("active", isActive);
        }
    });

    // ==========================================
    // 6. UI Auto-Hide Controls Timer (2.5s)
    // ==========================================
    function resetHideControlsTimer() {
        overlay.classList.remove("hide-controls");
        clearTimeout(controlsHideTimer);
        controlsHideTimer = setTimeout(() => {
            if (isPlaying && !isAnyDropdownOpen()) {
                overlay.classList.add("hide-controls");
            }
        }, 2500);
    }

    function isAnyDropdownOpen() {
        let open = false;
        document.querySelectorAll(".player-dropdown-menu").forEach(menu => {
            if (menu.classList.contains("open")) open = true;
        });
        return open;
    }

    // Hook listeners inside the wrapper
    const playerWrapper = document.querySelector(".player-wrap");
    if (playerWrapper) {
        playerWrapper.addEventListener("mousemove", resetHideControlsTimer);
        playerWrapper.addEventListener("click", resetHideControlsTimer);
        playerWrapper.addEventListener("mouseenter", resetHideControlsTimer);
        playerWrapper.addEventListener("mouseleave", () => {
            if (isPlaying) overlay.classList.add("hide-controls");
        });
    }

    // Keyboard Shortcuts Listener
    document.addEventListener("keydown", function (e) {
        if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
            return;
        }

        const key = e.key.toLowerCase();
        
        if (key === " ") {
            e.preventDefault();
            togglePlay();
        } else if (key === "f") {
            e.preventDefault();
            toggleFullscreen();
        } else if (key === "m") {
            e.preventDefault();
            toggleMute();
        } else if (key === "t") {
            e.preventDefault();
            toggleTheaterMode();
        } else if (e.key === "ArrowRight") {
            e.preventDefault();
            currentProgress = Math.min(totalDuration, currentProgress + 10);
            updateTimeDisplay();
            showToast("Visual Seek Forward +10s", "info");
        } else if (e.key === "ArrowLeft") {
            e.preventDefault();
            currentProgress = Math.max(0, currentProgress - 10);
            updateTimeDisplay();
            showToast("Visual Seek Backward -10s", "info");
        }
        
        resetHideControlsTimer();
    });
});

// Toast Notifications System Helper
function showToast(message, type = "info") {
    const existingContainer = document.getElementById("toast-container");
    const container = existingContainer || document.createElement("div");
    
    if (!existingContainer) {
        container.id = "toast-container";
        container.style.position = "fixed";
        container.style.bottom = "30px";
        container.style.right = "30px";
        container.style.zIndex = "10000";
        container.style.display = "flex";
        container.style.flexDirection = "column";
        container.style.gap = "10px";
        document.body.appendChild(container);
    }
    
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    // Style toast visually
    toast.style.background = "rgba(20, 20, 20, 0.9)";
    toast.style.borderLeft = `4px solid ${type === "success" ? "#2ecc71" : type === "warning" ? "#f1c40f" : type === "error" ? "#e74c3c" : "#3498db"}`;
    toast.style.color = "#fff";
    toast.style.padding = "12px 24px";
    toast.style.borderRadius = "4px";
    toast.style.fontFamily = "'Poppins', sans-serif";
    toast.style.fontSize = "13px";
    toast.style.fontWeight = "500";
    toast.style.boxShadow = "0 10px 30px rgba(0,0,0,0.5)";
    toast.style.backdropFilter = "blur(10px)";
    toast.style.opacity = "0";
    toast.style.transform = "translateY(20px)";
    toast.style.transition = "all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)";
    
    toast.textContent = message;
    container.appendChild(toast);
    
    // Trigger transition Reflow
    setTimeout(() => {
        toast.style.opacity = "1";
        toast.style.transform = "translateY(0)";
    }, 50);
    
    // Remove Toast after 4 seconds
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(-20px)";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
