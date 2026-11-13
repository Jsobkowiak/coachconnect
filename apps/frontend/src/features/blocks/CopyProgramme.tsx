import { useEffect, useRef, useState } from 'react';
import type { Cycle } from '../../shared/types';
import { copyProgramme } from './programme';

export function CopyProgramme({ source, cycles, onCopy, onClose }: {
  source: Cycle; cycles: Cycle[]; onCopy: (cycle: Cycle) => Promise<void>; onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  const targets = cycles.filter(c => c.id !== source.id);
  const [targetId, setTargetId] = useState(targets[0]?.id ?? '');
  const [sourceWeek, setSourceWeek] = useState('all');
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const target = targets.find(c => c.id === targetId);
  const count = target?.weeks.reduce((n, w) => n + w.sessions.length, 0) ?? 0;
  return <dialog ref={dialog} className="panel copy-programme" aria-labelledby="copy-title" onCancel={e => { e.preventDefault(); if (!busy) onClose(); }}>
    <h2 id="copy-title">Copier le programme</h2><p>Source : <strong>{source.name}</strong></p>
    {targets.length ? <>
      <fieldset disabled={busy}>
        <label>Bloc destinataire<select aria-label="Bloc destinataire" autoFocus value={targetId} onChange={e => { setTargetId(e.target.value); setConfirmed(false); }}>{targets.map(c => <option key={c.id} value={c.id}>{c.name} · {c.durationWeeks} semaines</option>)}</select></label>
        <label>Programme à copier<select aria-label="Programme à copier" value={sourceWeek} onChange={e => { setSourceWeek(e.target.value); setConfirmed(false); }}><option value="all">Toutes les semaines du bloc source</option>{source.weeks.map((w, i) => <option value={i} key={i}>Semaine {w.number}, répétée dans le bloc destinataire</option>)}</select></label>
        {target && <p>Les séances des {target.durationWeeks} semaines de « {target.name} » seront remplacées ({count} séances actuellement). {sourceWeek === 'all' && target.durationWeeks !== source.durationWeeks && (target.durationWeeks > source.durationWeeks ? 'Le programme source sera répété dans l’ordre pour remplir les semaines restantes.' : 'Seules les premières semaines du programme source seront utilisées.')} Les dates, objectifs et semaines allégées du destinataire sont conservés. Ajuste les charges des semaines allégées après la copie.</p>}
        <p>Les performances déjà enregistrées sont conservées.</p>
        <label className="check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>Je confirme le remplacement des séances prévues.</label>
      </fieldset>
      {error && <p role="alert" className="error">{error}</p>}
      <div className="actions"><button disabled={busy} onClick={onClose}>Annuler</button><button className="primary" disabled={busy || !confirmed || !target} onClick={async () => { if (!target) return; setBusy(true); setError(''); try { await onCopy(copyProgramme(source, target, sourceWeek === 'all' ? undefined : Number(sourceWeek))); onClose(); } catch(e) { setError((e as Error).message); } finally { setBusy(false); } }}>{busy ? 'Copie en cours…' : 'Copier et enregistrer'}</button></div>
    </> : <><p>Crée d’abord un autre bloc, ou utilise « Dupliquer » pour créer une copie complète de ce bloc.</p><button autoFocus onClick={onClose}>Fermer</button></>}
  </dialog>;
}
