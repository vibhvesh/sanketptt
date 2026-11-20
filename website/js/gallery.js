(function () {
  var track = document.getElementById("galTrack");
  if (!track) return;
  function step(dir) {
    var card = track.querySelector("figure");
    var amount = card ? card.getBoundingClientRect().width + 16 : track.clientWidth * 0.8;
    track.scrollBy({ left: dir * amount, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }
  var prev = document.getElementById("galPrev");
  var next = document.getElementById("galNext");
  if (prev) prev.addEventListener("click", function () { step(-1); });
  if (next) next.addEventListener("click", function () { step(1); });
})();
