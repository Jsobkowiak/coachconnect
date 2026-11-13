import { useEffect, useState } from 'react';
import { MeasurementComparison } from '../profile/MeasurementComparison';
import type { MeasurementEntry } from '../profile/measurementFields';
import { api } from '../../shared/api';
import type { StatsReport, StatsSeries } from './types';
import { ProgressChart, formatValue, formatDate } from './ProgressChart';
const signed=(n:number)=>(n>0?'+':'')+formatValue(n);
function SeriesSummary({series}:{series:StatsSeries}) {
 const points=series.points;if(!points.length)return null;
 const first=points[0],last=points[points.length-1],delta=last.value-first.value,recent=series.recent;
 return <>
  <div className="stats-summary-grid">
   <article><span>Début de période observée</span><strong>{formatValue(first.value)} <small>{series.unit}</small></strong><small>{formatDate(first.date,first.datePrecision)}</small></article>
   <article><span>Dernier relevé</span><strong>{formatValue(last.value)} <small>{series.unit}</small></strong><small>{formatDate(last.date,last.datePrecision)}</small></article>
   <article><span>Écart sur la période</span><strong>{points.length>1?signed(delta):'—'} <small>{points.length>1?series.unit:''}</small></strong><small>{points.length>1&&first.value!==0?`${signed(delta/first.value*100)} % · ${points.length} relevés`:'Il faut au moins deux dates pour comparer.'}</small></article>
  </div>
  <div className="stats-comparison"><h3>La tendance récente</h3><p>Moyenne des 28 derniers jours comparée aux 28 jours précédents. Au moins 3 dates de relevés dans chaque fenêtre pour afficher l’écart.</p>
   {recent.change!==null?<div className="stats-comparison-values"><span>28 jours précédents<strong>{formatValue(recent.previousMean!)} {series.unit}</strong></span><span>28 derniers jours<strong>{formatValue(recent.recentMean!)} {series.unit}</strong></span><span>Écart<strong>{signed(recent.change)} {series.unit}{recent.percent!==null?` (${signed(recent.percent)} %)`:''}</strong></span></div>:<p className="stats-muted">Comparaison à compléter : {recent.previousCount} date(s) dans la fenêtre précédente, {recent.recentCount} dans la récente. Sur une période d’un mois, choisis 3 mois ou plus pour comparer les deux fenêtres.</p>}
  </div>
 </>;
}
const modeLabel=(mode:string)=>mode==='reps'?'répétitions':mode==='time'?'durée':'distance';
export function Stats() {
 const [includeReferences,setIncludeReferences]=useState(true);
 const [entries,setEntries]=useState<MeasurementEntry[]>([]),[diaryError,setDiaryError]=useState('');
 const [months,setMonths]=useState(0),[band,setBand]=useState('all'),[tab,setTab]=useState('exercise');
 const [report,setReport]=useState<StatsReport>(),[loading,setLoading]=useState(true),[error,setError]=useState(''),[retry,setRetry]=useState(0);
 const [exerciseKey,setExerciseKey]=useState(''),[metric,setMetric]=useState(''),[bodyKey,setBodyKey]=useState('');
 useEffect(()=>{
  let live=true;setLoading(true);setError('');const bounds=band==='all'?'':`&minReps=${band.split('-')[0]}&maxReps=${band.split('-')[1]}`;
  api<StatsReport>(`/stats?months=${months}${bounds}${tab==='body'&&includeReferences?'&includeReferenceMeasurements=true':''}`).then(v=>{if(live)setReport(v);}).catch(e=>{if(live)setError(e.message);}).finally(()=>{if(live)setLoading(false);});
  return()=>{live=false;};
 },[months,band,retry,tab,includeReferences]);
 useEffect(()=>{if(tab!=='body')return;let live=true;setDiaryError('');api<MeasurementEntry[]>('/profile/body-measurements').then(v=>{if(live)setEntries(v);}).catch(()=>{if(live)setDiaryError('Le comparatif du carnet n’a pas pu être chargé. Réessaie avec Actualiser.');});return()=>{live=false;};},[tab,retry]);
 const exercises=report?.exercises??[];
 const exercise=exercises.find(e=>e.id+':'+e.mode===exerciseKey)??exercises.find(e=>e.days>0)??exercises[0];
 const series=exercise?.series.find(s=>s.key===metric)??exercise?.series.find(s=>s.points.length>0)??exercise?.series[0];
 const body=report?.measurements.find(s=>s.key===bodyKey)??report?.measurements.find(s=>s.points.length>0)??report?.measurements[0];
 return <section className="stats-page" aria-label="Statistiques de progression">
  <header className="stats-heading"><p className="eyebrow">MES STATS</p><h1>Voir ce qui évolue</h1><p>Compare tes performances et tes mensurations au fil des semaines, sur les données que tu as réellement enregistrées.</p></header>
  <div className="stats-controls"><label>Période<select aria-label="Période" value={months} onChange={e=>setMonths(Number(e.target.value))}><option value={1}>1 mois</option><option value={3}>3 mois</option><option value={6}>6 mois</option><option value={12}>1 an</option><option value={0}>Tout l’historique</option></select></label><button onClick={()=>setRetry(v=>v+1)} disabled={loading}>Actualiser</button></div>
  <div className="stats-tabs" role="group" aria-label="Type de statistiques">{[['exercise','Exercices'],['body','Mensurations'],['attendance','Régularité']].map(([key,label])=><button key={key} aria-pressed={tab===key} onClick={()=>setTab(key)}>{label}</button>)}</div>
  {error&&<p className="error" role="alert">{error} <button onClick={()=>setRetry(v=>v+1)}>Réessayer</button></p>}
  {loading?<p role="status" className="stats-loading">Calcul des courbes…</p>:report&&!error&&<>
   <div className="stats-overview"><article><strong>{report.completedWorkouts}</strong><span>Séances terminées</span></article><article><strong>{exercises.filter(e=>e.days>0).length}</strong><span>Exercices suivis</span></article><article><strong>{report.measurementDays}</strong><span>Relevés corporels</span></article></div>
   {tab==='exercise'&&<section className="stats-panel" aria-label="Progression par exercice">
    <header><p className="eyebrow">MES PERFORMANCES</p><h2>Un mouvement, plusieurs repères</h2><p>Les variantes et les modes de saisie restent distincts. Seules les séries validées des séances terminées sont prises en compte.</p></header>
    {exercises.length>0?<>
     <div className="stats-filter-grid"><label>Exercice<select aria-label="Exercice" value={exercise.id+':'+exercise.mode} onChange={e=>{setExerciseKey(e.target.value);setMetric('');}}>{exercises.map(e=><option key={e.id+':'+e.mode} value={e.id+':'+e.mode}>{e.name} · {modeLabel(e.mode)} ({e.days} j)</option>)}</select></label>
      <label>Indicateur<select aria-label="Indicateur" value={series.key} onChange={e=>setMetric(e.target.value)}>{exercise.series.map(s=><option key={s.key} value={s.key}>{s.label}</option>)}</select></label>
      <label>Comparer les séries de<select aria-label="Comparer les séries de" value={band} onChange={e=>setBand(e.target.value)} disabled={exercise.mode!=='reps'}><option value="all">Toutes les répétitions</option><option value="1-5">1 à 5 répétitions</option><option value="6-10">6 à 10 répétitions</option><option value="11-20">11 à 20 répétitions</option><option value="21-1000">21 répétitions et plus</option></select></label>
     </div>
     {series&&<><h3>{series.label} · {exercise.name}</h3><ProgressChart key={exercise.id+':'+exercise.mode+series.key+months+band} points={series.points} unit={series.unit} label={series.label}/><SeriesSummary series={series}/></>}
     <details className="stats-method"><summary>Lire les courbes de performance</summary><p>Un point correspond à une journée. Si tu fais plusieurs séances du même exercice le même jour, les totaux sont additionnés et les meilleures séries sont regroupées.</p><p>La charge est celle saisie dans la séance : elle n’inclut pas le poids du corps. Le volume externe correspond à la somme charge × répétitions ; il n’est affiché que si chaque série retenue de la journée a une charge renseignée. Les répétitions restent visibles sans charge.</p><p>Compare une même variante et une plage de répétitions proche. Une durée ou une distance plus grande ne signifie pas forcément une meilleure performance : le contexte de l’effort compte. Aucune estimation de 1RM n’est déduite de tes séries.</p></details>
    </>:<div className="stats-empty"><strong>Ta première courbe commence à la prochaine séance</strong><p>Termine et enregistre une séance dans « Ma séance ». Les performances apparaîtront ici, même si tu modifies ou supprimes ensuite le bloc.</p></div>}
    {report.excludedInProgress>0&&<p className="stats-muted">{report.excludedInProgress} séance(s) en cours exclue(s). Termine-les pour les inclure dans les statistiques.</p>}
   </section>}
   {tab==='body'&&body&&<section className="stats-panel" aria-label="Progression des mensurations"><header><p className="eyebrow">MES MENSURATIONS</p><h2>Ton évolution, mesure après mesure</h2><p>Retrouve les relevés de ton carnet et les anciens poids et tailles de ton profil.</p></header>{diaryError&&<p role="alert" className="error">{diaryError}</p>}<MeasurementComparison entries={entries}/><label className="profile-checkbox"><input type="checkbox" checked={includeReferences} onChange={e=>setIncludeReferences(e.target.checked)}/>Inclure les relevés avec une date de référence à venir</label><p className="stats-muted">Les courbes suivent la période choisie. Les dates de référence à venir sont signalées sur les points et restent exclues des tendances sur 28 jours.</p><label className="stats-body-selector">Mesure à suivre<select aria-label="Mesure à suivre" value={body.key} onChange={e=>setBodyKey(e.target.value)}>{report.measurements.map(m=><option value={m.key} key={m.key}>{m.label} ({m.points.length} relevés)</option>)}</select></label><h3>{body.label}</h3><ProgressChart key={body.key+months} points={body.points} unit={body.unit} label={body.label}/><SeriesSummary series={body}/><details className="stats-method"><summary>Comprendre ces relevés</summary><p>Un point par jour et par mesure, ou par mois lorsque le jour est inconnu. Les relevés mensuels sont affichés au début du mois par convention, avec le mois seul comme libellé, et exclus des comparaisons sur 28 jours. Les relevés datés à venir apparaissent uniquement si l’option correspondante est cochée ; ils restent exclus des comparaisons sur 28 jours. Le dernier relevé du carnet pour la journée est retenu ; il prend priorité sur le poids ou la taille issus du profil. Les champs laissés vides ne créent aucun point et ne valent jamais zéro.</p><p>Une hausse ou une baisse n’est pas automatiquement bonne ou mauvaise : compare-la à ton objectif, à tes performances et à tes conditions de mesure. Les kcal estimées ne constituent pas un historique de ce que tu as mangé.</p><p>Ajoute tes prochains relevés depuis « Mon profil », avec les guides « Où mesurer ? ».</p></details></section>}
   {tab==='attendance'&&<section className="stats-panel" aria-label="Régularité des entraînements"><header><p className="eyebrow">MA RÉGULARITÉ</p><h2>Les séances que tu as terminées</h2><p>Nombre de séances réalisées par semaine, du lundi au dimanche. Les semaines sans séance enregistrée apparaissent à zéro.</p></header><ProgressChart key={'attendance'+months} points={report.attendance} unit="séances" label="Séances par semaine" bars/><p className="stats-muted">Les semaines aux limites de la période peuvent être partielles. Une semaine sans séance enregistrée n’indique pas si tu t’es entraîné en dehors de l’application.</p></section>}
   <aside className="stats-interpretation"><h2>Quand la courbe ralentit</h2><p>Regarde ensemble les performances sur un même mouvement, la régularité et les mensurations. Une semaine allégée ou un changement de répétitions peut expliquer une variation. Plusieurs semaines comparables donnent davantage de contexte qu’une séance isolée.</p><p>Les écarts affichés sont des observations : l’application ne change pas automatiquement tes entraînements ou tes calories.</p></aside>
  </>}
 </section>;
}
