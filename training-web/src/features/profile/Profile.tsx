import { useEffect, useState, type FormEvent } from 'react';
import { api } from '../../shared/api';
import { Measurements } from './Measurements';
import type { Measurement, ProfileData, ProfileState } from './types';
const goals = [['maintenance','Maintenir mon poids'],['muscle_gain','Prendre du muscle'],['fat_loss','Perdre du poids'],['performance','Améliorer mes performances']];
const activities = [['low','Peu actif · journées surtout assises'],['moderate','Modérément actif · marche et sport réguliers'],['active','Actif · journées mobiles et sport fréquent'],['very_active','Très actif · travail physique ou entraînement soutenu']];
const levels = [['beginner','Débutant'],['intermediate','Intermédiaire'],['advanced','Confirmé']];
const number = (n:number) => new Intl.NumberFormat('fr-FR',{maximumFractionDigits:2}).format(n);
export function Profile({state,onSaved}:{state:ProfileState;onSaved:(s:ProfileState)=>void}) {
 const [editing,setEditing]=useState(!state.profile), [busy,setBusy]=useState(false), [error,setError]=useState(''),[saved,setSaved]=useState(false);
 const [measurementDirty,setMeasurementDirty]=useState(false);
 useEffect(()=>{const handler=(e:Event)=>setMeasurementDirty((e as CustomEvent<boolean>).detail);window.addEventListener('measurements-dirty',handler);return()=>window.removeEventListener('measurements-dirty',handler);},[]);
 const [history,setHistory]=useState<Measurement[]>([]),[historyError,setHistoryError]=useState('');
 useEffect(()=>{if(state.profile)api<Measurement[]>('/profile/measurements').then(setHistory).catch(()=>setHistoryError('Le suivi des mesures est indisponible.'));},[state.profile?.revision]);
 async function submit(e:FormEvent<HTMLFormElement>){
  e.preventDefault(); const f=new FormData(e.currentTarget);
  const text=(k:string)=>String(f.get(k)??'');
  const data:ProfileData={displayName:text('displayName'),birthDate:text('birthDate'),weightKg:Number(text('weightKg')),heightCm:Number(text('heightCm')),sex:state.profile?.data.sex??'unspecified',activityLevel:text('activityLevel'),goal:text('goal'),experience:text('experience'),weeklySessions:Number(text('weeklySessions')),targetWeightKg:text('targetWeightKg')?Number(text('targetWeightKg')):null,trainingNotes:text('trainingNotes'),calorieEstimatesEnabled:state.profile?.data.calorieEstimatesEnabled??false};
  setBusy(true);setError('');setSaved(false);
  try{const result=await api<ProfileState>('/profile','PUT',{revision:state.profile?.revision??0,data});onSaved(result);setEditing(false);setSaved(true);}catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 const d=state.profile?.data;
 return <section className="profile-page" aria-label="Profil sportif">
  <header className="profile-heading"><div><p className="eyebrow">{d?'MON PROFIL':'BIENVENUE CHEZ TOI'}</p><h1>{d?'Tes repères, ton évolution':'Commençons par ton profil sportif'}</h1><p>{d?'Tes mesures et tes objectifs pour suivre ta progression.':'Quelques informations pour préparer tes entraînements et suivre ta progression.'}</p></div>{d&&!editing&&<button onClick={()=>{if(measurementDirty&&!confirm('Les mensurations ne sont pas enregistrées. Ouvrir la modification du profil ?'))return;setEditing(true);setSaved(false);}}>Modifier mon profil</button>}</header>
  {saved&&<p className="profile-success" role="status">Profil enregistré.</p>}
  {editing?<form onSubmit={submit} className="profile-form" key={state.profile?.revision??'first'}>
   <fieldset><legend>1. Tes mesures</legend><div className="profile-fields">
    <label>Prénom ou pseudo (facultatif)<input name="displayName" maxLength={80} autoComplete="given-name" defaultValue={d?.displayName??''}/></label>
    <label>Date de naissance<input name="birthDate" type="date" autoComplete="bday" required defaultValue={d?.birthDate??''}/><small>Ton âge sera actualisé automatiquement.</small></label>
    <label>Poids actuel (kg)<input name="weightKg" type="number" inputMode="decimal" min="25" max="350" step="0.01" required placeholder="Ex. 75" defaultValue={d?.weightKg??''}/></label>
    <label>Taille (cm)<input name="heightCm" type="number" inputMode="decimal" min="100" max="250" step="0.01" required placeholder="Ex. 175" defaultValue={d?.heightCm??''}/></label>
    <label>Poids visé (kg, facultatif)<input name="targetWeightKg" type="number" inputMode="decimal" min="25" max="350" step="0.01" defaultValue={d?.targetWeightKg??''}/></label>
   </div></fieldset>
   <fieldset><legend>2. Ton activité et tes objectifs</legend><div className="profile-fields">
    <label>Objectif principal<select name="goal" required defaultValue={d?.goal??''}><option value="" disabled>Choisir un objectif</option>{goals.map(([v,l])=><option value={v} key={v}>{l}</option>)}</select></label>
    <label>Activité globale<select name="activityLevel" required defaultValue={d?.activityLevel??''}><option value="" disabled>Choisir ton niveau d’activité</option>{activities.map(([v,l])=><option value={v} key={v}>{l}</option>)}</select><small>Inclus tes déplacements, ton travail et le sport.</small></label>
    <label>Expérience sportive<select name="experience" required defaultValue={d?.experience??''}><option value="" disabled>Choisir ton expérience</option>{levels.map(([v,l])=><option value={v} key={v}>{l}</option>)}</select></label>
    <label>Séances prévues par semaine<input name="weeklySessions" type="number" inputMode="numeric" min="0" max="14" step="1" required defaultValue={d?.weeklySessions??''}/></label>
   </div><label>Préférences et contraintes d’entraînement (facultatif)<textarea name="trainingNotes" rows={3} maxLength={1000} defaultValue={d?.trainingNotes??''} placeholder="Matériel disponible, mouvements à adapter, préférences…"/></label>
   </fieldset>
   {error&&<p role="alert" className="error">{error}</p>}
   <div className="profile-actions">{d&&<button type="button" disabled={busy} onClick={()=>{setEditing(false);setError('');}}>Annuler</button>}<button className="primary" disabled={busy} type="submit">{busy?'Enregistrement…':d?'Enregistrer le profil':'Enregistrer et commencer'}</button></div>
  </form>:d&&<>
   <div className="profile-metrics">{[[`${number(d.weightKg)} kg`,'Poids actuel'],[`${number(d.heightCm)} cm`,'Taille'],[`${state.ageYears} ans`,'Âge'],[`${d.weeklySessions}`,'Séances / semaine']].map(([value,label])=><article key={label}><strong>{value}</strong><span>{label}</span></article>)}</div>
   <div className="profile-summary"><p><strong>{d.displayName||'Mon profil sportif'}</strong> · {goals.find(([v])=>v===d.goal)?.[1]} · {levels.find(([v])=>v===d.experience)?.[1]}</p><p>{activities.find(([v])=>v===d.activityLevel)?.[1]}{d.targetWeightKg?` · Poids visé : ${number(d.targetWeightKg)} kg`:''}</p>{d.trainingNotes&&<p className="profile-notes">{d.trainingNotes}</p>}</div>
   <Measurements state={state} onSaved={onSaved}/>
   <section className="profile-history"><h2>Historique des poids et tailles du profil</h2><p>Chaque changement de poids ou de taille conserve les mesures précédentes.</p>{historyError&&<p role="alert">{historyError}</p>}<div className="profile-table"><table><thead><tr><th>Date de mesure</th><th>Poids</th><th>Taille</th></tr></thead><tbody>{history.map(m=><tr key={m.id}><td>{new Date(m.recordedAt).toLocaleString('fr-FR',{dateStyle:'short',timeStyle:'short'})}</td><td>{number(m.weightKg)} kg</td><td>{number(m.heightCm)} cm</td></tr>)}</tbody></table></div></section>
  </>}
 </section>;
}
