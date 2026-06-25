/* ═══════════════════════════════════════════
   AMAN PHONE — main.js
   Handles:
     1. Nav active link highlighting
     2. index.html — OCR auto-scan on image pick
     3. report.html — OCR auto-fill all fields + city dropdown
   ═══════════════════════════════════════════ */

/* ── Nav active state is set server-side via Jinja active_page variable ── */


/* ═══════════════════════════════════════════
   2. CHECK PAGE — OCR scan on image select
   ═══════════════════════════════════════════ */
(function () {
  const imageInput  = document.getElementById("image-input");
  const imeiInput   = document.getElementById("imei-input");
  const submitBtn   = document.getElementById("submit-btn");
  const loadingHint = document.getElementById("loading-hint");

  if (!imageInput) return;   // not on check page

  imageInput.addEventListener("change", async function () {
    const file = imageInput.files[0];
    if (!file) return;

    // Show loading state
    loadingHint.style.display = "block";
    submitBtn.disabled        = true;
    submitBtn.textContent     = "Scanning...";
    imeiInput.value           = "";
    imeiInput.placeholder     = "Detecting IMEI...";

    const formData = new FormData();
    formData.append("image", file);

    try {
      const response = await fetch("/extract-imei", { method: "POST", body: formData });
      const data     = await response.json();

      if (data.error) {
        console.error("IMEI extraction error:", data.error);
        imeiInput.placeholder = "Could not detect IMEI — enter manually";
      } else {
        imeiInput.value = data.imei_1 || "";
        if (!data.imei_1) imeiInput.placeholder = "No IMEI found — enter manually";
        if (data.imei_2)  console.log("IMEI 2 detected:", data.imei_2);
        if (data.detection_method) console.log("Detection method:", data.detection_method);
      }
    } catch (err) {
      console.error("Fetch error:", err);
      imeiInput.placeholder = "Scan failed — enter IMEI manually";
    }

    // Restore UI
    loadingHint.style.display = "none";
    submitBtn.disabled        = false;
    submitBtn.textContent     = "Check Device Status";
  });
})();


/* ═══════════════════════════════════════════
   3. REPORT PAGE — OCR auto-fill + city dropdown
   ═══════════════════════════════════════════ */
