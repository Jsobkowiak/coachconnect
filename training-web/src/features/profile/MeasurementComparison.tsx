import { useState } from 'react';
import { today } from '../../shared/api';
import { measurementFields, measurementDateLabel, type MeasurementEntry } from './measurementFields';

export function MeasurementComparison({ entries }: { entries: MeasurementEntry[] }) {
 const [firstId, setFirstId] = useState(''), [lastId, setLastId] = useState('');
 const ordered = [...entries].sort((a,b)=>a.measuredOn.localeCompare(b.measuredOn)||a.createdAt.localeCompare(b.createdAt));
 if (ordered.length < 2) return null;
 const first = ordered.find(e=>e.id===firstId) ?? ordered[0];
 const last = ordered.find(e=>e.id===lastId) ?? ordered[ordered.length-1];
 const fields = measurementFields.filter(f=>first.values[f.key]!==undefined||last.values[f.key]!==undefined);
 const label = (entry:MeasurementEntry)=>measurementDateLabel(entry.measuredOn,entry.datePrecision)+(entry.measuredOn>today()?' · référence à venir':'');
 const value = (entry:MeasurementEntry,key:string,unit:string)=>entry.values[key]===undefined?'—':`${entry.values[key].toLocaleString('fr-FR',{maximumFractionDigits:2})} ${unit}`;
 return <section className="measurement-comparison" aria-label="Comparaison des relevés">
  <h3>Comparer deux relevés du carnet</h3>
  <p>Tous les relevés enregistrés sont disponibles ici, indépendamment de la période des courbes. Un tiret signifie que la mesure n’a pas été renseignée. Les méthodes de mesure différentes restent séparées.</p>
  <div className="measurement-comparison-selectors">
   <label>Premier relevé<select value={first.id} onChange={e=>setFirstId(e.target.value)}>{ordered.map(entry=><option key={entry.id} value={entry.id}>{label(entry)}</option>)}</select></label>
   <label>Second relevé<select value={last.id} onChange={e=>setLastId(e.target.value)}>{ordered.map(entry=><option key={entry.id} value={entry.id}>{label(entry)}</option>)}</select></label>
  </div>
  <div className="measurement-comparison-scroll" tabIndex={0} role="region" aria-label="Tableau comparatif des mensurations">
   <table><caption className="sr-only">Mensurations des deux relevés sélectionnés</caption><thead><tr><th scope="col">Mesure</th><th scope="col">{label(first)}</th><th scope="col">{label(last)}</th></tr></thead>
   <tbody>{fields.map(f=><tr key={f.key}><th scope="row">{f.label}</th><td>{value(first,f.key,f.unit)}</td><td>{value(last,f.key,f.unit)}</td></tr>)}</tbody></table>
  </div>
 </section>;
}
