/**
 * app.js - Client-Side Controller for SHIFT//HANDOVER Web Dashboard
 * Evidence-Grounded and Reliable Shift Handover Generator
 */

document.addEventListener("DOMContentLoaded", () => {
  // Authentication Helpers
  function getAuthHeaders(headers = {}) {
    const token = localStorage.getItem("shift_token");
    const out = { ...headers };
    if (token) {
      out["Authorization"] = `Bearer ${token}`;
    }
    return out;
  }

  async function authFetch(url, options = {}) {
    const opts = { ...options };
    opts.headers = getAuthHeaders(opts.headers || {});
    const res = await fetch(url, opts);
    if (res.status === 401) {
      localStorage.removeItem("shift_user");
      localStorage.removeItem("shift_token");
      window.location.href = "/login";
    }
    return res;
  }

  // Elements
  const liveClockEl = document.getElementById("live-clock");
  const shiftForm = document.getElementById("shift-form");
  const shiftStartInput = document.getElementById("shift-start");
  const shiftEndInput = document.getElementById("shift-end");
  const shiftTzSelect = document.getElementById("shift-tz");
  const presetPills = document.querySelectorAll(".preset-pill");
  const btnGenerate = document.getElementById("btn-generate");
  const btnDummyTest = document.getElementById("btn-dummy-test");
  const btnRefreshSources = document.getElementById("btn-refresh-sources");

  // Progress UI
  const progressSection = document.getElementById("progress-section");
  const progressMsg = document.getElementById("progress-status-msg");
  const stepFetch = document.getElementById("step-fetch");
  const stepFilter = document.getElementById("step-filter");
  const stepDedup = document.getElementById("step-dedup");
  const stepClassify = document.getElementById("step-classify");
  const stepPublish = document.getElementById("step-publish");

  // Results UI
  const resultsSection = document.getElementById("results-section");
  const resultsWindowLabel = document.getElementById("results-window-label");
  const btnViewPdf = document.getElementById("btn-view-pdf");
  const btnDownloadPdf = document.getElementById("btn-download-pdf");

  // Audit Stats Elements
  const statTotalRecords = document.getElementById("stat-total-records");
  const statIncludedRecords = document.getElementById("stat-included-records");
  const statExcludedRecords = document.getElementById("stat-excluded-records");
  const statUniqueItems = document.getElementById("stat-unique-items");

  // Metric Counters
  const cntCompleted = document.getElementById("cnt-completed");
  const cntInProgress = document.getElementById("cnt-in-progress");
  const cntBlockers = document.getElementById("cnt-blockers");
  const cntWatch = document.getElementById("cnt-watch");

  // Section Badges & Lists
  const badgeCompleted = document.getElementById("badge-completed");
  const badgeInProgress = document.getElementById("badge-in-progress");
  const badgeBlockers = document.getElementById("badge-blockers");
  const badgeWatch = document.getElementById("badge-watch");

  const listCompleted = document.getElementById("list-completed");
  const listInProgress = document.getElementById("list-in-progress");
  const listBlockers = document.getElementById("list-blockers");
  const listWatch = document.getElementById("list-watch");

  // PDF Modal UI
  const pdfModal = document.getElementById("pdf-modal");
  const modalClose = document.getElementById("modal-close");
  const modalDismissBtn = document.getElementById("modal-dismiss-btn");
  const modalDownloadLink = document.getElementById("modal-download-link");
  const pdfFrame = document.getElementById("pdf-frame");

  // Evidence Modal UI
  const evidenceModal = document.getElementById("evidence-modal");
  const evidenceTitle = document.getElementById("evidence-title");
  const evidenceSubtitle = document.getElementById("evidence-subtitle");
  const evidenceModalBody = document.getElementById("evidence-modal-body");
  const evidenceModalClose = document.getElementById("evidence-modal-close");
  const evidenceModalDismiss = document.getElementById("evidence-modal-dismiss");

  // User Profile & Authentication Verification
  async function loadUserProfile() {
    try {
      const res = await fetch("/api/me", { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (data.authenticated && data.user) {
          localStorage.setItem("shift_user", JSON.stringify(data.user));
          const user = data.user;
          const nameEl = document.getElementById("user-name");
          const roleEl = document.getElementById("user-role");
          const avatarEl = document.getElementById("user-avatar");
          if (nameEl) nameEl.textContent = user.name || "Operator";
          if (roleEl) roleEl.textContent = user.role || "On-Call SRE";
          if (avatarEl) avatarEl.textContent = user.avatar || (user.name ? user.name.substring(0, 2).toUpperCase() : "OP");
          return;
        }
      } else if (res.status === 401) {
        localStorage.removeItem("shift_user");
        localStorage.removeItem("shift_token");
        window.location.href = "/login";
        return;
      }
    } catch (e) {
      console.warn("User auth verification check failed:", e);
    }

    try {
      const stored = localStorage.getItem("shift_user");
      if (!stored) {
        window.location.href = "/login";
        return;
      }
      const user = JSON.parse(stored);
      const nameEl = document.getElementById("user-name");
      const roleEl = document.getElementById("user-role");
      const avatarEl = document.getElementById("user-avatar");
      if (nameEl) nameEl.textContent = user.name || "Operator";
      if (roleEl) roleEl.textContent = user.role || "On-Call SRE";
      if (avatarEl) avatarEl.textContent = user.avatar || (user.name ? user.name.substring(0, 2).toUpperCase() : "OP");
    } catch (e) {
      window.location.href = "/login";
    }
  }
  loadUserProfile();

  // Logout Handler
  const btnLogout = document.getElementById("btn-logout");
  if (btnLogout) {
    btnLogout.addEventListener("click", async (e) => {
      e.preventDefault();
      try {
        await fetch("/api/logout", { method: "POST", headers: getAuthHeaders() });
      } catch (err) {}
      localStorage.removeItem("shift_user");
      localStorage.removeItem("shift_token");
      window.location.href = "/login";
    });
  }

  // Live UTC Clock
  function updateLiveClock() {
    const now = new Date();
    const utcStr = now.toISOString().substring(11, 19) + " UTC";
    if (liveClockEl) liveClockEl.textContent = utcStr;
  }
  setInterval(updateLiveClock, 1000);
  updateLiveClock();

  // Load Data Source Health & Database Stats
  async function loadSourceHealth() {
    try {
      const res = await fetch("/api/status");
      const data = await res.json();

      const ticketSource = data.sources?.find(s => s.name === "Ticketing");
      const incidentSource = data.sources?.find(s => s.name === "Incident Management");
      const dbStats = data.database;

      const ticketCountEl = document.getElementById("ticket-count");
      const ticketBadgeEl = document.getElementById("ticket-badge");
      const incidentCountEl = document.getElementById("incident-count");
      const incidentBadgeEl = document.getElementById("incident-badge");

      const dbFileEl = document.getElementById("db-file");
      const dbCountsEl = document.getElementById("db-counts");
      const dbReportsCountEl = document.getElementById("db-reports-count");
      const dbBadgeEl = document.getElementById("db-badge");

      if (ticketSource && ticketCountEl) {
        ticketCountEl.textContent = `${ticketSource.total_records} records`;
        if (ticketSource.connected) {
          ticketBadgeEl.textContent = "● Demo Source • Ready";
          ticketBadgeEl.className = "source-status-badge connected";
        } else {
          ticketBadgeEl.textContent = "● Unavailable";
          ticketBadgeEl.className = "source-status-badge unavailable";
        }
      }

      if (incidentSource && incidentCountEl) {
        incidentCountEl.textContent = `${incidentSource.total_records} records`;
        if (incidentSource.connected) {
          incidentBadgeEl.textContent = "● Demo Source • Ready";
          incidentBadgeEl.className = "source-status-badge connected";
        } else {
          incidentBadgeEl.textContent = "● Unavailable";
          incidentBadgeEl.className = "source-status-badge unavailable";
        }
      }

      if (dbStats && dbFileEl) {
        dbFileEl.textContent = dbStats.database_file || "shift_handover.db";
        dbCountsEl.textContent = `${dbStats.tickets_count} tickets / ${dbStats.incidents_count} incidents`;
        dbReportsCountEl.textContent = `${dbStats.reports_count} generated reports`;
        if (dbStats.connected) {
          dbBadgeEl.textContent = "● Connected • Operational";
          dbBadgeEl.className = "source-status-badge connected";
        } else {
          dbBadgeEl.textContent = "● Disconnected";
          dbBadgeEl.className = "source-status-badge unavailable";
        }
      }
    } catch (err) {
      console.warn("Failed to fetch data sources status:", err);
    }
  }
  loadSourceHealth();
  if (btnRefreshSources) btnRefreshSources.addEventListener("click", loadSourceHealth);

  // Quick Shift Presets Click Handler
  presetPills.forEach(pill => {
    pill.addEventListener("click", () => {
      presetPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");

      const start = pill.getAttribute("data-start");
      const end = pill.getAttribute("data-end");
      const tz = pill.getAttribute("data-tz");

      if (start) shiftStartInput.value = start;
      if (end) shiftEndInput.value = end;
      if (tz) shiftTzSelect.value = tz;
    });
  });

  // Animated Pipeline Steps Runner
  async function animatePipelineSteps() {
    const steps = [
      { el: stepFetch, msg: "Step 1/5: Ingesting activity from Ticketing & Incident data feeds..." },
      { el: stepFilter, msg: "Step 2/5: Normalizing UTC timestamps & filtering shift window [start, end)..." },
      { el: stepDedup, msg: "Step 3/5: Grouping by (source, record_id) & collapsing progression updates..." },
      { el: stepClassify, msg: "Step 4/5: Applying deterministic rule-based classification into 4 sections..." },
      { el: stepPublish, msg: "Step 5/5: Compiling executive-grade single PDF report via ReportLab..." }
    ];

    for (let i = 0; i < steps.length; i++) {
      steps.forEach((s, idx) => {
        if (idx < i) {
          s.el.className = "pipe-step completed";
        } else if (idx === i) {
          s.el.className = "pipe-step active";
        } else {
          s.el.className = "pipe-step";
        }
      });
      progressMsg.textContent = steps[i].msg;
      await new Promise(r => setTimeout(r, 100));
    }
  }

  // Trigger Generation
  async function triggerGeneration(dummyMode = false) {
    const startVal = shiftStartInput.value;
    const endVal = shiftEndInput.value;
    const tzVal = shiftTzSelect.value;

    if (!startVal || !endVal) {
      alert("Please specify both Shift Start and Shift End timestamps.");
      return;
    }

    const isoStart = `${startVal}:00${tzVal}`;
    const isoEnd = `${endVal}:00${tzVal}`;

    // UI state
    btnGenerate.disabled = true;
    btnGenerate.style.opacity = "0.7";
    progressSection.classList.remove("hidden");
    resultsSection.classList.add("hidden");

    await animatePipelineSteps();

    try {
      const response = await authFetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          shift_start: isoStart,
          shift_end: isoEnd,
          dummy: dummyMode
        })
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || "Failed to generate handover note.");
      }

      // Mark all steps completed
      [stepFetch, stepFilter, stepDedup, stepClassify, stepPublish].forEach(el => {
        el.className = "pipe-step completed";
      });
      progressMsg.textContent = "Handover Generation Complete!";

      // Render Results
      renderResults(data);

      setTimeout(() => {
        progressSection.classList.add("hidden");
        resultsSection.classList.remove("hidden");
        resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 200);

    } catch (err) {
      alert(`Error generating handover note:\n${err.message}`);
      progressSection.classList.add("hidden");
    } finally {
      btnGenerate.disabled = false;
      btnGenerate.style.opacity = "1";
    }
  }

  // Render Section Items with Evidence Trigger
  function renderSectionList(container, items, sectionName) {
    container.innerHTML = "";

    if (!items || items.length === 0) {
      container.innerHTML = `<div class="empty-state-banner">No activity recorded in this category during the selected shift.</div>`;
      return;
    }

    items.forEach(item => {
      const card = document.createElement("div");
      card.className = "handover-item";

      const recId = item.record_id || "N/A";
      const source = item.source || "Sample Data";
      const summary = item.summary || item.title || "Untitled Activity";
      const timestamp = item.timestamp || item.timestamp_display || "N/A";
      const status = (item.status || "N/A").replace(/_/g, " ").toUpperCase();
      const priority = item.priority || item.severity || "";
      const assignee = item.assignee || item.service || "";
      const details = item.details || item.notes || "";
      const progression = item.progression || [];
      const evidence = item.evidence || null;

      let badgesHtml = `<span class="badge-pill badge-status">${escapeHtml(status)}</span>`;
      if (priority) {
        badgesHtml += `<span class="badge-pill badge-priority">${escapeHtml(priority)}</span>`;
      }
      if (assignee) {
        badgesHtml += `<span class="badge-pill badge-assignee">${escapeHtml(assignee)}</span>`;
      }

      let progressionHtml = "";
      if (progression && progression.length > 1) {
        progressionHtml = `
          <div class="item-progression-box">
            <span style="color: var(--text-muted);">Progression:</span> 
            ${progression.map(p => escapeHtml(p)).join('<span class="progression-arrow">→</span>')}
          </div>
        `;
      }

      let detailsHtml = "";
      if (details && details !== summary) {
        detailsHtml = `<p class="item-details-text">${escapeHtml(details)}</p>`;
      }

      card.innerHTML = `
        <div class="item-top-row">
          <div class="item-summary-wrap">
            <span class="item-record-id">[${escapeHtml(recId)}]</span>
            <span class="item-summary">${escapeHtml(summary)}</span>
          </div>
          <div class="item-trace-meta">
            <span>${escapeHtml(source)}</span> | ${escapeHtml(timestamp)}
          </div>
        </div>

        <div class="item-badges-row">
          ${badgesHtml}
          <button type="button" class="btn-view-evidence" data-evidence='${escapeHtml(JSON.stringify(evidence || item))}'>
            <span>🔍 View Evidence</span>
          </button>
        </div>

        ${detailsHtml}
        ${progressionHtml}
      `;

      // Attach Evidence Modal Click Handler
      const evidenceBtn = card.querySelector(".btn-view-evidence");
      if (evidenceBtn) {
        evidenceBtn.addEventListener("click", () => {
          openEvidenceModal(item);
        });
      }

      container.appendChild(card);
    });
  }

  // Open Evidence Grounding Modal
  function openEvidenceModal(item) {
    if (!evidenceModal) return;

    const recId = item.record_id || "N/A";
    const source = item.source || "Sample Source";
    const evidence = item.evidence || {};
    const updates = evidence.all_updates || [
      {
        timestamp: item.timestamp || "N/A",
        status: item.status || "N/A",
        summary: item.summary || "",
        details: item.details || "",
        assignee: item.assignee || "",
        priority: item.priority || ""
      }
    ];

    if (evidenceTitle) evidenceTitle.textContent = `Evidence Trace: [${recId}]`;
    if (evidenceSubtitle) evidenceSubtitle.textContent = `Source System: ${source} • ${updates.length} Grounded Update(s)`;

    if (evidenceModalBody) {
      let updatesHtml = "";
      updates.forEach((u, i) => {
        updatesHtml += `
          <div class="evidence-update-card">
            <div class="evidence-update-top">
              <span class="evidence-update-time">#${i + 1} • ${escapeHtml(u.timestamp || "N/A")}</span>
              <span class="evidence-update-status">${escapeHtml(u.status || "UPDATE")}</span>
            </div>
            ${u.summary ? `<div style="font-weight:600; color:var(--text-main); font-size:12px; margin-bottom:2px;">${escapeHtml(u.summary)}</div>` : ''}
            ${u.details && u.details !== u.summary ? `<p class="evidence-update-desc">${escapeHtml(u.details)}</p>` : ''}
            <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">
              ${u.assignee ? `<span>Assignee: ${escapeHtml(u.assignee)}</span> ` : ''}
              ${u.priority ? `<span>• Priority: ${escapeHtml(u.priority)}</span>` : ''}
            </div>
          </div>
        `;
      });

      evidenceModalBody.innerHTML = `
        <div class="evidence-header-info">
          <div class="evidence-meta-row">
            <span class="evidence-meta-label">Record Identifier</span>
            <span class="evidence-meta-val">${escapeHtml(recId)}</span>
          </div>
          <div class="evidence-meta-row">
            <span class="evidence-meta-label">Origin Feed</span>
            <span class="evidence-meta-val">${escapeHtml(source)}</span>
          </div>
          <div class="evidence-meta-row">
            <span class="evidence-meta-label">First Recorded</span>
            <span class="evidence-meta-val">${escapeHtml(evidence.first_seen || item.timestamp || "N/A")}</span>
          </div>
          <div class="evidence-meta-row">
            <span class="evidence-meta-label">Latest Transition</span>
            <span class="evidence-meta-val">${escapeHtml(evidence.last_updated || item.timestamp || "N/A")}</span>
          </div>
        </div>

        <div class="evidence-timeline-title">
          <span>📜 Raw Activity Progression Audit Trail:</span>
        </div>
        <div class="evidence-updates-list">
          ${updatesHtml}
        </div>
      `;
    }

    evidenceModal.classList.remove("hidden");
  }

  function closeEvidenceModal() {
    if (evidenceModal) evidenceModal.classList.add("hidden");
  }

  if (evidenceModalClose) evidenceModalClose.addEventListener("click", closeEvidenceModal);
  if (evidenceModalDismiss) evidenceModalDismiss.addEventListener("click", closeEvidenceModal);
  if (evidenceModal) {
    evidenceModal.addEventListener("click", (e) => {
      if (e.target === evidenceModal) closeEvidenceModal();
    });
  }

  // Render Full Handover Results
  function renderResults(data) {
    const shift = data.shift_window || {};
    resultsWindowLabel.textContent = `Shift: ${shift.start} → ${shift.end} (${shift.start_utc || ''})`;

    const metrics = data.metrics || {};
    
    // Update Audit & Filter Statistics Bar
    if (statTotalRecords) statTotalRecords.textContent = metrics.total_source_records ?? metrics.total_raw_events ?? 0;
    if (statIncludedRecords) statIncludedRecords.textContent = metrics.records_inside_shift ?? metrics.total_raw_events ?? 0;
    if (statExcludedRecords) statExcludedRecords.textContent = metrics.records_excluded ?? 0;
    if (statUniqueItems) statUniqueItems.textContent = metrics.unique_items_count ?? metrics.total_collapsed_items ?? 0;

    // Update Metric Counters
    if (cntCompleted) cntCompleted.textContent = metrics.completed || 0;
    if (cntInProgress) cntInProgress.textContent = metrics.in_progress || 0;
    if (cntBlockers) cntBlockers.textContent = metrics.blockers || 0;
    if (cntWatch) cntWatch.textContent = metrics.watch_list || 0;

    const sections = data.sections || {};
    const compList = sections.completed || [];
    const inProgList = sections.in_progress || [];
    const blockList = sections.blockers || [];
    const watchList = sections.watch_list || [];

    if (badgeCompleted) badgeCompleted.textContent = `${compList.length} item(s)`;
    if (badgeInProgress) badgeInProgress.textContent = `${inProgList.length} item(s)`;
    if (badgeBlockers) badgeBlockers.textContent = `${blockList.length} item(s)`;
    if (badgeWatch) badgeWatch.textContent = `${watchList.length} item(s)`;

    renderSectionList(listCompleted, compList, "COMPLETED");
    renderSectionList(listInProgress, inProgList, "IN PROGRESS");
    renderSectionList(listBlockers, blockList, "BLOCKERS / ESCALATIONS");
    renderSectionList(listWatch, watchList, "WATCH-LIST");

    // PDF Links
    if (data.pdf_url) {
      if (btnDownloadPdf) btnDownloadPdf.href = `${data.pdf_url}?download=1`;
      if (modalDownloadLink) modalDownloadLink.href = `${data.pdf_url}?download=1`;
      if (pdfFrame) pdfFrame.src = data.pdf_url;
    }
  }

  // Load Handover History from Database
  async function loadHandoverHistory() {
    const tableBody = document.getElementById("history-table-body");
    if (!tableBody) return;

    try {
      const res = await authFetch("/api/reports");
      const data = await res.json();
      const reports = data.reports || [];

      if (!reports.length) {
        tableBody.innerHTML = `<tr><td colspan="9" class="history-empty">No previous handover reports stored yet.</td></tr>`;
        return;
      }

      tableBody.innerHTML = "";
      reports.forEach(rep => {
        const tr = document.createElement("tr");
        const pdfUrl = `/api/download/${encodeURIComponent(rep.pdf_filename)}`;

        tr.innerHTML = `
          <td><strong>#${rep.id}</strong></td>
          <td class="code" style="font-size:11.5px;">${escapeHtml(rep.shift_start)} <br/><span style="color:var(--text-muted);">to</span> ${escapeHtml(rep.shift_end)}</td>
          <td><strong>${rep.total_items}</strong></td>
          <td><span class="history-pill completed">${rep.completed_count}</span></td>
          <td><span class="history-pill in-progress">${rep.in_progress_count}</span></td>
          <td><span class="history-pill blockers">${rep.blockers_count}</span></td>
          <td><span class="history-pill watch-list">${rep.watchlist_count}</span></td>
          <td style="font-size:11px; color:var(--text-secondary);">${escapeHtml(rep.generated_at)}</td>
          <td>
            <div class="history-actions">
              <button class="history-btn primary btn-view-report" data-id="${rep.id}">VIEW</button>
              <a href="${pdfUrl}?download=1" class="history-btn" target="_blank" download>PDF</a>
            </div>
          </td>
        `;
        tableBody.appendChild(tr);
      });

      // Attach View Handlers
      tableBody.querySelectorAll(".btn-view-report").forEach(btn => {
        btn.addEventListener("click", async () => {
          const reportId = btn.getAttribute("data-id");
          await viewHistoricalReport(reportId);
        });
      });
    } catch (err) {
      console.warn("Failed to load handover history:", err);
      tableBody.innerHTML = `<tr><td colspan="9" class="history-empty">Failed to load reports: ${escapeHtml(err.message)}</td></tr>`;
    }
  }

  // View Specific Historical Report
  async function viewHistoricalReport(reportId) {
    try {
      const res = await authFetch(`/api/reports/${reportId}`);
      const data = await res.json();
      if (data.success && data.report) {
        const rep = data.report;
        const formattedData = {
          success: true,
          shift_window: {
            start: rep.shift_start,
            end: rep.shift_end,
            start_utc: rep.shift_start,
            end_utc: rep.shift_end
          },
          metrics: {
            total_source_records: rep.total_items,
            total_raw_events: rep.total_items,
            records_inside_shift: rep.total_items,
            records_excluded: 0,
            unique_items_count: (rep.completed_count + rep.in_progress_count + rep.blockers_count + rep.watchlist_count),
            completed: rep.completed_count,
            in_progress: rep.in_progress_count,
            blockers: rep.blockers_count,
            watch_list: rep.watchlist_count
          },
          sections: {
            completed: rep.sections?.COMPLETED || [],
            in_progress: rep.sections?.["IN PROGRESS"] || [],
            blockers: rep.sections?.["BLOCKERS / ESCALATIONS"] || [],
            watch_list: rep.sections?.["WATCH-LIST"] || []
          },
          pdf_url: `/api/download/${encodeURIComponent(rep.pdf_filename)}`
        };

        resultsSection.classList.remove("hidden");
        renderResults(formattedData);
        resultsSection.scrollIntoView({ behavior: "smooth" });
      }
    } catch (e) {
      alert(`Error loading report #${reportId}: ${e.message}`);
    }
  }

  // History Refresh Button
  const btnRefreshHistory = document.getElementById("btn-refresh-history");
  if (btnRefreshHistory) {
    btnRefreshHistory.addEventListener("click", loadHandoverHistory);
  }
  loadHandoverHistory();

  // PDF Modal Listeners
  if (btnViewPdf && pdfModal) {
    btnViewPdf.addEventListener("click", () => {
      pdfModal.classList.remove("hidden");
    });
  }

  function closePdfModal() {
    if (pdfModal) pdfModal.classList.add("hidden");
  }

  if (modalClose) modalClose.addEventListener("click", closePdfModal);
  if (modalDismissBtn) modalDismissBtn.addEventListener("click", closePdfModal);
  if (pdfModal) {
    pdfModal.addEventListener("click", (e) => {
      if (e.target === pdfModal) closePdfModal();
    });
  }

  // Form Submit Handler
  if (shiftForm) {
    shiftForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      await triggerGeneration(false);
      loadHandoverHistory();
      loadSourceHealth();
    });
  }

  // Dummy Test Handler
  if (btnDummyTest) {
    btnDummyTest.addEventListener("click", async () => {
      await triggerGeneration(true);
      loadHandoverHistory();
      loadSourceHealth();
    });
  }

  // Hero Quick Run Handler
  const heroRunBtn = document.getElementById("hero-run-btn");
  if (heroRunBtn) {
    heroRunBtn.addEventListener("click", async () => {
      await triggerGeneration(false);
      loadHandoverHistory();
      loadSourceHealth();
    });
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
