import { useState } from "react";
import type { Cycle, Workout } from "../../shared/types";
import { CopyProgramme } from "./CopyProgramme";
import { Icon } from "../../shared/Icon";
const statusLabels: Record<string, string> = {
  draft: "Brouillon",
  active: "En cours",
  archived: "Archivé",
};
const dateLabel = (value: string) =>
  new Date(value + "T12:00:00").toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "short",
  });
export function BlockLibrary({
  cycles,
  workouts,
  onCreate,
  onEdit,
  onDuplicate,
  onCopy,
  onDelete,
  onWorkout,
}: {
  cycles: Cycle[];
  workouts: Workout[];
  onCreate: () => void;
  onEdit: (c: Cycle) => void;
  onDuplicate: (c: Cycle) => void;
  onCopy: (c: Cycle) => Promise<void>;
  onDelete: (c: Cycle) => void;
  onWorkout: () => void;
}) {
  const [copySource, setCopySource] = useState<Cycle | null>(null);
  const [filter, setFilter] = useState("all");
  const completed = workouts.filter((w) => w.status === "completed");
  const active = cycles.find((c) => c.status === "active");
  const totalSessions = cycles.reduce(
    (n, c) => n + c.weeks.reduce((n, w) => n + w.sessions.length, 0),
    0,
  );
  const visible = cycles.filter((c) => filter === "all" || c.status === filter);
  function exportCycle(c: Cycle) {
    const blob = new Blob([JSON.stringify(c, null, 2)], {
        type: "application/json",
      }),
      url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = c.name + ".json";
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <>
      {copySource && <CopyProgramme source={copySource} cycles={cycles} onCopy={onCopy} onClose={() => setCopySource(null)}/>}
      <header className="page-header">
        <div>
          <p className="eyebrow">PLANIFIER POUR PROGRESSER</p>
          <h1>Mes blocs</h1>
          <p>Tes objectifs. Tes semaines. Ton programme.</p>
        </div>
        <button
          className="primary"
          aria-label="+ Créer un bloc"
          onClick={onCreate}
        >
          <Icon name="plus" /> <span>Créer un bloc</span>
        </button>
      </header>
      <div className="metrics">
        <div>
          <span className="metric-icon">
            <Icon name="blocks" />
          </span>
          <div>
            <span>Blocs créés</span>
            <strong>{cycles.length}</strong>
          </div>
        </div>
        <div>
          <span className="metric-icon">
            <Icon name="calendar" />
          </span>
          <div>
            <span>Séances planifiées</span>
            <strong>{totalSessions}</strong>
          </div>
        </div>
        <div>
          <span className="metric-icon">
            <Icon name="check" />
          </span>
          <div>
            <span>Séances réalisées</span>
            <strong>{completed.length}</strong>
          </div>
        </div>
      </div>
      {active && (
        <section className="active-block-banner">
          <span className="active-block-symbol">
            <Icon name="workout" size={30} />
          </span>
          <div>
            <span className="tag">TON BLOC EN COURS</span>
            <h2>{active.name}</h2>
            <p>
              {active.goal ||
                `${active.durationWeeks} semaines pour avancer à ton rythme.`}
            </p>
          </div>
          <button className="primary" onClick={onWorkout}>
            Passer à ma séance <Icon name="arrow" size={17} />
          </button>
        </section>
      )}
      <div className="section-heading">
        <h2>
          Bibliothèque de blocs{" "}
          <span className="count-badge">{cycles.length}</span>
        </h2>
        <div className="segmented" aria-label="Filtrer les blocs">
          {Object.entries({
            all: "Tous",
            active: "En cours",
            draft: "Brouillons",
            archived: "Archivés",
          }).map(([value, label]) => (
            <button
              key={value}
              className={filter === value ? "selected" : ""}
              aria-pressed={filter === value}
              onClick={() => setFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="block-grid">
        {visible.map((c, index) => {
          const sessions = c.weeks[0]?.sessions ?? [];
          const sessionCount = c.weeks.reduce(
            (n, w) => n + w.sessions.length,
            0,
          );
          return (
            <article
              key={c.id}
              className={
                "block-card " + (c.status === "active" ? "active" : "")
              }
            >
              <div className="block-card-top">
                <span className={"block-symbol tone-" + (index % 3)}>
                  <Icon name="workout" size={25} />
                </span>
                <details className="card-menu">
                  <summary aria-label={"Options du bloc " + c.name}>
                    <Icon name="more" />
                  </summary>
                  <div>
                    <button onClick={() => onDuplicate(c)}>Dupliquer</button>
                    <button onClick={() => exportCycle(c)}>
                      Exporter en JSON
                    </button>
                    <button className="danger" onClick={() => onDelete(c)}>
                      Supprimer
                    </button>
                  </div>
                </details>
              </div>
              <div className={"tag status-" + c.status}>
                <span className="status-dot" />
                {statusLabels[c.status]}
              </div>
              <h2>{c.name}</h2>
              <p className="block-goal">
                {c.goal || "Ajoute un objectif à ce bloc."}
              </p>
              <div className="block-meta">
                <span>
                  <Icon name="calendar" size={15} />
                  {c.durationWeeks} semaines
                </span>
                <span>
                  <Icon name="workout" size={15} />
                  {sessionCount} séances
                </span>
              </div>
              <div className="block-session-preview">
                {sessions.length ? (
                  sessions.slice(0, 3).map((s) => (
                    <div key={s.id}>
                      <span>{s.title}</span>
                      <small>{s.exercises.length} exercices</small>
                    </div>
                  ))
                ) : (
                  <p>Aucune séance pour le moment</p>
                )}
                {sessions.length > 3 && (
                  <small>
                    + {sessions.length - 3} autres séances en semaine 1
                  </small>
                )}
              </div>
              <button onClick={() => setCopySource(c)}>Copier vers un autre bloc</button>
              <footer>
                <span>
                  {c.startDate
                    ? `${dateLabel(c.startDate)}${c.endDate ? " → " + dateLabel(c.endDate) : ""}`
                    : "Dates à définir"}
                </span>
                <button onClick={() => onEdit(c)}>
                  Ouvrir le bloc <Icon name="arrow" size={16} />
                </button>
              </footer>
            </article>
          );
        })}
      </div>
      {!visible.length && (
        <section className="empty">
          <span className="empty-icon">
            <Icon name="blocks" size={32} />
          </span>
          <h2>
            {cycles.length
              ? "Aucun bloc dans cette catégorie"
              : "Ton premier bloc commence ici"}
          </h2>
          <p>
            Choisis une durée, ajoute tes séances et prépare ta progression.
          </p>
          <button className="primary" onClick={onCreate}>
            Créer mon premier bloc
          </button>
        </section>
      )}
    </>
  );
}
