(function () {
  "use strict";

  const tocLinks = Array.from(document.querySelectorAll(".toc a"));
  const sections = tocLinks
    .map((link) => {
      const href = link.getAttribute("href") || "";
      const id = href.startsWith("#") ? href.slice(1) : "";
      return id ? document.getElementById(id) : null;
    })
    .filter(Boolean);

  if (!tocLinks.length || !sections.length) return;

  let activeId = "";

  function centerMobileLink(link) {
    const tocNav = link.closest(".toc");
    if (!tocNav) return;
    const linkRect = link.getBoundingClientRect();
    const navRect = tocNav.getBoundingClientRect();
    const left = tocNav.scrollLeft + linkRect.left - navRect.left
      - (tocNav.clientWidth - linkRect.width) / 2;
    tocNav.scrollTo({ left, behavior: "auto" });
  }

  function setActive(sectionId) {
    if (activeId === sectionId) return;
    const isInitialActivation = activeId === "";
    activeId = sectionId;
    let activeLink = null;
    tocLinks.forEach((link) => {
      const active = link.getAttribute("href") === "#" + sectionId;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
      if (active) activeLink = link;
      if (active && !isInitialActivation && !window.matchMedia("(max-width: 860px)").matches) {
        const tocNav = link.closest(".toc");
        if (tocNav) {
          const linkRect = link.getBoundingClientRect();
          const tocRect = tocNav.getBoundingClientRect();
          const padding = 24;
          if (linkRect.top < tocRect.top + padding || linkRect.bottom > tocRect.bottom - padding) {
            link.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }
        }
      }
    });
    if (activeLink && window.matchMedia("(max-width: 860px)").matches) {
      centerMobileLink(activeLink);
    }
  }

  function updateActiveSection() {
    // Se o usuário rolou até próximo ao final do documento, ativa a última seção
    const scrollBottom = window.innerHeight + window.scrollY;
    const documentHeight = document.documentElement.scrollHeight;
    if (documentHeight - scrollBottom < 80) {
      setActive(sections[sections.length - 1].id);
      return;
    }

    const line = window.matchMedia("(max-width: 860px)").matches ? 150 : 170;
    let current = sections[0];
    sections.forEach((section) => {
      if (section.getBoundingClientRect().top <= line) current = section;
    });
    if (current) setActive(current.id);
  }

  window.addEventListener("scroll", updateActiveSection, { passive: true });
  window.addEventListener("resize", () => {
    updateActiveSection();
    if (window.matchMedia("(max-width: 860px)").matches) {
      const activeLink = tocLinks.find((link) => link.classList.contains("active"));
      if (activeLink) centerMobileLink(activeLink);
    }
  });
  updateActiveSection();

  const tocNav = document.querySelector(".toc");
  if (tocNav) {
    tocNav.addEventListener(
      "wheel",
      function (e) {
        if (window.matchMedia("(max-width: 860px)").matches) return;
        const scrollTop = tocNav.scrollTop;
        const scrollHeight = tocNav.scrollHeight;
        const height = tocNav.clientHeight;
        const delta = e.deltaY;

        if (scrollHeight <= height) {
          return;
        }

        if (delta < 0 && scrollTop <= 0) {
          e.preventDefault();
        } else if (delta > 0 && scrollTop + height >= scrollHeight - 1) {
          e.preventDefault();
        }
      },
      { passive: false }
    );
  }

  document.querySelectorAll('a[href^="http://"], a[href^="https://"]').forEach((link) => {
    if (!link.getAttribute("target")) {
      link.setAttribute("target", "_blank");
    }
    const rel = link.getAttribute("rel") || "";
    if (!rel.includes("noopener")) {
      link.setAttribute("rel", (rel + " noopener noreferrer").trim());
    }
  });
  const tocToggleBtn = document.getElementById("toc-toggle-btn");
  if (tocToggleBtn) {
    const TOC_STORAGE_KEY = "estudos_toc_collapsed_v1";

    function applyTocCollapsed(collapsed) {
      document.body.classList.toggle("toc-collapsed", collapsed);
      tocToggleBtn.setAttribute("aria-expanded", collapsed ? "false" : "true");
      const label = collapsed ? "Expandir índice lateral" : "Recolher índice lateral";
      tocToggleBtn.setAttribute("aria-label", label);
      tocToggleBtn.setAttribute("title", label);
      window.dispatchEvent(new Event("study:layout-change"));
    }

    try {
      if (window.localStorage.getItem(TOC_STORAGE_KEY) === "1") {
        applyTocCollapsed(true);
      }
    } catch {
      // Ignora indisponibilidade de localStorage
    }

    tocToggleBtn.addEventListener("click", () => {
      const nextCollapsed = !document.body.classList.contains("toc-collapsed");
      applyTocCollapsed(nextCollapsed);
      try {
        window.localStorage.setItem(TOC_STORAGE_KEY, nextCollapsed ? "1" : "0");
      } catch {
        // Ignora indisponibilidade de localStorage
      }
    });
  }
})();

