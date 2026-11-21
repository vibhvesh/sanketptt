
(()=>{
 const stations={
  bbcworld:{name:"BBC World Service · International English",url:"https://stream.live.vc.bbcmedia.co.uk/bbc_world_service"},
  wnyc:{name:"WNYC 93.9 · USA English",url:"https://fm939.wnyc.org/wnycfm"},
  wfmu:{name:"WFMU Freeform · USA",url:"https://stream0.wfmu.org/freeform-128k.mp3"},
  kcrw24:{name:"KCRW Eclectic24 · USA",url:"https://kcrw.streamguys1.com/kcrw_192k_mp3_e24_internet_radio"},
  rteradio1:{name:"RTÉ Radio 1 · Ireland English",url:"https://www.rte.ie/manifests/radio1.m3u8"},
  rte2fm:{name:"RTÉ 2FM · Ireland English",url:"https://www.rte.ie/manifests/2fm.m3u8"},
  rternag:{name:"RTÉ Raidió na Gaeltachta · Irish",url:"https://www.rte.ie/manifests/rnag.m3u8"},

  vividh:{name:"AIR Vividh Bharati",url:"https://radio.wavespb.com/live/146ed6ec6dea5a24/146ed6ec6dea5a24.m3u8"},
  fmgold:{name:"AIR FM Gold Delhi",url:"https://d3r9rhourdc02u.cloudfront.net/assets/radio/airdelhi03/air003_Auto.m3u8"},
  news:{name:"AIR Live News 24x7",url:"https://d3r9rhourdc02u.cloudfront.net/assets/radio/airdelhi01/air001_Auto.m3u8"},
  rainbowdelhi:{name:"AIR FM Rainbow Delhi",url:"https://d3r9rhourdc02u.cloudfront.net/assets/radio/airdelhi02/air002_Auto.m3u8"},
  indraprastha:{name:"AIR Indraprastha Delhi",url:"https://d3r9rhourdc02u.cloudfront.net/assets/radio/airdelhi06/air006_Auto.m3u8"},
  vbsdelhi:{name:"AIR VBS Delhi",url:"https://d3r9rhourdc02u.cloudfront.net/assets/radio/airdelhi04/air004_Auto.m3u8"},
  aaradhana:{name:"Akashvani Aaradhana",url:"https://d3r9rhourdc02u.cloudfront.net/assets/radio/airdelhi05/air005_Auto.m3u8"},
  vadodara:{name:"Akashvani Vadodara",url:"https://radio.wavespb.com/live/e1c63b2c2b58921f/e1c63b2c2b58921f.m3u8"},
  ahmedabad:{name:"VBS Ahmedabad",url:"https://radio.wavespb.com/live/983903b6acb669f3/983903b6acb669f3.m3u8"},
  godhra:{name:"Akashvani Godhra",url:"https://radio.wavespb.com/live/3fa69e2c950b70e8/3fa69e2c950b70e8.m3u8"},
  bhuj:{name:"Akashvani Bhuj",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio195/playlist.m3u8"},
  rajkot:{name:"Akashvani Rajkot",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio155/playlist.m3u8"},
  vbsrajkot:{name:"VBS Rajkot",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio156/playlist.m3u8"},
  surat:{name:"Akashvani Surat",url:"https://radio.wavespb.com/live/fc6ce69c53a3d739/fc6ce69c53a3d739.m3u8"},
  patna:{name:"Akashvani Patna",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio087/playlist.m3u8"},
  rainbowpatna:{name:"FM Rainbow Patna",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio252/playlist.m3u8"},
  vbspatna:{name:"VBS Patna",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio251/playlist.m3u8"},
  purnia:{name:"Akashvani Purnia",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio147/playlist.m3u8"},
  bhagalpur:{name:"Akashvani Bhagalpur",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio292/playlist.m3u8"},
  darbhanga:{name:"Akashvani Darbhanga",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio160/playlist.m3u8"},
  bhopal:{name:"Akashvani Bhopal",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio146/playlist.m3u8"},
  indore:{name:"VBS Indore",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio241/playlist.m3u8"},
  jabalpur:{name:"Akashvani Jabalpur",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio167/playlist.m3u8"},
  jabalpurfm:{name:"Akashvani Jabalpur FM",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio240/playlist.m3u8"},
  rewa:{name:"Akashvani Rewa",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio225/playlist.m3u8"},
  balaghat:{name:"Akashvani Balaghat",url:"https://radio.wavespb.com/live/971411cf78525ddb/971411cf78525ddb.m3u8"},
  betul:{name:"Akashvani Betul",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio108/playlist.m3u8"},
  khandwa:{name:"Akashvani Khandwa",url:"https://radio.wavespb.com/live/76260628792d0528/76260628792d0528.m3u8"},
  sagar:{name:"Akashvani Sagar",url:"https://radio.wavespb.com/live/b60eae3df5a29197/b60eae3df5a29197.m3u8"},
  jaipur:{name:"Akashvani Jaipur",url:"https://radio.wavespb.com/live/ad081b4086797344/ad081b4086797344.m3u8"},
  vbsjaipur:{name:"VBS Jaipur",url:"https://radio.wavespb.com/live/72d34573791c739b/72d34573791c739b.m3u8"},
  alwar:{name:"Akashvani Alwar",url:"https://radio.wavespb.com/live/67a9516c2ccd3fd5/67a9516c2ccd3fd5.m3u8"},
  jodhpur:{name:"Akashvani Jodhpur",url:"https://radio.wavespb.com/live/520ec0fb4a9139a7/520ec0fb4a9139a7.m3u8"},
  bikaner:{name:"Akashvani Bikaner",url:"https://radio.wavespb.com/live/e2588cb0ff825cd9/e2588cb0ff825cd9.m3u8"},
  jaisalmer:{name:"Akashvani Jaisalmer",url:"https://radio.wavespb.com/live/54f9c9d68de4282b/54f9c9d68de4282b.m3u8"},
  jhalawar:{name:"Akashvani Jhalawar",url:"https://radio.wavespb.com/live/fdba5613a31b678b/fdba5613a31b678b.m3u8"},
  hisar:{name:"Akashvani Hisar",url:"https://radio.wavespb.com/live/d3f37eacc0dc6495/d3f37eacc0dc6495.m3u8"},
  rohtak:{name:"Akashvani Rohtak",url:"https://radio.wavespb.com/live/d617676f1e7ac0a1/d617676f1e7ac0a1.m3u8"},
  ranchi:{name:"Akashvani Ranchi",url:"https://radio.wavespb.com/live/66b77f1dfee894bc/66b77f1dfee894bc.m3u8"},
  vbsranchi:{name:"VBS Ranchi",url:"https://radio.wavespb.com/live/d839e1ea3f3fd644/d839e1ea3f3fd644.m3u8"},
  daman:{name:"Akashvani Daman",url:"https://radio.wavespb.com/live/c124a58382e75a46/c124a58382e75a46.m3u8"},
  simahapuri:{name:"FM Simahapuri Nellore",url:"https://radio.wavespb.com/live/8bc9175bb717c13b/8bc9175bb717c13b.m3u8"},
  rainbowvijayawada:{name:"FM Rainbow Vijayawada",url:"https://radio.wavespb.com/live/bad174fd7eac38d0/bad174fd7eac38d0.m3u8"},
  rainbowvizag:{name:"FM Rainbow Visakhapatnam",url:"https://radio.wavespb.com/live/147314c8aedf4389/147314c8aedf4389.m3u8"},
  fmitanagar:{name:"FM Arun Itanagar",url:"https://radio.wavespb.com/live/174624e09dbdcdde/174624e09dbdcdde.m3u8"},
  vbsraipur:{name:"VBS Raipur",url:"https://air.pc.cdn.bitgravity.com/air/live/pbaudio279/playlist.m3u8"},
  vbspanaji:{name:"VBS Panaji",url:"https://radio.wavespb.com/live/39dd51a3e97b19b1/39dd51a3e97b19b1.m3u8"},
  shimlafm:{name:"Akashvani Shimla FM",url:"https://radio.wavespb.com/live/66f234a8585d2fe0/66f234a8585d2fe0.m3u8"},
  rainbowranchi:{name:"FM Rainbow Ranchi",url:"https://radio.wavespb.com/live/af6f533f997d4ae1/af6f533f997d4ae1.m3u8"},
  kannadakaamanbilu:{name:"Rainbow Kannada Kaamanbilu",url:"https://d3r9rhourdc02u.cloudfront.net/assets/radio/airbang02/air034_Auto.m3u8"},
  rainbowkochi:{name:"FM Rainbow Kochi",url:"https://radio.wavespb.com/live/7df6f2a8c3c4d33b/7df6f2a8c3c4d33b.m3u8"},
  fmgoldmumbai:{name:"FM Gold Mumbai",url:"https://d3r9rhourdc02u.cloudfront.net/assets/radio/airmum01/air049_Auto.m3u8"},
  rainbowmumbai:{name:"FM Rainbow Mumbai",url:"https://d3r9rhourdc02u.cloudfront.net/assets/radio/airmum02/air050_Auto.m3u8"},
  jongphi:{name:"FM Jongphi Shillong",url:"https://radio.wavespb.com/live/989abf4a5fee9240/989abf4a5fee9240.m3u8"},
  zoawi:{name:"FM Zoawi Aizawl",url:"https://radio.wavespb.com/live/443b0a952fbbe057/443b0a952fbbe057.m3u8"},
  tragopan:{name:"FM Tragopan Kohima",url:"https://radio.wavespb.com/live/fff99886b825e2ae/fff99886b825e2ae.m3u8"},
  rainbowcuttack:{name:"FM Rainbow Cuttack",url:"https://radio.wavespb.com/live/e0ad71c249a45867/e0ad71c249a45867.m3u8"},
  rainbowjalandhar:{name:"FM Rainbow Jalandhar",url:"https://radio.wavespb.com/live/027744169f5fad66/027744169f5fad66.m3u8"},
  fmgoldchennai:{name:"FM Gold Chennai",url:"https://radio.wavespb.com/live/84ad819b3f45dc08/84ad819b3f45dc08.m3u8"},
  rainbowhyderabad:{name:"FM Rainbow Hyderabad",url:"https://radio.wavespb.com/live/3a02c5c035815bb9/3a02c5c035815bb9.m3u8"},
  ujjayanta:{name:"FM Ujjayanta Agartala",url:"https://radio.wavespb.com/live/d65912ef9829b8c9/d65912ef9829b8c9.m3u8"},
 };
 const $=id=>document.getElementById(id),audio=$("radioLineAudio"),select=$("radioStationSelect"),status=$("radioLineStatus");
 const bandButtons=[...document.querySelectorAll("[data-band]")],dial=$("tunerDial"),freq=$("tunerFrequency"),tunerName=$("tunerStationLabel"),bandLabel=$("tunerBandLabel"),favBtn=$("favoriteStation");
 let activeBand="ALL",visibleStations=[],scanBusy=false;
 const stationIds=Object.keys(stations);
 const scanBox=$("radioStationButtons"),scanProgress=$("radioScanProgress");
 const feedState={};let scanGeneration=0,scanRunning=false;
 function stationGroup(id){
  if(["bbcworld","wnyc","wfmu","kcrw24"].includes(id))return "INTERNATIONAL · ENGLISH";
  if(["rteradio1","rte2fm","rternag"].includes(id))return "INTERNATIONAL · IRELAND";
  if(["vividh","fmgold","news","rainbowdelhi","indraprastha","vbsdelhi","aaradhana"].includes(id))return "INDIA · NATIONAL";
  if(["vadodara","ahmedabad","godhra","bhuj","rajkot","vbsrajkot","surat","daman"].includes(id))return "WEST INDIA · GUJARATI";
  if(["patna","rainbowpatna","vbspatna","purnia","bhagalpur","darbhanga"].includes(id))return "BIHAR · HINDI / REGIONAL";
  if(["bhopal","indore","jabalpur","jabalpurfm","rewa","balaghat","betul","khandwa","sagar"].includes(id))return "CENTRAL INDIA · HINDI";
  if(["jaipur","vbsjaipur","alwar","jodhpur","bikaner","jaisalmer","jhalawar","hisar","rohtak"].includes(id))return "NORTH / WEST INDIA · REGIONAL";
  if(["ranchi","vbsranchi","simahapuri","rainbowvijayawada","rainbowvizag","fmitanagar","vbsraipur","vbspanaji","shimlafm","rainbowranchi","kannadakaamanbilu","rainbowkochi","fmgoldmumbai","rainbowmumbai","jongphi","zoawi","tragopan","rainbowcuttack","rainbowjalandhar","fmgoldchennai","rainbowhyderabad","ujjayanta"].includes(id))return "OTHER INDIAN LANGUAGES";
  return "OTHER VERIFIED STATIONS";
 }
 function populateVerifiedSelect(){
  const current=select.value,groups={};
  const good=stationIds.filter(id=>feedState[id]==="green");
  good.forEach(id=>{const g=stationGroup(id);(groups[g]||(groups[g]=[])).push(id)});
  select.innerHTML="";
  if(!good.length){const o=document.createElement("option");o.value="";o.textContent=scanRunning?"Scanning for working stations…":"No verified stations yet — scan again";select.appendChild(o);select.disabled=true;return}
  Object.keys(groups).forEach(group=>{const og=document.createElement("optgroup");og.label=group;groups[group].sort((a,b)=>stations[a].name.localeCompare(stations[b].name)).forEach(id=>{const o=document.createElement("option");o.value=id;o.textContent=stations[id].name;og.appendChild(o)});select.appendChild(og)});
  select.disabled=false;select.value=good.includes(current)?current:good[0];
 }
 function renderStationButtons(){
  const ids=stationIds.filter(id=>feedState[id]==="green").sort((a,b)=>stations[a].name.localeCompare(stations[b].name));
  scanBox.innerHTML="";
  ids.forEach(id=>{const btn=document.createElement("button");btn.type="button";btn.className="station-chip green"+(select.value===id?" selected":"");btn.title=stations[id].name+" · verified working";const led=document.createElement("i"),label=document.createElement("span");label.textContent=stations[id].name;btn.append(led,label);btn.addEventListener("click",()=>{chooseStation(id,false);renderStationButtons();playRadio()});scanBox.appendChild(btn)});
  if(!ids.length){const note=document.createElement("div");note.className="station-empty";note.textContent=scanRunning?"Testing feeds; only verified working stations will appear here…":"No green feeds yet. Run SCAN NOW to verify streams.";scanBox.appendChild(note)}
  populateVerifiedSelect();
 }
 function classifyError(d){
  const code=Number(d&&d.response&&d.response.code||0);
  if(code===404||code===410)return "red";
  return "yellow";
 }
 function probeStation(id,generation){
  return new Promise(resolve=>{
   const url=stations[id].url,isHls=isHlsStream(url),media=document.createElement("audio");
   media.crossOrigin="anonymous";media.muted=true;media.preload="auto";media.playsInline=true;
   let done=false,probe=null;
   const finish=state=>{if(done)return;done=true;clearTimeout(timer);try{if(probe)probe.destroy()}catch(e){}try{media.pause();media.removeAttribute("src");media.load()}catch(e){}resolve(state)};
   const timer=setTimeout(()=>finish("yellow"),12000);
   const checkPlayback=()=>{if(done)return;if(!media.paused&&media.readyState>=2&&media.currentTime>0.75){finish("green");return}setTimeout(checkPlayback,250)};
   media.addEventListener("error",()=>finish("yellow"),{once:true});
   if(isHls&&window.Hls&&Hls.isSupported()){
    probe=new Hls({enableWorker:true,lowLatencyMode:true,maxBufferLength:4,manifestLoadingTimeOut:6000,fragLoadingTimeOut:6000});
    probe.on(Hls.Events.MANIFEST_PARSED,()=>{media.play().then(checkPlayback).catch(()=>finish("yellow"))});
    probe.on(Hls.Events.ERROR,(_,d)=>{if(d&&d.fatal)finish(classifyError(d))});
    try{probe.loadSource(url);probe.attachMedia(media)}catch(e){finish("yellow")}
   }else{
    try{media.src=url;media.load();media.play().then(checkPlayback).catch(()=>finish("yellow"))}catch(e){finish("yellow")}
   }
  });
 }
 async function scanAllStations(){
  if(scanRunning)return;scanRunning=true;$("radioScanNow").disabled=true;const generation=++scanGeneration;
  const ids=stationIds.slice();let done=0,green=0,yellow=0,red=0;
  ids.forEach(id=>{feedState[id]="checking"});renderStationButtons();
  scanProgress.textContent="Checking "+ids.length+" streams in the background…";
  let cursor=0;
  async function worker(){while(cursor<ids.length&&generation===scanGeneration){const id=ids[cursor++];const state=await probeStation(id,generation);if(generation!==scanGeneration)return;feedState[id]=state;done++;if(state==="green")green++;else if(state==="yellow")yellow++;else red++;renderStationButtons();scanProgress.textContent="Scanned "+done+"/"+ids.length+" · Green "+green+" · Yellow "+yellow+" · Red "+red;}}
  await Promise.all([worker(),worker(),worker()]);
  if(generation===scanGeneration){scanRunning=false;$("radioScanNow").disabled=false;populateVerifiedSelect();renderStationButtons();scanProgress.textContent="Scan complete · "+green+" verified and listed · "+yellow+" uncertain (hidden) · "+red+" unavailable (hidden). Auto-rescan in 5 minutes."}
 }

 const isFM=id=>/fm|rainbow|vividh|vbs|indraprastha|aaradhana/i.test(stations[id].name);
 function refreshTuner(){
  visibleStations=stationIds.filter(id=>activeBand==="ALL"||(activeBand==="FM"&&isFM(id)));
  if(activeBand==="AM"||activeBand==="SW")visibleStations=[];
  const ix=Math.max(0,visibleStations.indexOf(select.value));
  dial.max=Math.max(0,visibleStations.length-1);dial.value=ix;
  bandLabel.textContent=activeBand==="ALL"?"ALL INTERNET RADIO STREAMS":activeBand+" BAND";
  $("tuneDown").disabled=$("tuneUp").disabled=!visibleStations.length;$("scanDown").disabled=$("scanUp").disabled=!visibleStations.length||scanBusy;
  if(!visibleStations.length){freq.textContent=activeBand==="AM"?"AM — NO FEEDS":activeBand==="SW"?"SW — NO FEEDS":"SCAN FOR STATIONS";tunerName.textContent="No verified "+activeBand+" stream source loaded";favBtn.textContent="☆ SAVE";favBtn.disabled=true;return}favBtn.disabled=false;
  const n=ix+1;freq.textContent=activeBand==="FM"?(87.5+((n-1)*0.2)%20).toFixed(1)+" MHz":"CH "+String(n).padStart(2,"0");
  tunerName.textContent=stations[visibleStations[ix]].name;
  updateFavorite();
 }
 function updateFavorite(){let f=[];try{f=JSON.parse(localStorage.getItem("sanketRadioFavorites")||"[]")}catch(e){}favBtn.textContent=f.includes(select.value)?"★ SAVED":"☆ SAVE"}
 function chooseStation(id,autoplay){if(!id||!stations[id])return;select.value=id;refreshTuner();say("Tuned to "+stations[id].name+(autoplay?" · scanning for stream":""));if(autoplay)playRadio()}
 function stepTune(dir,scan){if(!visibleStations.length){say("No verified "+activeBand+" stream sources are loaded yet.");return}let i=visibleStations.indexOf(select.value);if(i<0)i=dir>0?-1:0;const next=(i+dir+visibleStations.length)%visibleStations.length;chooseStation(visibleStations[next],scan)}
 function setBand(b){activeBand=b;bandButtons.forEach(x=>x.classList.toggle("active",x.dataset.band===b));if(b==="AM"||b==="SW"){refreshTuner();$("tunerNote").textContent="No verified "+b+" internet stream feeds are configured yet. The player cannot tune physical AM/SW frequencies without a radio receiver.";return}if(!visibleStations.includes(select.value))select.value=visibleStations[0]||"vividh";refreshTuner();$("tunerNote").textContent="Internet stream tuner: scan moves through the available "+b+" station list. Frequencies shown are dial positions, not verified terrestrial broadcast frequencies."}
 bandButtons.forEach(x=>x.addEventListener("click",()=>setBand(x.dataset.band)));
 $("tuneDown").addEventListener("click",()=>stepTune(-1,false));$("tuneUp").addEventListener("click",()=>stepTune(1,false));
 $("scanDown").addEventListener("click",()=>scanBand(-1));$("scanUp").addEventListener("click",()=>scanBand(1));
 dial.addEventListener("input",()=>{if(visibleStations[+dial.value])chooseStation(visibleStations[+dial.value],false)});
 favBtn.addEventListener("click",()=>{if(!select.value||!stations[select.value])return;let f=[];try{f=JSON.parse(localStorage.getItem("sanketRadioFavorites")||"[]")}catch(e){}if(f.includes(select.value))f=f.filter(x=>x!==select.value);else f.push(select.value);localStorage.setItem("sanketRadioFavorites",JSON.stringify(f));updateFavorite();say((f.includes(select.value)?"Saved ":"Removed ")+stations[select.value].name+(f.includes(select.value)?" to favorites":" from favorites"))});
 try{const last=localStorage.getItem("sanketRadioLastStation");if(last&&stations[last])select.value=last}catch(e){}
 refreshTuner();

 let hls=null,mediaSource=null,processor=null,mute=null,bot=null,bridging=false,streamReady=false;
 const powerBtn=$("radioPowerBtn"),powerLed=$("radioPowerLed"),playLed=$("radioPlayLed"),signalLed=$("radioSignalLed"),radioBars=$("radioBars");
 const meterBars=Array.from({length:24},()=>{const b=document.createElement("b");radioBars.appendChild(b);return b});
 let meterCtx=null,meterAnalyser=null,meterSource=null,meterData=null,meterFrame=0,meterConnected=false;
 function radioPowerState(on){powerBtn.classList.toggle("on",on);powerBtn.textContent=on?"STOP FM":"PLAY FM";powerBtn.setAttribute("aria-pressed",String(on));powerLed.classList.toggle("on",on);playLed.classList.toggle("on",on&&streamReady);signalLed.classList.toggle("on",on&&streamReady&&!audio.paused)}
 function animateRadioMeter(){if(meterAnalyser&&meterData&&streamReady&&!audio.paused){meterAnalyser.getByteFrequencyData(meterData);meterBars.forEach((b,i)=>{const v=meterData[Math.floor(i*meterData.length/meterBars.length)]||0;b.style.height=Math.max(5,Math.round(v/255*100))+"%"});signalLed.classList.toggle("on",meterData.some(v=>v>8))}else{meterBars.forEach(b=>b.style.height="5%");signalLed.classList.remove("on")}meterFrame=requestAnimationFrame(animateRadioMeter)}
 animateRadioMeter();
 async function attachRadioMeter(){try{const AudioCtor=window.AudioContext||window.webkitAudioContext;if(!AudioCtor)return;if(!meterCtx||meterCtx.state==="closed"){meterCtx=new AudioCtor();meterSource=null;meterAnalyser=null;meterConnected=false}if(!meterSource)meterSource=meterCtx.createMediaElementSource(audio);if(!meterAnalyser){meterAnalyser=meterCtx.createAnalyser();meterAnalyser.fftSize=128;meterData=new Uint8Array(meterAnalyser.frequencyBinCount)}if(!meterConnected){meterSource.connect(meterAnalyser);meterAnalyser.connect(meterCtx.destination);meterConnected=true}if(meterCtx.state==="suspended")await meterCtx.resume()}catch(e){console.warn("FM audio meter unavailable:",e)}}

 function say(t){status.textContent=t}
 audio.addEventListener("pause",()=>{playLed.classList.remove("on");signalLed.classList.remove("on")});
 audio.addEventListener("playing",()=>{if(streamReady)playLed.classList.add("on")});
 function station(){return stations[select.value]||stations.vividh}
 function cleanupStream(){if(hls){hls.destroy();hls=null}audio.pause();audio.removeAttribute("src");audio.load();streamReady=false;radioPowerState(false)}
 function isHlsStream(url){return /\.m3u8(?:$|[?#])/i.test(url)}
 async function playRadio(){
  const st=station();cleanupStream();audio.crossOrigin="anonymous";
  say("Tuning "+st.name+"…");
  return await new Promise(resolve=>{
   let settled=false,timer=setTimeout(()=>finish(false,"No stream response from "+st.name),12000);
   function finish(ok,msg){if(settled)return;settled=true;clearTimeout(timer);if(ok){streamReady=true;try{localStorage.setItem("sanketRadioLastStation",select.value)}catch(e){}refreshTuner();radioPowerState(true)}else{streamReady=false;radioPowerState(false)}say(msg);resolve(ok)}
   if(isHlsStream(st.url)&&window.Hls&&Hls.isSupported()){
    hls=new Hls({enableWorker:true,lowLatencyMode:true});hls.loadSource(st.url);hls.attachMedia(audio);
    hls.on(Hls.Events.MANIFEST_PARSED,async()=>{try{await audio.play();finish(true,"Playing "+st.name+" · station remembered")}catch(e){finish(false,"Playback blocked for "+st.name+": "+e.message)}});
    hls.on(Hls.Events.ERROR,(_,d)=>{if(d&&d.fatal)finish(false,"No playable signal: "+st.name+" · "+(d.details||d.type))});
   }else{
    audio.src=st.url;audio.load();audio.play().then(()=>finish(true,"Playing "+st.name+" · station remembered")).catch(e=>finish(false,"Unable to play "+st.name+": "+e.message));
   }
  });
 }
 async function scanBand(dir){
  if(scanBusy)return; if(!visibleStations.length){say("No "+activeBand+" stream sources are available to scan.");return}
  scanBusy=true;refreshTuner();const start=visibleStations.indexOf(select.value);let i=start<0?(dir>0?-1:0):start;
  say("Scanning "+activeBand+" band for a playable stream…");
  for(let n=0;n<visibleStations.length;n++){
   i=(i+dir+visibleStations.length)%visibleStations.length;
   chooseStation(visibleStations[i],false);
   let ok=false;try{ok=await playRadio()}catch(e){say("Could not test "+station().name+": "+e.message)}
   if(ok){say("Signal found · "+station().name+" · saved as last station");scanBusy=false;refreshTuner();return}
  }
  say("Scan complete: no playable stream found in "+activeBand+". Try another band or scan later.");scanBusy=false;refreshTuner();
 }
 function stopBridge(){
  const wasActive=bridging||!!bot;bridging=false;
  
  if(bot){try{bot.leave()}catch(e){}bot=null}
  $("radioBridgeBtn").disabled=!window.radioPowered;$("radioBridgeStopBtn").disabled=true;
  if(wasActive)say("Radio bridge stopped. PTT has priority; FM playback remains local.");
 }
 window.__sanketRadioPreempt=function(claimPTT){
  if(bridging||bot){stopBridge();setTimeout(claimPTT,220)}else claimPTT();
 };
 async function setupAudioGraph(){
  if(!window.radioPowered||!window.radio||!window.radio.name)throw new Error("Power on Boondock Echo PTT first.");
  await attachRadioMeter();
  if(!meterCtx||meterCtx.state==="closed"||!meterSource)throw new Error("FM audio graph is unavailable.");
  if(!processor){
   processor=meterCtx.createScriptProcessor(4096,1,1);
   mute=meterCtx.createGain();mute.gain.value=0;
   meterSource.connect(processor);processor.connect(mute);mute.connect(meterCtx.destination);
   processor.onaudioprocess=e=>{
    if(!bridging||!bot||!bot.talking||!bot.c||!bot.c.connected)return;
    const input=e.inputBuffer.getChannelData(0),ratio=meterCtx.sampleRate/(window.RATE||12000);
    const n=Math.floor(input.length/ratio);if(!n)return;
    const pcm=new Int16Array(n);
    for(let i=0;i<n;i++){const v=input[Math.floor(i*ratio)];pcm[i]=Math.max(-1,Math.min(1,v))*32767}
    bot.sendAudio(pcm);
   };
  }
 }
 async function bridge(){
  if(!window.radioPowered||!window.radio||!window.mqtt||!window.Radio) {say("Power on Boondock Echo PTT first.");return}
  if(!window.ac||ac.state==="closed"){say("Power on / join PTT first, then enable audio.");return}
  if(!streamReady||audio.paused){await playRadio();say("Wait until the radio is playing, then tap BRIDGE INTO PTT CHANNEL.");return}
  if(bot)stopBridge();
  try{await setupAudioGraph()}catch(e){say(e.message);return}
  const st=station();bot=new Radio(mqtt,{ch:radio.ch,on:(kind,value)=>{if(kind==="net")say("Radio gateway relay: "+value)}});
  bot.join("RADIO · "+st.name);
  say("Requesting the floor on PTT channel "+radio.ch+"…");
  bot.claim(ok=>{
   if(!ok){say("PTT channel is busy. Stop the current transmission and try again.");if(bot){bot.leave();bot=null}return}
   bridging=true;$("radioBridgeBtn").disabled=true;$("radioBridgeStopBtn").disabled=false;
   say("LIVE BRIDGE · "+st.name+" → PTT channel "+radio.ch+" · RX-only radio source");
  });
 }
 window.sanketImportRadioDirectory=async function(sourceUrl){
  const url=String(sourceUrl||"").trim();
  if(!/^https:\/\//i.test(url))throw new Error("Please use a public HTTPS directory or playlist URL.");
  let raw="",rows=[];
  if(/\\.(?:m3u8?|mp3|aac|ogg)(?:$|[?#])/i.test(url)){
   rows=[{name:new URL(url).hostname+" radio",url:url}];
  }else{
   const response=await fetch(url,{mode:"cors",cache:"no-store"});
   if(!response.ok)throw new Error("Directory returned HTTP "+response.status);
   raw=await response.text();
  }
  try{
   const data=JSON.parse(raw);
   rows=Array.isArray(data)?data:(data.stations||data.data||data.items||[]);
   if(!Array.isArray(rows)&&data&&typeof data==="object")rows=Object.values(data);
  }catch(e){}
  if(!rows.length&&/^\s*#EXTM3U/i.test(raw)){
   if(/#EXT-X-(TARGETDURATION|STREAM-INF|MEDIA-SEQUENCE)/i.test(raw))rows=[{name:new URL(url).hostname+" stream",url:url}];
   else{
    let name="";
    raw.split(/\r?\n/).forEach(line=>{
     line=line.trim();if(line.startsWith("#EXTINF")){name=(line.split(",").slice(1).join(",")||"Radio stream").trim()}
     else if(/^https:\/\//i.test(line)){rows.push({name:name||new URL(line).hostname,url:line});name=""}
    });
   }
  }
  if(!rows.length&&/(\.pls)(?:$|[?#])/i.test(url)){
   const title=(raw.match(/Title\d+=(.*)/i)||[])[1]||"Imported radio";
   const stream=(raw.match(/File\d+=(https:\/\/\S+)/i)||[])[1];
   if(stream)rows=[{name:title,url:stream}];
  }
  if(!rows.length){
   const links=raw.match(/https:\/\/[^\s"'<>]+\.(?:m3u8?|mp3|aac|ogg)(?:\?[^\s"'<>]*)?/gi)||[];
   rows=links.map((u,i)=>({name:"Imported stream "+(i+1),url:u.replace(/[),;]+$/,"")}));
  }
  if(!rows.length&&/\.(?:m3u8?|mp3|aac|ogg)(?:$|[?#])/i.test(url))rows=[{name:new URL(url).hostname+" radio",url:url}];
  const additions=[];
  rows.forEach((row,i)=>{
   const streamUrl=String(row.stream_url||row.url||row.stream||row.src||"").trim();
   const name=String(row.name||row.station_name||row.title||row.station||("Imported radio "+(i+1))).trim();
   if(!/^https:\/\//i.test(streamUrl)||!name)return;
   if(Object.values(stations).some(st=>st.url===streamUrl))return;
   let id="custom_"+name.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"").slice(0,32)+"_"+i;
   while(stations[id])id+="_x";
   stations[id]={name:name,url:streamUrl};stationIds.push(id);feedState[id]="checking";additions.push(id);
  });
  if(!additions.length)throw new Error("No new HTTPS station streams found. Use a CORS-enabled JSON/M3U directory or a direct stream URL.");
  renderStationButtons();
  let cursor=0,good=0,uncertain=0,failed=0;
  async function worker(){while(cursor<additions.length){const id=additions[cursor++];const state=await probeStation(id,scanGeneration);feedState[id]=state;if(state==="green")good++;else if(state==="yellow")uncertain++;else failed++;renderStationButtons();}}
  await Promise.all([worker(),worker(),worker()]);
  return {added:additions.length,working:good,uncertain:uncertain,unavailable:failed};
 };
 const importBtn=$("radioDirectoryImportBtn"),importInput=$("radioDirectoryUrl"),importStatus=$("radioDirectoryImportStatus");
 if(importBtn)importBtn.addEventListener("click",async()=>{
  importBtn.disabled=true;importStatus.textContent="Reading directory and testing discovered streams…";
  try{const result=await window.sanketImportRadioDirectory(importInput.value);importStatus.textContent="Import complete · "+result.working+" working · "+result.uncertain+" uncertain · "+result.unavailable+" unavailable. Working stations have been added to the station buttons.";say(importStatus.textContent)}
  catch(e){importStatus.textContent="Import failed: "+e.message+" · Some websites block browser access (CORS); use a direct JSON/M3U link or stream URL.";say(importStatus.textContent)}
  finally{importBtn.disabled=false}
 });
 $("radioScanNow").addEventListener("click",scanAllStations);
 renderStationButtons();setTimeout(scanAllStations,1200);setInterval(()=>{if(!document.hidden)scanAllStations()},300000);
  powerBtn.addEventListener("click",async()=>{if(streamReady&&!audio.paused){stopBridge();cleanupStream();say("FM playback stopped.");return}await playRadio()});
 $("radioBridgeStopBtn").disabled=true;$("radioBridgeBtn").disabled=!window.radioPowered;
 window.addEventListener("boondock:radio-state",e=>{const on=!!(e.detail&&e.detail.powered);if(!on&&bridging)stopBridge();$("radioBridgeBtn").disabled=!on||bridging;$("radioBridgeStopBtn").disabled=!bridging});
 $("radioBridgeBtn").addEventListener("click",bridge);
 $("radioBridgeStopBtn").addEventListener("click",stopBridge);
 select.addEventListener("change",()=>{if(bridging)stopBridge();cleanupStream();refreshTuner();renderStationButtons();say("Selected "+station().name+". Press PLAY FM to listen.")});
 window.addEventListener("beforeunload",()=>{stopBridge();cleanupStream();cancelAnimationFrame(meterFrame);if(meterCtx&&meterCtx.state!=="closed")meterCtx.close()});
})();