(function () {
  const imageInput      = document.getElementById("image-input");
  const imei1Input      = document.getElementById("imei-hidden");  // report page: imei-hidden is the real imei_1 field
  const imei2Input      = document.getElementById("imei2-input");
  const serialInput     = document.getElementById("serial-input");
  const modelInput      = document.getElementById("model-input");
  const colorInput      = document.getElementById("color-input");
  const submitBtn       = document.getElementById("submit-btn");
  const loadingHint     = document.getElementById("loading-hint");
  const autofillSummary = document.getElementById("autofill-summary");

  if (!imei1Input) return;   // not on report page
  if (!document.getElementById('report-form')) return;  // extra guard: skip on check page

  // ── Helpers ──────────────────────────────
  function autofill(el, value) {
    if (el && value) {
      el.value = value;
      el.classList.add("auto-filled");
    }
  }

  function clearAutofill() {
    [imei1Input, imei2Input, serialInput, modelInput, colorInput].forEach(el => {
      if (!el) return;
      el.value = "";
      el.classList.remove("auto-filled");
    });
    if (autofillSummary) {
      autofillSummary.style.display = "none";
      autofillSummary.textContent   = "";
    }
    if (imei1Input) imei1Input.placeholder = "15-digit primary IMEI";
  }

  function showSummary(data) {
    if (!autofillSummary) return;
    const filled = [];
    if (data.imei_1)        filled.push("IMEI 1");
    if (data.imei_2)        filled.push("IMEI 2");
    if (data.serial_number) filled.push("Serial");
    if (data.model_name)    filled.push("Model");
    if (data.color)         filled.push("Color");

    if (filled.length > 0) {
      autofillSummary.className     = "alert alert-success autofill-summary";
      autofillSummary.textContent   = "✅ Auto-filled: " + filled.join(", ");
      autofillSummary.style.display = "flex";
    }
  }

  // ── OCR image scan ────────────────────────
  if (imageInput) {
    imageInput.addEventListener("change", async function () {
      const file = imageInput.files[0];
      if (!file) return;

      clearAutofill();
      if (loadingHint)  loadingHint.style.display = "block";
      if (submitBtn)    { submitBtn.disabled = true; submitBtn.textContent = "Scanning..."; }
      if (imei1Input)   imei1Input.placeholder = "Detecting IMEI...";

      const formData = new FormData();
      formData.append("image", file);

      try {
        const response = await fetch("/extract-imei", { method: "POST", body: formData });
        const data     = await response.json();

        if (data.error) {
          console.error("Extraction error:", data.error);
          if (imei1Input) imei1Input.placeholder = "Could not detect IMEI — enter manually";
        } else {
          autofill(imei1Input,  data.imei_1);
          autofill(imei2Input,  data.imei_2);
          autofill(serialInput, data.serial_number);
          autofill(modelInput,  data.model_name);
          autofill(colorInput,  data.color);
          if (!data.imei_1 && imei1Input) imei1Input.placeholder = "No IMEI found — enter manually";
          showSummary(data);
          console.log("Detection method:", data.detection_method);
        }
      } catch (err) {
        console.error("Fetch error:", err);
        if (imei1Input) imei1Input.placeholder = "Scan failed — enter IMEI manually";
      }

      if (loadingHint) loadingHint.style.display = "none";
      if (submitBtn)   { submitBtn.disabled = false; submitBtn.textContent = "Report as Stolen"; }
    });
  }

  /* ── City dropdown ───────────────────────── */
  const EGYPT_CITIES = [
    "Cairo", "Giza", "Alexandria", "Shubra El Kheima", "Port Said",
    "Suez", "Luxor", "Mansoura", "El Mahalla El Kubra", "Tanta",
    "Asyut", "Ismailia", "Faiyum", "Zagazig", "Aswan",
    "Damietta", "Damanhur", "Minya", "Beni Suef", "Qena",
    "Sohag", "Hurghada", "Shibin El Kom", "Banha", "Kafr El Sheikh",
    "Arish", "Mallawi", "10th of Ramadan City", "Bilbays", "Marsa Matruh",
    "Idfu", "Mit Ghamr", "Al Hamidiyya", "Desouk", "Qalyub",
    "Abu Kabir", "Kafr El Dawwar", "Girga", "Akhmim", "Matareya",
    "New Cairo", "6th of October City", "Nasr City", "Heliopolis",
    "Maadi", "Zamalek", "Dokki", "Mohandessin", "Helwan", "Sharm El Sheikh",
  ];

  const placeInput    = document.getElementById("place-input");
  const placeHidden   = document.getElementById("place-hidden");
  const placeDropdown = document.getElementById("place-dropdown");

  if (!placeInput) return;

  let highlightIndex = -1;

  function renderDropdown(query) {
    const q = query.trim().toLowerCase();
    const filtered = q === ""
      ? EGYPT_CITIES
      : EGYPT_CITIES.filter(c => c.toLowerCase().includes(q));

    placeDropdown.innerHTML = "";
    highlightIndex = -1;

    if (filtered.length === 0) {
      placeDropdown.innerHTML = '<div class="dropdown-empty">No cities found</div>';
    } else {
      filtered.forEach(city => {
        const item = document.createElement("div");
        item.className   = "dropdown-item";
        item.textContent = city;
        item.setAttribute("role", "option");
        item.addEventListener("mousedown", e => { e.preventDefault(); selectCity(city); });
        placeDropdown.appendChild(item);
      });
    }

    placeDropdown.classList.add("open");
  }

  function selectCity(city) {
    placeInput.value  = city;
    placeHidden.value = city;
    placeDropdown.classList.remove("open");
    placeDropdown.innerHTML = "";
  }

  function updateHighlight(items) {
    items.forEach((item, i) => item.classList.toggle("highlighted", i === highlightIndex));
    if (highlightIndex >= 0) items[highlightIndex].scrollIntoView({ block: "nearest" });
  }

  placeInput.addEventListener("focus",  () => renderDropdown(placeInput.value));
  placeInput.addEventListener("input",  () => { placeHidden.value = placeInput.value; renderDropdown(placeInput.value); });
  placeInput.addEventListener("blur",   () => setTimeout(() => placeDropdown.classList.remove("open"), 150));
  placeInput.addEventListener("keydown", e => {
    const items = placeDropdown.querySelectorAll(".dropdown-item");
    if      (e.key === "ArrowDown")                    { e.preventDefault(); highlightIndex = Math.min(highlightIndex + 1, items.length - 1); updateHighlight(items); }
    else if (e.key === "ArrowUp")                      { e.preventDefault(); highlightIndex = Math.max(highlightIndex - 1, 0); updateHighlight(items); }
    else if (e.key === "Enter" && highlightIndex >= 0) { e.preventDefault(); selectCity(items[highlightIndex].textContent); }
    else if (e.key === "Escape")                       { placeDropdown.classList.remove("open"); }
  });
})();


