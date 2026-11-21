(function () {
  document.body.classList.add("yatra");
  var script = document.currentScript;
  var root = (script && script.getAttribute("data-root")) || "";
  if (!document.querySelector(".yatra-tools")) {
    var slot = document.querySelector("header .nav, header .bar, header .wrap");
    if (slot) {
      var tools = document.createElement("div");
      tools.className = "yatra-tools";
      tools.setAttribute("aria-label", "Shortcuts");
      tools.innerHTML = "<a href='" + root + "#pricing' aria-label='Offers'><svg viewBox='0 0 24 24'><path d='M20 12v8H5V12M2 7h20v5H2zM12 7v14'/></svg></a><a href='" + root + "#contact' aria-label='Alerts'><svg viewBox='0 0 24 24'><path d='M6 16V10a6 6 0 1 1 12 0v6l1.5 2H4.5z'/></svg><i>1</i></a>";
      slot.appendChild(tools);
    }
  }
  var more = document.getElementById("yatraMore");
  var tiles = document.getElementById("yatraTiles");
  if (more && tiles) {
    more.addEventListener("click", function () {
      var open = tiles.classList.toggle("is-open");
      more.setAttribute("aria-expanded", open ? "true" : "false");
      more.textContent = open ? "⌃" : "⌄";
    });
  }

  document.querySelectorAll(".yatra-filters button").forEach(function (button) {
    button.addEventListener("click", function () {
      var filter = button.getAttribute("data-filter");
      document.querySelectorAll(".yatra-filters button").forEach(function (item) {
        item.classList.toggle("is-on", item === button);
      });
      document.querySelectorAll(".price-card").forEach(function (card) {
        var plan = card.getAttribute("data-plan") || "all";
        card.hidden = filter !== "all" && plan !== filter;
      });
    });
  });

  if (!document.querySelector(".yatra-tabs")) {
    var nav = document.createElement("nav");
    nav.className = "yatra-tabs";
    nav.setAttribute("aria-label", "Primary");
    var here = location.pathname;
    var items = [
      ["Home", root || "./", "M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z"],
      ["Radios", root + "sanket-radios/", "M5 12h14M8 8h8M7 16h10"],
      ["Transcribe", root + "transcribe/", "M8 6h8v12H8zM6 9H4v6h2M18 9h2v6h-2"],
      ["PTT", root + "ptt2/", "M12 3a4 4 0 0 1 4 4v5a4 4 0 0 1-8 0V7a4 4 0 0 1 4-4zM8 19h8"],
      ["Contact", root + "#contact", "M4 6h16v12H4zM4 7l8 6 8-6"]
    ];
    items.forEach(function (item) {
      var link = document.createElement("a");
      link.href = item[1];
      link.innerHTML = "<svg viewBox='0 0 24 24'><path d='" + item[2] + "'/></svg><span>" + item[0] + "</span>";
      if (here.indexOf(item[1].replace("./", "").replace("#contact", "___")) !== -1 && item[0] !== "Home" && item[0] !== "Contact") link.className = "is-on";
      if ((here.endsWith("/preview/") || here.endsWith("/")) && item[0] === "Home") link.className = "is-on";
      nav.appendChild(link);
    });
    document.body.appendChild(nav);
  }

  if (!document.querySelector(".yatra-bubble")) {
    var bubble = document.createElement("a");
    bubble.className = "yatra-bubble";
    bubble.href = root + "#contact";
    bubble.setAttribute("aria-label", "Ask Sanket");
    bubble.textContent = "✦";
    document.body.appendChild(bubble);
  }
})();
