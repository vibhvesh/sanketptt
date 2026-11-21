(()=> {
"use strict";
const $=id=>document.getElementById(id),rig=document.querySelector(".rig");
if(!rig||!$("ptt")||!$("radioLinesDev"))return;
const channels=[["virtual","VIRTUAL"],["boondock-sptt","BOONDOCK SPTT"],["police-ptt","POLICE PTT"],["hospital-ptt","HOSPITAL PTT"],["mall-ptt","MALL PTT"],["construction-ptt","CONSTRUCTION PTT"],["boondockecho-lte","BOONDOCK ECHO LTE"]];
const params=new URLSearchParams(location.search),ch=params.get("ch")||"virtual";
const skins=[["boondockecho","Boondock Echo"],["motorola","Motorola"],["hytera","Hytera"],["kenwood","Kenwood"],["baofeng","Baofeng"],["sonim","Sonim"]];
const top=document.createElement("div");top.id="simpleRadioTop";top.innerHTML='<div class="simple-top-left"><button id="radioPower" type="button" aria-label="Power on radio" aria-pressed="false"><span class="power-glyph">⏻</span><span id="radioPowerText">OFF</span></button><div class="simple-channel"><i></i><b id="simpleChannelName"></b></div></div><div><select id="simpleSkin" aria-label="Radio skin"></select><button id="simpleClose" aria-label="Close radio">×</button></div>';
rig.querySelector(".brand").after(top);
const ledGroup=document.querySelector(".leds"),ledPwr=ledGroup&&ledGroup.querySelector(".led.pw");
if(ledGroup){top.querySelector(".simple-channel").after(ledGroup);ledGroup.style.display="flex";ledGroup.style.gap="7px";ledGroup.style.alignItems="center"}
if(ledPwr){ledPwr.id="ledpw";ledPwr.classList.remove("on")}
["rx","tx"].forEach(kind=>{const old=ledGroup&&ledGroup.querySelector(".led."+kind);if(old&&old.tagName!=="BUTTON"){const btn=document.createElement("button");btn.type="button";btn.id=kind==="rx"?"ledrx":"ledtx";btn.className=old.className+" status-led";btn.setAttribute("aria-label",kind==="rx"?"Receive status":"Transmit status");btn.setAttribute("aria-pressed","false");btn.innerHTML=old.innerHTML;old.replaceWith(btn);window[kind==="rx"?"ledrx":"ledtx"]=btn}});
const ledRx=$("ledrx"),ledTx=$("ledtx");
skins.forEach(([v,n])=>$("simpleSkin").add(new Option(n,v)));$("simpleSkin").value=params.get("skin")||"boondockecho";
$("simpleSkin").onchange=()=>{try{const u=new URL(window.parent.location.href);u.searchParams.set("skin",$("simpleSkin").value);window.parent.location.href=u.href}catch(e){const u=new URL(location.href);u.searchParams.set("skin",$("simpleSkin").value);location.href=u.href}};
$("simpleChannelName").textContent=(channels.find(x=>x[0]===ch)||channels[0])[1];
$("simpleClose").onclick=()=>{try{radio&&radio.leave()}catch(e){}try{window.top.close()}catch(e){}setTimeout(()=>{try{window.top.location.replace("/boondock-echo-live/")}catch(e){history.back()}},150)};
const login=$("login"),name=$("nm"),go=$("go"),main=$("main"),ptt=$("ptt");
const meterPanel=document.querySelector(".lcd .meter"),unlockButton=$("unlock");
if(meterPanel&&!$("simpleSquelch")){const sq=document.createElement("div");sq.id="simpleSquelch";sq.innerHTML='<label for="simpleSquelchLevel">SQUELCH <span id="simpleSquelchValue">0</span></label><input id="simpleSquelchLevel" type="range" min="0" max="40" step="1" value="0" aria-label="Squelch level">';meterPanel.appendChild(sq)}

ptt.textContent="POWER ON FIRST";ptt.setAttribute("aria-label","Power on the radio using the top-left switch before transmitting");
const pttDock=document.createElement("div");pttDock.id="simplePttDock";
const pttHint=ptt.nextElementSibling&&ptt.nextElementSibling.classList.contains("hint")?ptt.nextElementSibling:null;
pttDock.appendChild(ptt);if(pttHint)pttDock.appendChild(pttHint);
const topRight=top.querySelector("div:last-child");topRight.classList.add("simple-top-right");const lcd=document.querySelector(".lcd");lcd.after(pttDock);

login.style.display="none";go.style.display="none";main.style.display="none";lcd.after(name);name.after(pttDock);name.placeholder="Call sign";name.setAttribute("aria-label","Call sign");$("hd").style.display="none";
const more=document.createElement("button");more.id="simpleMore";more.textContent="⋮";more.setAttribute("aria-label","More radio controls");top.querySelector("div:last-child").appendChild(more);const drawer=document.createElement("div");drawer.id="simpleMoreDrawer";drawer.innerHTML='<div class="more-head"><b>RADIO OPTIONS</b><button id="moreClose">×</button></div><label>CHANNEL<select id="simpleChannel"></select></label><label class="auto-row">AUTO POWER ON <input id="simpleAutoPower" type="checkbox"></label><small>FM pauses automatically during PTT.</small>';
rig.append(drawer);
const skinLabel=document.createElement("label");skinLabel.textContent="RADIO SKIN";skinLabel.appendChild($("simpleSkin"));drawer.appendChild(skinLabel);

channels.forEach(([v,n])=>$("simpleChannel").add(new Option(n,v)));$("simpleChannel").value=channels.some(x=>x[0]===ch)?ch:"virtual";
$("simpleChannel").onchange=()=>{const u=new URL(location.href);u.searchParams.set("ch",$("simpleChannel").value);location.href=u.href};
const auto=$("simpleAutoPower");auto.checked=localStorage.getItem("sanketptt.autoPower")!=="off";auto.onchange=()=>localStorage.setItem("sanketptt.autoPower",auto.checked?"on":"off");
more.onclick=()=>{drawer.classList.toggle("open");$("radioLinesDev").classList.remove("open")};$("moreClose").onclick=()=>drawer.classList.remove("open");
const sstv=$("sstvP"),sstvBtn=$("sstvBtn"),sstvFile=$("sstvFile");
const sstvRow=document.createElement("div");sstvRow.id="simpleSstvRow";sstvRow.innerHTML='<span>SSTV SEND</span><small id="sstvProgress" aria-live="polite"></small><button id="sstvBrowse">BROWSE</button><button id="sstvTake">CAMERA</button>';main.after(sstvRow);
const sstvModal=document.createElement("div");sstvModal.id="simpleSstvModal";sstvModal.innerHTML='<div class="sstv-modal-head"><b>REVIEW IMAGE</b><button id="sstvModalClose" aria-label="Close">×</button></div>';sstvModal.appendChild($("sstvTx"));rig.appendChild(sstvModal);
$("sstvModalClose").onclick=()=>{$("sstvTx").style.display="none";sstvModal.classList.remove("open")};
$("sstvBrowse").onclick=()=>{sstvFile.removeAttribute("capture");sstvFile.click()};
$("sstvTake").onclick=()=>{sstvFile.setAttribute("capture","environment");sstvFile.click()};
$("sstvSend").textContent="OK · SEND";$("sstvCancel").textContent="CANCEL";window.addEventListener("boondock:sstv-start",()=>{sstvModal.classList.remove("open");$("sstvTx").style.display="none";$("sstvProgress").textContent="SENDING…"});const sstvStatusObserver=new MutationObserver(()=>{$("sstvProgress").textContent=$("sstvSt")?.textContent||""});if($("sstvSt"))sstvStatusObserver.observe($("sstvSt"),{childList:true,subtree:true,characterData:true});
if(sstvFile)document.body.appendChild(sstvFile);
if(sstvBtn)sstvBtn.remove();if(sstv)sstv.remove();
const fm=$("radioLinesDev"),audio=$("radioLineAudio");fm.classList.remove("open");
const fmBtn=document.createElement("button");fmBtn.id="simpleFM";fmBtn.type="button";fmBtn.textContent="FM RADIO";fmBtn.setAttribute("aria-expanded","false");rig.appendChild(fmBtn);
if(pttHint)pttHint.style.display="none";
const fmHead=fm.querySelector("h3"),fmClose=document.createElement("button");fmClose.id="fmPanelClose";fmClose.type="button";fmClose.textContent="×";fmClose.setAttribute("aria-label","Close FM radio panel");fmHead.appendChild(fmClose);
function closeFmPanel(){fm.classList.remove("open");fmBtn.textContent="FM RADIO";fmBtn.setAttribute("aria-expanded","false");}
fmBtn.onclick=()=>{drawer.classList.remove("open");const open=!fm.classList.contains("open");fm.classList.toggle("open",open);fmBtn.textContent=open?"CLOSE FM":"FM RADIO";fmBtn.setAttribute("aria-expanded",String(open))};
fmClose.onclick=closeFmPanel;
$("radioStationSelect").addEventListener("change",()=>{if($("radioStationSelect").value)closeFmPanel()});$("radioStationButtons").addEventListener("click",e=>{if(e.target.closest("button"))closeFmPanel()});

document.querySelector(".panel:has(#us)")?.remove();$("locp")?.remove();const logPanel=$("log")?.closest(".panel");if(logPanel)logPanel.style.display="none";
const messages=document.createElement("section");messages.id="simpleMessages";messages.innerHTML='<div class="ribbon-head">LAST FIVE AUDIO MESSAGES</div><div id="recentAudioRibbons"><small>Waiting for radio traffic</small></div><div class="transcript-head"><b>MESSAGE HISTORY · NEWEST AT BOTTOM</b><span id="whisperState">WHISPER · AUTO</span></div><div id="simpleTranscriptList"><small>Your sent and received messages will appear here</small></div><div id="simpleSstvGallery"><div class="transcript-head"><b>SSTV PICTURES</b><span>LOCAL & RECEIVED</span></div></div>';main.after(messages);$("simpleSstvGallery").appendChild($("sstvList"));
const css=[
"body{padding:0!important;background:#8f210f!important;overflow:hidden!important;height:100dvh!important}",
".rig{width:100%!important;max-width:520px!important;height:100dvh!important;min-height:0!important;overflow:hidden!important;padding:6px 9px!important;display:flex!important;flex-direction:column!important;gap:4px!important;border-radius:0!important}",
".brand{margin:0 5px!important;min-height:28px!important;max-height:28px!important;overflow:hidden!important}.brand h1{font-size:15px!important}",
"#simpleRadioTop{display:flex;align-items:center;justify-content:space-between;padding:2px 4px;min-height:34px;flex:0 0 34px}",
".simple-channel{display:flex;align-items:center;gap:8px;color:#f8dfd4;font:800 11px Arial,sans-serif;letter-spacing:1px}",
".simple-channel i{width:9px;height:9px;border-radius:50%;background:#f1d8cc;box-shadow:0 0 0 2px #ffffff44}",
"#simpleSkin{max-width:125px;min-height:30px!important;padding:4px!important;font:700 11px Arial!important;background:#6f1e12!important;color:#ffe8dd!important}",
"#simpleClose{width:30px;height:30px;border-radius:50%;background:#55170e;color:#fff;font:22px Arial}",
".lcd{padding:5px 8px!important;margin:0!important;flex:0 0 auto}.lcd .meter{display:block!important;margin-top:3px!important}.lcd .freq{font-size:clamp(19px,5vw,27px)!important;margin:1px 0!important;letter-spacing:1px!important}#st{font-size:10px!important;min-height:12px!important}.lcd .row{font-size:10px!important}.meter .lab{font-size:8px!important}.bars{height:8px!important;margin-top:1px!important}",
"#main{display:flex!important;flex-direction:column!important;align-items:center!important;gap:2px!important;margin:0!important;flex:0 0 auto}",
"#nm{width:100%!important;max-width:220px!important;min-height:34px!important;padding:6px!important;margin:0!important;text-align:center!important;background:#4f180f!important;color:#fff!important}",
"#ptt{width:min(29vw,168px)!important;height:min(29vw,168px)!important;min-width:118px!important;min-height:118px!important;max-width:168px!important;max-height:168px!important;aspect-ratio:1!important;margin:2px auto!important;border-radius:50%!important;font-size:17px!important;font-weight:900!important;touch-action:none!important;flex:0 0 auto}",
"#main .hint{color:#f4d4c7!important;font:10px Arial!important}",
"#simpleSquelch{display:flex;align-items:center;gap:8px;margin-top:3px;color:#e8c6b9;font:800 8px Arial;letter-spacing:1px}#simpleSquelch label{min-width:64px;display:flex;justify-content:space-between;gap:4px}#simpleSquelch input{height:10px;padding:0;margin:0;flex:1;accent-color:#f0b99e}",
"#simpleMessages{height:47dvh;min-height:0;max-height:none;flex:1 1 auto;display:flex;flex-direction:column;overflow:hidden;border:1px solid #f0cbbb88;border-radius:12px;background:#5d1a11dd;color:#fff0e8;padding:7px;gap:5px}",
".ribbon-head,.transcript-head{display:flex;justify-content:space-between;align-items:center;font:800 9px Arial;letter-spacing:1px;color:#f5d5c8}",
"#recentAudioRibbons{display:flex;gap:5px;overflow-x:auto;min-height:40px;padding-bottom:3px}",
".audio-ribbon{flex:0 0 92px;min-width:92px;border:1px solid #f2cdbb66;border-radius:8px;background:#7a2416;color:#fff1e9;padding:5px;font:10px Arial;text-align:left}",
".audio-ribbon b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.audio-ribbon small{display:block;color:#f2cbb9;margin-top:3px}",
"#simpleTranscriptList{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain}",
".transcript-item{padding:7px 5px;border-bottom:1px solid #f0d2c322;font:12px/1.4 Arial}.transcript-meta{display:flex;justify-content:space-between;color:#f3c6b2;font-size:9px;margin-bottom:3px}.transcript-text{color:#fff3ed;white-space:pre-wrap;overflow-wrap:anywhere}",
"#whisperState{font-size:8px;color:#f7d5c8}.empty-ribbon,.empty-transcript{font:11px Arial;color:#f0cdbf88;padding:8px}",
"#simpleMore,#simpleFM{position:static;z-index:25;width:auto;min-width:42px;height:30px;padding:0 9px;border-radius:8px;background:#641b10;border:1px solid #f0cbbb;color:#ffe7dc;font:800 10px Arial;box-shadow:0 2px 5px #0005}",
"#simpleMore{font-size:18px;min-width:30px;padding:0}#simpleFM{min-width:56px}",
"#simpleMoreDrawer{display:none;position:fixed;z-index:30;left:10px;bottom:52px;width:min(270px,calc(100vw - 20px));padding:12px;background:#58180f;border:1px solid #f0cbbb;border-radius:12px;box-shadow:0 10px 28px #0009;color:#ffeadf}",
"#simpleMoreDrawer.open{display:block}.more-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;font:800 11px Arial}",
"#sstvPick{display:none;margin-top:8px;gap:6px}#sstvPick.open{display:grid;grid-template-columns:1fr 1fr}#sstvPick b{grid-column:1/-1;font:800 10px Arial;color:#f5d5c8}#sstvPick button{padding:9px;background:#e9c8b8;color:#51170e;font:800 11px Arial}",
"#simpleMoreDrawer label{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:9px 0;font:11px Arial}#simpleMoreDrawer select{max-width:145px;min-height:34px!important;font-size:11px!important}",
"#simpleMoreDrawer input{width:18px;height:18px}#simpleSstv{width:100%;padding:9px;background:#e9c8b8;color:#51170e;font:800 11px Arial}",
"#radioLinesDev{display:block!important;position:fixed!important;z-index:45!important;left:0!important;right:0!important;bottom:0!important;top:auto!important;height:min(68dvh,560px)!important;max-height:68dvh!important;overflow:auto!important;margin:0!important;padding:14px 12px 76px!important;background:#3e170f!important;border-radius:18px 18px 0 0!important;box-shadow:0 -12px 36px #000b!important;transform:translateY(110%);visibility:hidden;transition:transform .28s ease,visibility .28s ease!important}",
"#radioLinesDev.open{transform:translateY(0)!important;visibility:visible!important}",
"#simpleFM{position:fixed!important;z-index:46!important;left:50%!important;bottom:calc(8px + env(safe-area-inset-bottom))!important;transform:translateX(-50%)!important;width:calc(100% - 20px)!important;max-width:500px!important;height:44px!important;border-radius:14px!important;background:linear-gradient(#f2c8ae,#d99c7e)!important;color:#45170f!important;font:900 12px Arial!important;box-shadow:0 3px 12px #0008!important}",
"#simplePttDock{display:flex;flex:0 0 auto;align-items:center;justify-content:center;min-height:0;padding:2px 0;margin:2px auto 4px}",
"#simplePttDock #ptt{width:min(40vw,190px)!important;height:min(40vw,190px)!important;min-width:142px!important;min-height:142px!important;max-width:190px!important;max-height:190px!important;margin:0 auto!important;flex:0 0 auto!important;font-size:17px!important}",
"#radioLinesDev.open{display:block!important}#radioLinesDev .radio-scan{max-height:140px;overflow:auto}",
"#sstvP,#locp,.panel:has(#us),.panel:has(#log),#net{display:none!important}",
"#sstvP.simple-sstv.open{display:block!important;position:fixed!important;z-index:40!important;left:10px!important;right:10px!important;bottom:54px!important;max-height:65dvh!important;overflow:auto!important;background:#5d1a11!important;color:#fff0e8!important;padding:10px!important;border:1px solid #f0cbbb!important;border-radius:12px!important}",
"#simpleSstvRow{display:flex;align-items:center;gap:6px;flex:0 0 36px;min-height:36px;padding:3px 5px;border:1px solid #f0cbbb88;border-radius:9px;background:#5d1a11;color:#ffe9df;font:800 9px Arial;letter-spacing:1px}#simpleSstvRow span{flex:1}#simpleSstvRow button{height:28px;min-width:82px;background:#e9c8b8;color:#51170e;border-radius:7px;font:800 10px Arial}#simpleSstvModal{display:none;position:fixed;z-index:60;inset:0;background:#180b09ed;align-items:center;justify-content:center;padding:16px}#simpleSstvModal.open{display:flex}#simpleSstvModal #sstvTx{display:block!important;width:min(94vw,390px);max-height:90dvh;overflow:auto;background:#5d1a11;padding:10px;border:1px solid #f0cbbb;border-radius:12px}#simpleSstvModal canvas{width:100%!important;height:auto!important}.sstv-modal-head{display:flex;justify-content:space-between;align-items:center;color:#ffe9df;font:800 12px Arial;margin-bottom:8px}.sstv-modal-head button{background:#7b291b;color:white;padding:6px 10px}#simpleMoreDrawer{top:72px;bottom:auto;max-height:75dvh;overflow:auto}#simpleMoreDrawer.open{display:block}#simpleRadioTop>div:last-child{display:flex;align-items:center;gap:5px}@media(max-height:720px){#ptt{width:min(25vw,142px)!important;height:min(25vw,142px)!important;min-width:105px!important;min-height:105px!important}#simpleMessages{height:auto;min-height:0}#nm{min-height:28px!important;font-size:14px!important}#main .hint{display:none!important}}",
].join("\n");
const messageGalleryStyle=document.createElement("style");messageGalleryStyle.textContent=`#simpleSstvGallery{flex:0 0 auto;max-height:112px;min-height:0;overflow-y:auto;border-top:1px solid #f0cbbb55;padding-top:4px}#simpleSstvGallery .transcript-head{position:sticky;top:0;background:#5d1a11;z-index:1;padding:2px 0}#simpleSstvGallery #sstvList{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin:3px 0 0;padding:0}#simpleSstvGallery #sstvList li{min-width:0;padding:3px;border:1px solid #f0cbbb55;border-radius:6px;overflow:hidden}#simpleSstvGallery #sstvList canvas,#simpleSstvGallery #sstvList img{width:100%;max-width:none;aspect-ratio:4/3;object-fit:contain}#simpleMessages #simpleTranscriptList{scroll-behavior:smooth;overflow-y:auto;overscroll-behavior:contain}#simpleMessages .transcript-item{scroll-margin-bottom:6px}#simpleMessages .transcript-item.mine{border-left:3px solid #f5c77a;padding-left:7px}#simpleMessages .transcript-item:not(.mine){border-left:3px solid #78c8ad;padding-left:7px}#simpleMessages .audio-ribbon{flex:0 0 92px}`;document.head.appendChild(messageGalleryStyle);
const pttDockStyle=document.createElement("style");pttDockStyle.textContent=`#simpleRadioTop>div:last-child{display:flex;align-items:center;justify-content:flex-end;gap:4px;min-width:0}#simplePttDock{display:flex;flex:0 0 auto;align-items:center;justify-content:center;min-height:0;padding:0;margin:0}#simplePttDock #ptt{width:52px!important;height:52px!important;min-width:52px!important;min-height:52px!important;max-width:52px!important;max-height:52px!important;margin:0!important;flex:0 0 52px!important;border-radius:50%!important;font-size:9px!important;letter-spacing:.2px!important;line-height:1.05!important;touch-action:none!important;box-shadow:inset 0 3px 6px #ffffff44,inset 0 -6px 10px #0005,0 2px 5px #0008!important}#simplePttDock .hint{display:none!important}#main{align-items:stretch!important}#nm{max-width:none!important}@media(max-width:600px){#simpleRadioTop{gap:3px;min-height:58px;flex-basis:58px;padding:1px 3px}#simpleRadioTop .simple-top-left{gap:4px;min-width:0}#simpleRadioTop .simple-channel{font-size:8px;letter-spacing:.2px;max-width:65px;overflow:hidden}#simpleRadioTop>div:last-child{gap:3px}#simplePttDock #ptt{width:48px!important;height:48px!important;min-width:48px!important;min-height:48px!important;max-width:48px!important;max-height:48px!important}#simpleFM{font-size:8px!important;padding:4px!important;min-width:0!important}#simpleMore{width:26px!important;min-width:26px!important}#simpleClose{width:24px!important;min-width:24px!important}#simpleSkin{display:none!important}}`;document.head.appendChild(pttDockStyle);
const topPttStyle=document.createElement("style");topPttStyle.textContent=`#simpleRadioTop{display:flex;align-items:center;justify-content:space-between;gap:6px}#simpleRadioTop .simple-top-right{display:flex;align-items:center;justify-content:flex-end;gap:6px;min-width:0}#simplePttDock{display:flex;align-items:center;justify-content:center;gap:0;min-height:0;padding:0;margin:0;flex:0 0 auto}#simplePttDock #ptt{width:56px!important;height:56px!important;min-width:56px!important;min-height:56px!important;max-width:56px!important;max-height:56px!important;margin:0!important;flex:0 0 56px!important;border-radius:50%!important;font-size:9px!important;line-height:1.05!important;padding:3px!important;letter-spacing:.2px!important}#simplePttDock .hint{display:none!important}#simpleRadioTop #simpleSkin{max-width:74px;min-width:0;font-size:9px;padding:5px}#simpleRadioTop #simpleClose{width:34px;height:34px;flex:0 0 34px}@media(max-width:600px){#simpleRadioTop{min-height:58px;flex-basis:auto}#simpleRadioTop .simple-top-right{gap:4px}#simplePttDock #ptt{width:52px!important;height:52px!important;min-width:52px!important;min-height:52px!important;max-width:52px!important;max-height:52px!important;flex-basis:52px!important}#simpleRadioTop #simpleSkin{max-width:60px;font-size:8px}#simpleRadioTop #simpleClose{width:30px;height:30px;flex-basis:30px}}`;document.head.appendChild(topPttStyle);
const style=document.createElement("style");style.id="simpleRadioStyles";style.textContent=css;document.head.appendChild(style);
const statusButtonStyle=document.createElement("style");statusButtonStyle.textContent=`#radioPower{min-width:106px!important;padding:0 10px!important}#radioPower .power-glyph{display:none!important}.rig:not(.radio-powered) .lcd .meter{display:none!important}.rig.radio-powered .lcd .meter{display:block!important}.led.status-led{appearance:none;-webkit-appearance:none;cursor:default;border:1px solid #f0cbbb55;border-radius:8px;padding:4px 6px;min-width:34px;background:linear-gradient(#38130f,#1e0b09);color:#e9cabc;font:900 9px Arial;display:flex;flex-direction:column;align-items:center;gap:3px;box-shadow:inset 0 1px 2px #ffffff18}.led.status-led i{width:10px;height:10px;border-radius:50%;background:#292929;box-shadow:inset 0 1px 3px #000}.led.status-led.rx.on{color:#c9ffe0;border-color:#45ed8a88}.led.status-led.rx.on i{background:#45ed8a;box-shadow:0 0 10px #45ed8a}.led.status-led.tx.on{color:#ffd1ce;border-color:#ff514b99}.led.status-led.tx.on i{background:#ff514b;box-shadow:0 0 10px #ff514b}.led.status-led:focus{outline:1px solid #ffe0cf}.led.pw i{background:#333!important;box-shadow:inset 0 1px 3px #000!important}.led.pw.on i{background:#ffc247!important;box-shadow:0 0 10px #ffc247!important}#simpleSquelch{display:flex}#simpleRadioTop .simple-top-left{display:flex;align-items:center;gap:8px;min-width:0;flex:1}#radioPower{min-width:64px;height:32px;border-radius:18px;border:1px solid #f8d7c5;background:linear-gradient(#502017,#2a100c);color:#f8dfd3;display:flex;align-items:center;justify-content:center;gap:4px;font:900 9px Arial;box-shadow:inset 0 1px 2px #ffffff30,0 2px 5px #0007}#radioPower .power-glyph{font-size:21px}#radioPower.is-on{background:linear-gradient(#f5c35e,#a95c1a);color:#30140c;box-shadow:0 0 10px #ffb52d88}#ptt:disabled{opacity:.58;filter:saturate(.55)}.lcd .meter{display:none}#simpleRadioTop .leds{display:flex;gap:5px!important;align-items:center}`;document.head.appendChild(statusButtonStyle);

const powerStyle=document.createElement("style");powerStyle.textContent=`#simpleRadioTop .simple-top-left{display:flex;align-items:center;gap:8px;min-width:0;flex:1}#radioPower{height:31px;min-width:62px;padding:2px 8px;border-radius:18px;border:1px solid #f7d9c9;background:linear-gradient(180deg,#542018,#2c100c);color:#f5d8cc;display:flex;align-items:center;justify-content:center;gap:4px;box-shadow:inset 0 1px 2px #ffffff30,0 2px 5px #0007;font:900 9px Arial;letter-spacing:1px}#radioPower .power-glyph{font:22px Arial;line-height:1}#radioPower.is-on{background:linear-gradient(180deg,#f4c15d,#a65b1a);color:#32140b;border-color:#ffe6a8;box-shadow:0 0 10px #ffb52d88,inset 0 1px 2px #fff9}#radioPower:disabled{opacity:.7}#ptt:disabled{opacity:.55;filter:grayscale(.45);pointer-events:none}#simpleRadioTop .simple-channel{min-width:0}#simpleRadioTop>div:last-child{flex:0 0 auto}@media(max-width:390px){#radioPower{min-width:54px;height:29px;padding:1px 6px}#radioPower .power-glyph{font-size:19px}}`;document.head.appendChild(powerStyle);

const ledStyle=document.createElement("style");ledStyle.textContent=`.leds{gap:7px!important}.led{font:800 8px Arial!important;letter-spacing:1px}.led i{width:11px!important;height:11px!important;display:block}#ledpw.on i{background:#ffc247!important;box-shadow:0 0 10px #ffc247;animation:pwrGlow 2s ease-in-out infinite}#ledrx.on i{background:#45ed8a!important;box-shadow:0 0 12px #45ed8a;animation:rxBlink .55s steps(2,end) infinite}#ledtx.on i{background:#ff514b!important;box-shadow:0 0 13px #ff514b;animation:txBlink .28s steps(2,end) infinite}@keyframes pwrGlow{50%{box-shadow:0 0 3px #ffc247;opacity:.8}}@keyframes rxBlink{50%{opacity:.25;box-shadow:none}}@keyframes txBlink{50%{opacity:.15;box-shadow:none}}#simpleRadioTop{gap:7px!important;flex-wrap:nowrap!important}#simpleRadioTop .simple-channel{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}#simpleRadioTop>div:last-child{display:flex;align-items:center;gap:4px}#simpleFM{min-width:48px!important;padding:0 6px!important}#simpleMore{min-width:26px!important;font-size:18px!important}#simpleSkin{max-width:88px!important;min-width:0!important}#simpleClose{flex:0 0 28px}#simpleSstvRow{margin-top:2px}@media(max-width:390px){.simple-channel{font-size:9px!important}.led{font-size:7px!important}.led i{width:9px!important;height:9px!important}#simpleSkin{max-width:72px!important}#simpleFM{min-width:42px!important;font-size:8px!important}}`;document.head.appendChild(ledStyle);

if(sstvFile)sstvFile.addEventListener("change",()=>{if(sstvFile.files&&sstvFile.files.length){sstvModal.classList.add("open");$("sstvTx").style.display="block";drawer.classList.remove("open")}});
$("sstvCancel")?.addEventListener("click",()=>{sstvModal.classList.remove("open");$("sstvTx").style.display="none"});
const oldRender=window.render;window.render=function(){if(oldRender)oldRender();if(!radioPowered){ptt.textContent="POWER ON FIRST";ptt.className="";$("st").textContent="POWER OFF"}else if(!window.radio||!radio.name){ptt.textContent="JOINING CHANNEL";$("st").textContent="JOINING CHANNEL"}else if(!holding&&!granted&&!(radio.floor&&radio.floor.id!==radio.id))ptt.textContent="HOLD TO TALK"};
const powerBtn=$("radioPower"),powerText=$("radioPowerText");
let radioPowered=false;window.radioPowered=false;
window.addEventListener("boondock:radio-state",e=>setRadioPower(!!(e.detail&&e.detail.powered)));
function setRadioPower(on){
 radioPowered=!!on;window.radioPowered=radioPowered;
 powerBtn.classList.toggle("is-on",radioPowered);powerBtn.setAttribute("aria-pressed",String(radioPowered));powerBtn.setAttribute("aria-label",radioPowered?"Power off radio":"Power on radio");powerText.textContent=radioPowered?"POWER OFF":"POWER ON";
 if(ledPwr)ledPwr.classList.toggle("on",radioPowered);
 rig.classList.toggle("radio-powered",radioPowered);if(meterPanel)meterPanel.style.removeProperty("display");
 ptt.disabled=!radioPowered;ptt.setAttribute("aria-disabled",String(!radioPowered));ptt.textContent=radioPowered?"HOLD TO TALK":"POWER ON FIRST";
 $("st").textContent=radioPowered?"STANDBY":"POWER OFF";
}
function stopMic(){
 try{if(proc){proc.disconnect();proc.onaudioprocess=null;proc=null}}catch(e){}
 try{if(stream){stream.getTracks().forEach(t=>t.stop());stream=null}}catch(e){}
 try{if(ac&&ac.state!=="closed")ac.close()}catch(e){}
 granted=false;holding=false;sstvTx=false;
}
async function powerOnRadio(){if(!window.BoondockRadio||typeof window.BoondockRadio.powerOn!=="function")throw new Error("RADIO_CORE_NOT_READY");return await window.BoondockRadio.powerOn()}
powerBtn.addEventListener("click",async(e)=>{
 e.preventDefault();e.stopPropagation();
 if(powerBtn.disabled)return;
 if(!radioPowered){
  if(!name.value.trim()){
   $("st").textContent="ENTER CALL SIGN BELOW";
   name.focus();
   return;
  }
  powerBtn.disabled=true;powerText.textContent="STARTING";$("st").textContent="REQUESTING MICROPHONE…";
  try{
   const joined=await powerOnRadio();
   if(!joined)throw new Error("RADIO_JOIN_NOT_CONFIRMED");
   setRadioPower(true);$("st").textContent="RADIO ON · "+radio.ch.toUpperCase();
  }catch(e){
   stopMic();setRadioPower(false);
   const msg=e&&e.message?e.message:(e&&e.name?e.name:String(e));
   const messages={
    ENTER_CALL_SIGN:"ENTER CALL SIGN BELOW",
    MICROPHONE_API_UNAVAILABLE:"MICROPHONE NOT AVAILABLE IN THIS BROWSER",
    HTTPS_REQUIRED_FOR_MICROPHONE:"OPEN THE HTTPS SITE",
    NotAllowedError:"MIC PERMISSION BLOCKED · ALLOW MICROPHONE",
    PermissionDeniedError:"MIC PERMISSION BLOCKED · ALLOW MICROPHONE",
    NotFoundError:"NO MICROPHONE FOUND",
    NotReadableError:"MICROPHONE IS BUSY · CLOSE OTHER APPS",
    RADIO_JOIN_NOT_CONFIRMED:"RADIO DID NOT JOIN"
   };
   $("st").textContent=messages[msg]||("POWER ON FAILED · "+msg.slice(0,34));
   console.error("Boondock radio power-on failed:",e);
  }finally{powerBtn.disabled=false;powerText.textContent=radioPowered?"POWER OFF":"POWER ON"}
 }else{
  try{if(window.BoondockRadio)window.BoondockRadio.powerOff();setRadioPower(false)}
  catch(err){$("st").textContent="POWER OFF FAILED";console.error(err)}
 }
});
// PTT is transmit-only. When the radio is off it displays POWER ON FIRST.
ptt.addEventListener("pointerdown",e=>{if(!radioPowered||!window.radio||!radio.name){e.preventDefault();e.stopImmediatePropagation()}},true);
ptt.addEventListener("click",e=>{if(!radioPowered||!window.radio||!radio.name){e.preventDefault();e.stopImmediatePropagation()}},true);
window.addEventListener("keydown",e=>{if(e.code==="Space"&&!radioPowered){e.preventDefault();e.stopImmediatePropagation()}},true);
setRadioPower(false);
// First-run permission gate: if permission is already granted, start silently.
// If the browser can prompt, getUserMedia asks once and continues after Allow.
(async()=>{
 if(!auto.checked||!name.value.trim())return;
 let permissionState="prompt";
 try{if(navigator.permissions&&navigator.permissions.query){const permission=await navigator.permissions.query({name:"microphone"});permissionState=permission.state||"prompt"}}catch(permissionCheckError){console.warn("Microphone permission query unavailable; using getUserMedia prompt",permissionCheckError)}
 if(permissionState==="denied"){$("st").textContent="MIC BLOCKED · ENABLE IN SITE SETTINGS";return}
 try{
  if(radioPowered||powerBtn.disabled)return;
  powerBtn.disabled=true;powerText.textContent="STARTING";
  // If permission is already granted this continues silently; if it is prompt,
  // the original getUserMedia call asks the user and continues after Allow.
  const joined=await powerOnRadio();
  if(joined){setRadioPower(true);$("st").textContent="RADIO ON · "+radio.ch.toUpperCase()}
 }catch(e){
  stopMic();setRadioPower(false);
  $("st").textContent=e&&e.name==="NotAllowedError"?"MIC PERMISSION DENIED":"AUTO START FAILED";
  console.error("Boondock first-run startup failed:",e);
 }finally{powerBtn.disabled=false}
})();
let asr=null,asrLoading=null,queue=Promise.resolve();const done=new Set(),texts=new Map();
async function loadWhisper(){if(asr)return asr;if(asrLoading)return asrLoading;$("whisperState").textContent="WHISPER · LOADING";asrLoading=import("https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.5").then(T=>T.pipeline("automatic-speech-recognition","onnx-community/whisper-base",{dtype:"q8"})).then(p=>{asr=p;$("whisperState").textContent="WHISPER · ON DEVICE";return p}).catch(e=>{$("whisperState").textContent="WHISPER · UNAVAILABLE";throw e});return asrLoading}
const sqlInput=$("simpleSquelchLevel");if(sqlInput){sqlInput.value=localStorage.getItem("sanketptt.squelch")||"0";$("simpleSquelchValue").textContent=sqlInput.value;sqlInput.oninput=()=>{$("simpleSquelchValue").textContent=sqlInput.value;localStorage.setItem("sanketptt.squelch",sqlInput.value)}}
function wavFloat(wav){const v=new DataView(wav),n=v.getUint32(40,true)/2,rate=v.getUint32(24,true),src=new Float32Array(n);for(let i=0;i<n;i++)src[i]=v.getInt16(44+i*2,true)/32768;const m=Math.floor(n*16000/rate),out=new Float32Array(m);for(let i=0;i<m;i++){const x=i*rate/16000,j=Math.floor(x),f=x-j;out[i]=src[j]*(1-f)+(src[Math.min(j+1,n-1)]||0)*f}return out}
let messagePlayer=null,messagePlayerUrl=null,messagePlayerButton=null;
function stopMessagePlayback(){
 if(messagePlayer){messagePlayer.pause();messagePlayer.src="";messagePlayer=null}
 if(messagePlayerUrl){URL.revokeObjectURL(messagePlayerUrl);messagePlayerUrl=null}
 if(messagePlayerButton){messagePlayerButton.textContent="▶ PLAY";messagePlayerButton.classList.remove("playing")}
 messagePlayerButton=null;
}
function playMessage(e,button){
 if(messagePlayerButton===button&&messagePlayer&&!messagePlayer.paused){stopMessagePlayback();return}
 stopMessagePlayback();
 messagePlayerUrl=URL.createObjectURL(new Blob([e.wav],{type:"audio/wav"}));
 messagePlayer=new Audio(messagePlayerUrl);messagePlayerButton=button;
 button.textContent="■ STOP";button.classList.add("playing");
 messagePlayer.onended=stopMessagePlayback;
 messagePlayer.onerror=stopMessagePlayback;
 messagePlayer.play().catch(err=>{stopMessagePlayback();console.warn("Message playback failed:",err)});
}
function drawMessages(entries){
 const recent=$("recentAudioRibbons"),list=$("simpleTranscriptList");
 const ordered=entries.slice().sort((a,b)=>a.t0-b.t0),last=ordered.slice(-5);
 recent.innerHTML=last.length?"":'<small class="empty-ribbon">No recorded messages yet</small>';
 last.slice().reverse().forEach(e=>{
  const b=document.createElement("button");b.type="button";b.className="audio-ribbon"+(e.mine?" mine":"");
  const who=document.createElement("b");who.textContent=(e.name||"Radio")+(e.mine?" · YOU":"");
  const tm=document.createElement("small");tm.textContent=new Date(e.t0).toLocaleTimeString();
  const action=document.createElement("span");action.className="ribbon-play";action.textContent="▶ PLAY";
  b.append(who,tm,action);b.onclick=()=>playMessage(e,action);recent.appendChild(b);
 });
 list.innerHTML=ordered.length?"":'<small class="empty-transcript">Your sent and received messages will appear here</small>';
 ordered.forEach(e=>{
  const item=document.createElement("article");item.className="transcript-item"+(e.mine?" mine":"");
  const meta=document.createElement("div");meta.className="transcript-meta";
  const who=document.createElement("span");who.textContent=(e.name||"Radio")+(e.mine?" · YOU":"");
  const right=document.createElement("span");right.style.display="flex";right.style.alignItems="center";right.style.gap="8px";
  const tm=document.createElement("time");tm.textContent=new Date(e.t0).toLocaleTimeString();
  const play=document.createElement("button");play.type="button";play.className="message-play";play.textContent="▶ PLAY";play.onclick=()=>playMessage(e,play);
  right.append(tm,play);meta.append(who,right);
  const body=document.createElement("div");body.className="transcript-text";body.textContent=texts.get(e.key)||"Transcribing locally with Whisper…";
  item.append(meta,body);list.appendChild(item);
  if(!done.has(e.key)){
   done.add(e.key);
   queue=queue.then(async()=>{
    try{const pipe=await loadWhisper(),r=await pipe(wavFloat(e.wav),{task:"transcribe",chunk_length_s:30,stride_length_s:5});texts.set(e.key,(r.text||"").trim()||"No speech detected")}
    catch(err){texts.set(e.key,"Whisper unavailable: "+err.message)}
    drawMessages(rec.entries||[]);
   });
  }
 });
 requestAnimationFrame(()=>{list.scrollTop=list.scrollHeight;messages.scrollTop=messages.scrollHeight});
}

rec.onChange=entries=>{renderLog(entries);drawMessages(entries)};drawMessages(rec.entries||[]);
let fmWasPlaying=false,busy=false;function pauseFm(){if(audio&&!audio.paused){fmWasPlaying=true;audio.pause()}}
const oldDown=window.down;if(oldDown)window.down=function(e){pauseFm();return oldDown(e)};
setInterval(()=>{if(!window.radio)return;const f=radio.floor,active=!!(f&&(f.id!==radio.id||radio.talking));if(active&&!busy)pauseFm();if(!active&&busy&&fmWasPlaying&&audio){fmWasPlaying=false;audio.play().catch(()=>{})}busy=active},180);


const sstvProgressStyle=document.createElement("style");sstvProgressStyle.textContent=`#simpleSstvRow #sstvProgress{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font:9px Arial;color:#ffe2a8;letter-spacing:0}`;document.head.appendChild(sstvProgressStyle);
const playbackStyle=document.createElement("style");playbackStyle.textContent=`.audio-ribbon{display:flex!important;flex-direction:column!important;justify-content:center;gap:3px}.audio-ribbon .ribbon-play{font-weight:800;color:#ffe3a8;font-size:9px}.audio-ribbon.mine,.transcript-item.mine{border-color:#f5c77a88;background:#7c301c}.message-play{border:1px solid #f0cbbb88;border-radius:6px;background:#702316;color:#ffe9df;padding:3px 7px;font:800 9px Arial}.message-play.playing,.ribbon-play.playing{background:#a34a24;color:#fff}`;document.head.appendChild(playbackStyle);
const unifiedUiStyle=document.createElement("style");unifiedUiStyle.textContent=`#simpleFM{min-width:66px!important}#fmPanelClose{margin-left:auto;width:30px;height:28px;border-radius:7px;background:#641b10;border:1px solid #f0cbbb;color:#ffe7dc;font:22px Arial;line-height:1}#radioLinesDev{top:76px!important;bottom:48px!important;max-height:calc(100dvh - 132px)!important;border-radius:14px!important;box-shadow:0 12px 34px #000b!important}#radioLinesDev.open{display:block!important}#radioLinesDev h3{display:flex;align-items:center;gap:8px}#radioLinesDev .radio-tuner #radioPowerBtn{font-size:15px!important}#radioLinesDev .radio-tuner #radioPowerBtn:before{content:"FM · "}#radioLinesDev .radio-tuner #radioPowerBtn{letter-spacing:1px}#radioLinesDev .band-row button:disabled{opacity:.4;filter:grayscale(1)}#radioLinesDev .rl-row button:disabled{opacity:.45}#simpleRadioTop button:focus-visible,#simpleSstvRow button:focus-visible{outline:2px solid #ffe5a8;outline-offset:2px}`;document.head.appendChild(unifiedUiStyle);

/* BOONDOCK ECHO — clean handheld faceplate, final authoritative layout */
const approvedFaceplate=document.createElement("style");
approvedFaceplate.id="boondock-approved-faceplate";
approvedFaceplate.textContent=`
html,body{width:100%;height:100%;min-height:0;margin:0!important;padding:0!important;overflow:hidden!important;background:#8f210f!important}
body{font-family:Arial,Helvetica,sans-serif!important}
.rig{position:relative!important;width:100%!important;max-width:520px!important;height:100dvh!important;min-height:0!important;margin:0 auto!important;padding:8px 12px calc(58px + env(safe-area-inset-bottom))!important;display:flex!important;flex-direction:column!important;gap:7px!important;overflow:hidden!important;border:2px solid #e9c8b8!important;border-radius:0!important;background:linear-gradient(180deg,#a9361b 0%,#92220f 55%,#7b1c0d 100%)!important;box-shadow:inset 0 0 0 5px #ffffff18!important}
.rig:before,.rig:after{display:none!important}
.brand{display:none!important}
#simpleRadioTop{order:0!important;display:flex!important;flex:0 0 42px!important;min-height:42px!important;align-items:center!important;justify-content:space-between!important;gap:7px!important;padding:0 3px!important}
#simpleRadioTop .simple-top-left{display:flex!important;align-items:center!important;gap:9px!important;min-width:0!important;flex:1!important}
#radioPower{height:34px!important;min-width:68px!important;padding:0 9px!important;border:1px solid #f4d3c3!important;border-radius:18px!important;background:linear-gradient(#572016,#2b100b)!important;color:#ffeadf!important;font:900 10px Arial!important}
#radioPower.is-on{background:linear-gradient(#f5c35e,#a95c1a)!important;color:#32140b!important}
.simple-channel{min-width:0!important;max-width:none!important;flex:1!important;overflow:hidden!important;white-space:nowrap!important;text-overflow:ellipsis!important;color:#ffe6da!important;font:800 11px Arial!important;letter-spacing:1px!important}
#simpleRadioTop .leds{display:flex!important;align-items:center!important;gap:5px!important}
.led{font:800 8px Arial!important;color:#f4d8cc!important}
.led i{width:10px!important;height:10px!important}
#simpleRadioTop>div:last-child{display:flex!important;align-items:center!important;gap:5px!important}
#simpleSkin{display:none!important}
#simpleClose{width:32px!important;height:32px!important;flex:0 0 32px!important;border-radius:50%!important;background:#57180f!important;color:#fff!important;font:23px Arial!important}
.lcd{order:1!important;flex:0 0 auto!important;margin:0!important;padding:9px 12px!important;border:4px solid #4b2118!important;border-radius:15px!important;background:linear-gradient(180deg,#35170f,#160b08)!important;color:#f7d9cb!important;box-shadow:inset 0 0 18px #000,0 2px 8px #0005!important;text-shadow:none!important}
.lcd .row{font:12px Arial!important;color:#e8c9bb!important}
.lcd .freq{margin:7px 0!important;font:900 clamp(28px,7vw,43px) Orbitron,Arial,sans-serif!important;letter-spacing:2px!important;color:#f5d8cb!important;text-shadow:0 0 10px #f2b9a0!important}
#st{min-height:17px!important;font:13px Arial!important;color:#f4d4c7!important}
.lcd .meter{display:none!important}
#nm{order:2!important;display:block!important;flex:0 0 48px!important;width:min(100%,390px)!important;height:48px!important;min-height:48px!important;margin:0 auto!important;padding:7px 12px!important;border:2px solid #bd8978!important;border-radius:15px!important;background:#551b12!important;color:#fff!important;text-align:center!important;font:18px Arial!important}
#simplePttDock{order:3!important;display:flex!important;flex:1 1 0!important;min-height:0!important;width:100%!important;align-items:center!important;justify-content:center!important;margin:0!important;padding:3px 0!important}
#simplePttDock #ptt{display:block!important;width:min(68vw,42dvh,420px)!important;height:min(68vw,42dvh,420px)!important;min-width:210px!important;min-height:210px!important;max-width:420px!important;max-height:420px!important;aspect-ratio:1/1!important;flex:0 1 auto!important;margin:0 auto!important;border:7px solid #542016!important;border-radius:50%!important;background:radial-gradient(circle at 36% 27%,#ffb18e 0%,#f46a3e 38%,#d83b1d 72%,#8d210f 100%)!important;box-shadow:0 0 0 4px #f2d1c2,0 10px 24px #3b100a99,inset 0 -13px 22px #70200e88,inset 0 5px 15px #ffffff55!important;color:#fff4ed!important;text-shadow:0 2px 3px #6a1b0c!important;font:900 26px Orbitron,Arial,sans-serif!important;letter-spacing:3px!important;touch-action:none!important}
#simplePttDock #ptt.on{background:radial-gradient(circle at 36% 27%,#ffc1a8,#f12e20 55%,#8b0906)!important}
#simplePttDock #ptt.busy{background:radial-gradient(circle at 36% 27%,#ffe5a0,#e99b22 55%,#81500c)!important}
#simplePttDock .hint{display:none!important}
#main{display:none!important;height:0!important;min-height:0!important;flex:0 0 0!important;margin:0!important;padding:0!important}
#simpleMessages{order:4!important;display:flex!important;flex:1 1 150px!important;width:100%!important;height:auto!important;min-height:110px!important;max-height:none!important;margin:0 0 2px!important;padding:12px!important;gap:7px!important;overflow:hidden!important;border:1px solid #d8a18c!important;border-radius:18px!important;background:#5b1b11eF!important;color:#fff0e8!important}
.ribbon-head,.transcript-head{font:800 10px Arial!important;letter-spacing:1px!important;color:#f7d8ca!important}
#recentAudioRibbons{min-height:40px!important;flex:0 0 auto!important}
#simpleTranscriptList{flex:1 1 auto!important;min-height:0!important;overflow:auto!important}
.transcript-item{font:12px/1.4 Arial!important}
.transcript-meta{color:#f1c6b5!important}
.transcript-text{color:#fff2eb!important}
.message-play{background:#702316!important;color:#ffe9df!important}
#simpleSstvGallery{display:none!important}
#simpleSstvRow{position:fixed!important;left:12px!important;bottom:calc(54px + env(safe-area-inset-bottom))!important;z-index:24!important;width:1px!important;height:1px!important;overflow:hidden!important;opacity:0!important;pointer-events:none!important}
#simpleMore,#simpleFM{position:fixed!important;z-index:50!important;bottom:calc(9px + env(safe-area-inset-bottom))!important;width:auto!important;height:42px!important;min-width:116px!important;padding:0 18px!important;border:1px solid #f2d0c1!important;border-radius:24px!important;background:#5b1a10!important;color:#ffeadf!important;box-shadow:0 3px 9px #0006!important;font:800 11px Arial!important;letter-spacing:.4px!important}
#simpleMore{left:14px!important}
#simpleFM{right:14px!important;left:auto!important;transform:none!important}
#simpleMoreDrawer{position:fixed!important;z-index:55!important;left:12px!important;top:58px!important;bottom:auto!important;width:min(290px,calc(100vw - 24px))!important;max-height:calc(100dvh - 130px)!important;overflow:auto!important;border:1px solid #e8c1af!important;border-radius:14px!important;background:#57190f!important;color:#ffeadf!important;box-shadow:0 12px 30px #0009!important}
#simpleMoreDrawer.open{display:block!important}
#radioLinesDev{display:block!important;position:fixed!important;z-index:60!important;left:0!important;right:0!important;top:auto!important;bottom:0!important;width:100%!important;height:min(72dvh,620px)!important;max-height:72dvh!important;margin:0!important;padding:14px 12px calc(64px + env(safe-area-inset-bottom))!important;overflow:auto!important;border:1px solid #e8c1af!important;border-bottom:0!important;border-radius:20px 20px 0 0!important;background:#42170f!important;box-shadow:0 -12px 32px #000a!important;transform:translateY(105%)!important;visibility:hidden!important;transition:transform .28s ease,visibility .28s ease!important}
#radioLinesDev.open{display:block!important;transform:translateY(0)!important;visibility:visible!important}
#radioLinesDev h3{display:flex!important;align-items:center!important;gap:8px!important;color:#ffe0cf!important}
#fmPanelClose{margin-left:auto!important}
#sstvP,#locp,.panel:has(#us),.panel:has(#log),#net{display:none!important}
@media(max-height:700px){
 .rig{gap:4px!important;padding-top:5px!important}
 #simpleRadioTop{flex-basis:35px!important;min-height:35px!important}
 .lcd{padding:6px 9px!important}
 .lcd .freq{font-size:clamp(24px,6vw,34px)!important;margin:3px 0!important}
 #nm{flex-basis:40px!important;height:40px!important;min-height:40px!important;font-size:16px!important}
 #simplePttDock #ptt{width:min(61vw,34dvh,340px)!important;height:min(61vw,34dvh,340px)!important;min-width:190px!important;min-height:190px!important}
 #simpleMessages{min-height:90px!important}
}
@media(max-width:380px){
 #simpleRadioTop .simple-channel{font-size:9px!important;letter-spacing:.3px!important}
 #radioPower{min-width:58px!important}
 #simpleMore,#simpleFM{min-width:100px!important;height:38px!important}
}
`;
document.head.appendChild(approvedFaceplate);


/* Keep call-sign and PTT as separate, visible faceplate rows; preserve a tappable power switch. */
const powerFixStyle=document.createElement("style");
powerFixStyle.textContent=`
#simpleRadioTop,#simpleRadioTop *{pointer-events:auto!important}
#radioPower{position:relative!important;z-index:80!important;pointer-events:auto!important;touch-action:manipulation!important;cursor:pointer!important}
#nm{position:relative!important;z-index:5!important;order:2!important;display:block!important;flex:0 0 48px!important;width:min(100%,390px)!important;height:48px!important;min-height:48px!important;margin:0 auto!important}
#simplePttDock{order:3!important;position:relative!important;z-index:4!important}
`;
document.head.appendChild(powerFixStyle);

if(typeof window.render==="function")window.render();
setInterval(()=>{const powered=!!(window.radio&&radio.name);if(powerBtn&&!powerBtn.disabled&&radioPowered&&!powered)setRadioPower(false);if(!radioPowered&&ptt.textContent!=="POWER ON FIRST")ptt.textContent="POWER ON FIRST";if(powered&&radioPowered&&!holding&&!granted&&!(radio.floor&&radio.floor.id!==radio.id))ptt.textContent="HOLD TO TALK"},500);
})();