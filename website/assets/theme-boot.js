(function () {
  try {
    var saved = localStorage.getItem("sanket-theme") || "system";
    if (saved !== "light" && saved !== "dark") saved = "system";
    var dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.themeMode = saved;
    document.documentElement.dataset.theme = saved === "system" ? (dark ? "dark" : "light") : saved;
  } catch (error) {
    document.documentElement.dataset.theme = "light";
    document.documentElement.dataset.themeMode = "system";
  }
})();