/* ═══════════════════════════════════════════
   4. HOME PAGE — Stats count-up animation
   Targets: .home-stats__number
   Runs once on page load via IntersectionObserver
   ═══════════════════════════════════════════ */
(function () {
  const statEls = document.querySelectorAll(".home-stats__number");

  // Only run on the home page where stats exist
  if (!statEls.length) return;

  // ── Ease-out timing function ─────────────
  // Returns a value 0→1 that decelerates toward the end
  function easeOut(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  // ── Animate a single element ─────────────
  // Reads the target number from data-target,
  // preserves any prefix (e.g. "+") in the original text.
  function animateCounter(el) {
    const rawText  = el.getAttribute("data-target") || el.textContent.trim();
    const prefix   = rawText.startsWith("+") ? "+" : "";
    const target   = parseInt(rawText.replace(/\D/g, ""), 10);

    // If target is 0 or NaN — nothing to animate
    if (!target || isNaN(target)) {
      el.textContent = prefix + "0";
      return;
    }

    const duration = 1000;   // ms
    const start    = performance.now();

    // Set to 0 immediately to avoid showing the raw server value
    el.textContent = prefix + "0";

    function tick(now) {
      const elapsed  = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const current  = Math.round(easeOut(progress) * target);

      el.textContent = prefix + current.toLocaleString();

      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        // Ensure exact final value
        el.textContent = prefix + target.toLocaleString();
      }
    }

    requestAnimationFrame(tick);
  }

  // ── Store target values before DOM changes ─
  statEls.forEach(el => {
    el.setAttribute("data-target", el.textContent.trim());
  });

  // ── Trigger on scroll into view ───────────
  // Uses IntersectionObserver so the animation only runs
  // when the stats section is actually visible.
  // Falls back to immediate animation if not supported.
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            animateCounter(entry.target);
            obs.unobserve(entry.target);   // animate only once
          }
        });
      },
      { threshold: 0.3 }   // trigger when 30% of element is visible
    );

    statEls.forEach(el => observer.observe(el));

  } else {
    // Fallback for older browsers
    statEls.forEach(el => animateCounter(el));
  }
})();


/* ═══════════════════════════════════════════
   5. LOGIN MODAL
   ═══════════════════════════════════════════ */
(function () {
  const overlay    = document.getElementById("login-modal");
  const closeBtn   = document.getElementById("modal-close");
  const form       = document.getElementById("modal-login-form");
  const errorEl    = document.getElementById("modal-error");
  const submitBtn  = document.getElementById("modal-submit-btn");

  if (!overlay) return;   // modal not present on this page

  // ── Open / close helpers ──────────────────
  function openModal() {
    overlay.classList.add("open");
    document.getElementById("modal-username").focus();
  }

  function closeModal() {
    overlay.classList.remove("open");
    errorEl.classList.remove("visible");
    errorEl.textContent = "";
    form.reset();
  }

  // ── Trigger: navbar Login link ────────────
  const loginLink = document.getElementById("nav-login-link");
  if (loginLink) {
    loginLink.addEventListener("click", function (e) {
      e.preventDefault();
      openModal();
    });
  }

  // ── Auto-open if URL has ?login=1 ─────────
  // Used when /dashboard redirects unauthenticated users
  if (new URLSearchParams(window.location.search).get("login") === "1") {
    openModal();
  }

  // ── Close: X button ───────────────────────
  closeBtn.addEventListener("click", closeModal);

  // ── Close: click outside modal card ──────
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) closeModal();
  });

  // ── Close: ESC key ────────────────────────
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && overlay.classList.contains("open")) closeModal();
  });

  // ── Form submit via fetch ─────────────────
  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    submitBtn.disabled    = true;
    submitBtn.textContent = "Signing in...";
    errorEl.classList.remove("visible");

    const formData = new FormData(form);

    try {
      const response = await fetch("/login", {
        method: "POST",
        body:   formData
      });

      const data = await response.json();

      if (data.success) {
        // Redirect to dashboard (or wherever server specifies)
        window.location.href = data.redirect || "/dashboard";
      } else {
        // Show error inside modal — no page reload
        errorEl.textContent = data.error || "Login failed.";
        errorEl.classList.add("visible");
        submitBtn.disabled    = false;
        submitBtn.textContent = "Sign In";
      }

    } catch (err) {
      console.error("Login fetch error:", err);
      errorEl.textContent = "Connection error. Please try again.";
      errorEl.classList.add("visible");
      submitBtn.disabled    = false;
      submitBtn.textContent = "Sign In";
    }
  });

})();


