/** FinSkalp enterprise shell — nav highlight + breadcrumb for live SPA. */
(function () {
  const BREADCRUMB = {
    dashboard: "Командный центр",
    osint: "Центр OSINT",
    wallet: "Проверка кошелька",
    microservices: "Микросервисы",
    platform: "Модули платформы",
    ops: "Расследования",
    instruments: "Консоль ИЦ",
    registries: "Реестры",
    reports: "Отчёты 115-ФЗ",
  };

  function highlightNav(view) {
    document.querySelectorAll("[data-fs-view]").forEach((btn) => {
      btn.classList.toggle("fs-nav-active", btn.dataset.fsView === view);
    });
    const bc = document.getElementById("fsBreadcrumb");
    if (bc) bc.textContent = BREADCRUMB[view] || view;
  }

  function patchSwitchView() {
    if (typeof window.switchView !== "function") return;
    const orig = window.switchView;
    window.switchView = function (view) {
      orig(view);
      highlightNav(view);
    };
    highlightNav(window.currentView || "dashboard");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", patchSwitchView);
  } else {
    patchSwitchView();
  }
})();
