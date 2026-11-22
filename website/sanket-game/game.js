const SERVER="https://stlu-001.sanketptt.com";let BUDGET=1500;const HISTORY_KEY="sanket_prisha_shopper_history_v1";
const CATEGORIES=[
{title:"🍎 Fruits",subtitle:"Fresh and juicy picks",items:[
["apple","Red Apple","1 piece",25,["apple"],"🍎","photo-1560806887-1e4cd0b6cbd6"],
["banana","Banana","1 dozen",50,["banana"],"🍌","photo-1571771894821-ce9b6c11b08e"],
["orange","Sweet Orange","1 kg",80,["orange"],"🍊","photo-1547514701-42782101795e"],
["mango","Mango","1 kg",120,["mango"],"🥭","photo-1553279768-865429fa0078"],
["grapes","Green Grapes","500 g",65,["grape","grapes"],"🍇","photo-1537640538966-79f369143f8f"]]},
{title:"🥕 Vegetables",subtitle:"Colourful everyday vegetables",items:[
["tomato","Tomato","1 kg",40,["tomato"],"🍅","photo-1546094096-0df4bcaaa337"],
["potato","Potato","1 kg",35,["potato"],"🥔","photo-1518977676601-b53f82aba655"],
["onion","Red Onion","1 kg",45,["onion"],"🧅","photo-1518977676601-b53f82aba655"],
["carrot","Carrot","500 g",30,["carrot"],"🥕","photo-1445282768818-728615cc910a"],
["cucumber","Cucumber","500 g",25,["cucumber"],"🥒","photo-1604977042946-1eecc30f269e"]]},
{title:"🥛 Dairy & Bakery",subtitle:"Milk, cheese and breakfast favourites",items:[
["milk","Fresh Milk","1 litre",60,["milk"],"🥛","photo-1563636619-e9143da7973b"],
["curd","Plain Curd","400 g",35,["curd","yogurt","yoghurt"],"🥣","photo-1488477181946-6428a0291777"],
["butter","Butter","100 g",55,["butter"],"🧈","photo-1589985270826-4b7bb135bc9d"],
["cheese","Cheese Slices","1 pack",90,["cheese"],"🧀","photo-1486297678162-eb2a19b0a32d"],
["bread","Brown Bread","1 loaf",40,["bread"],"🍞","photo-1509440159596-0249088772ff"]]},
{title:"🌾 Rice & Pantry",subtitle:"Kitchen basics for every home",items:[
["rice","White Rice","1 kg",80,["rice"],"🍚","photo-1586201375761-83865001e31c"],
["atta","Whole Wheat Flour (Atta)","1 kg",45,["atta","flour","wheat"],"🌾","photo-1574323347407-f5e1ad6d020b"],
["oil","Cooking Oil","1 litre",150,["oil"],"🫗","photo-1474979266404-7eaacbcd87c5"],
["sugar","White Sugar","1 kg",50,["sugar"],"🧂","photo-1581441363689-1f3c3c414635"],
["dal","Toor Dal","1 kg",140,["dal","lentil"],"🫘","photo-1515543904379-3d757"]]},
{title:"🍪 Snacks & Drinks",subtitle:"Little treats and tea-time snacks",items:[
["biscuits","Marie Biscuits","1 pack",30,["biscuit","biscuits"],"🍪","photo-1558961363-fa8fdf82db35"],
["tea","Black Tea","250 g",120,["tea"],"🍵","photo-1544787219-7f47ccb76574"],
["juice","Orange Juice","1 litre",90,["juice"],"🧃","photo-1621506289937-a8e4df240d0b"],
["chips","Potato Chips","1 pack",20,["chips"],"🥔","photo-1566478989037-eec170784d0b"],
["chocolate","Milk Chocolate","1 bar",45,["chocolate"],"🍫","photo-1511381939415-e44015466834"]]}
,{title:"🏍️ Bikes & Cars",subtitle:"Dream rides for your big shopping challenge",items:[
["bicycle","Kids Bicycle","1 bicycle",12000,["bicycle","cycle"],"🚲","photo-1485965120184-e220f721d03e"],
["scooter","Scooter","1 scooter",85000,["scooter"],"🛵","photo-1558981806-ec527fa84c39"],
["motorbike","Motorbike","1 bike",125000,["motorbike","motorcycle","bike"],"🏍️","photo-1558981403-c5f9899a28bc"],
["electricbike","Electric Bike","1 electric bike",145000,["electric bike","ebike"],"⚡","photo-1558981806-ec527fa84c39"],
["hatchback","Family Hatchback Car","1 car",650000,["hatchback","car"],"🚗","photo-1492144534655-ae79c964c9d7"],
["suv","Family SUV","1 SUV",1250000,["suv","sports utility vehicle"],"🚙","photo-1519641471654-76ce0107ad1b"]
]}];
const ITEMS=CATEGORIES.flatMap(c=>c.items.map(x=>({id:x[0],name:x[1],unit:x[2],price:x[3],words:x[4],emoji:x[5],img:""})));
const $=id=>document.getElementById(id),money=n=>"₹"+Math.round(n).toLocaleString("en-IN");let player="",clips=[],rec=null,stream=null,recording=false,busy=false,selected={},page=0;
const show=id=>$(id).hidden=false,hide=id=>$(id).hidden=true;
function getHistory(){try{return JSON.parse(sessionStorage.getItem(HISTORY_KEY)||"[]")}catch{return []}}
function saveHistory(entry){try{const h=getHistory();h.unshift(entry);sessionStorage.setItem(HISTORY_KEY,JSON.stringify(h.slice(0,50)));return true}catch{return false}}
function selectedTotal(){return ITEMS.reduce((s,x)=>s+x.price*(selected[x.id]||0),0)}
function updateBudget(extra=0){const n=selectedTotal()+extra,p=Math.min(100,n/BUDGET*100),box=$("budgetBox");$("budgetValue").textContent=money(n)+" / "+money(BUDGET);$("budgetFill").style.width=p+"%";box.classList.toggle("close-to-limit",n>=BUDGET*.9&&n<=BUDGET);box.classList.toggle("over-limit",n>BUDGET);$("budgetHint").textContent=n===BUDGET-1?"😲 WOW! Just ₹1 left! So close!":n>=BUDGET*.9&&n<=BUDGET?"🎯 Almost there! Stay under your budget!":n>BUDGET?"🙈 Oops! That's over your budget. Remove something!":"Pick items and watch your basket fill up!"}
function renderProducts(){const holder=$("marketPages");holder.innerHTML=CATEGORIES.map((cat,i)=>'<section class="market-page" data-page="'+i+'">'+cat.items.map(x=>{const q=selected[x[0]]||0;const svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 180"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff7e8"/><stop offset="1" stop-color="#e9f4ff"/></linearGradient></defs><rect width="240" height="180" rx="22" fill="url(#g)"/><circle cx="35" cy="30" r="12" fill="#ffd28b" opacity=".65"/><circle cx="205" cy="145" r="19" fill="#bde6cb" opacity=".65"/><text x="120" y="116" text-anchor="middle" font-size="88">' + x[5] + '</text></svg>';const photo="data:image/svg+xml;charset=UTF-8,"+encodeURIComponent(svg);return '<article class="product-card '+(q?"added":"")+'"><div class="product-photo"><img src="'+photo+'" alt="'+x[1]+'" loading="lazy" onerror="this.remove();this.parentElement.innerHTML=\'<span class=\\\'fallback\\\'>'+x[5]+'</span>\'"></div><div class="product-info"><div class="product-name">'+x[1]+'</div><div class="product-unit">'+x[2]+'</div><div class="product-price">'+money(x[3])+'</div><div class="product-actions"><button data-add="'+x[0]+'">'+(q?"Add more":"+ Add")+'</button><span class="qty">'+(q?"× "+q:"")+'</span></div></div></article>'}).join("")+'</section>').join("");holder.querySelectorAll("[data-add]").forEach(b=>b.onclick=()=>{const id=b.dataset.add;selected[id]=(selected[id]||0)+1;renderProducts();renderSelected()});renderPageDots();updatePageUI()}
function renderPageDots(){$("pageDots").innerHTML=CATEGORIES.map((c,i)=>'<button class="page-dot '+(i===page?"active":"")+'" aria-label="Go to '+c.title+'" data-page="'+i+'"></button>').join("");$("pageDots").querySelectorAll("button").forEach(b=>b.onclick=()=>goPage(+b.dataset.page))}
function goPage(i){page=Math.max(0,Math.min(CATEGORIES.length-1,i));$("marketViewport").scrollTo({left:$("marketViewport").clientWidth*page,behavior:"smooth"});updatePageUI()}
function updatePageUI(){const c=CATEGORIES[page];$("pageTitle").textContent=c.title;$("pageSubtitle").textContent=c.subtitle;$("pageNumber").textContent=(page+1)+" / "+CATEGORIES.length;$("prevPage").disabled=page===0;$("nextPage").disabled=page===CATEGORIES.length-1;$("pageDots").querySelectorAll("button").forEach((b,i)=>b.classList.toggle("active",i===page))}
let scrollTimer; $("marketViewport").addEventListener("scroll",()=>{clearTimeout(scrollTimer);scrollTimer=setTimeout(()=>{page=Math.round($("marketViewport").scrollLeft/Math.max(1,$("marketViewport").clientWidth));updatePageUI()},80)});
$("prevPage").onclick=()=>goPage(page-1);$("nextPage").onclick=()=>goPage(page+1);
function renderSelected(){const items=ITEMS.filter(x=>selected[x.id]);$("selectedCount").textContent=items.reduce((n,x)=>n+selected[x.id],0)+" items in your basket";$("selectedList").textContent=items.length?items.map(x=>x.name+" × "+selected[x.id]+" — "+money(x.price*selected[x.id])).join("\n"):"Your selected groceries will appear here.";updateBudget();$("finishBtn").disabled=!items.length&&!clips.length}
function listText(){return ITEMS.filter(x=>selected[x.id]).map(x=>x.name+" × "+selected[x.id]+" — "+money(x.price*selected[x.id])).join("\n")||"No items selected yet."}
async function copyText(t){try{await navigator.clipboard.writeText(t);return true}catch{const a=document.createElement("textarea");a.value=t;document.body.append(a);a.select();const ok=document.execCommand("copy");a.remove();return ok}}
$("joinBtn").onclick=()=>{player=$("name").value.trim();if(!player)return alert("Enter your name");$("welcome").textContent="Welcome, "+player;hide("join");show("lobby")};
document.querySelectorAll("[data-budget]").forEach(b=>b.onclick=()=>{$("budgetInput").value=b.dataset.budget;document.querySelectorAll("[data-budget]").forEach(x=>x.classList.toggle("chosen",x===b))});
$("startBtn").onclick=()=>{const entered=Number($("budgetInput").value);if(!Number.isFinite(entered)||entered<100||entered>10000000){alert("Choose a budget between ₹100 and ₹1 crore.");return}BUDGET=Math.round(entered);clips=[];selected={};page=0;$("clips").innerHTML="";$("count").textContent="0";hide("lobby");show("round");show("pttDock");$("nextBtn").disabled=true;renderProducts();renderSelected();$("status").textContent="READY";$("finishBtn").disabled=true;updateBudget()};
async function wav(blob){const c=new AudioContext(),b=await c.decodeAudioData(await blob.arrayBuffer()),rate=16000,n=Math.ceil(b.duration*rate),src=b.getChannelData(0),a=new Float32Array(n);for(let i=0;i<n;i++){let p=i*b.sampleRate/rate,l=Math.floor(p),f=p-l;a[i]=src[l]*(1-f)+src[Math.min(l+1,src.length-1)]*f}const ab=new ArrayBuffer(44+n*2),v=new DataView(ab),w=(o,s)=>{for(let i=0;i<s.length;i++)v.setUint8(o+i,s.charCodeAt(i))};w(0,"RIFF");v.setUint32(4,36+n*2,true);w(8,"WAVE");w(12,"fmt ");v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,rate,true);v.setUint32(28,rate*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);w(36,"data");v.setUint32(40,n*2,true);for(let i=0;i<n;i++){let s=Math.max(-1,Math.min(1,a[i]));v.setInt16(44+i*2,s<0?s*32768:s*32767,true)}await c.close();return new Blob([ab],{type:"audio/wav"})}
async function startRec(){if(recording||busy)return;try{stream=await navigator.mediaDevices.getUserMedia({audio:true});let parts=[];rec=new MediaRecorder(stream);rec.ondataavailable=e=>e.data.size&&parts.push(e.data);rec.onstop=async()=>{try{clips.push(await wav(new Blob(parts,{type:rec.mimeType})));$("count").textContent=clips.length;$("clips").insertAdjacentHTML("beforeend","<li>Voice order "+clips.length+" saved</li>");$("nextBtn").disabled=false;$("finishBtn").disabled=false;$("status").textContent="SAVED"}catch(e){$("status").textContent="Audio error"}finally{stream?.getTracks().forEach(t=>t.stop());stream=null;recording=false;$("ptt").classList.remove("recording")}};rec.start();recording=true;$("ptt").classList.add("recording");$("status").textContent="RECORDING"}catch(e){alert("Please allow microphone access")}}
function stopRec(){if(recording&&rec?.state==="recording"){$("status").textContent="SAVING";rec.stop()}}
const ptt=$("ptt");ptt.addEventListener("contextmenu",e=>e.preventDefault());ptt.addEventListener("selectstart",e=>e.preventDefault());ptt.addEventListener("dragstart",e=>e.preventDefault());ptt.addEventListener("pointerdown",e=>{e.preventDefault();e.stopPropagation();try{ptt.setPointerCapture(e.pointerId)}catch{}startRec()});["pointerup","pointercancel","lostpointercapture"].forEach(x=>ptt.addEventListener(x,e=>{e.preventDefault();stopRec()}));
$("nextBtn").onclick=()=>{$("nextBtn").disabled=true;$("status").textContent="READY FOR NEXT ITEM"};
async function transcribe(blob){const r=await fetch(SERVER+"/api/transcribe",{method:"POST",headers:{"Content-Type":"audio/wav"},body:blob});if(!r.ok)throw Error("Transcription server HTTP "+r.status);return String((await r.json()).text||"").trim()}
function parse(t){const s=t.toLowerCase(),item=ITEMS.find(x=>x.words.some(w=>new RegExp("\\b"+w+"\\b").test(s)));if(!item)return null;let q=1,m=s.match(/\b(\d+)\b/);if(m)q=Math.max(1,Math.min(99,+m[1]));else{const words={one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9,ten:10,a:1,an:1};for(const [w,n] of Object.entries(words))if(new RegExp("\\b"+w+"\\b").test(s)){q=n;break}}return {item,q}}
$("copyBtn").onclick=async()=>{const ok=await copyText(listText());$("copyBtn").textContent=ok?"Copied!":"Copy failed";setTimeout(()=>$("copyBtn").textContent="Copy list",1600)};
function playCelebration(won,total){
const margin=BUDGET-total,goodMargin=won&&margin>=BUDGET*.1;
const box=$("celebration");
box.className="celebration "+(won?(goodMargin?"win-big":"win-close"):"loss");
$("resultFace").textContent=won?"😄":"😭";
$("resultTitle").textContent=won?"YOU DID IT!":"OH NO! TRY AGAIN!";
$("resultMessage").textContent=won?(goodMargin?"Brilliant! You saved "+money(margin)+"!":"So close to your budget! Nice shopping!"):"Over budget by "+money(Math.max(0,total-BUDGET))+". Try again!";
$("confetti").innerHTML=won?Array.from({length:goodMargin?70:28},(_,i)=>'<i style="--x:'+((i*37)%100)+'%;--c:'+["#f47721","#22a65a","#f2c94c","#4597dc","#e76ca0","#7b61ff"][i%6]+';--d:'+(1.4+(i%8)*.2)+'s;--delay:-'+(i%11)*.17+'s"></i>').join(""):"";
}
function billingText(key){const all={en:{title:"Creating your bill…",subtitle:"Prisha is checking your basket and adding everything up.",one:"⏳ Checking your shopping basket…",two:"○ Calculating item prices…",three:"○ Printing your bill…",done:"✓ Your bill is ready!"},hi:{title:"आपका बिल बन रहा है…",subtitle:"प्रिशा आपकी टोकरी और कुल कीमत जाँच रही है।",one:"⏳ आपकी खरीदारी जाँची जा रही है…",two:"○ सामान की कीमत जोड़ी जा रही है…",three:"○ आपका बिल तैयार हो रहा है…",done:"✓ आपका बिल तैयार है!"},gu:{title:"તમારું બિલ બની રહ્યું છે…",subtitle:"પ્રિશા તમારી ટોપલી અને કુલ કિંમત ચકાસી રહી છે.",one:"⏳ તમારી ખરીદી તપાસી રહી છે…",two:"○ વસ્તુઓની કિંમત ગણાઈ રહી છે…",three:"○ તમારું બિલ છપાઈ રહ્યું છે…",done:"✓ તમારું બિલ તૈયાર છે!"}};return (all[GAME_LANGUAGE]||all.en)[key]}
function billingStage(stage){
 const fill=$("billingProgressFill"),one=$("billingStepOne"),two=$("billingStepTwo"),three=$("billingStepThree");
 const labels=["one","two","three"];
 [one,two,three].forEach((el,i)=>{el.classList.toggle("active",i===stage-1);el.classList.toggle("complete",i<stage-1)});
 const done=["✓","✓","✓"];
 [one,two,three].forEach((el,i)=>{const key=labels[i];el.textContent=i<stage-1?done[i]+" "+billingText(key).replace(/^[^ ]+ /,""):i===stage-1?billingText(key):"○ "+billingText(key).replace(/^[^ ]+ /,"")});
 fill.style.width=(stage===1?22:stage===2?64:92)+"%";
}
function showBilling(){
 $("billingTitle").textContent=billingText("title");$("billingSubtitle").textContent=billingText("subtitle");
 $("billingOverlay").hidden=false;document.body.classList.add("billing-open");billingStage(1);
}
function hideBilling(){ $("billingOverlay").hidden=true;document.body.classList.remove("billing-open"); }
$("finishBtn").onclick=async()=>{
 if((!clips.length&&!Object.keys(selected).length)||busy)return;
 busy=true;$("finishBtn").disabled=true;$("status").textContent=clips.length?"TRANSCRIBING":"BUILDING BASKET";
 showBilling();
 try{
  const rows=[];
  if(clips.length){
   billingStage(1);
   for(const audio of clips){try{const text=await transcribe(audio);rows.push({text,order:parse(text)})}catch(e){rows.push({text:"Transcription error: "+e.message,order:null})}}
  }
  billingStage(2);
  const basket=new Map();let sum=0;
  for(const x of ITEMS)if(selected[x.id]){const q=selected[x.id];basket.set(x.id,{name:x.name,q,total:x.price*q});sum+=x.price*q}
  for(const r of rows)if(r.order){const x=r.order.item,q=r.order.q,old=basket.get(x.id)||{name:x.name,q:0,total:0};old.q+=q;old.total+=x.price*q;basket.set(x.id,old);sum+=x.price*q}
  await new Promise(resolve=>setTimeout(resolve,550));
  billingStage(3);$("billingTitle").textContent=billingText("done");$("billingSubtitle").textContent=billingText("done");
  $("billingProgressFill").style.width="100%";
  [ $("billingStepOne"),$("billingStepTwo"),$("billingStepThree")].forEach(el=>el.classList.add("complete"));
  await new Promise(resolve=>setTimeout(resolve,700));
  hideBilling();hide("round");hide("pttDock");show("result");
  const won=sum<=BUDGET&&basket.size>0;playCelebration(won,sum);
  $("cart").innerHTML=Array.from(basket.values()).map(x=>'<div class="product-card"><div class="product-info"><div class="product-name">'+x.name+' × '+x.q+'</div><div class="product-price">'+money(x.total)+'</div></div></div>').join("")+rows.map(r=>'<div class="product-card"><div class="product-info"><span>'+(r.text||"No speech")+'</span><b>'+(r.order?"Voice accepted":"Not recognised")+'</b></div></div>').join("");
  $("total").textContent=money(sum);$("total").parentElement.classList.toggle("near-total",sum>=BUDGET*.9&&sum<=BUDGET);
  $("message").textContent=sum>BUDGET?"Over budget — you lost.":won?"Within your budget — you win!":"No valid items were accepted.";
  const saved=saveHistory({player,total:sum,won,playedAt:new Date().toISOString(),orders:[...Array.from(basket.values()).map(x=>({transcript:x.name,accepted:true,item:x.name,quantity:x.q})),...rows.map(r=>({transcript:r.text,accepted:!!r.order,item:r.order?.item.name||"",quantity:r.order?.q||0}))]});
  $("message").textContent+=(saved?" Game saved in this tab's session history.":" Game history could not be saved.");
 }catch(e){hideBilling();$("status").textContent="ERROR";alert("Could not prepare the bill. Please try again.");}
 finally{hideBilling();busy=false;$("finishBtn").disabled=!(Object.keys(selected).length||clips.length)}
};
$("copyResult").onclick=async()=>{const ok=await copyText(Array.from(document.querySelectorAll("#cart .product-card")).map(x=>x.innerText).join("\n")+"\nTotal: "+$("total").textContent);$("copyResult").textContent=ok?"Copied!":"Copy failed"};
$("againBtn").onclick=()=>{hide("result");show("lobby")};
$("historyBtn").onclick=()=>{const games=getHistory().filter(g=>g.player.toLowerCase()===player.toLowerCase());show("history");$("historyText").textContent=games.length?games.map((g,i)=>{const d=new Date(g.playedAt);return (i+1)+". "+d.toLocaleString()+" — "+(g.won?"WON":"LOST")+" — "+money(g.total)+"\n"+g.orders.map(o=>"   "+o.transcript+(o.accepted?" → "+o.item+" × "+o.quantity:" → Rejected")).join("\n")}).join("\n\n"):"No games saved in this tab's session yet."};
$("closeHistory").onclick=()=>hide("history");

/* Regional language support: Hindi and Gujarati */
let GAME_LANGUAGE="en";
const GAME_TEXT={
hi:{ready:"खेलने के लिए तैयार?",name:"अपना नाम लिखें",join:"चलो खरीदारी करें!",aisles:["🍎 फल","🥕 सब्ज़ियाँ","🥛 दूध और बेकरी","🌾 अनाज और राशन","🍪 नाश्ता और पेय","🏍️ बाइक और कार"],subs:["ताज़े और रसीले फल","रोज़ की रंग-बिरंगी सब्ज़ियाँ","दूध, पनीर और नाश्ते की चीज़ें","रसोई का ज़रूरी राशन","बिस्कुट, चाय और स्वादिष्ट चीज़ें","आपकी पसंद की सवारी"],budget:"🛒 आपका खरीदारी बजट",hint:"सामान चुनें और अपनी टोकरी भरें!",intro:"अगली दुकान पर जाने के लिए बाएँ या दाएँ स्वाइप करें। सामान जोड़ने के लिए दबाएँ।",back:"← पीछे",next:"अगली दुकान →",add:"+ जोड़ें",more:"और जोड़ें",copy:"सूची कॉपी करें",finish:"मेरी टोकरी दिखाएँ! 🛒",voice:"बोले गए ऑर्डर:",total:"आपका कुल",readyText:"नमस्ते! मैं प्रिशा हूँ! 👋",buddy:"आपकी खरीदारी की दोस्त",hello:"आइए साथ में खरीदारी करें और अपनी टोकरी भरें!",count:"सामान आपकी टोकरी में",win:"आप बजट में रहे — आप जीत गए!",lose:"बजट से ज़्यादा खर्च — आप हार गए।",winTitle:"आप जीत गए!",loseTitle:"कोई बात नहीं! फिर कोशिश करें!",near:"बहुत करीब थे! शानदार खरीदारी!",great:"आपने बजट में खरीदारी की। बहुत खूब!",try:"आपकी टोकरी बजट से ऊपर हो गई। फिर कोशिश करें!"},
gu:{ready:"રમવા માટે તૈયાર છો?",name:"તમારું નામ લખો",join:"ચાલો ખરીદી કરીએ!",aisles:["🍎 ફળ","🥕 શાકભાજી","🥛 દૂધ અને બેકરી","🌾 અનાજ અને કરિયાણું","🍪 નાસ્તો અને પીણાં","🏍️ બાઈક અને કાર"],subs:["તાજાં અને રસદાર ફળ","રોજિંદાં રંગબેરંગી શાકભાજી","દૂધ, ચીઝ અને નાસ્તાની વસ્તુઓ","રસોડાની જરૂરી વસ્તુઓ","બિસ્કિટ, ચા અને નાસ્તો","તમારી મનપસંદ સવારી"],budget:"🛒 તમારું ખરીદી બજેટ",hint:"વસ્તુઓ પસંદ કરો અને ટોપલી ભરો!",intro:"આગલી દુકાનમાં જવા ડાબે કે જમણે સ્વાઇપ કરો. વસ્તુ ઉમેરવા દબાવો.",back:"← પાછા",next:"આગલી દુકાન →",add:"+ ઉમેરો",more:"વધુ ઉમેરો",copy:"યાદી કોપી કરો",finish:"મારી ટોપલી જુઓ! 🛒",voice:"સાચવેલા વૉઇસ ઓર્ડર:",total:"તમારું કુલ",readyText:"નમસ્તે! હું પ્રિશા છું! 👋",buddy:"તમારી ખરીદીની મિત્ર",hello:"ચાલો સાથે ખરીદી કરીએ અને ટોપલી ભરીએ!",count:"વસ્તુઓ તમારી ટોપલીમાં",win:"તમે બજેટમાં રહ્યા — તમે જીતી ગયા!",lose:"બજેટ કરતાં વધુ ખર્ચ — તમે હારી ગયા.",winTitle:"તમે જીતી ગયા!",loseTitle:"કોઈ વાંધો નહીં! ફરી રમો!",near:"ખૂબ નજીક હતા! સરસ ખરીદી!",great:"તમે બજેટમાં ખરીદી કરી. શાબાશ!",try:"તમારી ટોપલી બજેટ કરતાં વધી ગઈ. ફરી પ્રયાસ કરો!"}
};
const GAME_PRODUCTS={
hi:{apple:"सेब",banana:"केला",orange:"संतरा",mango:"आम",grapes:"अंगूर",tomato:"टमाटर",potato:"आलू",onion:"प्याज़",carrot:"गाजर",cucumber:"खीरा",milk:"ताज़ा दूध",curd:"दही",butter:"मक्खन",cheese:"चीज़ स्लाइस",bread:"ब्राउन ब्रेड",rice:"चावल",atta:"गेहूँ का आटा",oil:"खाना पकाने का तेल",sugar:"चीनी",dal:"तूर दाल",biscuits:"मैरी बिस्कुट",tea:"काली चाय",juice:"संतरे का जूस",chips:"आलू चिप्स",chocolate:"मिल्क चॉकलेट",bicycle:"बच्चों की साइकिल",scooter:"स्कूटर",motorbike:"मोटरसाइकिल",electricbike:"इलेक्ट्रिक बाइक",hatchback:"हैचबैक कार",suv:"एसयूवी कार"},
gu:{apple:"સફરજન",banana:"કેળાં",orange:"સંતરું",mango:"કેરી",grapes:"દ્રાક્ષ",tomato:"ટામેટાં",potato:"બટાકા",onion:"ડુંગળી",carrot:"ગાજર",cucumber:"કાકડી",milk:"તાજું દૂધ",curd:"દહીં",butter:"માખણ",cheese:"ચીઝ સ્લાઇસ",bread:"બ્રાઉન બ્રેડ",rice:"ચોખા",atta:"ઘઉંનો લોટ",oil:"ખાદ્ય તેલ",sugar:"ખાંડ",dal:"તુવેર દાળ",biscuits:"મેરી બિસ્કિટ",tea:"કાળી ચા",juice:"નારંગીનો રસ",chips:"બટાકાની વેફર",chocolate:"મિલ્ક ચોકલેટ",bicycle:"બાળકોની સાઇકલ",scooter:"સ્કૂટર",motorbike:"મોટરસાઇકલ",electricbike:"ઇલેક્ટ્રિક બાઇક",hatchback:"હેચબેક કાર",suv:"એસયુવી કાર"}
};
const GAME_SPOKEN={
hi:{apple:["सेब"],banana:["केला","केले"],orange:["संतरा"],mango:["आम"],grapes:["अंगूर"],tomato:["टमाटर"],potato:["आलू"],onion:["प्याज","प्याज़"],carrot:["गाजर"],cucumber:["खीरा"],milk:["दूध"],curd:["दही"],butter:["मक्खन"],cheese:["चीज"],bread:["ब्रेड"],rice:["चावल"],atta:["आटा"],oil:["तेल"],sugar:["चीनी"],dal:["दाल"],biscuits:["बिस्कुट"],tea:["चाय"],juice:["जूस"],chips:["चिप्स"],chocolate:["चॉकलेट"],bicycle:["साइकिल"],scooter:["स्कूटर"],motorbike:["मोटरसाइकिल","बाइक"],electricbike:["इलेक्ट्रिक बाइक"],hatchback:["कार"],suv:["एसयूवी","कार"]},
gu:{apple:["સફરજન"],banana:["કેળા","કેળું"],orange:["સંતરું"],mango:["કેરી"],grapes:["દ્રાક્ષ"],tomato:["ટામેટાં"],potato:["બટાકા"],onion:["ડુંગળી"],carrot:["ગાજર"],cucumber:["કાકડી"],milk:["દૂધ"],curd:["દહીં"],butter:["માખણ"],cheese:["ચીઝ"],bread:["બ્રેડ"],rice:["ચોખા"],atta:["લોટ"],oil:["તેલ"],sugar:["ખાંડ"],dal:["દાળ"],biscuits:["બિસ્કિટ"],tea:["ચા"],juice:["જ્યુસ","રસ"],chips:["વેફર"],chocolate:["ચોકલેટ"],bicycle:["સાઇકલ"],scooter:["સ્કૂટર"],motorbike:["મોટરસાઇકલ","બાઇક"],electricbike:["ઇલેક્ટ્રિક બાઇક"],hatchback:["કાર"],suv:["એસયુવી","કાર"]}
};
function gameT(k){return (GAME_TEXT[GAME_LANGUAGE]||{})[k]||""}
function gameItemName(id,english){return (GAME_PRODUCTS[GAME_LANGUAGE]||{})[id]||english}
function applyGameLanguage(){
 const d=GAME_TEXT[GAME_LANGUAGE]||{};
 document.documentElement.lang=GAME_LANGUAGE;
 $("readyTitle").textContent=GAME_LANGUAGE==="en"?"Ready to play?":d.ready;
 $("name").placeholder=GAME_LANGUAGE==="en"?"Your name":d.name;
 $("joinBtn").textContent=GAME_LANGUAGE==="en"?"Let's go shopping!":d.join;
 document.querySelector(".mascot-kicker").textContent=GAME_LANGUAGE==="en"?"YOUR SHOPPING BUDDY":d.buddy;
 document.querySelector(".mascot-welcome h2").textContent=GAME_LANGUAGE==="en"?"Hi! I'm Prisha! 👋":d.readyText;
 document.querySelector(".mascot-welcome p").textContent=GAME_LANGUAGE==="en"?"Let's go shopping together. Fill our basket and have fun!":d.hello;
 if(!$("round").hidden){renderProducts();renderSelected();updatePageUI()}
}
$("languageSelect").addEventListener("change",e=>{GAME_LANGUAGE=e.target.value;applyGameLanguage()});
const oldRenderProducts=renderProducts;
renderProducts=function(){oldRenderProducts();if(GAME_LANGUAGE==="en")return;document.querySelectorAll(".market-page").forEach((section,i)=>{const cat=CATEGORIES[i];section.querySelectorAll(".product-card").forEach((card,j)=>{const item=cat.items[j];if(!item)return;card.querySelector(".product-name").textContent=gameItemName(item[0],item[1]);const im=card.querySelector("img");if(im)im.alt=gameItemName(item[0],item[1]);const btn=card.querySelector("[data-add]");if(btn)btn.textContent=selected[item[0]]?gameT("more"):gameT("add")})})};
const oldUpdatePageUI=updatePageUI;
updatePageUI=function(){oldUpdatePageUI();if(GAME_LANGUAGE==="en")return;const d=GAME_TEXT[GAME_LANGUAGE];$("pageTitle").textContent=d.aisles[page];$("pageSubtitle").textContent=d.subs[page];$("prevPage").textContent=d.back;$("nextPage").textContent=d.next};
const oldRenderSelected=renderSelected;
renderSelected=function(){oldRenderSelected();if(GAME_LANGUAGE!=="en"){$("selectedCount").textContent=ITEMS.reduce((n,x)=>n+(selected[x.id]||0),0)+" "+gameT("count");$("selectedList").textContent=ITEMS.filter(x=>selected[x.id]).map(x=>gameItemName(x.id,x.name)+" × "+selected[x.id]+" — "+money(x.price*selected[x.id])).join("\n")||"—";$("copyBtn").textContent=gameT("copy");$("finishBtn").textContent=gameT("finish")}};
const oldUpdateBudget=updateBudget;
updateBudget=function(extra=0){oldUpdateBudget(extra);if(GAME_LANGUAGE!=="en"){$("budgetBox").querySelector(".budget-line span").textContent=gameT("budget");$("budgetHint").textContent=selectedTotal()>BUDGET?((GAME_LANGUAGE==="hi")?"🙈 अरे! बजट पार हो गया। कुछ सामान हटाएँ!":"🙈 અરે! બજેટ વધી ગયું. થોડી વસ્તુઓ દૂર કરો!"):selectedTotal()>=BUDGET*.9?((GAME_LANGUAGE==="hi")?"🎯 बहुत करीब! बजट के अंदर रहें!":"🎯 બહુ નજીક! બજેટમાં રહો!"):gameT("hint")}};
const oldParse=parse;
parse=function(t){const found=oldParse(t);if(found)return found;const s=String(t||"").toLowerCase();for(const item of ITEMS){const words=(GAME_SPOKEN[GAME_LANGUAGE]||{})[item.id]||[];for(const word of words){const at=s.indexOf(word);if(at>=0){const before=s.slice(0,at).trim().split(/\s+/).pop();const nums={one:1,two:2,three:3};let q=/^\d+$/.test(before)?Math.max(1,Math.min(99,Number(before))):1;if(GAME_LANGUAGE==="hi"&&/दो|दोनो/.test(before))q=2;if(GAME_LANGUAGE==="gu"&&/બે/.test(before))q=2;return {item,q}}}}return null};
const oldTranscribe=transcribe;
transcribe=async function(blob){const r=await fetch(SERVER+"/api/transcribe",{method:"POST",headers:{"Content-Type":"audio/wav","X-Sanket-Language":GAME_LANGUAGE},body:blob});if(!r.ok)throw Error("Transcription server HTTP "+r.status);return String((await r.json()).text||"").trim()};
const oldPlayCelebration=playCelebration;
playCelebration=function(won,total){oldPlayCelebration(won,total);if(GAME_LANGUAGE!=="en"){$("resultTitle").textContent=gameT(won?"winTitle":"loseTitle");$("resultMessage").textContent=won?(total>=BUDGET*.9?gameT("near"):gameT("great")):gameT("try")}};