/* ═══════════════════════════════════════════
   6. LOGOUT CONFIRMATION MODAL
   ═══════════════════════════════════════════ */
(function () {
  const overlay    = document.getElementById("logout-modal");
  const closeBtn   = document.getElementById("logout-modal-close");
  const cancelBtn  = document.getElementById("logout-cancel-btn");
  const logoutLink = document.getElementById("nav-logout-link");

  if (!overlay || !logoutLink) return;

  function openLogoutModal()  { overlay.classList.add("open"); }
  function closeLogoutModal() { overlay.classList.remove("open"); }

  // Intercept logout nav click → open confirmation instead
  logoutLink.addEventListener("click", function (e) {
    e.preventDefault();
    openLogoutModal();
  });

  closeBtn.addEventListener("click",  closeLogoutModal);
  cancelBtn.addEventListener("click", closeLogoutModal);

  // Click outside card to cancel
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) closeLogoutModal();
  });

  // ESC to cancel
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && overlay.classList.contains("open")) closeLogoutModal();
  });
  // #logout-confirm-btn is a plain <a href="/logout"> — no JS needed for confirm action
})();


/* ═══════════════════════════════════════════
   7. DARK MODE — theme toggle
   Reads/saves preference in localStorage
   Sets [data-theme="dark"] on <html>
   ═══════════════════════════════════════════ */
(function () {

  const STORAGE_KEY = "aman-theme";
  const html        = document.documentElement;

  // ── Apply saved theme on page load (dark is default) ─
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved !== "light") html.setAttribute("data-theme", "dark");

  // ── Inject toggle button into every navbar ─
  const navLinks = document.querySelector(".nav-links");
  if (!navLinks) return;

  const btn = document.createElement("button");
  btn.className   = "theme-toggle";
  btn.id          = "theme-toggle-btn";
  btn.title       = "Toggle dark / light mode";
  btn.textContent = html.getAttribute("data-theme") === "dark" ? "☀️" : "🌙";

  navLinks.appendChild(btn);

  // ── Toggle handler ────────────────────────
  btn.addEventListener("click", function () {
    const isDark = html.getAttribute("data-theme") === "dark";

    if (isDark) {
      html.removeAttribute("data-theme");
      localStorage.setItem(STORAGE_KEY, "light");
      btn.textContent = "🌙";
    } else {
      html.setAttribute("data-theme", "dark");
      localStorage.setItem(STORAGE_KEY, "dark");
      btn.textContent = "☀️";
    }

    // Notify charts to update their colors
    document.dispatchEvent(new CustomEvent("themechange"));
  });

  // ── Update Chart.js colors on theme change ─
  // Dashboard charts listen for this event and re-render
  document.addEventListener("themechange", function () {
    const dark       = html.getAttribute("data-theme") === "dark";
    const tickColor  = dark ? "#9aa0b0" : "#7a8499";
    const gridColor  = dark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.05)";

    // Update all registered Chart instances
    if (typeof Chart !== "undefined" && Chart.instances) {
      Object.values(Chart.instances).forEach(chart => {
        // Update scale colors
        if (chart.options.scales) {
          Object.values(chart.options.scales).forEach(scale => {
            if (scale.ticks)  scale.ticks.color = tickColor;
            if (scale.grid)   scale.grid.color  = gridColor;
          });
        }
        // Update legend colors
        if (chart.options.plugins?.legend?.labels) {
          chart.options.plugins.legend.labels.color = tickColor;
        }
        chart.update("none");
      });
    }
  });

})();


/* ═══════════════════════════════════════════
   8. HAMBURGER MENU — mobile nav toggle
   Uses max-height animation via CSS .open class
   ═══════════════════════════════════════════ */
