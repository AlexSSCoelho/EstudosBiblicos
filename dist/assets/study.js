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
})();
