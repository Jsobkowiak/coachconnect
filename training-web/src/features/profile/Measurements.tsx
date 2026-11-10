import { useEffect, useState, type FormEvent } from 'react';
import { api, today, uid } from '../../shared/api';
import type { ProfileState } from './types';
import { measurementFields, measurementDateLabel, type MeasurementEntry } from './measurementFields';
import { MeasurementComparison } from './MeasurementComparison';
const fmt = (n:number) => n.toLocaleString('fr-FR',{maximumFractionDigits:2});
const dateLabel = measurementDateLabel;
export function Measurements({state,onSaved}:{state:ProfileState;onSaved:(state:ProfileState)=>void}) {
 const [entries,setEntries]=useState<MeasurementEntry[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const [open,setOpen]=useState(false),[busy,setBusy]=useState(false),[success,setSuccess]=useState('');
 const [date,setDate]=useState(today),[sync,setSync]=useState(false),[requestId,setRequestId]=useState(uid);
 const [dirty,setDirty]=useState(false);
 useEffect(()=>{window.dispatchEvent(new CustomEvent('measurements-dirty',{detail:dirty}));const warn=(e:BeforeUnloadEvent)=>{if(dirty)e.preventDefault();};window.addEventListener('beforeunload',warn);return()=>{window.removeEventListener('beforeunload',warn);window.dispatchEvent(new CustomEvent('measurements-dirty',{detail:false}));};},[dirty]);
 const [metric,setMetric]=useState('weightKg');
 useEffect(()=>{let active=true;api<MeasurementEntry[]>('/profile/body-measurements').then(v=>{if(active)setEntries(v);}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[]);
 async function save(e:FormEvent<HTMLFormElement>) {
  e.preventDefault();const f=new FormData(e.currentTarget), values:Record<string,number>={};
  for(const field of measurementFields){const raw=String(f.get(field.key)??'').trim();if(raw)values[field.key]=Number(raw);}
  if(!Object.keys(values).length){setError('Renseigne au moins une mesure.');return;}
  setBusy(true);setError('');setSuccess('');
  try {
   const entry=await api<MeasurementEntry>('/profile/body-measurements','POST',{id:requestId,measuredOn:date,values,notes:String(f.get('notes')??''),updateProfile:sync,profileRevision:state.profile!.revision});
   setEntries(old=>[entry,...old.filter(v=>v.id!==entry.id)].sort((a,b)=>b.measuredOn.localeCompare(a.measuredOn)||b.createdAt.localeCompare(a.createdAt)));
   setDirty(false);setOpen(false);setRequestId(uid());setSync(false);setSuccess('Mesures enregistrées.');
   if(sync){try{onSaved(await api<ProfileState>('/profile'));}catch{setError('Mesures enregistrées ; recharge la page pour actualiser le poids affiché et les kcal.');}}
  }catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 const readings=entries.filter(e=>e.measuredOn<=today()&&e.values[metric]!==undefined), field=measurementFields.find(f=>f.key===metric)!;
 const change=readings.length>1?readings[0].values[metric]-readings[readings.length-1].values[metric]:null;
 return <section className="measurement-book" aria-label="Carnet de mensurations">
  <header className="measurement-heading"><div><p className="eyebrow">MON ÉVOLUTION</p><h2>Carnet de mensurations</h2><p>Poids, stature et tours du corps. Un relevé mensuel dans les mêmes conditions permet de comparer ton évolution.</p></div><button className="primary" onClick={()=>{setOpen(true);setDate(today());setError('');setSuccess('');}} disabled={open}>Ajouter une mesure</button></header>
  {error&&<p className="error" role="alert">{error}</p>}{success&&<p className="profile-success" role="status">{success}</p>}
  <details className="measurement-guide"><summary>Bien prendre ses mesures</summary><p>Utilise un mètre ruban souple non extensible, posé au contact du corps sans comprimer la peau. Reste relâché et mesure dans les mêmes conditions, si possible avant l’entraînement. Fais deux relevés pour vérifier et garde le même point de mesure.</p><p>Les indications « Où mesurer ? » donnent les repères pour chaque zone. Pour les bras et les jambes, distingue bien la gauche de la droite.</p><p>Repères de pesée : <a href="https://www.england.nhs.uk/long-read/how-to-record-your-weight/" target="_blank" rel="noreferrer">NHS England</a>. Repères taille et hanches : <a href="https://www.who.int/publications/i/item/9789241501491" target="_blank" rel="noreferrer">OMS</a>. Les autres tours servent au suivi sportif : conserve surtout une méthode identique.</p></details>
  {open&&<form className="profile-form measurement-form" onSubmit={save} onChange={()=>setDirty(true)}>
   <label>Date de mesure<input aria-label="Date de mesure" type="date" disabled={busy} min="1900-01-01" max={today()} value={date} onChange={e=>{setDate(e.target.value);setSync(false);}} required/></label>
   {['Repères','Buste','Bras','Jambes'].map(group=><fieldset key={group}><legend>{group}</legend><div className="measurement-fields">{measurementFields.filter(f=>f.group===group).map(f=><div className="measurement-field" key={f.key}><label htmlFor={'measure-'+f.key}>{f.label} ({f.unit})</label><input id={'measure-'+f.key} name={f.key} type="number" disabled={busy} inputMode="decimal" min={f.min} max={f.max} step="0.01" placeholder="Facultatif"/><details><summary>Où mesurer ? <span className="sr-only">{f.label}</span></summary><p>{f.guide}</p></details></div>)}</div></fieldset>)}
   <label>Notes et conditions (facultatif)<textarea disabled={busy} name="notes" rows={3} maxLength={1000} placeholder="Ex. à jeun, cuisse à 15 cm au-dessus de la rotule…"/></label>
   <label className="profile-checkbox"><input type="checkbox" checked={sync} disabled={busy||date!==today()} onChange={e=>setSync(e.target.checked)}/>Actualiser aussi mon poids / ma stature de profil et les calculs de kcal</label><small>Disponible pour une mesure d’aujourd’hui contenant le poids ou la stature. Les autres mensurations sont conservées dans ce carnet.</small>
   <div className="profile-actions"><button type="button" disabled={busy} onClick={()=>{setDirty(false);setOpen(false);setRequestId(uid());setError('');setSync(false);}}>Annuler</button><button className="primary" disabled={busy} type="submit">{busy?'Enregistrement…':'Enregistrer les mesures'}</button></div>
  </form>}
  {loading?<p role="status">Chargement du carnet…</p>:entries.length===0?<p className="measurement-empty">Ton carnet est prêt. Ajoute ton premier relevé pour suivre ton évolution. Les anciennes mesures du profil restent disponibles ci-dessous.</p>:<>
   <label className="measurement-selector">Suivre une mesure<select value={metric} onChange={e=>setMetric(e.target.value)}>{measurementFields.map(f=><option value={f.key} key={f.key}>{f.label}</option>)}</select></label>
   {readings.length>0?<div className="measurement-progress"><strong>{fmt(readings[0].values[metric])} {field.unit}</strong><span>Dernier relevé : {dateLabel(readings[0].measuredOn,readings[0].datePrecision)}</span>{change!==null&&<span>Évolution depuis le {dateLabel(readings[readings.length-1].measuredOn,readings[readings.length-1].datePrecision)} : {change>0?'+':''}{fmt(change)} {field.unit}</span>}</div>:<p>Aucun relevé de {field.label.toLocaleLowerCase('fr-FR')} dans le carnet.</p>}
   <MeasurementComparison entries={entries}/>
   <h3>Tous mes relevés · {entries.length}</h3><p>Les relevés sont conservés par date. Pour corriger une valeur, ajoute un nouveau relevé et précise la correction dans les notes.</p>
   <div className="measurement-history">{entries.map(entry=><article key={entry.id}><header><strong>{dateLabel(entry.measuredOn,entry.datePrecision)}</strong>{entry.datePrecision==="month"&&<small>Jour non précisé</small>}{entry.measuredOn>today()&&<small>À venir · hors des courbes jusqu’à cette date</small>}{entry.updatedProfile&&<small>Profil actualisé à l’enregistrement</small>}</header><dl>{measurementFields.filter(f=>entry.values[f.key]!==undefined).map(f=><div key={f.key}><dt>{f.label}</dt><dd>{fmt(entry.values[f.key])} {f.unit}</dd></div>)}</dl>{entry.notes&&<p className="profile-notes">{entry.notes}</p>}</article>)}</div>
  </>}
 </section>;
}
