import { useEffect, useRef, useState } from 'react';
import type { StatsPoint } from './types';
export const formatValue=(value:number)=>value.toLocaleString('fr-FR',{maximumFractionDigits:2});
export const formatDate=(date:string,precision?:string)=>new Date(date+'T12:00:00').toLocaleDateString('fr-FR',precision==='month'?{month:'long',year:'numeric'}:undefined);
const time=(date:string)=>new Date(date+'T12:00:00Z').getTime();
export function ProgressChart({points,unit,label,bars=false}:{points:StatsPoint[];unit:string;label:string;bars?:boolean}) {
 const [index,setIndex]=useState<number|null>(null);
 const svg=useRef<SVGSVGElement>(null),[chartWidth,setChartWidth]=useState(800);
 useEffect(()=>{if(!svg.current)return;const resize=new ResizeObserver(entries=>{const w=entries[0]?.contentRect.width;if(w)setChartWidth(Math.max(220,w));});resize.observe(svg.current);return()=>resize.disconnect();},[points.length]);
 if(!points.length)return <div className="stats-empty"><strong>Pas encore de données pour cette courbe</strong><p>Enregistre une séance terminée ou une mesure, ou élargis la période sélectionnée.</p></div>;
 const selected=Math.min(index??points.length-1,points.length-1),point=points[selected];
 const width=chartWidth,height=270,left=60,right=20,top=22,bottom=44,plotWidth=width-left-right,plotHeight=height-top-bottom;
 const values=points.map(p=>p.value),min=Math.min(...values),max=Math.max(...values),padding=Math.max((max-min)*.15,Math.abs(max)*.02,.5);
 const low=bars?0:Math.max(0,min-padding),high=bars?Math.max(1,max*1.2):max+padding;
 const first=time(points[0].date),last=time(points[points.length-1].date),span=Math.max(86400000,last-first);
 const x=(p:StatsPoint)=>points.length===1?left+plotWidth/2:left+(time(p.date)-first)/span*plotWidth;
 const y=(v:number)=>top+plotHeight-(v-low)/(high-low)*plotHeight;
 const path=points.map((p,i)=>`${i?'L':'M'} ${x(p)} ${y(p.value)}`).join(' ');
 const compact=(n:number)=>new Intl.NumberFormat('fr-FR',{notation:Math.abs(n)>=10000?'compact':'standard',maximumFractionDigits:1}).format(n);
 return <div className="progress-chart">
  <div className="chart-reading" aria-live="polite"><span>{formatDate(point.date,point.datePrecision)}</span><strong>{formatValue(point.value)} <small>{unit}</small></strong>{point.detail&&<span>{point.detail}</span>}</div>
  <svg ref={svg} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${label}. ${points.length} relevés. Du ${formatDate(points[0].date,points[0].datePrecision)} au ${formatDate(points[points.length-1].date,points[points.length-1].datePrecision)}.`} onPointerMove={e=>{
   const rect=e.currentTarget.getBoundingClientRect();const pointer=(e.clientX-rect.left)/rect.width*width;
   let nearest=0;for(let i=1;i<points.length;i++)if(Math.abs(x(points[i])-pointer)<Math.abs(x(points[nearest])-pointer))nearest=i;setIndex(nearest);
  }}>
   <title>{label} ({unit})</title>
   {[0,1,2,3,4].map(i=>{const value=low+(high-low)*i/4;return <g key={i}><line className="chart-gridline" x1={left} x2={width-right} y1={y(value)} y2={y(value)}/><text x={left-12} y={y(value)+4} textAnchor="end">{compact(value)}</text></g>;})}
   {bars?points.map((p,i)=><rect className={i===selected?'chart-bar selected':'chart-bar'} key={i} x={x(p)-Math.min(18,plotWidth/points.length*.65)/2} y={y(p.value)} width={Math.min(18,plotWidth/points.length*.65)} height={Math.max(0,y(0)-y(p.value))} rx="3"/>):<>
    {points.length>1&&<path className="chart-line" d={path}/>}
    {points.length<160&&points.map((p,i)=><circle className="chart-point" key={i} cx={x(p)} cy={y(p.value)} r={i===selected?6:3}/>)}
   </>}
   <line className="chart-cursor" x1={x(point)} x2={x(point)} y1={top} y2={top+plotHeight}/>
   <circle className="chart-highlight" cx={x(point)} cy={y(point.value)} r="6"/>
   <text x={left} y={height-12}>{formatDate(points[0].date,points[0].datePrecision)}</text>
   {points.length>1&&<text x={width-right} y={height-12} textAnchor="end">{formatDate(points[points.length-1].date,points[points.length-1].datePrecision)}</text>}
  </svg>
  {points.length>1&&<label className="chart-explorer">Explorer les relevés<input aria-label={`Explorer ${label}`} type="range" min={0} max={points.length-1} value={selected} onChange={e=>setIndex(Number(e.target.value))}/><small>Survole la courbe ou déplace le curseur. Les dates sont espacées selon le temps écoulé.</small></label>}
  <details className="chart-data"><summary>Voir les données du graphique ({points.length})</summary><div className="stats-table"><table><thead><tr><th>Date</th><th>Valeur ({unit})</th><th>Détail</th></tr></thead><tbody>{points.map((p,i)=><tr key={i}><td>{formatDate(p.date,p.datePrecision)}</td><td>{formatValue(p.value)}</td><td>{p.detail??'—'}</td></tr>)}</tbody></table></div></details>
 </div>;
}
