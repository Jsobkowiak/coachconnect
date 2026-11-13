import { uid } from '../../shared/api';
import type { Cycle, Session, SessionPart } from '../../shared/types';

export const formats: Record<string, string> = { traditional: 'Force / classique', circuit: 'Circuit / superset', amrap: 'AMRAP', emom: 'EMOM', for_time: 'For time' };
export function copySession(source: Session): Session {
  const session = structuredClone(source);
  session.id = uid();
  const ids = new Map(session.parts?.map(p => [p.id, uid()]));
  session.parts?.forEach(p => { p.id = ids.get(p.id)!; });
  session.exercises.forEach(p => { p.id = uid(); if (p.partId) p.partId = ids.get(p.partId); });
  return session;
}
// Retain destination dates, duration and deload markers; only replace planned sessions.
export function copyProgramme(source: Cycle, destination: Cycle, sourceWeek?: number): Cycle {
  const result = structuredClone(destination);
  result.weeks.forEach((week, i) => {
    const origin = source.weeks[sourceWeek ?? i % source.weeks.length];
    week.sessions = origin.sessions.map(copySession);
  });
  return result;
}
export function orderExercises(session: Session) {
  if (session.parts) session.exercises.sort((a, b) => session.parts!.findIndex(p => p.id === a.partId) - session.parts!.findIndex(p => p.id === b.partId));
}
export function addPart(session: Session): string {
  if (!session.parts?.length) {
    const first: SessionPart = { id: uid(), title: 'Partie 1', format: session.format, timeCapMinutes: session.timeCapMinutes, notes: '' };
    session.parts = [first];
    session.exercises.forEach(p => { p.partId = first.id; });
  }
  const next = { id: uid(), title: `Partie ${session.parts.length + 1}`, format: 'amrap', timeCapMinutes: 12, notes: '' };
  session.parts.push(next);
  return next.id;
}
export function partLabel(part: SessionPart) {
  return `${part.title} · ${formats[part.format] ?? part.format}${part.timeCapMinutes ? ` · ${part.timeCapMinutes} min` : ''}`;
}
