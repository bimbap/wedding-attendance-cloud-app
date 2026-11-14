// Frontend Application Logic for Wedding Attendance & Guestbook (AWS Amplify SPA)

const STORAGE_KEY_API = "lks_wedding_api_url";

// Seed fallback data for offline / preview mode
const SEED_ATTENDEES = [
  {
    guestId: "WA-9B41FA",
    name: "David & Sarah Miller",
    attendanceStatus: "Attending",
    pax: 2,
    relationship: "Close Friend",
    wishes: "Wishing you both a lifetime of love, joy, and endless happiness! Congratulations Arya & Sarah!",
    createdAt: new Date(Date.now() - 3600000 * 2).toISOString()
  },
  {
    guestId: "WA-2F88E1",
    name: "The Anderson Family",
    attendanceStatus: "Attending",
    pax: 4,
    relationship: "Family",
    wishes: "May your journey together be blessed with abundance, peace, and shared dreams. So proud of you both!",
    createdAt: new Date(Date.now() - 3600000 * 6).toISOString()
  },
  {
    guestId: "WA-7C14D3",
    name: "Marcus Vance",
    attendanceStatus: "Declined",
    pax: 0,
    relationship: "Colleague",
    wishes: "Sending warm congratulations from overseas! Wishing you an unforgettable celebration.",
    createdAt: new Date(Date.now() - 3600000 * 12).toISOString()
  }
];

let state = {
  apiUrl: localStorage.getItem(STORAGE_KEY_API) || "",
  attendees: [...SEED_ATTENDEES],
  stats: {
    totalRsvp: 3,
    totalHadir: 2,
    totalTidakHadir: 1,
    totalRagu: 0,
    totalPaxConfirmed: 6
  }
};

// DOM References
const dotElement = document.getElementById("api-status-dot");
const statusText = document.getElementById("api-status-text");
const rsvpForm = document.getElementById("rsvp-form");
const wishesList = document.getElementById("wishes-list");
const btnSubmit = document.getElementById("btn-submit");
const spinner = document.getElementById("form-spinner");
const configModal = document.getElementById("config-modal");
const ticketModal = document.getElementById("ticket-modal");
const inputApiUrl = document.getElementById("input-api-url");
const btnOpenConfig = document.getElementById("btn-open-config");
const btnSaveConfig = document.getElementById("btn-save-config");
const btnCancelConfig = document.getElementById("btn-cancel-config");
const btnCloseTicket = document.getElementById("btn-close-ticket");
const btnRefresh = document.getElementById("btn-refresh");
const mainLayout = document.getElementById("main-layout");
const sectionForm = document.getElementById("section-form");
const sectionWishes = document.getElementById("section-wishes");
const navLinks = document.querySelectorAll(".spa-nav-link");

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
  setupSpaRouter();
  setupPaxButtons();
  setupConfigModal();
  updateApiStatusUi();
  applyRoute(window.location.pathname);
  await fetchAttendees();
  applyRoute(window.location.pathname);
});

// 0. Client-Side SPA Router (supports /, /rsvp, /guestbook, /ticket/:guestId)
function setupSpaRouter() {
  document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-spa-link]");
    if (!link) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    const targetPath = link.getAttribute("href") || "/";
    navigateTo(targetPath);
  });

  window.addEventListener("popstate", () => {
    applyRoute(window.location.pathname);
  });
}

function navigateTo(pathname) {
  const cleanPath = pathname.startsWith("/") ? pathname : `/${pathname}`;
  if (window.location.pathname !== cleanPath) {
    window.history.pushState({}, "", cleanPath);
  }
  applyRoute(cleanPath);
}

function applyRoute(rawPathname) {
  const path = (rawPathname || "/").replace(/\/+$/, "") || "/";
  const ticketMatch = path.match(/^\/ticket\/([A-Za-z0-9_-]+)$/);

  let activeTab = "/";
  if (path === "/rsvp") {
    activeTab = "/rsvp";
    sectionForm.style.display = "";
    sectionWishes.style.display = "none";
    mainLayout.classList.add("single-view");
    ticketModal.classList.remove("active");
  } else if (path === "/guestbook" || ticketMatch) {
    activeTab = "/guestbook";
    sectionForm.style.display = "none";
    sectionWishes.style.display = "";
    mainLayout.classList.add("single-view");
  } else {
    activeTab = "/";
    sectionForm.style.display = "";
    sectionWishes.style.display = "";
    mainLayout.classList.remove("single-view");
    ticketModal.classList.remove("active");
  }

  navLinks.forEach((el) => {
    el.classList.toggle("active", el.dataset.route === activeTab);
  });

  if (ticketMatch) {
    const guestId = ticketMatch[1];
    const matched = state.attendees.find((a) => String(a.guestId).toLowerCase() === guestId.toLowerCase());
    if (matched) {
      showTicketModal(matched, false);
    }
  }
}

