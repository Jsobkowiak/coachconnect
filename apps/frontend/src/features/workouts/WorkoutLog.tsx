import { partLabel } from "../blocks/programme";
import { useEffect, useState } from "react";
import type {
  Cycle,
  Workout,
  PerformedSet,
  Exercise,
} from "../../shared/types";
import { Icon } from "../../shared/Icon";
import { today, uid } from "../../shared/api";
import { Illustration, ExerciseDetail } from "../catalog/Catalog";
import { loadRecord, improvesRecord, showsLoadRecord } from "./records";
const blankSet = (number: number, loadKg: number | null): PerformedSet => ({
  number,
  reps: null,
  loadKg,
  durationSeconds: null,
  distanceMeters: null,
  rpe: null,
  completed: false,
});
export function WorkoutLog({
  accountId,
  cycles,
  history,
  onSave,
  onDelete,
  onRefresh,
}: {
  accountId: string;
  cycles: Cycle[];
  history: Workout[];
  onSave: (w: Workout) => Promise<Workout>;
  onDelete: (w: Workout) => Promise<void>;
  onRefresh: () => Promise<void>;
}) {
  const draftKey="coachconnect-workout-draft:"+accountId;
  const [cycleId, setCycleId] = useState(
      cycles.find((c) => c.status === "active")?.id ?? cycles[0]?.id ?? "",
    ),
    [wn, setWn] = useState(1),
    [sessionId, setSessionId] = useState(""),
    [workout, setWorkout] = useState<Workout | null>(() => {
      try {
        const saved = localStorage.getItem(draftKey);
        return saved ? (JSON.parse(saved).workout ?? JSON.parse(saved)) : null;
      } catch {
        return null;
      }
    }),
    [dirty, setDirty] = useState(() => {
      try {
        const saved = localStorage.getItem(draftKey);
        return saved ? (JSON.parse(saved).dirty ?? true) : false;
      } catch {
        return false;
      }
    }),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [detail, setDetail] = useState<Exercise | null>(null),
    [restUntil, setRestUntil] = useState<number | null>(null),
    [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (workout) {
      try {
        localStorage.setItem(
          draftKey,
          JSON.stringify({ workout, dirty }),
        );
      } catch {
        /* A full local cache must not prevent saving to the API. */
      }
    } else localStorage.removeItem(draftKey);
  }, [workout, dirty, draftKey]);
  const cycle = cycles.find((c) => c.id === cycleId),
    week = cycle?.weeks.find((w) => w.number === wn);
  useEffect(() => {
    if (!workout) return;
    const before = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", before);
    return () => window.removeEventListener("beforeunload", before);
  }, [dirty, workout]);
  useEffect(() => {
    if (!restUntil) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [restUntil]);
  function start() {
    const session =
      week?.sessions.find((s) => s.id === sessionId) ?? week?.sessions[0];
    if (!cycle?.id || !session) return;
    const id = uid();
    const w: Workout = {
      id,
      revision: 0,
      cycleId: cycle.id,
      weekNumber: wn,
      sessionId: session.id,
      performedOn: today(),
      status: "in_progress",
      notes: "",
      plannedSession: structuredClone(session),
      exercises: session.exercises.map((p) => ({
        prescriptionId: p.id,
        sets: Array.from({ length: p.sets }, (_, i) =>
          blankSet(i + 1, p.loadKg),
        ),
      })),
    };
    setWorkout(w);
    setDirty(true);
    setError("");
  }
  function edit(fn: (w: Workout) => void) {
    setWorkout((w) => {
      if (!w) return w;
      const next = structuredClone(w);
      fn(next);
      return next;
    });
    setDirty(true);
  }
  async function save(finish = false) {
    if (!workout) return;
    setBusy(true);
    setError("");
    try {
      const saved = await onSave({
        ...workout,
        status: finish ? "completed" : workout.status,
      });
      setWorkout(saved);
      setDirty(false);
      await onRefresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    window.dispatchEvent(new CustomEvent("workout-dirty", { detail: dirty }));
    return () => {
      window.dispatchEvent(new CustomEvent("workout-dirty", { detail: false }));
    };
  }, [dirty]);
  const total = workout?.exercises.reduce((n, e) => n + e.sets.length, 0) ?? 0,
    done =
      workout?.exercises.reduce(
        (n, e) => n + e.sets.filter((s) => s.completed).length,
        0,
      ) ?? 0;
  const remaining = restUntil
    ? Math.max(0, Math.ceil((restUntil - now) / 1000))
    : 0;
  return (
    <div className="workout-page">
      <fieldset disabled={busy} className="workout-fieldset">
        <header className="page-header">
          <div>
            <p className="eyebrow">ENTRAÎNEMENT</p>
            <h1>{workout ? workout.plannedSession.title : "Ma séance"}</h1>
            <p>Retrouve ton programme et enregistre chaque série.</p>
          </div>
        </header>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {!workout ? (
          <div className="workout-home-grid">
            <section className="panel workout-picker">
              <div className="section-kicker">
                <Icon name="workout" />
                <span>PRÊT À T’ENTRAÎNER ?</span>
              </div>
              <h2>Choisis ta séance</h2>
              <label>
                Bloc
                <select
                  value={cycleId}
                  onChange={(e) => {
                    setCycleId(e.target.value);
                    setWn(1);
                    setSessionId("");
                  }}
                >
                  <option value="">Choisir un bloc</option>
                  {cycles.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Semaine
                <select
                  value={wn}
                  onChange={(e) => {
                    setWn(Number(e.target.value));
                    setSessionId("");
                  }}
                >
                  {cycle?.weeks.map((w) => (
                    <option key={w.number} value={w.number}>
                      Semaine {w.number}
                      {w.deload ? " · allégée" : ""}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Séance
                <select
                  value={sessionId || week?.sessions[0]?.id || ""}
                  onChange={(e) => setSessionId(e.target.value)}
                >
                  {week?.sessions.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title}
                    </option>
                  ))}
                </select>
              </label>
              <div className="session-preview">
                {(
                  week?.sessions.find((s) => s.id === sessionId) ??
                  week?.sessions[0]
                )?.exercises
                  .slice(0, 3)
                  .map((p) => (
                    <div key={p.id}>
                      <Illustration exercise={p.snapshot} onOpen={setDetail} />
                      <span>
                        <strong>{p.snapshot.name}</strong>
                        <small>
                          {p.sets} séries ·{" "}
                          {p.mode === "reps"
                            ? `${p.repsMin}–${p.repsMax} répétitions`
                            : p.mode === "time"
                              ? `${p.durationSeconds ?? 0} secondes`
                              : `${p.distanceMeters ?? 0} mètres`}
                        </small>
                      </span>
                    </div>
                  ))}
              </div>
              <button
                className="primary"
                disabled={!week?.sessions.length}
                onClick={start}
              >
                Commencer la séance
              </button>
              {!cycles.length && (
                <p>Crée d’abord un bloc dans l’espace conception.</p>
              )}
            </section>
            <section className="panel">
              <div className="section-heading">
                <h2>Historique</h2>
                <span className="count-badge">{history.length}</span>
              </div>
              {history.length ? (
                history.map((w) => (
                  <button
                    className="history-row"
                    key={w.id}
                    onClick={() => {
                      setWorkout(structuredClone(w));
                      setError("");
                      setDirty(false);
                    }}
                  >
                    <span className="history-icon">
                      <Icon
                        name={w.status === "completed" ? "check" : "clock"}
                      />
                    </span>
                    <div>
                      <strong>{w.plannedSession.title}</strong>
                      <span>
                        {w.performedOn} · semaine {w.weekNumber} ·{" "}
                        {w.status === "completed" ? "Terminée" : "En cours"}
                      </span>
                    </div>
                    <Icon name="chevron" size={17} />
                  </button>
                ))
              ) : (
                <p>Aucune séance enregistrée pour le moment.</p>
              )}
            </section>
          </div>
        ) : (
          <>
            <section className="panel">
              <div className="form-grid">
                <label>
                  Date de réalisation
                  <input
                    type="date"
                    value={workout.performedOn}
                    onChange={(e) =>
                      edit((w) => {
                        w.performedOn = e.target.value;
                      })
                    }
                  />
                </label>
                <p>
                  Semaine {workout.weekNumber} · {done}/{total} séries validées
                  <br />
                  <strong>
                    {dirty
                      ? "À enregistrer"
                      : workout.status === "completed"
                        ? "Séance terminée"
                        : "Enregistré"}
                  </strong>
                </p>
              </div>
              {workout.plannedSession.warmup && (
                <p>
                  <strong>Échauffement :</strong>{" "}
                  {workout.plannedSession.warmup}
                </p>
              )}
              <div className="workout-stats">
                <div>
                  <span>Séries validées</span>
                  <strong>
                    {done}
                    <small> / {total}</small>
                  </strong>
                </div>
                <div>
                  <span>Volume réalisé</span>
                  <strong>
                    {workout.exercises
                      .reduce(
                        (sum, e) =>
                          sum +
                          e.sets
                            .filter((s) => s.completed)
                            .reduce(
                              (n, s) => n + (s.reps ?? 0) * (s.loadKg ?? 0),
                              0,
                            ),
                        0,
                      )
                      .toLocaleString("fr-FR")}
                    <small> kg</small>
                  </strong>
                </div>
                <div>
                  <span>Exercices</span>
                  <strong>{workout.exercises.length}</strong>
                </div>
              </div>
              <progress
                max={Math.max(1, total)}
                value={done}
                aria-label="Progression des séries"
              />
            </section>
            {workout.exercises.map((entry, ei) => {
              const p = workout.plannedSession.exercises.find(
                (p) => p.id === entry.prescriptionId,
              )!;
              const record = showsLoadRecord(p)
                ? loadRecord(history, p.exerciseId)
                : null;
              const candidate = showsLoadRecord(p)
                ? loadRecord([workout], p.exerciseId)
                : null;
              const pendingRecord = dirty && improvesRecord(candidate, record);
              const numberLabel = (value: number) =>
                value.toLocaleString("fr-FR");
              const previous = history
                .filter((w) => w.id !== workout.id)
                .flatMap((w) =>
                  w.exercises.map((e) => ({
                    w,
                    e,
                    p: w.plannedSession.exercises.find(
                      (x) => x.id === e.prescriptionId,
                    ),
                  })),
                )
                .filter(
                  (x) =>
                    x.p?.exerciseId === p.exerciseId &&
                    x.p.mode === p.mode &&
                    x.e.sets.some((s) => s.completed),
                )
                .sort((a, b) =>
                  b.w.performedOn.localeCompare(a.w.performedOn),
                )[0];
              return (
                <article className="panel workout-exercise" key={p.id}>
                  {p.partId && (() => { const part = workout.plannedSession.parts?.find(x => x.id === p.partId); return part ? <div className="workout-part"><strong>{partLabel(part)}</strong>{part.notes && <p>{part.notes}</p>}</div> : null; })()}
                  <div className="exercise-heading">
                    <Illustration exercise={p.snapshot} onOpen={setDetail} />
                    <div>
                      <h2>{p.snapshot.name}</h2>
                      <p>
                        Prévu : {p.sets} ×{" "}
                        {p.mode === "reps"
                          ? `${p.repsMin}–${p.repsMax} rép.`
                          : p.mode === "time"
                            ? `${p.durationSeconds ?? 0} s`
                            : `${p.distanceMeters ?? 0} m`}
                        {p.loadKg !== null ? ` · ${p.loadKg} kg` : ""}
                        {p.percent1RM ? ` · ${p.percent1RM} % 1RM` : ""} · repos{" "}
                        {p.restSeconds} s
                      </p>
                    </div>
                  </div>
                  {showsLoadRecord(p) && (
                    <div
                      className="personal-record"
                      aria-label={"Record de charge de " + p.snapshot.name}
                    >
                      <span className="record-label">
                        <Icon name="trophy" size={15} /> RECORD DE CHARGE
                      </span>
                      {record ? (
                        <>
                          <strong>
                            {numberLabel(record.loadKg)} kg{" "}
                            <span>× {record.reps} rép.</span>
                          </strong>
                          <small>
                            {new Date(
                              record.performedOn + "T12:00:00",
                            ).toLocaleDateString("fr-FR")}{" "}
                            · séries validées
                          </small>
                        </>
                      ) : (
                        <p>
                          Pas encore de record : valide une série avec une
                          charge et enregistre la séance.
                        </p>
                      )}
                      {p.snapshot.equipment === "bodyweight" && (
                        <small>
                          Pour les tractions et dips, la charge correspond au
                          lest ajouté.
                        </small>
                      )}
                      {pendingRecord && candidate && (
                        <p className="new-record" role="status">
                          {record ? "Nouveau record" : "Premier record"} :{" "}
                          {numberLabel(candidate.loadKg)} kg × {candidate.reps}{" "}
                          rép. · à enregistrer
                        </p>
                      )}
                    </div>
                  )}
                  {p.notes && <p>{p.notes}</p>}
                  {previous && (
                    <p className="previous">
                      Dernière fois ({previous.w.performedOn}) :{" "}
                      {previous.e.sets
                        .filter((s) => s.completed)
                        .map((s) =>
                          p.mode === "reps"
                            ? `${s.reps} rép.${s.loadKg !== null ? ` à ${s.loadKg} kg` : ""}`
                            : p.mode === "time"
                              ? `${s.durationSeconds} s`
                              : `${s.distanceMeters} m`,
                        )
                        .join(" / ")}
                    </p>
                  )}
                  <div className="set-table-heading" aria-hidden="true">
                    <span>SÉRIE</span>
                    <span>PRÉCÉDENT</span>
                    <span>
                      {p.mode === "reps"
                        ? "RÉP."
                        : p.mode === "time"
                          ? "TEMPS (S)"
                          : "DISTANCE (M)"}
                    </span>
                    <span>KG</span>
                    <span>✓</span>
                  </div>
                  {entry.sets.map((s, i) => (
                    <div
                      className={"set-row " + (s.completed ? "done" : "")}
                      key={s.number}
                    >
                      <span className="set-number">{s.number}</span>
                      <span className="previous-set">
                        {(() => {
                          const last = previous?.e.sets.find(
                            (row) => row.number === s.number && row.completed,
                          );
                          return last
                            ? p.mode === "reps"
                              ? `${last.loadKg ?? "—"} kg × ${last.reps ?? "—"}`
                              : p.mode === "time"
                                ? `${last.durationSeconds ?? "—"} s`
                                : `${last.distanceMeters ?? "—"} m`
                            : "—";
                        })()}
                      </span>
                      <label>
                        {p.mode === "reps"
                          ? "Répétitions"
                          : p.mode === "time"
                            ? "Durée (s)"
                            : "Distance (m)"}
                        <input
                          aria-label={`${p.snapshot.name}, série ${s.number}, ${p.mode === "reps" ? "répétitions" : p.mode === "time" ? "durée" : "distance"}`}
                          inputMode={p.mode === "reps" ? "numeric" : "decimal"}
                          type="number"
                          min="0"
                          max={
                            p.mode === "reps"
                              ? 1000
                              : p.mode === "time"
                                ? 86400
                                : 100000
                          }
                          value={
                            (p.mode === "reps"
                              ? s.reps
                              : p.mode === "time"
                                ? s.durationSeconds
                                : s.distanceMeters) ?? ""
                          }
                          onChange={(e) =>
                            edit((w) => {
                              const target = w.exercises[ei].sets[i],
                                key =
                                  p.mode === "reps"
                                    ? "reps"
                                    : p.mode === "time"
                                      ? "durationSeconds"
                                      : "distanceMeters";
                              target[key] =
                                e.target.value === ""
                                  ? null
                                  : Number(e.target.value);
                              target.completed = false;
                            })
                          }
                        />
                      </label>
                      <label>
                        Charge (kg)
                        <input
                          aria-label={`${p.snapshot.name}, série ${s.number}, charge`}
                          inputMode="decimal"
                          type="number"
                          min="0"
                          max="1000"
                          step="0.5"
                          value={s.loadKg ?? ""}
                          onChange={(e) =>
                            edit((w) => {
                              w.exercises[ei].sets[i].loadKg =
                                e.target.value === ""
                                  ? null
                                  : Number(e.target.value);
                            })
                          }
                        />
                      </label>
                      <button
                        className={"validate " + (s.completed ? "checked" : "")}
                        aria-label={`${s.completed ? "Dévalider" : "Valider"} la série ${s.number} de ${p.snapshot.name}`}
                        onClick={() => {
                          const performance =
                            p.mode === "reps"
                              ? s.reps
                              : p.mode === "time"
                                ? s.durationSeconds
                                : s.distanceMeters;
                          if (!s.completed && performance === null) {
                            setError(
                              "Renseigne la performance avant de valider la série.",
                            );
                            return;
                          }
                          edit((w) => {
                            w.exercises[ei].sets[i].completed = !s.completed;
                          });
                          setError("");
                          if (!s.completed) {
                            setNow(Date.now());
                            setRestUntil(Date.now() + p.restSeconds * 1000);
                          }
                        }}
                      >
                        <Icon name="check" size={20} />
                      </button>
                    </div>
                  ))}
                  <button
                    disabled={entry.sets.length >= 30}
                    onClick={() =>
                      edit((w) =>
                        w.exercises[ei].sets.push(
                          blankSet(entry.sets.length + 1, p.loadKg),
                        ),
                      )
                    }
                  >
                    <Icon name="plus" size={16} /> Ajouter une série
                  </button>
                  {entry.sets.length > 1 && (
                    <button
                      onClick={() => {
                        if (
                          entry.sets.at(-1)?.completed &&
                          !confirm("Retirer cette série validée ?")
                        )
                          return;
                        edit((w) => {
                          w.exercises[ei].sets.pop();
                        });
                      }}
                    >
                      Retirer la dernière série
                    </button>
                  )}
                </article>
              );
            })}
            <section className="panel">
              <label>
                Notes de séance
                <textarea
                  maxLength={5000}
                  placeholder="Sensations, difficulté, adaptation…"
                  value={workout.notes}
                  onChange={(e) =>
                    edit((w) => {
                      w.notes = e.target.value;
                    })
                  }
                />
              </label>
              {workout.plannedSession.cooldown && (
                <p>Retour au calme : {workout.plannedSession.cooldown}</p>
              )}
              <button
                onClick={() => {
                  if (
                    !dirty ||
                    confirm("Quitter sans enregistrer les modifications ?")
                  ) {
                    setWorkout(null);
                    setDirty(false);
                    setRestUntil(null);
                  }
                }}
              >
                Retour aux séances
              </button>
              {workout.revision > 0 && (
                <button
                  className="danger"
                  disabled={busy}
                  onClick={async () => {
                    if (!confirm("Supprimer définitivement ces performances ?"))
                      return;
                    setBusy(true);
                    try {
                      await onDelete(workout);
                      await onRefresh();
                      setWorkout(null);
                      setDirty(false);
                    } catch (e) {
                      setError((e as Error).message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Supprimer ces performances
                </button>
              )}
            </section>
            <div className="workout-savebar">
              <span aria-live="polite">
                {restUntil
                  ? remaining
                    ? `Repos : ${remaining} s`
                    : "Repos terminé"
                  : `${done}/${total} séries`}
              </span>
              <button disabled={busy} onClick={() => save()}>
                Enregistrer
              </button>
              <button
                disabled={busy}
                className="primary"
                onClick={() => save(true)}
              >
                Terminer
              </button>
            </div>
          </>
        )}
        <p className="credits">Exercise data by RepDB (repdb.co) · Crédits dans les illustrations.</p>
        {detail && (
          <ExerciseDetail exercise={detail} onClose={() => setDetail(null)} />
        )}
      </fieldset>
    </div>
  );
}
