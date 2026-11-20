(function () {
  var saved = localStorage.getItem("sanket-color");
  document.documentElement.setAttribute("data-theme", saved === "dark" ? "dark" : "light");

  function inSub() {
    return /\/(docs|transcribe|dmr|radio|aakashvani|pi|newlook|dev)\//.test(location.pathname);
  }
  var root = inSub() ? "../" : "";

  function headerHtml() {
    return '' +
      '<header class="site-header"><div class="wrap bar">' +
      '<a class="logo" href="' + root + '#home"><img src="' + root + 'sanket-mark.svg" alt="" width="36" height="36"><span>SANKET <b>PTT</b><small>CANBERRA VISION</small></span></a>' +
      '<button class="nav-toggle" id="navToggle" type="button" aria-expanded="false" aria-controls="siteNav">Menu</button>' +
      '<nav class="site-nav" id="siteNav" aria-label="Primary">' +
      drop("Products", [
        ["Sanket PTT", root + "?ch=virtual"],
        ["Control room", root + "#demo"],
        ["आकाशवाणी", root + "aakashvani/"],
        ["Transcribe", root + "transcribe/"],
        ["Sanket SDR", root + "#sdr"],
        ["Sanket Edge", root + "#edge"],
        ["SanketVaani", root + "#vaani"]
      ]) +
      drop("Solutions", [
        ["Live demo", root + "#demo"],
        ["Use cases", root + "#use-cases"],
        ["Radio hub", root + "radio-hub.html"]
      ]) +
      drop("Resources", [
        ["PTT guide", root + "docs/Sanket_PTT_User_Guide.html"],
        ["Transcribe guide", root + "docs/Sanket_Transcribe_User_Guide.html"],
        ["Edge guide", root + "docs/Sanket_Edge_User_Guide.html"],
        ["Android app", root + "releases/download/v1.0-android/Sanket_PTT.apk"]
      ]) +
      '<a class="nav-link" href="' + root + '#pricing">Pricing</a>' +
      '<a class="nav-link" href="' + root + '#contact">Contact</a>' +
      '<button class="theme-btn" id="themeToggle" type="button" aria-label="Toggle color theme"><span class="switch" aria-hidden="true"><i></i></span></button>' +
      '</nav></div></header><div class="nav-backdrop" id="navBackdrop" hidden></div>';
  }
  function drop(label, items) {
    var links = items.map(function (item) {
      return '<a role="menuitem" href="' + item[1] + '">' + item[0] + "</a>";
    }).join("");
    return '<div class="drop"><button class="drop-btn" type="button" aria-expanded="false" aria-haspopup="true">' + label + '</button><div class="drop-panel" role="menu">' + links + "</div></div>";
  }

  if (document.body && document.body.dataset.chrome === "auto") {
    ["css/base.css", "css/chrome.css"].forEach(function (file) {
      var href = root + file;
      if ([].some.call(document.styleSheets, function (sheet) { return (sheet.href || "").indexOf(file) !== -1; })) return;
      var link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      document.head.appendChild(link);
    });
  }
  var mount = document.getElementById("chrome");
  if (mount) mount.outerHTML = headerHtml();
  else if (document.body && document.body.dataset.chrome === "auto") {
    document.body.insertAdjacentHTML("afterbegin", headerHtml());
    if (!document.querySelector(".site-footer")) {
      document.body.insertAdjacentHTML("beforeend", '<footer class="wrap site-footer"><span>Sanket · Canberra Vision</span><a href="' + root + '#home">Back to home</a></footer>');
    }
  }

  var nav = document.getElementById("siteNav");
  var toggle = document.getElementById("navToggle");
  var backdrop = document.getElementById("navBackdrop");
  function setOpen(on) {
    document.body.classList.toggle("nav-open", on);
    if (toggle) toggle.setAttribute("aria-expanded", String(on));
    if (backdrop) backdrop.hidden = !on;
  }
  if (toggle) toggle.addEventListener("click", function () { setOpen(!document.body.classList.contains("nav-open")); });
  if (backdrop) backdrop.addEventListener("click", function () { setOpen(false); });

  document.querySelectorAll(".drop").forEach(function (dropEl) {
    var btn = dropEl.querySelector(".drop-btn");
    if (!btn) return;
    btn.addEventListener("click", function (event) {
      event.preventDefault();
      var open = dropEl.classList.toggle("open");
      btn.setAttribute("aria-expanded", String(open));
      document.querySelectorAll(".drop.open").forEach(function (other) {
        if (other !== dropEl) {
          other.classList.remove("open");
          var b = other.querySelector(".drop-btn");
          if (b) b.setAttribute("aria-expanded", "false");
        }
      });
    });
    btn.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        dropEl.classList.add("open");
        btn.setAttribute("aria-expanded", "true");
        var first = dropEl.querySelector("a");
        if (first) first.focus();
      }
    });
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      setOpen(false);
      document.querySelectorAll(".drop.open").forEach(function (dropEl) {
        dropEl.classList.remove("open");
        var b = dropEl.querySelector(".drop-btn");
        if (b) b.setAttribute("aria-expanded", "false");
      });
    }
  });
  if (nav) nav.querySelectorAll("a").forEach(function (a) { a.addEventListener("click", function () { setOpen(false); }); });

  var themeBtn = document.getElementById("themeToggle");
  function paintTheme() {
    var mode = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    if (themeBtn) themeBtn.setAttribute("aria-label", mode === "dark" ? "Switch to light theme" : "Switch to dark theme");
  }
  paintTheme();
  if (themeBtn) themeBtn.addEventListener("click", function () {
    var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("sanket-color", next);
    paintTheme();
    window.sanketToast(next === "dark" ? "Dark theme" : "Light theme");
  });

  var stack = document.createElement("div");
  stack.className = "toasts";
  document.body.appendChild(stack);
  window.sanketToast = function (message) {
    var el = document.createElement("div");
    el.className = "toast";
    el.textContent = message;
    stack.appendChild(el);
    setTimeout(function () { el.remove(); }, 2800);
  };

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var nodes = document.querySelectorAll(".reveal");
  if (reduce || !("IntersectionObserver" in window)) nodes.forEach(function (el) { el.classList.add("in"); });
  else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) { if (entry.isIntersecting) entry.target.classList.add("in"); });
    }, { threshold: 0.12 });
    nodes.forEach(function (el) { io.observe(el); });
  }

  var year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());
})();
