const fs=require('fs'),mqtt=require('mqtt');
const src=fs.readFileSync('index.html','utf8').match(/<script id=core>([\s\S]*?)<\/script>/)[1];
const m={exports:{}};new Function('module','Buffer',src)(m,Buffer);const {Radio,distKm}=m.exports;
const rsrc=fs.readFileSync('index.html','utf8').match(/<script id=rec>([\s\S]*?)<\/script>/)[1];const m2={exports:{}};new Function('module',rsrc)(m2);const {Recorder,buildWav}=m2.exports;
const ch='test'+Date.now()%1e5,sleep=t=>new Promise(r=>setTimeout(r,t));
const mk=(n)=>{const s={audio:0,last:null,rec:new Recorder(12000)};var r;r=new Radio(mqtt,{ch,brokers:process.env.B?[process.env.B]:undefined,on:(k,v)=>{if(k=='state')s.last=v;if(k=='audio'){s.audio+=v.length;const f=r.floor;if(f){const fu=r.users[f.id];s.rec.feed(f.id,f.name,v,false,undefined,fu&&fu.loc)}}if(k=='state'&&s.pf&&(!v.floor||v.floor.id!==s.pf.id))s.rec.end();if(k=='state')s.pf=v.floor;if(k=='net')console.log(n,'net',v)}});r.s=s;return r};
const ok=(c,msg)=>{console.log(c?'PASS':'FAIL',msg);if(!c)process.exitCode=1};
(async()=>{const obs=mk('observer');const rs=[];for(let i=0;i<10;i++)rs.push(mk('u'+i));await sleep(4000);
 rs.forEach((r,i)=>r.join('user'+i));await sleep(3000);
 ok(obs.s.last&&obs.s.last.users.length==10,'observer (not joined) sees 10 online: '+(obs.s.last&&obs.s.last.users.length));
 // location propagation
 rs[0].setLoc({lat:28.6139,lon:77.209,acc:12,src:'gps',city:'New Delhi, IN'});rs[1].setLoc({lat:19.076,lon:72.8777,acc:25000,src:'ip',city:'Mumbai, India'});await sleep(2500);
 {const u=obs.s.last.users.find(x=>x.id==rs[0].id),v=rs[2].users[rs[1].id];ok(u&&u.loc&&u.loc.lat==28.6139&&u.loc.src=='gps'&&u.loc.acc==12&&u.loc.city=='New Delhi, IN'&&v&&v.loc&&v.loc.src=='ip','location in heartbeat propagates (gps + ip)')}
 {const d=distKm(rs[0].loc,rs[1].loc);ok(d>1100&&d<1200,'distance Delhi-Mumbai '+d.toFixed(0)+' km')}
 ok(rs.slice(2).every(r=>r.users[rs[3].id]&&r.users[rs[3].id].loc===null),'clients without location still listed (loc=null)');
 // old client: raw heartbeat without loc field, and garbage loc
 obs.c.publish(obs.T('presence/oldclnt1'),JSON.stringify({id:'oldclnt1',name:'OldRig',ts:Date.now()}),{retain:false});
 obs.c.publish(obs.T('presence/badloc01'),JSON.stringify({id:'badloc01',name:'Bad',ts:Date.now(),loc:{lat:'x',lon:999}}),{retain:false});await sleep(1500);
 ok(rs[2].users.oldclnt1&&rs[2].users.oldclnt1.name=='OldRig'&&rs[2].users.oldclnt1.loc===null&&rs[2].users.badloc01.loc===null,'old client without location accepted; invalid loc rejected');
 obs.c.publish(obs.T('presence/oldclnt1'),'',{retain:true});obs.c.publish(obs.T('presence/badloc01'),'',{retain:true});await sleep(1000);
 rs[1].setLoc(null);await sleep(1500);ok(rs[2].users[rs[1].id].loc===null,'stop sharing clears location for others');
 rs[1].setLoc({lat:19.076,lon:72.8777,acc:25000,src:'ip',city:'Mumbai, India'});await sleep(1500);
 // race: two claim simultaneously
 let a,b;rs[0].claim(x=>a=x);rs[1].claim(x=>b=x);await sleep(1200);
 ok((a?1:0)+(b?1:0)==1&&rs[0].floor.id==rs[1].floor.id,`race resolved to one talker (u0=${a},u1=${b})`);
 const w=a?rs[0]:rs[1],l=a?rs[1]:rs[0];
 ok(rs.slice(2).every(r=>r.floor&&r.floor.id==w.id),'all listeners agree on talker');
 let c;rs[2].claim(x=>c=x);await sleep(800);ok(c===false,'third claim denied while busy');
 for(let i=0;i<25;i++){w.sendAudio(new Int16Array(4096/4).fill(i));await sleep(85)}await sleep(1500);
 const got=rs.filter(r=>r!==w).map(r=>r.s.audio);ok(got.every(g=>g==25*1024),'audio relayed to 9 listeners: '+got.join(','));
 await sleep(0);
 ok(l.sendAudio(new Int16Array(10))===false,'loser cannot transmit');
 w.release();await sleep(1000);ok(rs.every(r=>!r.floor),'floor released');
 const L=rs.filter(r=>r!==w).map(r=>r.s.rec.entries);ok(L.every(e=>e.length==1&&e[0].id==w.id&&e[0].samples==25*1024&&Math.abs(e[0].dur-25*1024/12000)<1e-9&&e[0].wav.byteLength==44+25*1024*2&&e[0].loc&&e[0].loc.city==(w===rs[0]?'New Delhi, IN':'Mumbai, India')),'replay entry (tagged with talker location) on 9 listeners, dur '+(L[0][0]&&L[0][0].dur.toFixed(3))+'s');
 {const w8=new DataView(buildWav([new Int16Array([1,-2,32767])],12000));ok(String.fromCharCode(w8.getUint8(0),w8.getUint8(1),w8.getUint8(2),w8.getUint8(3))=='RIFF'&&w8.getUint32(24,true)==12000&&w8.getUint16(34,true)==16&&w8.getUint32(40,true)==6&&w8.getInt16(46,true)==-2,'WAV header/data valid')}
 {const R=new Recorder(12000);for(let i=0;i<60;i++){R.feed('a','A',new Int16Array(100),false,i*5000);R.end()}ok(R.entries.length==50,'log capped at 50')}
 // vanish timeout
 rs[3].claim(()=>{});await sleep(700);rs[3].c.end(true);rs[3].closed=true;clearInterval(rs[3].timer);await sleep(4000);
 ok(rs[4].floor==null,'floor auto-released after talker vanished');
 ok(obs.s.last.users.length==9,'last will removed vanished user: '+obs.s.last.users.length);
 rs[5].leave();await sleep(1500);ok(obs.s.last.users.length==8,'clean leave: '+obs.s.last.users.length);
 [obs,...rs].forEach(r=>{try{r.leave()}catch(e){}});setTimeout(()=>process.exit(),800);})();
