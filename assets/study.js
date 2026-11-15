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
