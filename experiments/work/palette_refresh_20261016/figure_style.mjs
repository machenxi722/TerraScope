import {mix} from './styled_art.mjs';
export function figureArt(a){
 const old=a.box;
 function box(x,y,w,h,fill='#FFFFFF',edge='#B3C0CD'){
  const q=old(x,y,w,h,fill,edge);
  if(typeof fill==='string'&&/^#[0-9A-F]{6}$/i.test(fill)&&fill.toUpperCase()!=='#FFFFFF'){
   const c=typeof edge==='string'&&/^#[0-9A-F]{6}$/i.test(edge)?edge:'#8095AF';
   if(w>=250&&h>=120){
    q.fill={type:'solid',color:mix(fill,'#FFFFFF',.50),pattern:{type:'lightDown',color:mix(mix(fill,'#FFFFFF',.50),c,.17)}};
    q.line={fill:mix(c,'#294F82',.1),width:1.3,style:'solid'};
   }else if(w>=80&&h>=32){
    q.fill={type:'gradient',gradientKind:'linear',angleDeg:90,stops:[{offset:0,color:mix(fill,'#FFFFFF',.38)},{offset:100000,color:fill}]};
    q.line={fill:mix(c,'#203653',.10),width:1.05,style:'solid'};
   }
  }
  return q;
 }
 return {...a,box};
}
