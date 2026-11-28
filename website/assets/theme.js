(function () {
  var KEY = "sanket-theme";
  var order = ["system", "light", "dark"];

  function systemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function mode() {
    var saved = "system";
    try { saved = localStorage.getItem(KEY) || "system"; } catch (error) {}
    return order.indexOf(saved) === -1 ? "system" : saved;
  }

  function apply(next) {
    var choice = order.indexOf(next) === -1 ? "system" : next;
    try { localStorage.setItem(KEY, choice); } catch (error) {}
    document.documentElement.dataset.themeMode = choice;
    document.documentElement.dataset.theme = choice === "system" ? systemTheme() : choice;
    label();
  }

  function labelText() {
    var choice = mode();
    if (choice === "dark") return "Dark";
    if (choice === "light") return "Light";
    return "Auto";
  }

  function label() {
    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      var text = labelText();
      button.textContent = text;
      button.setAttribute("aria-label", "Color theme, " + text + ". Activate to change.");
    });
  }

  function toggle() {
    var current = mode();
    apply(order[(order.indexOf(current) + 1) % order.length]);
  }

  function framed() {
    try { return window.self !== window.top; } catch (error) { return true; }
  }

  function radioDevice() {
    return framed() || document.documentElement.classList.contains("ptt-embed") || !!document.querySelector(".rig, .radio");
  }

  function ensureButton() {
    if (radioDevice()) {
      document.querySelectorAll(".rig [data-theme-toggle], .radio [data-theme-toggle], .theme-toggle.is-fixed").forEach(function (button) {
        button.remove();
      });
      return;
    }
    if (document.querySelector("[data-theme-toggle]")) return;
    var host = document.querySelector("header .head-actions, header .nav-end, header .landing-nav-actions, header .bar");
    if (!host) return;
    var button = document.createElement("button");
    button.type = "button";
    button.className = "theme-toggle";
    button.setAttribute("data-theme-toggle", "");
    host.appendChild(button);
  }

  ensureButton();
  document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
    button.addEventListener("click", toggle);
  });
  label();

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
    if (mode() === "system") apply("system");
  });

  document.querySelectorAll(".plan-filters button, .yatra-filters button").forEach(function (button) {
    button.addEventListener("click", function () {
      var filter = button.getAttribute("data-filter") || "all";
      var group = button.parentElement;
      if (group) {
        group.querySelectorAll("button").forEach(function (item) {
          item.classList.toggle("is-on", item === button);
          item.setAttribute("aria-selected", item === button ? "true" : "false");
        });
      }
      document.querySelectorAll(".price-card, .fl-price").forEach(function (card) {
        var plan = card.getAttribute("data-plan") || "all";
        card.hidden = filter !== "all" && plan !== filter;
      });
    });
  });
})();
