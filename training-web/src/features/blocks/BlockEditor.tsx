import { useEffect, useState } from "react";
import { uid, days } from "../../shared/api";
import type {
  Cycle,
  Session,
  Exercise,
  Prescription,
} from "../../shared/types";
import { Catalog, Illustration, ExerciseDetail } from "../catalog/Catalog";
import { copySession, orderExercises } from "./programme";
import { SessionParts } from "./SessionParts";
export function newCycle(): Cycle {
  return {
    name: "Nouveau bloc",
    goal: "",
    notes: "",
    discipline: "strength",
    status: "draft",
    startDate: null,
    durationWeeks: 8,
    weeks: Array.from({ length: 8 }, (_, i) => ({
      number: i + 1,
      focus: "",
      notes: "",
      deload: false,
      sessions: [],
    })),
  };
}
export function BlockEditor({
  initial,
  onSave,
  onClose,
}: {
  initial: Cycle;
  onSave: (c: Cycle) => Promise<Cycle>;
  onClose: () => void;
}) {
  const [cycle, setCycle] = useState<Cycle>(structuredClone(initial)),
    [wi, setWi] = useState(0),
    [partId, setPartId] = useState<string | undefined>(),
    [si, setSi] = useState<string | null>(null),
    [dirty, setDirty] = useState(!initial.id),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [catalog, setCatalog] = useState(false),
    [detail, setDetail] = useState<Exercise | null>(null);
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);
  const week = cycle.weeks[wi],
    session = week.sessions.find((s) => s.id === si) ?? week.sessions[0];
  const part = session?.parts?.find(p => p.id === partId) ?? session?.parts?.[0];
  const visibleExercises = session?.exercises.map((p, i) => ({p, i})).filter(({p}) => !part || p.partId === part.id) ?? [];
  function edit(fn: (c: Cycle) => void) {
    setCycle((c) => {
      const next = structuredClone(c);
      fn(next);
      return next;
    });
    setDirty(true);
  }
  function sessionEdit(fn: (s: Session) => void) {
    if (session)
      edit((c) => {
        const s = c.weeks[wi].sessions.find((x) => x.id === session.id)!;
        fn(s);
      });
  }
  async function save() {
    setBusy(true);
    setError("");
    try {
      const saved = await onSave(cycle);
      setCycle(saved);
      setDirty(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function resize(n: number) {
    if (!Number.isInteger(n) || n < 1 || n > 52) return;
    if (
      n < cycle.weeks.length &&
      cycle.weeks.slice(n).some((w) => w.sessions.length) &&
      !confirm("Retirer les dernières semaines et leurs séances prévues ?")
    )
      return;
    edit((c) => {
      c.durationWeeks = n;
      c.weeks = Array.from(
        { length: n },
        (_, i) =>
          c.weeks[i] ?? {
            number: i + 1,
            focus: "",
            notes: "",
            deload: false,
            sessions: [],
          },
      );
    });
    setWi((w) => Math.min(w, n - 1));
  }
  function addExercise(e: Exercise) {
    sessionEdit((s) =>
      { s.exercises.push({
        partId: part?.id,
        id: uid(),
        exerciseId: e.id,
        snapshot: e,
        mode: "reps",
        sets: 3,
        repsMin: 6,
        repsMax: 8,
        restSeconds: 120,
        loadKg: null,
        rir: 2,
      }); orderExercises(s); },
    );
    setCatalog(false);
  }
  const patch = (index: number, key: keyof Prescription, value: unknown) =>
    sessionEdit((s) => {
      Object.assign(s.exercises[index], { [key]: value });
      if (key === "loadKg" && value !== null)
        s.exercises[index].percent1RM = null;
      if (key === "percent1RM" && value !== null)
        s.exercises[index].loadKg = null;
      if (key === "rpe" && value !== null) s.exercises[index].rir = null;
      if (key === "rir" && value !== null) s.exercises[index].rpe = null;
    });
  function number(
    p: Prescription,
    i: number,
    k: keyof Prescription,
    label: string,
    min: number,
    max: number,
    optional = false,
  ) {
    return (
      <label>
        {label}
        <input
          type="number"
          min={min}
          max={max}
          step={
            ["loadKg", "rpe", "distanceMeters", "percent1RM"].includes(k)
              ? "0.5"
              : "1"
          }
          value={p[k] === null || p[k] === undefined ? "" : String(p[k])}
          onChange={(e) =>
            patch(
              i,
              k,
              e.target.value === "" && optional ? null : Number(e.target.value),
            )
          }
        />
      </label>
    );
  }
  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">ÉDITEUR DE BLOC</p>
          <h1>{cycle.name}</h1>
          <p>
            {dirty ? "Modifications non enregistrées" : "Bloc enregistré"} · les
            performances restent dans le carnet de séance.
          </p>
        </div>
        <div className="actions">
          <button
            onClick={() => {
              if (!dirty || confirm("Quitter sans enregistrer ?")) onClose();
            }}
          >
            Retour
          </button>
          <button disabled={busy} className="primary" onClick={save}>
            {busy ? "Enregistrement…" : "Enregistrer le bloc"}
          </button>
        </div>
      </header>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <fieldset disabled={busy} className="editor-body">
        <section className="panel form-grid">
          <label>
            Nom du bloc
            <input
              maxLength={120}
              value={cycle.name}
              onChange={(e) =>
                edit((c) => {
                  c.name = e.target.value;
                })
              }
            />
          </label>
          <label>
            Durée (semaines)
            <input
              type="number"
              min="1"
              max="52"
              value={cycle.durationWeeks}
              onChange={(e) => resize(Number(e.target.value))}
            />
          </label>
          <label>
            Date de début
            <input
              type="date"
              value={cycle.startDate ?? ""}
              onChange={(e) =>
                edit((c) => {
                  c.startDate = e.target.value || null;
                })
              }
            />
          </label>
          <label>
            Statut
            <select
              value={cycle.status}
              onChange={(e) =>
                edit((c) => {
                  c.status = e.target.value;
                })
              }
            >
              <option value="draft">Brouillon</option>
              <option value="active">Actif</option>
              <option value="archived">Archivé</option>
            </select>
          </label>
          <label>
            Discipline
            <select
              value={cycle.discipline}
              onChange={(e) =>
                edit((c) => {
                  c.discipline = e.target.value;
                })
              }
            >
              <option value="strength">Musculation</option>
              <option value="mixed">Mixte</option>
              <option value="crossfit">CrossFit</option>
            </select>
          </label>
          <label>
            Objectif
            <input
              maxLength={1000}
              placeholder="Ex. progresser au bench, tractions en volume"
              value={cycle.goal}
              onChange={(e) =>
                edit((c) => {
                  c.goal = e.target.value;
                })
              }
            />
          </label>
          <label className="span-all">
            Notes du bloc
            <textarea
              maxLength={5000}
              value={cycle.notes}
              onChange={(e) =>
                edit((c) => {
                  c.notes = e.target.value;
                })
              }
            />
          </label>
        </section>
        <div className="editor-layout">
          <aside className="panel week-list">
            <h2>Les semaines</h2>
            {cycle.weeks.map((w, i) => (
              <button
                key={i}
                className={wi === i ? "selected" : ""}
                onClick={() => {
                  setWi(i);
                  setSi(null);
                }}
              >
                Semaine {i + 1}
                <small>
                  {w.deload ? "Allégée · " : ""}
                  {w.sessions.length} séance(s)
                </small>
              </button>
            ))}
          </aside>
          <div>
            <section className="panel">
              <header>
                <h2>Semaine {wi + 1}</h2>
                <div className="actions">
                  <button
                    onClick={() => {
                      const target = Number(
                        prompt(
                          "Copier cette semaine vers quel numéro ?",
                          String(wi + 2),
                        ),
                      );
                      if (
                        !Number.isInteger(target) ||
                        target < 1 ||
                        target > cycle.durationWeeks ||
                        target === wi + 1
                      )
                        return;
                      if (
                        cycle.weeks[target - 1].sessions.length &&
                        !confirm("Remplacer les séances de cette semaine ?")
                      )
                        return;
                      edit((c) => {
                        c.weeks[target - 1] = {
                          ...structuredClone(week),
                          number: target,
                          sessions: week.sessions.map(copySession),
                        };
                      });
                    }}
                  >
                    Copier la semaine
                  </button>
                  <button
                    onClick={() => {
                      const n: Session = {
                        id: uid(),
                        title: "Nouvelle séance",
                        day: 0,
                        format: "traditional",
                        durationMinutes: 60,
                        exercises: [],
                      };
                      edit((c) => c.weeks[wi].sessions.push(n));
                      setSi(n.id);
                    }}
                  >
                    + Séance
                  </button>
                </div>
              </header>
              <div className="form-grid">
                <label>
                  Priorité de la semaine
                  <input
                    maxLength={200}
                    value={week.focus}
                    onChange={(e) =>
                      edit((c) => {
                        c.weeks[wi].focus = e.target.value;
                      })
                    }
                  />
                </label>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={week.deload}
                    onChange={(e) =>
                      edit((c) => {
                        c.weeks[wi].deload = e.target.checked;
                      })
                    }
                  />
                  Semaine allégée
                </label>
                <label>
                  Notes de la semaine
                  <textarea
                    maxLength={2000}
                    value={week.notes}
                    onChange={(e) =>
                      edit((c) => {
                        c.weeks[wi].notes = e.target.value;
                      })
                    }
                  />
                </label>
              </div>
            </section>
            <div className="session-tabs">
              {week.sessions.map((s) => (
                <button
                  className={session?.id === s.id ? "selected" : ""}
                  key={s.id}
                  onClick={() => setSi(s.id)}
                >
                  {days[s.day]} · {s.title}
                </button>
              ))}
            </div>
            {session ? (
              <section className="panel">
                <header>
                  <h2>{session.title}</h2>
                  <div className="actions">
                    <button
                      onClick={() => {
                        const copy = copySession(session);
                        copy.title += " · copie";
                        edit((c) => c.weeks[wi].sessions.push(copy));
                        setSi(copy.id);
                      }}
                    >
                      Dupliquer
                    </button>
                    <button
                      className="danger"
                      onClick={() => {
                        if (confirm("Retirer cette séance du programme ?"))
                          edit((c) => {
                            c.weeks[wi].sessions = c.weeks[wi].sessions.filter(
                              (s) => s.id !== session.id,
                            );
                          });
                      }}
                    >
                      Retirer
                    </button>
                  </div>
                </header>
                <div className="form-grid">
                  <label>
                    Nom de la séance
                    <input
                      maxLength={120}
                      value={session.title}
                      onChange={(e) =>
                        sessionEdit((s) => {
                          s.title = e.target.value;
                        })
                      }
                    />
                  </label>
                  <label>
                    Jour
                    <select
                      value={session.day}
                      onChange={(e) =>
                        sessionEdit((s) => {
                          s.day = Number(e.target.value);
                        })
                      }
                    >
                      {days.map((d, i) => (
                        <option value={i} key={i}>
                          {d}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Durée estimée (min)
                    <input
                      type="number"
                      min="1"
                      max="300"
                      value={session.durationMinutes}
                      onChange={(e) =>
                        sessionEdit((s) => {
                          s.durationMinutes = Number(e.target.value);
                        })
                      }
                    />
                  </label>
                  {!session.parts?.length && <><label>
                    Format
                    <select
                      value={session.format}
                      onChange={(e) =>
                        sessionEdit((s) => {
                          s.format = e.target.value;
                        })
                      }
                    >
                      {Object.entries({
                        traditional: "Classique",
                        circuit: "Circuit / superset",
                        amrap: "AMRAP",
                        emom: "EMOM",
                        for_time: "For time",
                      }).map(([v, l]) => (
                        <option key={v} value={v}>
                          {l}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Time cap (min)
                    <input
                      type="number"
                      min="1"
                      max="300"
                      value={session.timeCapMinutes ?? ""}
                      onChange={(e) =>
                        sessionEdit((s) => {
                          s.timeCapMinutes = e.target.value
                            ? Number(e.target.value)
                            : null;
                        })
                      }
                    />
                  </label>
                  </>}
                  <label>
                    Échauffement
                    <textarea
                      maxLength={2000}
                      value={session.warmup ?? ""}
                      onChange={(e) =>
                        sessionEdit((s) => {
                          s.warmup = e.target.value;
                        })
                      }
                    />
                  </label>
                  <label>
                    Retour au calme
                    <textarea
                      maxLength={2000}
                      value={session.cooldown ?? ""}
                      onChange={(e) =>
                        sessionEdit((s) => {
                          s.cooldown = e.target.value;
                        })
                      }
                    />
                  </label>
                  <label>
                    Notes de séance
                    <textarea
                      maxLength={3000}
                      value={session.notes ?? ""}
                      onChange={(e) =>
                        sessionEdit((s) => {
                          s.notes = e.target.value;
                        })
                      }
                    />
                  </label>
                </div>
                <SessionParts session={session} selected={part?.id} onSelect={setPartId} onChange={sessionEdit}/>
                {visibleExercises.map(({p, i}, visibleIndex) => (
                  <article className="prescription" key={p.id}>
                    <header>
                      <div className="exercise-heading">
                        <Illustration
                          exercise={p.snapshot}
                          onOpen={setDetail}
                        />
                        <h3>
                          {i + 1}. {p.snapshot.name}
                        </h3>
                      </div>
                      <div className="actions">
                        <button
                          disabled={visibleIndex === 0}
                          aria-label="Monter l’exercice"
                          onClick={() =>
                            sessionEdit((s) => {
                              [s.exercises[i - 1], s.exercises[i]] = [
                                s.exercises[i],
                                s.exercises[i - 1],
                              ];
                            })
                          }
                        >
                          ↑
                        </button>
                        <button
                          disabled={visibleIndex === visibleExercises.length - 1}
                          aria-label="Descendre l’exercice"
                          onClick={() =>
                            sessionEdit((s) => {
                              [s.exercises[i + 1], s.exercises[i]] = [
                                s.exercises[i],
                                s.exercises[i + 1],
                              ];
                            })
                          }
                        >
                          ↓
                        </button>
                        <button
                          aria-label="Retirer l’exercice"
                          onClick={() =>
                            sessionEdit((s) => {
                              s.exercises.splice(i, 1);
                            })
                          }
                        >
                          ×
                        </button>
                      </div>
                    </header>
                    <div className="prescription-grid">
                      {part && <label>Partie de l’exercice<select value={p.partId} onChange={e => sessionEdit(s => { s.exercises[i].partId = e.target.value; orderExercises(s); })}>{session.parts!.map(x => <option key={x.id} value={x.id}>{x.title}</option>)}</select></label>}
                      <label>
                        Mesure
                        <select
                          value={p.mode}
                          onChange={(e) => patch(i, "mode", e.target.value)}
                        >
                          <option value="reps">Répétitions</option>
                          <option value="time">Temps</option>
                          <option value="distance">Distance</option>
                        </select>
                      </label>
                      {number(p, i, "sets", "Séries", 1, 30)}
                      {p.mode === "reps" ? (
                        <>
                          {number(p, i, "repsMin", "Rép. min", 1, 1000)}
                          {number(p, i, "repsMax", "Rép. max", 1, 1000)}
                        </>
                      ) : p.mode === "time" ? (
                        number(p, i, "durationSeconds", "Durée (s)", 1, 86400)
                      ) : (
                        number(
                          p,
                          i,
                          "distanceMeters",
                          "Distance (m)",
                          1,
                          100000,
                        )
                      )}
                      {number(p, i, "loadKg", "Charge (kg)", 0, 1000, true)}
                      {number(p, i, "restSeconds", "Repos (s)", 0, 900)}
                      {number(p, i, "percent1RM", "% de 1RM", 1, 150, true)}
                      {number(p, i, "rir", "RIR", 0, 10, true)}
                      {number(p, i, "rpe", "RPE", 1, 10, true)}
                      <label>
                        Tempo
                        <input
                          maxLength={40}
                          value={p.tempo ?? ""}
                          onChange={(e) => patch(i, "tempo", e.target.value)}
                        />
                      </label>
                      <label>
                        Groupe / superset
                        <input
                          maxLength={30}
                          value={p.group ?? ""}
                          onChange={(e) => patch(i, "group", e.target.value)}
                        />
                      </label>
                      <label>
                        Consigne
                        <input
                          maxLength={2000}
                          value={p.notes ?? ""}
                          onChange={(e) => patch(i, "notes", e.target.value)}
                        />
                      </label>
                    </div>
                  </article>
                ))}
                <button
                  className="add-exercise"
                  onClick={() => setCatalog(true)}
                >
                  + Ajouter un exercice
                </button>
                <p className="credits">
                  Exercise data by RepDB (repdb.co) · Crédits dans les
                  illustrations.
                </p>
              </section>
            ) : (
              <div className="empty">
                Ajoute une séance pour commencer cette semaine.
              </div>
            )}
          </div>
        </div>
      </fieldset>
      {catalog && (
        <div className="overlay">
          <Catalog onAdd={addExercise} onClose={() => setCatalog(false)} />
        </div>
      )}
      {detail && (
        <ExerciseDetail exercise={detail} onClose={() => setDetail(null)} />
      )}
    </>
  );
}
