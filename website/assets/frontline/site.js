(function () {
  var menu = document.getElementById("fl-menu");
  var nav = document.getElementById("fl-nav");
  if (menu && nav) {
    menu.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      menu.setAttribute("aria-expanded", open ? "true" : "false");
      menu.textContent = open ? "Close" : "Menu";
    });
    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        nav.classList.remove("open");
        menu.setAttribute("aria-expanded", "false");
        menu.textContent = "Menu";
      });
    });
  }
  var form = document.getElementById("contactForm");
  if (!form) return;
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var data = new FormData(form);
    var subject = encodeURIComponent("Sanket deployment enquiry — " + data.get("name"));
    var body = encodeURIComponent("Name: " + data.get("name") + "\nEmail: " + data.get("email") + "\nOrganisation: " + data.get("org") + "\nEstimated channels: " + data.get("channels") + "\n\n" + data.get("message"));
    location.href = "mailto:akshatsingh@canberravision.com?cc=akshat@sanketptt.com&subject=" + subject + "&body=" + body;
    var note = document.getElementById("formNote");
    if (note) note.textContent = "Your email app should open with the enquiry draft. Nothing is submitted to a website server.";
  });
})();
