import { useEffect, useState } from "react";
import { api } from "../../shared/api";
import type { Exercise, Media } from "../../shared/types";
const safeLink = (s: string) => {
  try {
    const u = new URL(s);
    return ["https:", "http:"].includes(u.protocol) ? u.href : "#";
  } catch {
    return "#";
  }
};
const mediaRequests = new Map<string, Promise<Media | undefined>>();
function currentMedia(id: string): Promise<Media | undefined> {
  const existing = mediaRequests.get(id);
  if (existing) return existing;
  const request = api<Exercise>("/catalog/exercises/" + encodeURIComponent(id))
    .then((exercise) => {
      if (!exercise.media) mediaRequests.delete(id);
      return exercise.media;
    })
    .catch(() => {
      mediaRequests.delete(id);
      return undefined;
    });
  mediaRequests.set(id, request);
  return request;
}
export function Illustration({
  exercise,
  onOpen,
}: {
  exercise: Exercise;
  onOpen?: (e: Exercise) => void;
}) {
  const [resolvedMedia, setResolvedMedia] = useState<Media | undefined>(
    undefined,
  );
  useEffect(() => {
    let mounted = true;
    setResolvedMedia(undefined);
    currentMedia(exercise.id).then((media) => {
      if (mounted) setResolvedMedia(media);
    });
    return () => {
      mounted = false;
    };
  }, [exercise.id]);
  const media = resolvedMedia ?? exercise.media;
  const image = media?.images[0];
  return image && /^[a-f0-9]{64}\.(png|jpg|webp|svg)$/.test(image.filename) ? (
    <button
      className="illustration"
      type="button"
      onClick={() => onOpen?.({ ...exercise, media })}
      aria-label={"Illustrations de " + exercise.name}
    >
      <img
        loading="lazy"
        src={"/api/catalog/media/assets/" + image.filename}
        alt={exercise.name}
      />
    </button>
  ) : (
    <span className="no-image">Visuel indisponible</span>
  );
}
function Credits({ media }: { media: Media }) {
  const licenses = [
    ...new Map(
      media.images.map((i) => {
        const l = i.license ?? media.license;
        return [JSON.stringify(l), l];
      }),
    ).values(),
  ];
  return (
    <div className="credits">
      {licenses.map((l, i) => (
        <p key={i}>
          {l.author} ·{" "}
          <a href={safeLink(l.url)} target="_blank" rel="noreferrer">
            {l.name}
          </a>{" "}
          ·{" "}
          <a href={safeLink(l.source_url)} target="_blank" rel="noreferrer">
            Source : {media.source}
          </a>
          {l.ai_generated ? " · Illustration générée par IA" : ""}
        </p>
      ))}
      {media.source === "repdb" && <p>Exercise data by RepDB (repdb.co)</p>}
    </div>
  );
}
export function ExerciseDetail({
  exercise,
  onClose,
}: {
  exercise: Exercise;
  onClose: () => void;
}) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);
  return (
    <div className="overlay">
      <section
        role="dialog"
        aria-modal="true"
        aria-label={exercise.name}
        className="modal"
      >
        <header>
          <h2>{exercise.name}</h2>
          <button onClick={onClose} autoFocus>
            Fermer
          </button>
        </header>
        <div className="positions">
          {exercise.media?.images.map((im, i) => (
            <img
              key={im.filename}
              src={"/api/catalog/media/assets/" + im.filename}
              alt={`${exercise.name}, position ${i + 1}`}
            />
          ))}
        </div>
        {exercise.media && <Credits media={exercise.media} />}
        <p>{exercise.description}</p>
        <p>
          <strong>Matériel :</strong>{" "}
          {exercise.required_equipment?.join(", ") ?? exercise.equipment}
        </p>
        <ol>
          {exercise.instructions.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>
        <h3>Erreurs fréquentes</h3>
        <ul>
          {exercise.common_mistakes?.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
export function Catalog({
  onAdd,
  onClose,
}: {
  onAdd?: (e: Exercise) => void;
  onClose?: () => void;
}) {
  const [q, setQ] = useState(""),
    [offset, setOffset] = useState(0),
    [data, setData] = useState<{ items: Exercise[]; total: number }>({
      items: [],
      total: 0,
    }),
    [error, setError] = useState(""),
    [selected, setSelected] = useState<Exercise | null>(null);
  useEffect(() => {
    let live = true;
    const timer = setTimeout(() => {
      api<typeof data>(
        `/catalog/exercises?limit=20&offset=${offset}&q=${encodeURIComponent(q)}`,
      )
        .then((r) => {
          if (live) {
            setData(r);
            setError("");
          }
        })
        .catch((e) => {
          if (live) setError(e.message);
        });
    }, 180);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [q, offset]);
  return (
    <section
      className={onClose ? "modal wide" : "catalog"}
      aria-label="Catalogue d’exercices"
    >
      <header>
        <div>
          <p className="eyebrow">LE RÉPERTOIRE</p>
          <h2>Choisir un mouvement</h2>
        </div>
        {onClose && <button onClick={onClose}>Fermer</button>}
      </header>
      <input
        className="search"
        type="search"
        aria-label="Rechercher un exercice"
        placeholder="Rechercher : traction, développé couché…"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOffset(0);
        }}
      />
      <p>{data.total} exercices · fiches en français</p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="catalog-grid">
        {data.items.map((e) => (
          <article className="exercise-card" key={e.id}>
            <Illustration exercise={e} onOpen={setSelected} />
            <h3>{e.name}</h3>
            <p>{e.required_equipment?.join(", ") ?? e.equipment}</p>
            <button onClick={() => setSelected(e)}>Voir les consignes</button>
            {onAdd && (
              <button className="primary" onClick={() => onAdd(e)}>
                Ajouter à la séance
              </button>
            )}
          </article>
        ))}
      </div>
      <footer>
        <button
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - 20))}
        >
          Précédent
        </button>
        <span>
          {data.total
            ? `${offset + 1}–${Math.min(offset + 20, data.total)} / ${data.total}`
            : "Aucun résultat"}
        </span>
        <button
          disabled={offset + 20 >= data.total}
          onClick={() => setOffset(offset + 20)}
        >
          Suivant
        </button>
      </footer>
      <p className="credits">
        Exercise data by RepDB (repdb.co) · Crédits et licences dans chaque
        fiche.
      </p>
      {selected && (
        <ExerciseDetail exercise={selected} onClose={() => setSelected(null)} />
      )}
    </section>
  );
}
