(function () {
  const skin = new URLSearchParams(location.search).get("skin") || document.body.dataset.skin;
  const themes = {
    motorola: {
      bg: "#101317", frame: "#292e35", edge: "#c83232", lcd: "#17251c", screen: "#a8d878",
      accent: "#e43b35", glow: "#e43b3544", ptt: "#a92323", ptt2: "#ed4a36", font: "Arial, sans-serif",
      radius: "18px"
    },
    hytera: {
      bg: "#101812", frame: "#202a25", edge: "#65a832", lcd: "#b4d78b", screen: "#18351d",
      accent: "#75bd36", glow: "#78c83c55", ptt: "#1d542b", ptt2: "#54a82f", font: "Arial, sans-serif",
      radius: "24px"
    },
    kenwood: {
      bg: "#101a27", frame: "#303b49", edge: "#4e83bd", lcd: "#c6d8e8", screen: "#172f49",
      accent: "#4e91d0", glow: "#4e91d044", ptt: "#164a80", ptt2: "#2879bb", font: "Arial, sans-serif",
      radius: "14px"
    },
    baofeng: {
      bg: "#19140e", frame: "#28231d", edge: "#e47b1b", lcd: "#f0bd59", screen: "#38230d",
      accent: "#f28a20", glow: "#f28a2055", ptt: "#a54a0c", ptt2: "#ef8618", font: "'Share Tech Mono', monospace",
      radius: "10px"
    },
    boondockecho: {
      bg: "#8f210f", frame: "#b83319", edge: "#e6cfc0", lcd: "#31150f", screen: "#f4dfd1",
      accent: "#f2d8c9", glow: "#ffd8c044", ptt: "#8e260f", ptt2: "#e65b2b", font: "Arial, sans-serif",
      radius: "22px"
    },
    sonim: {
      bg: "#111318", frame: "#242831", edge: "#e4b72e", lcd: "#182b49", screen: "#d5e4ff",
      accent: "#e4b72e", glow: "#e4b72e55", ptt: "#29384f", ptt2: "#d4a91f", font: "Arial, sans-serif",
      radius: "28px"
    }
  };
  const t = themes[skin] || themes.motorola;
  const frame = document.getElementById("radio-client");
  const css = `
    html,body{margin:0!important;min-height:100%!important;background:${t.bg}!important;padding:8px!important;font-family:${t.font}!important}
    .rig{max-width:520px!important;margin:0 auto!important;background:linear-gradient(145deg,${t.frame},#101318)!important;border:3px solid ${t.edge}!important;border-radius:${t.radius}!important;box-shadow:0 18px 42px #000b,inset 0 2px 0 #ffffff22!important;padding:16px!important}
    .brand h1{background:none!important;color:${t.accent}!important;-webkit-text-fill-color:${t.accent}!important;letter-spacing:1.5px!important}
    .brand small{color:#aeb8c4!important}
    .led.pw i{background:#333!important;box-shadow:inset 0 1px 3px #000!important}.led.pw.on i{background:#f5bd28!important;box-shadow:0 0 10px #f5bd28!important}
    .lcd{background:linear-gradient(180deg,${t.lcd},${t.screen})!important;color:${t.screen}!important;border:3px solid #080b0d!important;box-shadow:inset 0 0 18px #000b,0 0 15px ${t.glow}!important;text-shadow:0 0 7px ${t.accent}!important}
    .lcd .row{color:inherit!important}
    .freq{color:inherit!important}
    .bars b.l{background:${t.accent}!important;box-shadow:0 0 6px ${t.accent}!important}
    .bars b.l.y{background:#f5c542!important}.bars b.l.r{background:#ef3939!important}
    .panel{background:#090d12cc!important;border:1px solid ${t.edge}55!important;border-radius:12px!important}
    .panel h3{color:${t.accent}!important}
    input{border-color:${t.edge}99!important}
    #go{background:linear-gradient(135deg,#50c878,${t.accent})!important;box-shadow:0 4px 0 #111!important}
    #ptt{width:min(74vw,285px)!important;height:min(74vw,285px)!important;max-width:285px!important;max-height:285px!important;aspect-ratio:1/1!important;border-radius:50%!important;background:radial-gradient(circle at 35% 28%,${t.ptt2},${t.ptt} 70%)!important;border:5px solid #080b0d!important;box-shadow:0 0 0 3px ${t.edge},0 0 24px ${t.glow},inset 0 -8px 16px #0008!important}
    #ptt.on{background:radial-gradient(circle at 35% 28%,#ff7770,#b30000 70%)!important;box-shadow:0 0 0 3px #ff3b30,0 0 36px #ff3020!important}
    #ptt.busy{background:radial-gradient(circle at 35% 28%,#ffe39a,#b36a00 70%)!important}
    #log li .cs{color:${t.accent}!important}
    #map{border-color:${t.edge}88!important}
    #net{color:#aab6c3!important}
    a{color:${t.accent}!important}
    ${skin === "motorola" ? ".rig:before,.rig:after{width:13px;height:13px;background:radial-gradient(#e8e8e8,#555)!important}.rig{border-left:5px solid #7d858e!important;border-right:5px solid #7d858e!important}" : ""}
    ${skin === "hytera" ? ".lcd{border-radius:7px!important}.freq{letter-spacing:1px!important}.rig{box-shadow:0 0 0 4px #151a17,0 18px 42px #000b!important}" : ""}
    ${skin === "kenwood" ? ".lcd{border-radius:5px!important}.freq{font-family:Arial,sans-serif!important;letter-spacing:2px!important}.rig{border-radius:12px!important}" : ""}
    ${skin === "baofeng" ? ".lcd{border-radius:3px!important;text-shadow:none!important}.freq{font-family:'Share Tech Mono',monospace!important}.panel h3{letter-spacing:1px!important}" : ""}
    ${skin === "sonim" ? ".rig{border:6px solid #d6aa26!important;box-shadow:0 0 0 3px #111,0 18px 42px #000c!important}.panel{border-radius:18px!important}#ptt{border-radius:50%!important;width:min(74vw,285px)!important;height:min(74vw,285px)!important;max-width:285px!important;max-height:285px!important;aspect-ratio:1/1!important}" : ""}
    ${skin === "boondockecho" ? `
    .rig{position:relative!important;overflow:hidden!important;background:linear-gradient(155deg,#b83a1c 0%,#8f210f 58%,#6e180d)!important;border:5px solid #e7d2c5!important;box-shadow:0 0 0 3px #48140d,0 18px 42px #000b!important}
    .rig:after{content:"";position:absolute;inset:150px -20px 20px;background-repeat:no-repeat;background-position:center bottom;background-size:100% 78%;opacity:.23;pointer-events:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 420' fill='none'%3E%3Cg stroke='%23f5d9c9' stroke-width='3' opacity='.9'%3E%3Cpath d='M-20 260 90 180 145 140 205 175 290 55 345 105 390 80 470 145 620 230'/%3E%3Cpath d='M-20 285 90 205 150 165 205 200 290 80 345 130 390 105 470 170 620 255'/%3E%3Cpath d='M35 330 120 260 175 245 230 275 300 170 365 210 420 185 500 245 620 300'/%3E%3Cpath d='M70 370 145 315 200 300 260 325 325 235 390 270 450 245 530 295 620 340'/%3E%3C/g%3E%3C/svg%3E")}
    .brand{position:relative;z-index:2;min-height:74px!important;align-items:center!important}
    .brand h1{font-family:Arial,sans-serif!important;font-size:clamp(20px,5vw,28px)!important;letter-spacing:2px!important;color:#f5dfd4!important;-webkit-text-fill-color:#f5dfd4!important;text-shadow:0 2px 2px #57190f!important}
    .brand small{color:#f3cbb9!important;letter-spacing:2px!important}
    .lcd{position:relative;z-index:2;background:linear-gradient(180deg,#38180f,#1d0e0a)!important;color:#f5d9c9!important;border-color:#6e2a19!important;text-shadow:0 0 8px #f4b9a0!important}
    .panel{position:relative;z-index:2;background:#651b12dd!important;border:1px solid #efcbbb77!important}
    .panel h3{color:#f4d8ca!important}
    #ptt{position:relative;z-index:3;width:min(76vw,285px)!important;height:min(76vw,285px)!important;border-radius:50%!important;background:radial-gradient(circle at 35% 25%,#ffb18c,#df4a22 48%,#7e1b0c)!important;border:7px solid #52180f!important;box-shadow:0 0 0 3px #f1d3c3,0 9px 20px #310d08aa,inset 0 -10px 15px #4a100a99!important}
    #ptt.on{background:radial-gradient(circle at 35% 25%,#ffc4b9,#ed3024 48%,#7d0909)!important}
    #ptt.busy{background:radial-gradient(circle at 35% 25%,#fff0a6,#dc9a25 48%,#75400c)!important}
    #boondockLteIndicators{position:relative;z-index:3;display:flex;flex-direction:row;align-items:center;justify-content:center;gap:12px;width:100%;margin:6px auto;flex-wrap:nowrap}
    #boondockLteIndicators .lte-indicator{display:flex;align-items:center;justify-content:center;gap:8px;min-width:82px;padding:0;border:0;border-radius:0;background:transparent;color:#f7e5dc;font:800 9px Arial,sans-serif;letter-spacing:.7px}
    #boondockLteIndicators .lte-dot{display:none}
    #boondockLteIndicators svg{display:none}#boondockLteIndicators .status-led{display:flex;flex-direction:row;align-items:center;gap:7px;min-width:70px;padding:8px 12px;border:1px solid #f0cbbb;border-radius:9px;background:linear-gradient(#42170f,#1d0b08);color:#f7e5dc;font:900 11px Arial;letter-spacing:1px;box-shadow:inset 0 1px 2px #ffffff22,0 2px 6px #0008}#boondockLteIndicators .status-led i{width:10px;height:10px;border-radius:50%;background:#292929;box-shadow:inset 0 1px 3px #000}#boondockLteIndicators .status-led.rx.on{color:#c9ffe0;border-color:#45ed8a}#boondockLteIndicators .status-led.rx.on i{background:#45ed8a;box-shadow:0 0 10px #45ed8a}#boondockLteIndicators .status-led.tx.on{color:#ffd1ce;border-color:#ff514b}#boondockLteIndicators .status-led.tx.on i{background:#ff514b;box-shadow:0 0 10px #ff514b}
    #clientControls{position:relative;z-index:3}
    #net{position:relative;z-index:3;color:#f3d4c7!important}
    ` : ""}
  `;
  function apply() {
    try {
      const doc = frame.contentDocument;
      if (!doc || !doc.head) return;
      let style = doc.getElementById("sanket-radio-skin");
      if (!style) { style = doc.createElement("style"); style.id = "sanket-radio-skin"; doc.head.appendChild(style); }
      if (skin === "boondockecho" && !doc.getElementById("boondockLteIndicators")) {
        const brand = doc.querySelector(".brand");
        if (brand) {
          const indicators = doc.createElement("div");
          indicators.id = "boondockLteIndicators";
          const heading = brand.querySelector("h1"); if (heading) heading.textContent = "BOONDOCK ECHO";
          const subheading = brand.querySelector("small"); if (subheading) subheading.textContent = "LTE COMMUNICATIONS";
          indicators.innerHTML = '<div class="lte-indicator rx-slot">RX</div><div class="lte-indicator tx-slot">TX</div>';
          const rxButton = doc.getElementById("ledrx"), txButton = doc.getElementById("ledtx");
          if (rxButton) { rxButton.innerHTML = "<i></i><span>RX</span>"; rxButton.setAttribute("aria-label","Receive activity"); indicators.querySelector(".rx-slot").appendChild(rxButton); }
          if (txButton) { txButton.innerHTML = "<i></i><span>TX</span>"; txButton.setAttribute("aria-label","Transmit activity"); indicators.querySelector(".tx-slot").appendChild(txButton); }
          brand.after(indicators);
        }
      }
      style.textContent = css;
      doc.documentElement.style.background = t.bg;
    } catch (e) {}
  }
  frame.addEventListener("load", apply);
  setTimeout(apply, 700);
  document.title = "SanketPTT · " + skin.charAt(0).toUpperCase() + skin.slice(1) + " Radio";
})();