// 1. PAX Button Selector
function setupPaxButtons() {
  const paxButtons = document.querySelectorAll(".btn-pax");
  const hiddenPaxInput = document.getElementById("input-pax");

  paxButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      paxButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      hiddenPaxInput.value = btn.dataset.val;
    });
  });

  const statusSelect = document.getElementById("select-status");
  const paxGroup = document.getElementById("pax-group");

  statusSelect.addEventListener("change", () => {
    if (statusSelect.value === "Declined" || statusSelect.value === "Tidak Hadir") {
      paxGroup.style.display = "none";
    } else {
      paxGroup.style.display = "flex";
    }
  });
}

// 2. API Configuration Modal
function setupConfigModal() {
  btnOpenConfig.addEventListener("click", () => {
    inputApiUrl.value = state.apiUrl;
    configModal.classList.add("active");
  });

  btnCancelConfig.addEventListener("click", () => {
    configModal.classList.remove("active");
  });

  btnSaveConfig.addEventListener("click", () => {
    const rawVal = inputApiUrl.value.trim().replace(/\/$/, "");
    state.apiUrl = rawVal;
    localStorage.setItem(STORAGE_KEY_API, rawVal);
    configModal.classList.remove("active");
    updateApiStatusUi();
    fetchAttendees();
  });

  btnCloseTicket.addEventListener("click", () => {
    ticketModal.classList.remove("active");
    if (window.location.pathname.startsWith("/ticket/")) {
      navigateTo("/guestbook");
    }
  });

  btnRefresh.addEventListener("click", () => {
    btnRefresh.style.transform = "rotate(180deg)";
    fetchAttendees().finally(() => {
      setTimeout(() => { btnRefresh.style.transform = "none"; }, 400);
    });
  });
}

function updateApiStatusUi() {
  if (state.apiUrl) {
    dotElement.classList.add("online");
    statusText.textContent = "API Gateway Live";
  } else {
    dotElement.classList.remove("online");
    statusText.textContent = "Mode: Local Demo";
  }
}

// 3. Fetch Attendees and Statistics
async function fetchAttendees() {
  if (!state.apiUrl) {
    renderStats(state.stats);
    renderWishes(state.attendees);
    return;
  }

  wishesList.innerHTML = `<div class="loading-state">Connecting to Amazon API Gateway & DynamoDB...</div>`;

  try {
    const res = await fetch(`${state.apiUrl}/attendees`);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();

    state.attendees = data.data || [];
    state.stats = data.stats || state.stats;

    renderStats(state.stats);
    renderWishes(state.attendees);
  } catch (err) {
    console.warn("Fetch failed, reverting to cached/seed view:", err);
    wishesList.innerHTML = `<div class="loading-state" style="color: var(--danger)">Unable to reach API Gateway (${err.message}). Showing local cached data.</div>`;
    setTimeout(() => {
      renderStats(state.stats);
      renderWishes(state.attendees);
    }, 1200);
  }
}

// 4. Render Stats HUD
function renderStats(stats) {
  document.getElementById("stat-total-rsvp").textContent = stats.totalRsvp || 0;
  document.getElementById("stat-total-hadir").textContent = stats.totalHadir || stats.totalAttending || 0;
  document.getElementById("stat-total-pax").textContent = stats.totalPaxConfirmed || 0;
  document.getElementById("stat-total-wishes").textContent = stats.totalRsvp || 0;
}

