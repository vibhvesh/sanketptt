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
        ["Sanket PTT", root + "?ch=virtual", "Named channels and push to talk", "#0078d4"],
        ["Control room", root + "#demo", "Live lines, users and text", "#ff9900"],
        ["आकाशवाणी", root + "aakashvani/", "Speaker zones and announcements", "#0d9488"],
        ["Transcribe", root + "transcribe/", "Timestamped channel text", "#7c3aed"],
        ["Sanket SDR", root + "#sdr", "Authorised defence surveillance", "#12805c"],
        ["Sanket Edge", root + "#edge", "On-site Raspberry Pi listener", "#db2777"],
        ["SanketVaani", root + "#vaani", "A learning agent beside a leading model", "#5b3cc4"]
      ]) +
      drop("Solutions", [
        ["Live demo", root + "#demo", "Talk and transcription together", "#0078d4"],
        ["Use cases", root + "#use-cases", "Field, events, control rooms", "#0d9488"],
        ["Radio hub", root + "radio-hub.html", "Channels and station tools", "#ff9900"]
      ]) +
      drop("Resources", [
        ["PTT guide", root + "docs/Sanket_PTT_User_Guide.html", "How to join and talk", "#0078d4"],
        ["Transcribe guide", root + "docs/Sanket_Transcribe_User_Guide.html", "Start a live transcript", "#7c3aed"],
        ["Edge guide", root + "docs/Sanket_Edge_User_Guide.html", "Set up the Pi listener", "#db2777"],
        ["Android app", root + "releases/download/v1.0-android/Sanket_PTT.apk", "Download the PTT app", "#12805c"]
      ]) +
      '<a class="nav-link" href="' + root + '#pricing">Pricing</a>' +
      '<a class="nav-link" href="' + root + '#contact">Contact</a>' +
      '<div class="read-mode" role="group" aria-label="Color theme">' +
      '<button type="button" data-mode="light">Light</button>' +
      '<button type="button" data-mode="dark">Dark</button></div>' +
      '</nav></div></header><div class="nav-backdrop" id="navBackdrop" hidden></div>';
  }
  function drop(label, items) {
    var links = items.map(function (item) {
      var dot = item[3] ? ' style="--dot:' + item[3] + '"' : "";
      var blurb = item[2] ? "<small>" + item[2] + "</small>" : "";
      return '<a role="menuitem" href="' + item[1] + '"' + dot + "><b>" + item[0] + "</b>" + blurb + "</a>";
    }).join("");
    var wide = items.length > 3 ? " mega" : "";
    return '<div class="drop"><button class="drop-btn" type="button" aria-expanded="false" aria-haspopup="true">' + label + '</button><div class="drop-panel' + wide + '" role="menu">' + links + "</div></div>";
  }

  if (document.body && document.body.dataset.chrome === "auto") {
    ["css/tokens.css", "css/base.css", "css/chrome.css"].forEach(function (file) {
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

  var modeNames = { light: "Light", dark: "Dark" };
  function paintTheme() {
    var mode = document.documentElement.getAttribute("data-theme") || "light";
    document.querySelectorAll(".read-mode button").forEach(function (btn) {
      var on = btn.getAttribute("data-mode") === mode;
      btn.setAttribute("aria-pressed", String(on));
    });
  }
  paintTheme();
  document.querySelectorAll(".read-mode button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var next = btn.getAttribute("data-mode");
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("sanket-color", next);
      paintTheme();
      window.sanketToast(modeNames[next] + " reading theme");
    });
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
