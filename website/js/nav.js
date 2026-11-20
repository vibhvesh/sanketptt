(function () {
  var menu = document.getElementById("menu");
  var links = document.getElementById("links");
  if (menu && links) {
    menu.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      menu.setAttribute("aria-expanded", String(open));
      menu.textContent = open ? "✕" : "☰";
    });
    links.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () {
        links.classList.remove("open");
        menu.setAttribute("aria-expanded", "false");
        menu.textContent = "☰";
      });
    });
  }
  var year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());
})();
