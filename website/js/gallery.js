(function () {
  var root = document.getElementById("explorer");
  if (!root) return;
  var tabs = root.querySelectorAll('[role="tab"]');
  var panels = root.querySelectorAll('[role="tabpanel"]');
  function select(id) {
    tabs.forEach(function (tab) {
      var on = tab.getAttribute("aria-controls") === id;
      tab.setAttribute("aria-selected", String(on));
    });
    panels.forEach(function (panel) { panel.hidden = panel.id !== id; });
  }
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () { select(tab.getAttribute("aria-controls")); });
  });
})();