document.addEventListener("DOMContentLoaded", () => {
  const header = document.querySelector(".header");
  const navLinks = document.querySelectorAll(".nav__links a[href^=\"#\"]");
  const navToggle = document.querySelector(".nav__toggle");
  const navMenu = document.querySelector(".nav__links");
  const yearSpan = document.getElementById("year");

  if (yearSpan) {
    yearSpan.textContent = new Date().getFullYear().toString();
  }

  window.addEventListener("scroll", () => {
    if (!header) return;
    const scrolled = window.scrollY > 10;
    header.classList.toggle("header--scrolled", scrolled);
  });

  navLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      const href = link.getAttribute("href");
      if (!href || !href.startsWith("#")) return;

      const target = document.querySelector(href);
      if (!target) return;

      event.preventDefault();
      const headerOffset = header ? header.offsetHeight : 0;
      const elementPosition = target.getBoundingClientRect().top + window.scrollY;
      const offsetPosition = elementPosition - headerOffset + 1;

      window.scrollTo({
        top: offsetPosition,
        behavior: "smooth",
      });

      if (navMenu && navToggle && navMenu.classList.contains("nav__links--open")) {
        navMenu.classList.remove("nav__links--open");
        navToggle.classList.remove("nav__toggle--open");
      }
    });
  });

  if (navToggle && navMenu) {
    navToggle.addEventListener("click", () => {
      navMenu.classList.toggle("nav__links--open");
      navToggle.classList.toggle("nav__toggle--open");
    });
  }
});