(function () {
  const toggle   = document.getElementById("nav-toggle");
  const navLinks = document.querySelector(".nav-links");

  if (!toggle || !navLinks) return;

  function openMenu() {
    navLinks.classList.add("open");
    toggle.innerHTML = "&#10005;";       // ✕
    toggle.setAttribute("aria-expanded", "true");
  }

  function closeMenu() {
    navLinks.classList.remove("open");
    toggle.innerHTML = "&#9776;";        // ☰
    toggle.setAttribute("aria-expanded", "false");
  }

  toggle.addEventListener("click", function (e) {
    e.stopPropagation();
    navLinks.classList.contains("open") ? closeMenu() : openMenu();
  });

  // Close when a nav link is clicked
  navLinks.querySelectorAll("a.nav-link").forEach(link => {
    link.addEventListener("click", closeMenu);
  });

  // Close when clicking anywhere outside the navbar
  document.addEventListener("click", function (e) {
    const navbar = document.querySelector(".nav-header");
    if (navbar && !navbar.contains(e.target)) closeMenu();
  });

  // Close on ESC
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeMenu();
  });
})();


/* ═══════════════════════════════════════════
   9. DROP ZONE — drag & drop image upload
   Works on check.html and report.html
   Syncs with existing #image-input logic
   ═══════════════════════════════════════════ */
(function () {
  const dropZone   = document.getElementById("drop-zone");
  const fileInput  = document.getElementById("image-input");
  const preview    = document.getElementById("drop-zone-preview");

  if (!dropZone || !fileInput) return;

  // ── Show preview and update state ────────
  function handleFile(file) {
    if (!file || !file.type.startsWith("image/")) return;

    // Show preview
    const reader = new FileReader();
    reader.onload = e => {
      if (preview) {
        preview.src = e.target.result;
      }
      dropZone.classList.add("has-file");
    };
    reader.readAsDataURL(file);
  }

  // ── File input change (click to browse) ──
  // The native input sits over the drop zone and catches clicks naturally
  fileInput.addEventListener("change", function () {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
  });

  // ── Drag & drop events ────────────────────
  dropZone.addEventListener("dragover", function (e) {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });

  dropZone.addEventListener("dragleave", function (e) {
    // Only remove if leaving the drop zone itself, not a child
    if (!dropZone.contains(e.relatedTarget)) {
      dropZone.classList.remove("drag-over");
    }
  });

  dropZone.addEventListener("drop", function (e) {
    e.preventDefault();
    dropZone.classList.remove("drag-over");

    const file = e.dataTransfer.files[0];
    if (!file) return;

    // Assign to the hidden input so the form submits it correctly
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;

    // Trigger the existing image-scan logic in the rest of main.js
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));

    handleFile(file);
  });

  // ── Keyboard accessibility ────────────────
  dropZone.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

})();


/* ═══════════════════════════════════════════
   10. IMAGE UPLOAD UX
   Handles check.html and report.html
   Features:
   - Rotating scan messages with spinner
   - Error: only "Try another image" (no inline manual button)
   - Success: IMEI badge + auto-submit (check only)
   - Manual IMEI: validation delay before submit
   - Report page: fills imei1-input + model + color from scan
   ═══════════════════════════════════════════ */
