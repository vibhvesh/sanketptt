// Robot36 SSTV encoder/decoder (pure JS, browser + node). 320x240, VIS 8, ~36 s.
(function(root){
var W=320,H=240,VIS=8;
var L={sync:9,porch:3,y:88,sep:4.5,porch2:1.5,c:44};L.line=L.sync+L.porch+L.y+L.sep+L.porch2+L.c; // 150 ms
function clamp(v){return v<0?0:v>255?255:v}
function toYUV(r,g,b){return[16+(65.738*r+129.057*g+25.064*b)/256,128+(-37.945*r-74.494*g+112.439*b)/256,128+(112.439*r-94.154*g-18.285*b)/256]} // Y,U(B-Y),V(R-Y)
function fromYUV(y,u,v){y=1.164*(y-16);u-=128;v-=128;return[clamp(y+1.596*v),clamp(y-0.813*v-0.391*u),clamp(y+2.018*u)]}
function v2f(v){return 1500+clamp(v)*800/255}
// rgba: Uint8ClampedArray W*H*4 -> Int16Array PCM at fs
function encode(rgba,fs){fs=fs||12000;var segs=[],t=0;function seg(d,f){segs.push([t,t+d,f]);t+=d}
 seg(300,1900);seg(10,1200);seg(300,1900);seg(30,1200);var p=0;for(var b=0;b<7;b++){var bit=(VIS>>b)&1;p^=bit;seg(30,bit?1100:1300)}seg(30,p?1100:1300);seg(30,1200);
 var Y=new Float32Array(W*H),U=new Float32Array(W*H),V=new Float32Array(W*H);
 for(var i=0;i<W*H;i++){var q=toYUV(rgba[i*4],rgba[i*4+1],rgba[i*4+2]);Y[i]=q[0];U[i]=q[1];V[i]=q[2]}
 for(var l=0;l<H;l++){(function(l){var ev=l%2===0,l2=ev?l+1:l-1;
  seg(L.sync,1200);seg(L.porch,1500);seg(L.y,function(fr){return v2f(Y[l*W+Math.min(W-1,Math.floor(fr*W))])});
  seg(L.sep,ev?1500:2300);seg(L.porch2,1900);
  seg(L.c,function(fr){var x=Math.min(159,Math.floor(fr*160))*2,C=ev?V:U,a=0;for(var k=0;k<2;k++)a+=C[l*W+x+k]+C[l2*W+x+k];return v2f(a/4)})})(l)}
 seg(300,1200); // tail
 var n=Math.ceil(t*fs/1000),out=new Int16Array(n),ph=0,s=0;
 for(var j=0;j<n;j++){var ms=j*1000/fs;while(s<segs.length-1&&ms>=segs[s][1])s++;var g=segs[s],f=typeof g[2]==='function'?g[2]((ms-g[0])/(g[1]-g[0])):g[2];
  ph+=2*Math.PI*f/fs;if(ph>2*Math.PI)ph-=2*Math.PI;out[j]=Math.round(Math.sin(ph)*16000)}
 return out}
// streaming decoder
function Rx(fs,cb){this.fs=fs||12000;this.cb=cb||{};this.x=[];this.f=[];this.fN=0;this.state='vis';this.lead=0;this.low=0;this.lowStart=-1;this.scan=0;
 this.rgba=new Uint8ClampedArray(W*H*4);for(var i=3;i<this.rgba.length;i+=4)this.rgba[i]=255;this.line=0;this.off=0;this.started=false;this.done=false}
Rx.prototype.push=function(i16){var x=this.x,f=this.f,K=2;for(var i=0;i<i16.length;i++)x.push(i16[i]);
 while(this.fN+K+1<x.length){var n=this.fN,num=0,den=0;for(var k=Math.max(1,n-K);k<=n+K;k++){num+=x[k]*(x[k-1]+x[k+1]);den+=2*x[k]*x[k]}
  var c=den>0?num/den:1;c=c>1?1:c<-1?-1:c;f.push(Math.acos(c)*this.fs/(2*Math.PI));this.fN++}
 this.run()};
Rx.prototype.avg=function(a,b){a=Math.max(0,Math.round(a));b=Math.min(this.f.length,Math.round(b));if(b<=a)b=a+1;var s=0,n=0;for(var i=a;i<b&&i<this.f.length;i++){s+=this.f[i];n++}return n?s/n:0};
Rx.prototype.run=function(){var f=this.f,fs=this.fs,ms=fs/1000;
 if(this.state==='vis'){for(;this.scan<f.length;this.scan++){var v=f[this.scan];
   if(Math.abs(v-1900)<120){this.lead++;this.low=0}else{if(this.lead>0){this.prevLead=this.lead}if(Math.abs(v-1200)>=120)this.miss=(this.miss||0)+1}if(Math.abs(v-1900)<120){}else if(Math.abs(v-1200)<120){if(this.low===0){this.lowStart=this.scan;this.leadBefore=this.prevLead||0;this.prevLead=0}this.low++;this.lead=0;
    if(this.low>=20*ms&&this.leadBefore>=150*ms){this.s0=this.lowStart;this.state='bits';break}}else{this.lead=0;if(this.low>0)this.prevLead=0;this.low=0}}}
 if(this.state==='bits'){var s0=this.s0;if(f.length<s0+300*ms)return;var code=0,par=0;
  for(var b=0;b<8;b++){var c=s0+(30+30*b)*ms,bit=this.avg(c+5*ms,c+25*ms)<1200?1:0;if(b<7)code|=bit<<b;par^=bit}
  if(code!==VIS||par!==0){this.state='vis';this.scan=s0+20*ms;this.lead=0;this.low=0;return}
  this.state='img';this.img0=s0+300*ms;this.started=true;this.cb.start&&this.cb.start('Robot36')}
 if(this.state==='img'){while(this.line<H){var l=this.line,st=this.img0+l*L.line*ms+this.off;if(f.length<st+L.line*ms+12)return;
   if(l>0){for(var n=Math.round(st-12);n<st+12;n++)if(f[n]<1350&&f[n-1]>=1350){var d=n-st;this.off+=0*d;st=this.img0+l*L.line*ms+this.off;break}}
   var yS=st+(L.sync+L.porch)*ms,yd=L.y*ms/W,cS=st+(L.sync+L.porch+L.y+L.sep+L.porch2)*ms,cd=L.c*ms/160;
   var ys=new Float32Array(W),cs=new Float32Array(160);
   for(var i=0;i<W;i++)ys[i]=(this.avg(yS+i*yd+0.2,yS+(i+1)*yd-0.2)-1500)*255/800;
   for(var i=0;i<160;i++)cs[i]=(this.avg(cS+i*cd+0.3,cS+(i+1)*cd-0.3)-1500)*255/800;
   this['y'+(l%2)]=ys;this['c'+(l%2)]=cs;
   if(l%2===1){for(var r=0;r<2;r++){var yy=this['y'+r],row=l-1+r;for(var i=0;i<W;i++){var q=fromYUV(yy[i],this.c1[i>>1],this.c0[i>>1]),o=(row*W+i)*4;this.rgba[o]=q[0];this.rgba[o+1]=q[1];this.rgba[o+2]=q[2]}}
    this.cb.lines&&this.cb.lines(l-1,2)}
   this.line++}
  if(!this.done){this.done=true;this.cb.done&&this.cb.done(this.rgba)}}};
Rx.prototype.progress=function(){return this.line/H};
var api={W:W,H:H,encode:encode,Rx:Rx,lineMs:L.line,durationSec:(910+H*L.line+300)/1000};
if(typeof module!=='undefined')module.exports=api;else root.SSTV=api})(this);