// 5. Render Wishes Feed
function renderWishes(list) {
  if (!list || list.length === 0) {
    wishesList.innerHTML = `<div class="empty-state">No wishes recorded yet. Be the first to share your blessings!</div>`;
    return;
  }

  wishesList.innerHTML = list.map(item => {
    const isAttending = item.attendanceStatus === "Attending" || item.attendanceStatus === "Hadir";
    const isDeclined = item.attendanceStatus === "Declined" || item.attendanceStatus === "Tidak Hadir";

    let statusClass = "hadir";
    let statusLabel = `Attending (${item.pax || 1} Pax)`;

    if (isDeclined) {
      statusClass = "tidak-hadir";
      statusLabel = "Declined";
    } else if (!isAttending) {
      statusClass = "ragu";
      statusLabel = "Tentative";
    }

    const dateStr = item.createdAt ? new Date(item.createdAt).toLocaleDateString("en-US", {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
    }) : "Just now";

    const guestId = item.guestId || "";
    const ticketLink = guestId
      ? `<a href="/ticket/${encodeURIComponent(guestId)}" class="btn-ticket-link" data-spa-link>Pass: ${escapeHtml(guestId)}</a>`
      : "";

    return `
      <div class="wish-item">
        <div class="wish-meta">
          <span class="wish-name">${escapeHtml(item.name)} <small style="color: var(--text-muted); font-size: 0.8rem">· ${escapeHtml(item.relationship || 'Guest')}</small></span>
          <span class="status-chip ${statusClass}">${statusLabel}</span>
        </div>
        <p class="wish-text">"${escapeHtml(item.wishes || 'Best wishes to the happy couple!')}"</p>
        <div class="wish-footer">
          <span class="wish-time">${dateStr}</span>
          ${ticketLink}
        </div>
      </div>
    `;
  }).join("");
}

// 6. Handle RSVP Form Submission
rsvpForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const name = document.getElementById("input-name").value.trim();
  const relationship = document.getElementById("select-relationship").value;
  const attendanceStatus = document.getElementById("select-status").value;
  const isAttending = attendanceStatus === "Attending" || attendanceStatus === "Hadir";
  const pax = isAttending ? Number(document.getElementById("input-pax").value) : 0;
  const wishes = document.getElementById("input-wishes").value.trim() || "Wishing you both endless happiness and love!";

  if (!name) return;

  btnSubmit.disabled = true;
  spinner.style.display = "inline-block";

  const payload = { name, relationship, attendanceStatus, pax, wishes };

  try {
    let ticketData = null;

    if (state.apiUrl) {
      const response = await fetch(`${state.apiUrl}/attendees`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errObj = await response.json();
        throw new Error(errObj.message || `Server error ${response.status}`);
      }

      const resJson = await response.json();
      ticketData = resJson.ticket;
      await fetchAttendees();
    } else {
      // Local Mock fallback
      const randomSuffix = Math.random().toString(36).substring(2, 8).toUpperCase();
      ticketData = {
        guestId: `WA-${randomSuffix}`,
        name,
        attendanceStatus,
        pax,
        createdAt: new Date().toISOString()
      };

      state.attendees.unshift({ ...payload, guestId: ticketData.guestId, createdAt: ticketData.createdAt });
      state.stats.totalRsvp += 1;
      if (isAttending) {
        state.stats.totalHadir += 1;
        state.stats.totalPaxConfirmed += pax;
      } else if (attendanceStatus === "Declined" || attendanceStatus === "Tidak Hadir") {
        state.stats.totalTidakHadir += 1;
      }
      renderStats(state.stats);
      renderWishes(state.attendees);
    }

    // Show Confirmation Ticket Modal
    showTicketModal(ticketData);

    // Reset Form
    rsvpForm.reset();
    document.getElementById("input-pax").value = "1";
    document.querySelectorAll(".btn-pax").forEach((b, i) => b.classList.toggle("active", i === 0));

  } catch (err) {
    alert(`Failed to submit attendance RSVP: ${err.message}`);
  } finally {
    btnSubmit.disabled = false;
    spinner.style.display = "none";
  }
});

function showTicketModal(ticket, updateUrl = true) {
  document.getElementById("modal-ticket-code").textContent = ticket.guestId;
  document.getElementById("modal-guest-name").textContent = ticket.name;
  document.getElementById("modal-guest-status").textContent = ticket.attendanceStatus;
  document.getElementById("modal-guest-pax").textContent = `${ticket.pax} Guests`;
  document.getElementById("modal-guest-time").textContent = new Date(ticket.createdAt).toLocaleString("en-US");

  if (updateUrl && ticket.guestId) {
    const ticketPath = `/ticket/${encodeURIComponent(ticket.guestId)}`;
    if (window.location.pathname !== ticketPath) {
      window.history.pushState({}, "", ticketPath);
    }
  }
  ticketModal.classList.add("active");
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, m => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[m]);
}