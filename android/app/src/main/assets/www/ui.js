/* Yo'l Guard — visual layer only (no app logic). Loaded after app.js. */
(function () {
  "use strict";
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* inject styles this file needs */
  var css = document.createElement("style");
  css.textContent =
    ".rip{position:absolute;border-radius:50%;transform:scale(0);pointer-events:none;" +
    "background:rgba(255,255,255,.35);animation:rip .6s cubic-bezier(.16,1,.3,1)}" +
    "@keyframes rip{to{transform:scale(2.6);opacity:0}}" +
    ".card{--mx:50%;--my:0%}" +
    ".card::after{content:'';position:absolute;inset:0;border-radius:inherit;pointer-events:none;" +
    "opacity:0;transition:opacity .35s;background:radial-gradient(260px circle at var(--mx) var(--my)," +
    "rgba(245,165,36,.10),transparent 60%)}" +
    ".card:hover::after{opacity:1}";
  document.head.appendChild(css);

  /* ripple on tactile elements */
  if (!reduce) {
    document.addEventListener("pointerdown", function (e) {
      var el = e.target.closest(".primary,.ghost,.sos,.camera,.tab,.arow");
      if (!el) return;
      var r = el.getBoundingClientRect();
      var d = Math.max(r.width, r.height);
      var s = document.createElement("span");
      s.className = "rip";
      s.style.width = s.style.height = d + "px";
      s.style.left = (e.clientX - r.left - d / 2) + "px";
      s.style.top = (e.clientY - r.top - d / 2) + "px";
      var pos = getComputedStyle(el).position;
      if (pos === "static") el.style.position = "relative";
      if (getComputedStyle(el).overflow === "visible") el.style.overflow = "hidden";
      el.appendChild(s);
      setTimeout(function () { s.remove(); }, 650);
    }, { passive: true });
  }

  /* cursor spotlight on cards */
  if (!reduce && window.matchMedia("(pointer:fine)").matches) {
    document.addEventListener("pointermove", function (e) {
      var c = e.target.closest(".card");
      if (!c) return;
      var r = c.getBoundingClientRect();
      c.style.setProperty("--mx", (e.clientX - r.left) + "px");
      c.style.setProperty("--my", (e.clientY - r.top) + "px");
    }, { passive: true });
  }

  /* reveal admin rows / messages as they are inserted */
  if (!reduce && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (ents) {
      ents.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { threshold: 0.08 });
    var scan = function () {
      document.querySelectorAll(".arow:not(.reveal),.msg:not(.reveal)").forEach(function (el) {
        el.classList.add("reveal"); io.observe(el);
      });
    };
    var mo = new MutationObserver(scan);
    mo.observe(document.body, { childList: true, subtree: true });
    scan();
  }
})();
