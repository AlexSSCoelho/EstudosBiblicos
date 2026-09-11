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

  function setActive(sectionId) {
    if (activeId === sectionId) return;
    const isInitialActivation = activeId === "";
    activeId = sectionId;
    tocLinks.forEach((link) => {
      const active = link.getAttribute("href") === "#" + sectionId;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
      if (active && !isInitialActivation && window.matchMedia("(max-width: 860px)").matches) {
        link.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
      } else if (active && !isInitialActivation) {
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
  }

  function updateActiveSection() {
    const line = window.matchMedia("(max-width: 860px)").matches ? 150 : 170;
    let current = sections[0];
    sections.forEach((section) => {
      if (section.getBoundingClientRect().top <= line) current = section;
    });
    if (current) setActive(current.id);
  }

  window.addEventListener("scroll", updateActiveSection, { passive: true });
  window.addEventListener("resize", updateActiveSection);
  updateActiveSection();

  const tocNav = document.querySelector(".toc");
  if (tocNav) {
    tocNav.addEventListener(
      "wheel",
      function (e) {
        const scrollTop = tocNav.scrollTop;
        const scrollHeight = tocNav.scrollHeight;
        const height = tocNav.clientHeight;
        const delta = e.deltaY;

        if (scrollHeight <= height) {
          e.preventDefault();
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
})();
