/**
 * FinSkalp UI system — theme, skeletons, data tables
 */
(function (global) {
  const THEME_KEY = "finskalp-theme";

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY) || "dark";
    document.documentElement.setAttribute("data-theme", saved);
    const btn = document.getElementById("themeToggle");
    if (btn) btn.setAttribute("aria-pressed", saved === "light" ? "true" : "false");
  }

  function toggleTheme() {
    const cur = document.documentElement.getAttribute("data-theme") || "dark";
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem(THEME_KEY, next);
    const btn = document.getElementById("themeToggle");
    if (btn) btn.setAttribute("aria-pressed", next === "light" ? "true" : "false");
    global.dispatchEvent(new CustomEvent("finskalp:theme", { detail: { theme: next } }));
  }

  function skeletonHtml(rows = 4, cols = 3) {
    let html = '<div class="skeleton-block" aria-busy="true" aria-label="Загрузка">';
    for (let r = 0; r < rows; r++) {
      html += '<div class="skeleton-row">';
      for (let c = 0; c < cols; c++) {
        html += `<div class="skeleton-cell" style="width:${60 + (c * 17) % 40}%"></div>`;
      }
      html += "</div>";
    }
    html += "</div>";
    return html;
  }

  function riskClass(score) {
    if (score >= 85) return "risk-critical";
    if (score >= 65) return "risk-high";
    if (score >= 40) return "risk-medium";
    if (score >= 15) return "risk-low";
    return "risk-clear";
  }

  /**
   * Render sortable data table (client-side, no reload)
   * @param {string} tableId
   * @param {string[]} headers - display labels
   * @param {object[]} rows - array of cell arrays or objects with keys
   * @param {object} opts
   */
  function renderDataTable(tableId, headers, rows, opts = {}) {
    const mount = document.getElementById(tableId);
    if (!mount) return;
    const keys = opts.keys || headers.map((_, i) => String(i));
    let sortCol = opts.defaultSortCol ?? null;
    let sortAsc = true;

    function sortedRows() {
      if (sortCol === null) return rows.slice();
      const idx = keys.indexOf(sortCol);
      if (idx < 0) return rows.slice();
      return rows.slice().sort((a, b) => {
        const av = Array.isArray(a) ? a[idx] : a[sortCol];
        const bv = Array.isArray(b) ? b[idx] : b[sortCol];
        const na = parseFloat(av);
        const nb = parseFloat(bv);
        let cmp = !isNaN(na) && !isNaN(nb) ? na - nb : String(av).localeCompare(String(bv), "ru");
        return sortAsc ? cmp : -cmp;
      });
    }

    function paint() {
      const body = sortedRows()
        .map((row) => {
          const cells = Array.isArray(row)
            ? row
            : keys.map((k) => row[k] ?? "");
          return `<tr>${cells.map((c) => `<td>${c}</td>`).join("")}</tr>`;
        })
        .join("");
      mount.innerHTML = `
        <table class="data-table" role="grid">
          <thead><tr>${headers
            .map((h, i) => {
              const key = keys[i];
              const active = sortCol === key;
              const arrow = active ? (sortAsc ? " ▲" : " ▼") : "";
              return `<th scope="col" tabindex="0" data-sort-key="${key}" class="sortable${active ? " active" : ""}" aria-sort="${active ? (sortAsc ? "ascending" : "descending") : "none"}">${h}${arrow}</th>`;
            })
            .join("")}</tr></thead>
          <tbody>${body}</tbody>
        </table>`;
      mount.querySelectorAll("th.sortable").forEach((th) => {
        th.addEventListener("click", () => onSort(th.dataset.sortKey));
        th.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onSort(th.dataset.sortKey);
          }
        });
      });
    }

    function onSort(key) {
      if (sortCol === key) sortAsc = !sortAsc;
      else {
        sortCol = key;
        sortAsc = true;
      }
      paint();
    }

    paint();
  }

  global.FinSkalpUI = {
    initTheme,
    toggleTheme,
    skeletonHtml,
    riskClass,
    renderDataTable,
    initKeyboardNav,
  };

  const VIEW_SHORTCUTS = {
    d: "dashboard",
    o: "osint",
    w: "wallet",
    m: "microservices",
    p: "platform",
    i: "ops",
    r: "registries",
    t: "reports",
  };

  function initKeyboardNav() {
    let pendingG = false;
    document.querySelectorAll(".nav-item[data-view]").forEach((btn, idx) => {
      btn.setAttribute("tabindex", "0");
      btn.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          btn.click();
        }
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
          e.preventDefault();
          const items = [...document.querySelectorAll(".nav-item[data-view]")];
          const i = items.indexOf(btn);
          const next = e.key === "ArrowDown" ? Math.min(i + 1, items.length - 1) : Math.max(i - 1, 0);
          items[next]?.focus();
        }
        if (e.key >= "1" && e.key <= "9") {
          const items = [...document.querySelectorAll(".nav-item[data-view]")];
          items[parseInt(e.key, 10) - 1]?.click();
        }
      });
    });
    document.addEventListener("keydown", (e) => {
      if (e.target.matches("input, textarea, select") && e.key !== "Escape") return;
      if (e.key === "Escape") {
        FinSkalpGraph?.closePanel?.();
        return;
      }
      if (e.key === "g" && !e.ctrlKey && !e.metaKey) {
        pendingG = true;
        setTimeout(() => { pendingG = false; }, 800);
        return;
      }
      if (pendingG && VIEW_SHORTCUTS[e.key]) {
        pendingG = false;
        e.preventDefault();
        switchView(VIEW_SHORTCUTS[e.key]);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initKeyboardNav();
  });
})(window);
