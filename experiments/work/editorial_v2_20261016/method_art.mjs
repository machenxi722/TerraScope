import fs from 'node:fs/promises';import path from 'node:path';
import {paper}from'../alignment_revision/diagram_utils.mjs';
const C={ink:'#233C48',edge:'#83969D',blue:'#DCECF5',db:'#427C9C',cyan:'#B9DCEB',gold:'#F7E6C6',orange:'#BA7B48',sage:'#DDEBDA',green:'#54856B',lav:'#E7E0F2',purple:'#8971A8',soft:'#F7F9FA',grid:'#E0E8EB'};
export function mix(a,b,t){const f=s=>[1,3,5].map(i=>parseInt(s.slice(i,i+2),16));const x=f(a),y=f(b);return'#'+x.map((v,i)=>Math.round(v*(1-t)+y[i]*t).toString(16).padStart(2,'0')).join('');}
export function art(s){
const p=paper(s),{text,box,shape,arrow,img}=p;
const tx=(str,x,y,w,h,size=21,bold=false,col=C.ink,align='left')=>text(str,x,y,w,h,size,bold,align,col);
function line(x1,y1,x2,y2,col=C.edge,width=1.2,dash=false){const l=Math.min(x1,x2),t=Math.min(y1,y2),w=Math.max(.1,Math.abs(x2-x1)),h=Math.max(.1,Math.abs(y2-y1));return s.shapes.add({geometry:'custom',position:{left:l,top:t,width:w,height:h},fill:'none',line:{fill:col,width,style:dash?'dash':'solid'},customPaths:[{width:w,height:h,commands:[{moveTo:{x:x1-l,y:y1-t}},{lineTo:{x:x2-l,y:y2-t}}]}]});}
function poly(pts,fill,edge=C.edge,lw=.8){const xx=pts.map(p=>p[0]),yy=pts.map(p=>p[1]),x=Math.min(...xx),y=Math.min(...yy),w=Math.max(...xx)-x,h=Math.max(...yy)-y;return s.shapes.add({geometry:'custom',position:{left:x,top:y,width:w,height:h},fill,line:{fill:edge,width:lw,style:'solid'},customPaths:[{width:w,height:h,commands:[{moveTo:{x:pts[0][0]-x,y:pts[0][1]-y}},...pts.slice(1).map(p=>({lineTo:{x:p[0]-x,y:p[1]-y}})),{close:{}}]}]});}
function region(title,x,y,w,h,col=C.db,fill='#FFFFFF'){const r=box(x,y,w,h,fill,mix(col,'#FFFFFF',.35));r.line={fill:mix(col,'#FFFFFF',.28),width:1.15,style:'dash'};tx(title,x+15,y+9,w-30,29,23,true,col);return r;}
function module(title,x,y,w,h,fill=C.blue,col=C.db,sub=''){box(x+3,y+3,w,h,'#EDF1F2','none');box(x,y,w,h,fill,mix(col,'#FFFFFF',.3));tx(title,x+9,y+(sub?3:4),w-18,sub?30:h-8,w<130?18:w<190?20:22,true,C.ink,'center');if(sub)tx(sub,x+9,y+h-24,w-18,21,16,false,col,'center');}
function freeze(x,y,r=10){for(let k=0;k<3;k++){const a=k*Math.PI/3;line(x-r*Math.cos(a),y-r*Math.sin(a),x+r*Math.cos(a),y+r*Math.sin(a),C.db,1.7);}for(let k=0;k<6;k++){const a=k*Math.PI/3;let xx=x+r*.65*Math.cos(a),yy=y+r*.65*Math.sin(a);for(const d of [-.8,.8])line(xx,yy,xx-r*.32*Math.cos(a+d),yy-r*.32*Math.sin(a+d),C.db,1.3);}}
function learn(x,y){poly([[x,y-12],[x+7,y-3],[x+9,y+4],[x+5,y+11],[x-3,y+12],[x-9,y+6],[x-8,y-2],[x-4,y+2]],C.orange,'none');poly([[x,y-1],[x+4,y+5],[x+2,y+10],[x-2,y+10],[x-4,y+5]],'#F7DEAF','none');}
function vec(x,y,n,col,w=13,h=24,gap=4){for(let i=0;i<n;i++){const z=box(x+i*(w+gap),y,w,h,mix(col,'#FFFFFF',i%3===0?.05:.25),mix(col,C.ink,.2));z.line.width=.7;}}
function tensor(x,y,w,h,col=C.blue,n=3,grid=5){for(let k=n-1;k>=0;k--){let xx=x+k*5,yy=y-k*5;shape('rect',xx,yy,w,h,mix(col,'#FFFFFF',.12*k),mix(C.db,'#FFFFFF',.35),.75);}for(let i=1;i<grid;i++){line(x+i*w/grid,y,x+i*w/grid,y+h,mix(C.db,'#FFFFFF',.65),.5);line(x,y+i*h/grid,x+w,y+i*h/grid,mix(C.db,'#FFFFFF',.65),.5);}poly([[x+w,y],[x+w+10,y-10],[x+w+10,y+h-10],[x+w,y+h]],mix(col,C.db,.12),mix(C.db,'#FFFFFF',.4),.65);}
function layerStack(x,y,w,h,col=C.lav,n=3){for(let i=n-1;i>=0;i--){box(x+i*5,y-i*5,w,h,mix(col,'#FFFFFF',i*.1),C.edge);}for(let i=0;i<3;i++)box(x+12,y+12+i*(h-24)/3,w-24,(h-30)/3,mix(col,'#FFFFFF',.35),'none');}
function cap(str){line(43,655,1237,655,'#B7CAC3',1);tx(str,48,664,1184,28,22,true,'#335B4A');}
return{...p,tx,line,poly,region,module,freeze,learn,vec,tensor,layerStack,cap};
}
