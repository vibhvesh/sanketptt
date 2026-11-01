// SSTV encoder + audio decoder (pure JS, browser + node). Standard modes: Robot36, Martin M1, Scottie S1, PD120.
// Decoder: complex FM discriminator -> VIS detection (1900 leader / 1200 break / 8-bit VIS) -> sync-tracked line decode with slant correction.
(function(root){
function clamp(v){return v<0?0:v>255?255:v}
function toYUV(r,g,b){return[16+(65.738*r+129.057*g+25.064*b)/256,128+(-37.945*r-74.494*g+112.439*b)/256,128+(112.439*r-94.154*g-18.285*b)/256]}
function fromYUV(y,u,v){y=1.164*(y-16);u-=128;v-=128;return[clamp(y+1.596*v),clamp(y-0.813*v-0.391*u),clamp(y+2.018*u)]}
function v2f(v){return 1500+clamp(v)*800/255}
// chans: [t0 ms relative to sync start, duration ms, kind]; unit = ms per scan unit; rows = image rows per unit; first = ms from VIS end to first sync
var MODES={
 r36:{name:'Robot36',vis:8,W:320,H:240,unit:150,rows:1,first:0,sync:9,chans:[[12,88,'Y'],[106,44,'C']],sep:[100,4.5]},
 m1:{name:'Martin M1',vis:44,W:320,H:256,unit:446.446,rows:1,first:0,sync:4.862,chans:[[5.434,146.432,'G'],[152.438,146.432,'B'],[299.442,146.432,'R']]},
 s1:{name:'Scottie S1',vis:60,W:320,H:256,unit:428.22,rows:1,first:288.48,sync:9,chans:[[-277.98,138.24,'G'],[-138.24,138.24,'B'],[10.5,138.24,'R']]},
 pd120:{name:'PD120',vis:95,W:640,H:496,unit:508.48,rows:2,first:0,sync:20,chans:[[22.08,121.6,'Y0'],[143.68,121.6,'V'],[265.28,121.6,'U'],[386.88,121.6,'Y1']]}};
var BYVIS={};for(var k in MODES){MODES[k].id=k;BYVIS[MODES[k].vis]=MODES[k]}
function dur(m){return (910+m.first+(m.H/m.rows)*m.unit+300)/1000}
// rgba: W*H*4 of the mode's size -> Int16Array PCM
function encode(rgba,fs,mode){fs=fs||12000;var m=MODES[mode||'r36'],W=m.W,H=m.H,segs=[],t=0;function seg(d,f){segs.push([t,t+d,f]);t+=d}
 seg(300,1900);seg(10,1200);seg(300,1900);seg(30,1200);var p=0;for(var b=0;b<7;b++){var bit=(m.vis>>b)&1;p^=bit;seg(30,bit?1100:1300)}seg(30,p?1100:1300);seg(30,1200);
 var px=function(c,x,y){var o=(y*W+x)*4;return c==='R'?rgba[o]:c==='G'?rgba[o+1]:rgba[o+2]};
 var Y=new Float32Array(W*H),U=new Float32Array(W*H),V=new Float32Array(W*H);
 for(var i=0;i<W*H;i++){var q=toYUV(rgba[i*4],rgba[i*4+1],rgba[i*4+2]);Y[i]=q[0];U[i]=q[1];V[i]=q[2]}
 function scan(d,fn){seg(d,function(fr){return v2f(fn(Math.min(W-1,Math.floor(fr*W))))})}
 if(m.id==='s1')seg(9,1200);
 for(var u=0;u<H/m.rows;u++)(function(l){
  if(m.id==='r36'){var ev=l%2===0,l2=ev?l+1:l-1;seg(9,1200);seg(3,1500);scan(88,function(x){return Y[l*W+x]});seg(4.5,ev?1500:2300);seg(1.5,1900);
   seg(44,function(fr){var x=Math.min(159,Math.floor(fr*160))*2,C=ev?V:U,a=0;for(var k=0;k<2;k++)a+=C[l*W+x+k]+C[l2*W+x+k];return v2f(a/4)})}
  else if(m.id==='m1'){seg(4.862,1200);seg(.572,1500);['G','B','R'].forEach(function(c){scan(146.432,function(x){return px(c,x,l)});seg(.572,1500)})}
  else if(m.id==='s1'){seg(1.5,1500);scan(138.24,function(x){return px('G',x,l)});seg(1.5,1500);scan(138.24,function(x){return px('B',x,l)});seg(9,1200);seg(1.5,1500);scan(138.24,function(x){return px('R',x,l)})}
  else{var a=2*l,b=a+1;seg(20,1200);seg(2.08,1500);scan(121.6,function(x){return Y[a*W+x]});scan(121.6,function(x){return (V[a*W+x]+V[b*W+x])/2});
   scan(121.6,function(x){return (U[a*W+x]+U[b*W+x])/2});scan(121.6,function(x){return Y[b*W+x]})}})(u);
 seg(300,1200);
 var n=Math.ceil(t*fs/1000),out=new Int16Array(n),ph=0,s=0;
 for(var j=0;j<n;j++){var ms=j*1000/fs;while(s<segs.length-1&&ms>=segs[s][1])s++;var g=segs[s],f=typeof g[2]==='function'?g[2]((ms-g[0])/(g[1]-g[0])):g[2];
  ph+=2*Math.PI*f/fs;if(ph>2*Math.PI)ph-=2*Math.PI;out[j]=Math.round(Math.sin(ph)*16000)}
 return out}

// ---- streaming decoder ----
function Rx(fs,cb){fs=fs||12000;this.dec=fs>16000?Math.round(fs/12000):1;this.da=0;this.dn=0;this.q=[];this.qn=0;this.tm=null;this.fs=fs/this.dec;this.cb=cb||{};var ms=this.ms=this.fs/1000;
 var N=this.taps=Math.max(15,Math.round(this.fs/12000*31))|1,fc=1100/this.fs,h=[],s=0;for(var i=0;i<N;i++){var x=i-(N-1)/2,v=(x?Math.sin(2*Math.PI*fc*x)/(Math.PI*x):2*fc)*(0.54-0.46*Math.cos(2*Math.PI*i/(N-1)));h.push(v);s+=v}
 this.h=h.map(function(v){return v/s});this.ri=[];this.qi=[];this.ph=0;this.pz=null;
 this.o=0;this.f=[];this.P=[0];this.near=[0];this.low=[0];this.state='vis';this.scan=0;this.done=false;this.started=false;this.mode=null;this.line=0;this.units=0}
Rx.prototype.push=function(a){var self=this;if(this.qn>this.fs*this.dec*200){this.q=[];this.qn=0;this.reset()}this.q.push(a);this.qn+=a.length;
 if(!this.tm)this.tm=setTimeout(function(){self.drain()},0)};
Rx.prototype.drain=function(){var self=this,t0=Date.now();this.tm=null;
 try{while(this.q.length&&Date.now()-t0<12){var a=this.q.shift();this.qn-=a.length;this._push(a)}}catch(e){console.error('SSTV decode error',e);this.q=[];this.qn=0;this.reset()}
 if(this.q.length)this.tm=setTimeout(function(){self.drain()},0)};
Rx.prototype.reset=function(){var was=this.state==='img';if(was)try{this.finish(true)}catch(e){}this.state='vis';this.mode=null;this.f=[];this.P=[0];this.near=[0];this.low=[0];this.o=0;this.scan=0;this.pz=null;this.ri=null};
Rx.prototype._push=function(a){var fs=this.fs,w=2*Math.PI*1900/fs,h=this.h,N=h.length,D=this.dec;
 if(!this.ri||this.ri.length!==N){this.ri=new Float64Array(N);this.qi=new Float64Array(N);this.rp=0;this.rc=0}var ri=this.ri,qi=this.qi;
 for(var i=0;i<a.length;i++){var x=a[i];if(D>1){this.da+=x;if(++this.dn<D)continue;x=this.da/D;this.da=0;this.dn=0}
  ri[this.rp]=x*Math.cos(this.ph);qi[this.rp]=-x*Math.sin(this.ph);this.rp=(this.rp+1)%N;this.ph+=w;if(this.ph>2*Math.PI)this.ph-=2*Math.PI;
  if(this.rc<N){this.rc++;if(this.rc<N)continue}var I=0,Q=0,p=this.rp;for(var k=0;k<N;k++){I+=h[k]*ri[p];Q+=h[k]*qi[p];if(++p===N)p=0}
  var fr=1900;if(this.pz){var re=I*this.pz[0]+Q*this.pz[1],im=Q*this.pz[0]-I*this.pz[1];fr=1900+Math.atan2(im,re)*fs/(2*Math.PI)}this.pz=[I,Q];
  if(fr<900)fr=900;if(fr>2500)fr=2500;var L=this.f.length;this.f.push(fr);this.P.push(this.P[L]+fr);this.near.push(this.near[L]+(Math.abs(fr-1900)<150?1:0));this.low.push(this.low[L]+(fr<1350?1:0))}
 this.run()};
Rx.prototype.end=function(){return this.o+this.f.length};
Rx.prototype.avg=function(a,b){var o=this.o,L=this.f.length;a-=o;b-=o;if(a<0)a=0;if(b>L)b=L;if(b-a<1){var c=Math.min(L-1,Math.max(0,Math.floor((a+b)/2)));return this.f[c]}
 var ia=Math.floor(a),ib=Math.floor(b),P=this.P,f=this.f,s=P[ib]-P[ia]-(a-ia)*f[ia]+(ib<L?(b-ib)*f[ib]:0);return s/(b-a)};
Rx.prototype.cnt=function(arr,a,b){a=Math.max(0,Math.round(a-this.o));b=Math.min(this.f.length,Math.round(b-this.o));return b>a?arr[b]-arr[a]:0};
Rx.prototype.trim=function(keep){var d=this.f.length-keep;if(d<=0)return;this.f=this.f.slice(d);var self=this;['P','near','low'].forEach(function(k){var A=self[k],b=A[d];self[k]=A.slice(d).map(function(v){return v-b})});this.o+=d};
Rx.prototype.run=function(){var ms=this.ms,E=this.end();
 if(this.state==='vis'){var st=Math.max(this.scan,this.o+Math.round(205*ms));
  for(var n=st;n<E-Math.round(305*ms);n++){
   if(!(this.avg(n-3*ms,n)>1600&&this.avg(n,n+4*ms)<1450))continue; // falling edge
   if(this.cnt(this.near,n-200*ms,n)<0.6*200*ms)continue; // leader
   var best=null;for(var dn=-3*ms;dn<=3*ms;dn+=ms/2){var s0=n+dn,sb=this.avg(s0+5*ms,s0+25*ms);if(sb<1050||sb>1350)continue;
    var code=0,par=0,ok=true;for(var b=0;b<8;b++){var c=s0+(30+30*b)*ms,v=this.avg(c+6*ms,c+24*ms);if(v<1000||v>1400){ok=false;break}var bit=v<1200?1:0;if(b<7)code|=bit<<b;par^=bit}
    var sp=this.avg(s0+275*ms,s0+295*ms);if(ok&&par===0&&BYVIS[code]&&sp>1050&&sp<1350){best={s0:s0,m:BYVIS[code]};break}}
   if(best){this.begin(best.m,best.s0+300*ms);break}}
  if(this.state==='vis'){this.scan=Math.max(st,E-Math.round(305*ms));if(this.f.length>12*this.fs)this.trim(4*this.fs)}}
 if(this.state==='img')this.img()};
Rx.prototype.begin=function(m,img0){this.mode=m;this.W=m.W;this.H=m.H;this.img0=img0;this.state='img';this.started=true;this.done=false;this.line=0;this.units=0;this.miss=0;
 this.pts=[];this.base=img0+m.first*this.ms;this.per=m.unit*this.ms;this.rgba=new Uint8ClampedArray(m.W*m.H*4);for(var i=3;i<this.rgba.length;i+=4)this.rgba[i]=255;
 this.cb.start&&this.cb.start(m.name,m.W,m.H)};
Rx.prototype.fit=function(){var p=this.pts,n=p.length;if(n<3)return;var sx=0,sy=0,sxx=0,sxy=0;for(var i=0;i<n;i++){sx+=p[i][0];sy+=p[i][1];sxx+=p[i][0]*p[i][0];sxy+=p[i][0]*p[i][1]}
 var d=n*sxx-sx*sx;if(!d)return;var b=(n*sxy-sx*sy)/d,a=(sy-b*sx)/n,m=this.mode.unit*this.ms;if(Math.abs(b-m)/m<0.02){this.per=b;this.base=a}};
Rx.prototype.img=function(){var m=this.mode,ms=this.ms,U=m.H/m.rows,sl=m.sync*ms;if(this.end()-this.img0>(dur(m)+10)*this.fs){this.finish(true);return}
 while(this.units<U){var u=this.units,e=this.base+u*this.per,last=m.chans[m.chans.length-1],need=e+(last[0]+last[1]+2)*ms;
  var win=(this.pts.length<3?12:4)*ms;if(this.end()<Math.max(need,e+win+sl+3*ms))return;
  var bp=-1,bs=-1e9;for(var p=e-win;p<=e+win;p+=1){var s=this.cnt(this.low,p,p+sl)-this.cnt(this.low,p-2*ms,p)*sl/(2*ms)*0.5-this.cnt(this.low,p+sl,p+sl+2*ms)*sl/(2*ms)*0.5;if(s>bs){bs=s;bp=p}}
  if(bs>0.6*sl){this.miss=0;var pr=this.pts.length>=3?this.base+u*this.per:bp;if(this.pts.length<3||Math.abs(bp-pr)<3*ms){this.pts.push([u,bp]);if(this.pts.length>40)this.pts.shift();this.fit()}}else this.miss++;
  var t=this.pts.length>=3?this.base+u*this.per:(bs>0.6*sl?bp:e);this.decode(u,t);this.units++;this.line=Math.min(m.H,this.units*m.rows);
  if(this.miss>12){this.finish(true);return}
  var keepFrom=Math.floor(this.base+this.units*this.per-40*ms);if(keepFrom-this.o>4*this.fs)this.trim(this.end()-keepFrom)}
 this.finish(false)};
Rx.prototype.decode=function(u,t){var m=this.mode,ms=this.ms,W=m.W,self=this,ch={};
 m.chans.forEach(function(c){var n=c[2]==='C'?W/2:W,d=c[1]*ms/n,s=t+c[0]*ms,a=new Float32Array(n);for(var i=0;i<n;i++)a[i]=(self.avg(s+i*d+d*0.1,s+(i+1)*d-d*0.1)-1500)*255/800;ch[c[2]]=a});
 var put=function(row,x,q){var o=(row*W+x)*4;self.rgba[o]=q[0];self.rgba[o+1]=q[1];self.rgba[o+2]=q[2]};
 if(m.id==='r36'){var odd=this.avg(t+m.sep[0]*ms+ms,t+(m.sep[0]+m.sep[1])*ms-ms)>1900;if(u%2!==(odd?1:0)&&Math.abs(this.avg(t+m.sep[0]*ms+ms,t+(m.sep[0]+m.sep[1])*ms-ms)-1900)<250)odd=u%2===1;
  this['y'+(u%2)]=ch.Y;this[odd?'cu':'cv']=ch.C;if(u%2===1&&this.cu&&this.cv){for(var r=0;r<2;r++){var yy=this['y'+r];if(!yy)continue;for(var x=0;x<W;x++)put(u-1+r,x,fromYUV(yy[x],this.cu[x>>1],this.cv[x>>1]))}this.cb.lines&&this.cb.lines(u-1,2)}}
 else if(m.rows===1){for(var x=0;x<W;x++)put(u,x,[clamp(ch.R[x]),clamp(ch.G[x]),clamp(ch.B[x])]);this.cb.lines&&this.cb.lines(u,1)}
 else{for(var x=0;x<W;x++){put(2*u,x,fromYUV(ch.Y0[x],ch.U[x],ch.V[x]));put(2*u+1,x,fromYUV(ch.Y1[x],ch.U[x],ch.V[x]))}this.cb.lines&&this.cb.lines(2*u,2)}};
Rx.prototype.finish=function(partial){if(this.state!=='img')return;this.state='vis';this.done=!partial;this.partial=partial;this.scan=this.end();this.trim(Math.round(this.fs));this.scan=this.end();
 this.cb.done&&this.cb.done(this.rgba,partial,this.mode.name)};
Rx.prototype.flush=function(){if(this.state==='img')this.finish(true)};
Rx.prototype.progress=function(){return this.mode?this.line/this.mode.H:0};
var api={MODES:MODES,encode:encode,Rx:Rx,duration:function(k){return dur(MODES[k])},W:320,H:240,durationSec:dur(MODES.r36)};
if(typeof module!=='undefined'&&module.exports)module.exports=api;if(root)root.SSTV=api})(this);