(function () {
  "use strict";

  const terms = Array.from(document.querySelectorAll(".lex-term[data-tooltip]"));
  if (!terms.length) return;

  const tooltip = document.createElement("div");
  tooltip.className = "lex-tooltip";
  tooltip.id = "lex-tooltip";
  tooltip.setAttribute("role", "tooltip");
  tooltip.hidden = true;
  document.body.appendChild(tooltip);

  let activeTerm = null;
  let pinnedByClick = false;

  terms.forEach((term) => {
    if (!term.hasAttribute("tabindex")) {
      term.setAttribute("tabindex", "0");
    }
  });

  function positionTooltip(term) {
    const rect = term.getBoundingClientRect();
    const margin = 12;
    const gap = 10;
    const topbar = document.querySelector(".topbar");
    const minTop = (topbar ? topbar.getBoundingClientRect().bottom : 0) + 8;

    tooltip.style.left = "0px";
    tooltip.style.top = "0px";
    const tipRect = tooltip.getBoundingClientRect();

    let placement = "top";
    let top = rect.top - tipRect.height - gap;
    if (top < minTop) {
      placement = "bottom";
      top = rect.bottom + gap;
    }

    const centerX = rect.left + rect.width / 2;
    let left = centerX - tipRect.width / 2;
    const maxLeft = window.innerWidth - tipRect.width - margin;
    left = Math.max(margin, Math.min(left, maxLeft));

    const arrowLeft = Math.max(14, Math.min(centerX - left, tipRect.width - 14));
    tooltip.dataset.placement = placement;
    tooltip.style.setProperty("--arrow-left", arrowLeft + "px");
    tooltip.style.left = left + "px";
    tooltip.style.top = top + "px";
  }

  function showTooltip(term, pin) {
    const text = (term.getAttribute("data-tooltip") || "").trim();
    if (!text) return;
    if (activeTerm && activeTerm !== term) {
      activeTerm.classList.remove("is-tooltip-open");
      activeTerm.removeAttribute("aria-describedby");
    }
    activeTerm = term;
    pinnedByClick = Boolean(pin);
    tooltip.textContent = text;
    tooltip.hidden = false;
    positionTooltip(term);
    tooltip.classList.add("is-visible");
    term.classList.add("is-tooltip-open");
    term.setAttribute("aria-describedby", tooltip.id);
  }

  function hideTooltip() {
    if (!activeTerm) return;
    activeTerm.classList.remove("is-tooltip-open");
    activeTerm.removeAttribute("aria-describedby");
    activeTerm = null;
    pinnedByClick = false;
    tooltip.classList.remove("is-visible");
    tooltip.hidden = true;
  }

  terms.forEach((term) => {
    term.addEventListener("mouseenter", () => {
      if (!pinnedByClick) showTooltip(term, false);
    });
    term.addEventListener("mouseleave", () => {
      if (!pinnedByClick && activeTerm === term) hideTooltip();
    });
    term.addEventListener("focusin", () => {
      if (!pinnedByClick) showTooltip(term, false);
    });
    term.addEventListener("focusout", () => {
      if (!pinnedByClick && activeTerm === term) hideTooltip();
    });
    term.addEventListener("click", (e) => {
      e.stopPropagation();
      if (activeTerm === term && pinnedByClick) {
        hideTooltip();
      } else {
        showTooltip(term, true);
      }
    });
  });

  document.addEventListener("click", (e) => {
    if (activeTerm && !e.target.closest(".lex-term")) {
      hideTooltip();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && activeTerm) {
      hideTooltip();
    }
  });

  window.addEventListener(
    "scroll",
    () => {
      if (activeTerm) positionTooltip(activeTerm);
    },
    { passive: true }
  );
  window.addEventListener("resize", () => {
    if (activeTerm) positionTooltip(activeTerm);
  });
})();

(function () {
  "use strict";

  const THEME_STORAGE_KEY = "estudos_theme_v1";
  const toggleBtn = document.getElementById("theme-toggle-btn");
  const root = document.documentElement;
  const themeMeta = document.querySelector('meta[name="theme-color"]');

  function getPreferredTheme() {
    try {
      const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
      if (saved === "dark" || saved === "light") return saved;
    } catch {
      // Ignora indisponibilidade de localStorage
    }
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function applyTheme(theme) {
    const isDark = theme === "dark";
    root.setAttribute("data-theme", theme);
    if (themeMeta) {
      themeMeta.setAttribute("content", isDark ? "#111613" : "#20372a");
    }
    if (toggleBtn) {
      const label = isDark ? "Ativar modo claro" : "Ativar modo escuro";
      toggleBtn.setAttribute("aria-label", label);
      toggleBtn.setAttribute("aria-pressed", isDark ? "true" : "false");
      toggleBtn.setAttribute("title", label);
    }
  }

  applyTheme(getPreferredTheme());

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const nextTheme = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      applyTheme(nextTheme);
      try {
        window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
      } catch {
        // Ignora indisponibilidade de localStorage
      }
    });
  }
})();
