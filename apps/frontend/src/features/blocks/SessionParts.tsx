import type { Session } from '../../shared/types';
import { addPart, formats, orderExercises } from './programme';

export function SessionParts({ session, selected, onSelect, onChange }: {
  session: Session; selected?: string; onSelect: (id: string) => void;
  onChange: (fn: (session: Session) => void) => void;
}) {
  const parts = session.parts ?? [], current = parts.find(p => p.id === selected);
  const index = parts.findIndex(p => p.id === selected);
  return <section className="session-parts" aria-label="Parties de la séance">
    <header><div><h3>Déroulé de la séance</h3><p>Force, puis un ou plusieurs circuits : chaque partie a ses propres exercices.</p></div>
      <button disabled={parts.length >= 12} onClick={() => { const draft = structuredClone(session); const id = addPart(draft); onChange(s => Object.assign(s, draft)); onSelect(id); }}>+ Ajouter une partie</button>
    </header>
    {parts.length > 0 && <>
      <div className="session-tabs" aria-label="Choisir une partie">{parts.map((p, i) => <button key={p.id} className={p.id === selected ? 'selected' : ''} aria-pressed={p.id === selected} onClick={() => onSelect(p.id)}>{i + 1}. {p.title}<small>{formats[p.format]} · {session.exercises.filter(e => e.partId === p.id).length} exercices</small></button>)}</div>
      {current && <>
        <div className="actions">
          <button disabled={index === 0} aria-label="Monter la partie" onClick={() => onChange(s => { [s.parts![index - 1], s.parts![index]] = [s.parts![index], s.parts![index - 1]]; orderExercises(s); })}>↑</button>
          <button disabled={index === parts.length - 1} aria-label="Descendre la partie" onClick={() => onChange(s => { [s.parts![index + 1], s.parts![index]] = [s.parts![index], s.parts![index + 1]]; orderExercises(s); })}>↓</button>
          <button className="danger" disabled={parts.length === 1} onClick={() => { if (confirm(`Supprimer « ${current.title} » et ses exercices prévus ?`)) onChange(s => { s.parts = s.parts!.filter(p => p.id !== current.id); s.exercises = s.exercises.filter(p => p.partId !== current.id); }); }}>Supprimer la partie</button>
        </div>
        <div className="form-grid">
          <label>Nom de la partie<input maxLength={120} value={current.title} onChange={e => onChange(s => { s.parts![index].title = e.target.value; })}/></label>
          <label>Format de la partie<select value={current.format} onChange={e => onChange(s => { s.parts![index].format = e.target.value; })}>{Object.entries(formats).map(([v, label]) => <option key={v} value={v}>{label}</option>)}</select></label>
          <label>Durée / time cap de la partie (min)<input type="number" min={1} max={300} value={current.timeCapMinutes ?? ''} onChange={e => onChange(s => { s.parts![index].timeCapMinutes = e.target.value ? Number(e.target.value) : null; })}/></label>
          <label>Consignes de la partie<textarea maxLength={2000} placeholder="Ex. 5 tours, repos 2 min avant la suite…" value={current.notes ?? ''} onChange={e => onChange(s => { s.parts![index].notes = e.target.value; })}/></label>
        </div>
        <p>Exercices de « {current.title} ». Pour un AMRAP, indique les répétitions par tour et utilise les consignes pour préciser le déroulé.</p>
      </>}
    </>}
  </section>;
}