(function () {

  /* ─────────────────────────────────────────
     SHARED UTILITIES
  ───────────────────────────────────────── */

  const SCAN_MESSAGES = [
    "Analyzing image...",
    "Searching for IMEI barcode...",
    "Scanning barcode...",
    "Validating IMEI format...",
    "Finalizing result..."
  ];

  /* ─── Progress bar state ─────────────────── */
  let _progTimer = null;
  let _progVal   = 0;

  function _getBar() {
    return document.getElementById("scan-prog-bar");
  }

  function _setBar(pct, transition) {
    const bar = _getBar();
    if (!bar) return;
    bar.style.transition = transition || "width 0.4s ease";
    bar.style.width      = pct + "%";
    _progVal = pct;
  }

  /** Begin animating progress bar 0 → ~88% */
  function startProgress() {
    clearInterval(_progTimer);
    _progVal = 0;
    _setBar(0, "none");
    _progTimer = setInterval(() => {
      if (_progVal >= 88) { clearInterval(_progTimer); return; }
      const step = _progVal < 50 ? 8 : _progVal < 75 ? 4 : 1.5;
      _setBar(Math.min(_progVal + step, 88), "width 0.4s ease");
    }, 280);
  }

  /** Complete bar to 100%, then fire optional callback */
  function completeProgress(cb) {
    clearInterval(_progTimer);
    _setBar(100, "width 0.25s ease");
    setTimeout(cb || (() => {}), 280);
  }

  /** Instantly reset bar to 0% (on retry) */
  function resetProgress() {
    clearInterval(_progTimer);
    _progVal = 0;
    const bar = _getBar();
    if (bar) { bar.style.transition = "none"; bar.style.width = "0%"; }
  }

  /** Start rotating scan messages + progress bar. Returns a stop function.
   *
   * Sequence (run ONCE, no loop):
   *   0. "Analyzing image..."          (shown immediately)
   *   1. "Searching for IMEI barcode..."
   *   2. "Scanning IMEI barcode..."
   *   3. "Validating IMEI format..."
   *   4. "Finalizing result..."        (hold here until backend responds)
   *
   * After the 4th message the function stops scheduling further updates.
   * The "Finalizing result..." text stays visible until completeProgress()
   * replaces the status element with the success/error state.
   */
  function startScanMessages(statusEl) {
    if (!statusEl) return () => {};

    // Only the first 4 messages advance automatically;
    // the 5th ("Finalizing result...") is shown and held.
    const SEQUENCE = [
      "Analyzing image...",
      "Searching for IMEI barcode...",
      "Scanning IMEI barcode...",
      "Validating IMEI format...",
      "Finalizing result..."
    ];
    const HOLD_IDX = SEQUENCE.length - 1;   // index of the hold message

    let idx     = 0;
    let stopped = false;
    let timer   = null;

    function showMsg(msg) {
      statusEl.className     = "scan-status scanning";
      statusEl.style.display = "flex";

      if (idx === 0) {
        // First render — build full DOM with progress bar
        statusEl.innerHTML =
          '<div class="scan-spinner"></div>' +
          '<div class="scan-status__body">' +
            '<span class="scan-msg">' + msg + '</span>' +
            '<div class="scan-progress">' +
              '<div class="scan-progress-bar" id="scan-prog-bar"></div>' +
            '</div>' +
          '</div>';
        startProgress();
      } else {
        // Subsequent steps — only swap the text
        const msgEl = statusEl.querySelector(".scan-msg");
        if (msgEl) msgEl.textContent = msg;
      }
    }

    function advance() {
      if (stopped) return;
      showMsg(SEQUENCE[idx]);

      // Stop scheduling after reaching the hold message
      if (idx < HOLD_IDX) {
        idx++;
        timer = setTimeout(advance, 900);
      }
      // idx === HOLD_IDX: "Finalizing result..." is now showing; do nothing further
    }

    advance();

    return function stop() {
      stopped = true;
      if (timer) { clearTimeout(timer); timer = null; }
    };
  }

  function showSuccess(statusEl, html) {
    if (!statusEl) return;
    statusEl.className     = "scan-status success";
    statusEl.innerHTML     = html;
    statusEl.style.display = "flex";
  }

  function showError(statusEl, html) {
    if (!statusEl) return;
    statusEl.className     = "scan-status error";
    statusEl.innerHTML     = html;
    statusEl.style.display = "flex";
  }

  function hideScanStatus(statusEl) {
    if (!statusEl) return;
    statusEl.style.display = "none";
    statusEl.innerHTML     = "";
    statusEl.className     = "scan-status";
  }

  /** Reset drop zone to empty state */
  function resetDropZone(dz, fileInput) {
    if (dz)        dz.classList.remove("has-file");
    if (fileInput) fileInput.value = "";
    const preview = document.getElementById("drop-zone-preview");
    if (preview)   { preview.src = ""; }
  }

  /** Show drop zone preview from a File object */
  function previewFile(file, dz) {
    if (!file || !dz) return;
    const preview = dz.querySelector(".drop-zone__preview");
    if (!preview) return;
    const reader = new FileReader();
    reader.onload = e => {
      preview.src = e.target.result;
      dz.classList.add("has-file");
    };
    reader.readAsDataURL(file);
  }

  /* ─────────────────────────────────────────
     CHECK PAGE
  ───────────────────────────────────────── */
  const checkForm       = document.getElementById("check-form");
  const imeiHidden      = document.getElementById("imei-hidden");
  const checkDz         = document.getElementById("drop-zone");
  const checkFileInput  = document.getElementById("image-input");
  const checkStatus     = document.getElementById("scan-status");
  const manualToggleBtn = document.getElementById("manual-toggle-btn");
  const backToScanBtn   = document.getElementById("back-to-scan-btn");
  const uploadView      = document.getElementById("upload-view");
  const manualView      = document.getElementById("manual-view");
  const imeiManual      = document.getElementById("imei-manual");
  const manualStatus    = document.getElementById("manual-status");
  const submitBtn       = document.getElementById("submit-btn");

  // ── Manual / upload toggle ───────────────
  if (manualToggleBtn && uploadView && manualView) {
    manualToggleBtn.addEventListener("click", () => {
      uploadView.style.display = "none";
      manualView.style.display = "block";
      if (imeiManual) imeiManual.focus();
    });
  }

  if (backToScanBtn && uploadView && manualView) {
    backToScanBtn.addEventListener("click", () => {
      manualView.style.display = "none";
      uploadView.style.display = "block";
      if (imeiManual) imeiManual.value = "";
      if (imeiHidden) imeiHidden.value = "";
      hideScanStatus(checkStatus);
      hideScanStatus(manualStatus);
      resetDropZone(checkDz, checkFileInput);
    });
  }

  // ── Manual submit: validation delay (check) ─
  if (checkForm && imeiManual && imeiHidden && submitBtn) {
    checkForm.addEventListener("submit", function (e) {
      // Only intercept when manual view is showing
      if (!manualView || manualView.style.display === "none") return;

      const val = imeiManual.value.trim();
      if (!val) return; // let browser required attr handle empty

      e.preventDefault();

      hideScanStatus(manualStatus);
      submitBtn.disabled    = true;
      submitBtn.textContent = "Validating...";

      showSuccess(manualStatus,
        '<div class="scan-spinner" style="border-top-color:var(--blue);border-color:rgba(26,115,232,0.2);"></div>' +
        '<span>Validating IMEI format...</span>'
      );
      // Use scanning class for this intermediate state
      manualStatus.className = "scan-status scanning";

      setTimeout(() => {
        imeiHidden.value = val;
        checkForm.submit();
      }, 450);
    });
  }

  // ── Image scan (check page) ──────────────
  if (checkFileInput && checkForm) {
    checkFileInput.addEventListener("change", async function () {
      const file = checkFileInput.files[0];
      if (!file) return;

      previewFile(file, checkDz);

      const stopMessages = startScanMessages(checkStatus);
      if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Scanning..."; }

      const fd = new FormData();
      fd.append("image", file);

      try {
        const res  = await fetch("/extract-imei", { method: "POST", body: fd });
        const data = await res.json();
        stopMessages();

        if (data.error || !data.imei_1) {
          // Error — only "Try another image", no inline manual button
          completeProgress(() => {
            showError(checkStatus,
              `<div>
                 <div style="margin-bottom:8px;">❌ Could not extract IMEI from image.</div>
                 <div class="scan-error-actions">
                   <button type="button" class="btn btn-outline" id="retry-upload-btn">📷 Try another image</button>
                 </div>
               </div>`
            );
            document.getElementById("retry-upload-btn")?.addEventListener("click", () => {
              hideScanStatus(checkStatus);
              resetDropZone(checkDz, checkFileInput);
              resetProgress();
              if (imeiHidden) imeiHidden.value = "";
            });
            if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Check Device Status"; }
          });

        } else {
          // Success — badge + auto-submit
          imeiHidden.value = data.imei_1;
          completeProgress(() => {
            showSuccess(checkStatus,
              `<div>
                 <span>✅ IMEI extracted successfully</span>
                 <div class="imei-scan-badge">📱 ${data.imei_1}</div>
               </div>`
            );
            if (submitBtn) { submitBtn.textContent = "Checking device status..."; }
            setTimeout(() => { if (checkForm) checkForm.submit(); }, 900);
          });
        }

      } catch (err) {
        completeProgress(() => {
          showError(checkStatus, "❌ Connection error. Please try again.");
          if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Check Device Status"; }
        });
      }
    });
  }

  /* ─────────────────────────────────────────
     REPORT PAGE
     Detected by presence of imei1-input
     (report page uses named input, not hidden)
  ───────────────────────────────────────── */
  const reportForm      = document.getElementById("report-form");
  const reportFileInput = reportForm ? document.getElementById("image-input") : null;
  const reportStatus    = reportForm ? document.getElementById("scan-status")  : null;
  const imei1Input      = document.getElementById("imei-hidden");  // report page: imei-hidden is the real imei_1 field
  const modelInput      = document.getElementById("model-input");
  const colorInput      = document.getElementById("color-input");
  const reportSubmitBtn = reportForm ? document.getElementById("submit-btn")   : null;
  // Manual toggle refs for report page
  const rManualToggle   = reportForm ? document.getElementById("manual-toggle-btn") : null;
  const rBackToScan     = reportForm ? document.getElementById("back-to-scan-btn")  : null;
  const rUploadView     = reportForm ? document.getElementById("upload-view")        : null;
  const rManualView     = reportForm ? document.getElementById("manual-view")        : null;
  const rImeiManual     = reportForm ? document.getElementById("imei-manual")        : null;
  const rManualStatus   = reportForm ? document.getElementById("manual-status")      : null;
  const rDropZone       = reportForm ? document.getElementById("drop-zone")          : null;
  // Hidden IMEI field on report page
  const rImeiHidden     = reportForm ? document.getElementById("imei-hidden")        : null;

  // Only run on report page (detected by report-form ID)
  if (reportForm) {

    // ── Manual / upload toggle (report) ───
    if (rManualToggle && rUploadView && rManualView) {
      rManualToggle.addEventListener("click", () => {
        rUploadView.style.display = "none";
        rManualView.style.display = "block";
        if (rImeiManual) rImeiManual.focus();
      });
    }

    if (rBackToScan && rUploadView && rManualView) {
      rBackToScan.addEventListener("click", () => {
        rManualView.style.display = "none";
        rUploadView.style.display = "block";
        if (rImeiManual) rImeiManual.value = "";
        hideScanStatus(reportStatus);
        hideScanStatus(rManualStatus);
        resetDropZone(rDropZone, reportFileInput);
      });
    }

    // ── Manual submit: validation delay (report) ─
    reportForm.addEventListener("submit", function (e) {
      if (!rManualView || rManualView.style.display === "none") return;
      const val = rImeiManual ? rImeiManual.value.trim() : "";
      if (!val) return;

      e.preventDefault();

      hideScanStatus(rManualStatus);
      if (reportSubmitBtn) { reportSubmitBtn.disabled = true; reportSubmitBtn.textContent = "Validating..."; }

      if (rManualStatus) {
        rManualStatus.className    = "scan-status scanning";
        rManualStatus.innerHTML    =
          '<div class="scan-spinner" style="border-top-color:var(--blue);border-color:rgba(26,115,232,0.2);"></div>' +
          '<span>Validating IMEI format...</span>';
        rManualStatus.style.display = "flex";
      }

      setTimeout(() => {
        // Sync manual IMEI to hidden field for form submission
        if (imei1Input) imei1Input.value = val;
        reportForm.submit();
      }, 450);
    });

    // ── Image scan (report page) ──────────
    if (reportFileInput) {
      reportFileInput.addEventListener("change", async function () {
        const file = reportFileInput.files[0];
        if (!file) return;

        previewFile(file, rDropZone);

        const stopMessages = startScanMessages(reportStatus);
        if (reportSubmitBtn) { reportSubmitBtn.disabled = true; reportSubmitBtn.textContent = "Scanning..."; }

        const fd = new FormData();
        fd.append("image", file);

        try {
          const res  = await fetch("/extract-imei", { method: "POST", body: fd });
          const data = await res.json();
          stopMessages();

          if (data.error || !data.imei_1) {
            // Error — only "Try another image"
            completeProgress(() => {
              showError(reportStatus,
                `<div>
                   <div style="margin-bottom:8px;">❌ Could not extract IMEI from image.</div>
                   <div class="scan-error-actions">
                     <button type="button" class="btn btn-outline" id="report-retry-btn">📷 Try another image</button>
                   </div>
                 </div>`
              );
              document.getElementById("report-retry-btn")?.addEventListener("click", () => {
                hideScanStatus(reportStatus);
                resetDropZone(rDropZone, reportFileInput);
                resetProgress();
              });
            });

          } else {
            // Fill inputs + show success badge
            if (imei1Input)  imei1Input.value = data.imei_1;   // fills hidden input imei_1
            // if (modelInput && data.model_name) modelInput.value = data.model_name;
            // if (colorInput && data.color)      colorInput.value = data.color;

            const filled = ["IMEI"];
            // if (data.model_name) filled.push("Model");
            // if (data.color)      filled.push("Color");

            completeProgress(() => {
              showSuccess(reportStatus,
                `<div>
                   <span>✅ ${filled.join(", ")} filled from image</span>
                   <div class="imei-scan-badge">📱 ${data.imei_1}</div>
                 </div>`
              );
            });
          }

        } catch (err) {
          completeProgress(() => {
            showError(reportStatus, "❌ Connection error. Please try again.");
          });
        }

        if (reportSubmitBtn) { reportSubmitBtn.disabled = false; reportSubmitBtn.textContent = "Report as Stolen"; }
      });
    }
  }

})();