/* ============================================================
   OTT EXPLORER - FRONTEND ENGINE
   ============================================================ */

document.addEventListener("DOMContentLoaded", function () {
    // 1. Scroll-Activated Header Background
    const navbar = document.querySelector(".navbar");
    if (navbar) {
        window.addEventListener("scroll", function () {
            if (window.scrollY > 20) {
                navbar.classList.add("scrolled");
            } else {
                navbar.classList.remove("scrolled");
            }
        });
    }

    // 2. Carousel Tracks Scroll Handlers
    const scrollTracks = document.querySelectorAll(".carousel-track");
    scrollTracks.forEach(track => {
        const container = track.closest(".carousel-container");
        if (!container) return;
        
        const nextBtn = container.querySelector(".carousel-btn.next");
        const prevBtn = container.querySelector(".carousel-btn.prev");
        
        if (nextBtn) {
            nextBtn.addEventListener("click", () => {
                track.scrollBy({ left: track.clientWidth * 0.75, behavior: "smooth" });
            });
        }
        
        if (prevBtn) {
            prevBtn.addEventListener("click", () => {
                track.scrollBy({ left: -track.clientWidth * 0.75, behavior: "smooth" });
            });
        }
    });

    // 3. Dynamic Unified Autocomplete Suggestions
    const searchInput = document.getElementById("search-input") || document.getElementById("s-input");
    const acDropdown = document.getElementById("ac-dropdown") || document.getElementById("ac-box");
    let acTimer = null;

    if (searchInput && acDropdown) {
        searchInput.addEventListener("keypress", function (e) {
            if (e.key === "Enter") {
                const query = this.value.trim();
                if (query.length >= 2) {
                    acDropdown.style.display = "none";
                    window.location.href = `/search?q=${encodeURIComponent(query)}`;
                }
            }
        });

        searchInput.addEventListener("input", function () {
            clearTimeout(acTimer);
            const query = this.value.trim();
            if (query.length < 2) {
                acDropdown.style.display = "none";
                acDropdown.innerHTML = "";
                return;
            }

            acTimer = setTimeout(function () {
                fetch(`/api/suggest?q=${encodeURIComponent(query)}`)
                    .then(r => r.json())
                    .then(data => {
                        if (!data || data.length === 0) {
                            acDropdown.style.display = "none";
                            return;
                        }
                        
                        acDropdown.innerHTML = "";
                        acDropdown.style.display = "block";
                        
                        data.forEach(item => {
                            const row = document.createElement("div");
                            row.className = "search-history-row";
                            row.style.cursor = "pointer";
                            
                            const poster = item.poster ? `<img src="${item.poster}" style="width:30px;height:45px;object-fit:cover;border-radius:4px;background:#333;">` : `<div style="width:30px;height:45px;background:#333;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:10px;">?</div>`;
                            
                            row.innerHTML = `
                                <div style="display:flex;align-items:center;gap:12px;">
                                    ${poster}
                                    <div>
                                        <div style="font-size:13px;font-weight:600;">${item.title}</div>
                                        <div style="font-size:11px;color:#a3a3a3;text-transform:uppercase;">${item.type} · ${item.year}</div>
                                    </div>
                                </div>
                            `;
                            
                            row.addEventListener("click", () => {
                                // Save search to history API
                                fetch("/api/search-history", {
                                    method: "POST",
                                    headers: {"Content-Type": "application/json"},
                                    body: JSON.stringify({ query: item.title })
                                });
                                
                                searchInput.value = item.title;
                                acDropdown.style.display = "none";
                                
                                // Navigate
                                window.location.href = `/${item.type}/${item.id}`;
                            });
                            
                            acDropdown.appendChild(row);
                        });
                    });
            }, 300);
        });

        // Hide suggestions on document click
        document.addEventListener("click", function (e) {
            if (!searchInput.contains(e.target) && !acDropdown.contains(e.target)) {
                acDropdown.style.display = "none";
            }
        });
    }

    // 4. Custom Watchlist Toggle Handlers
    const wlButtons = document.querySelectorAll(".watchlist-toggle-btn");
    wlButtons.forEach(btn => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            
            const contentId = this.dataset.contentId;
            const contentType = this.dataset.contentType;
            const title = this.dataset.title;
            const poster = this.dataset.poster;
            
            fetch("/watchlist/toggle", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    content_id: contentId,
                    content_type: contentType,
                    title: title,
                    poster: poster
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    if (data.added) {
                        this.classList.add("added");
                        this.innerHTML = "✓ Added";
                        showToast(`"${title}" added to My List`, "success");
                    } else {
                        this.classList.remove("added");
                        this.innerHTML = "+ Watchlist";
                        showToast(`Removed "${title}" from My List`, "info");
                    }
                    
                    // If we are on the watchlist index page, let's trigger a dynamic list remove animation
                    const watchlistCard = this.closest(".watchlist-card-container");
                    if (watchlistCard && !data.added) {
                        watchlistCard.style.transition = "transform 0.4s ease, opacity 0.4s ease";
                        watchlistCard.style.transform = "scale(0.8)";
                        watchlistCard.style.opacity = "0";
                        setTimeout(() => {
                            watchlistCard.remove();
                            // Check if tabs are empty
                            const grid = watchlistCard.closest(".watchlist-grid");
                            if (grid && grid.querySelectorAll(".watchlist-card-container").length === 0) {
                                window.location.reload(); // Reload to show empty states
                            }
                        }, 400);
                    }
                } else {
                    showToast(data.message || "Failed to edit Watchlist", "error");
                }
            })
            .catch(() => {
                showToast("Connection issue updating watchlist", "error");
            });
        });
    });
});

// 5. Toast Notifications Engine
function showToast(message, type = "success") {
    let container = document.querySelector(".toast-container");
    if (!container) {
        container = document.createElement("div");
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = "🔔";
    if (type === "success") icon = "✓";
    else if (type === "error") icon = "⚠";
    else if (type === "info") icon = "ℹ";
    
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-message">${message}</div>
        <div class="toast-close">×</div>
    `;

    // Handle close button
    toast.querySelector(".toast-close").addEventListener("click", () => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    });

    container.appendChild(toast);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(10px)";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
