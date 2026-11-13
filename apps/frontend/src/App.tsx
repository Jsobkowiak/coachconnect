import type { AccountUser } from "./features/accounts/types";
import { AccountPanel } from "./features/accounts/AccountPanel";
import { useEffect, useState, useRef } from "react";
import { api } from "./shared/api";
import type { Cycle, Workout } from "./shared/types";
import { BlockEditor, newCycle } from "./features/blocks/BlockEditor";
import { BlockLibrary } from "./features/blocks/BlockLibrary";
import { WorkoutLog } from "./features/workouts/WorkoutLog";
import { Catalog } from "./features/catalog/Catalog";
import { Icon, type IconName } from "./shared/Icon";
import { Profile } from "./features/profile/Profile";
import { Stats } from "./features/stats/Stats";
import type { ProfileState } from "./features/profile/types";
type View = "blocks" | "workouts" | "catalog" | "profile" | "stats";
type Domain = "training" | "tracking";
const domains: {id:Domain;label:string;icon:IconName;views:{view:View;label:string;icon:IconName}[]}[] = [
 {id:"training",label:"Entraînement",icon:"workout",views:[{view:"workouts",label:"Ma séance",icon:"workout"},{view:"blocks",label:"Mes blocs",icon:"blocks"},{view:"catalog",label:"Exercices",icon:"exercise"}]},
 {id:"tracking",label:"Suivi",icon:"chart",views:[{view:"stats",label:"Stats",icon:"chart"},{view:"profile",label:"Mon profil",icon:"account"}]},
];
export function App({user,onSessionEnded,legacyAvailable}:{user:AccountUser;onSessionEnded:()=>Promise<void>;legacyAvailable:boolean}) {
  const [accountOpen,setAccountOpen]=useState(false);
  const lastDomainViews=useRef<Record<Domain,View>>({training:window.matchMedia("(max-width:700px)").matches?"workouts":"blocks",tracking:"stats"});
  const [view, setView] = useState<View>(
    location.hash === "#stats" ? "stats" : location.hash === "#profil" ? "profile" : location.hash === "#blocs"
      ? "blocks"
      : location.hash === "#seance"
        ? "workouts"
        : location.hash === "#illustrations"
          ? "catalog"
          : window.matchMedia("(max-width:700px)").matches
            ? "workouts"
            : "blocks",
  );
  useEffect(()=>{const domain=domains.find(d=>d.views.some(item=>item.view===view));if(domain)lastDomainViews.current[domain.id]=view;},[view]);
  const [cycles, setCycles] = useState<Cycle[]>([]),
    [workouts, setWorkouts] = useState<Workout[]>([]),
    [editing, setEditing] = useState<Cycle | null>(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [workoutDirty, setWorkoutDirty] = useState(false);
  const [measurementsDirty, setMeasurementsDirty] = useState(false);
  const [profileState, setProfileState] = useState<ProfileState>();
  useEffect(() => {
    document.documentElement.dataset.theme = "light";
    if (location.hash === "#nutrition") history.replaceState(null, "", window.matchMedia("(max-width:700px)").matches ? "#seance" : "#blocs");
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", "#ffffff");
    try {
      localStorage.removeItem("coachconnect-theme");
    } catch {
      /* Light is enforced even if storage is unavailable. */
    }
  }, []);
  async function refresh() {
    const [c, w] = await Promise.all([
      api<Cycle[]>("/cycles"),
      api<Workout[]>("/workouts"),
    ]);
    setCycles(c);
    setWorkouts(w);
  }
  useEffect(() => {
    const handler = (e: Event) =>
      setWorkoutDirty((e as CustomEvent<boolean>).detail);
    window.addEventListener("workout-dirty", handler);
    return () => window.removeEventListener("workout-dirty", handler);
  }, []);
  useEffect(() => {
    Promise.all([refresh(), api<ProfileState>("/profile").then(setProfileState)])
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    const handler = (e:Event) => setMeasurementsDirty((e as CustomEvent<boolean>).detail);
    window.addEventListener("measurements-dirty", handler);
    return () => window.removeEventListener("measurements-dirty", handler);
  }, []);
  function navigate(next: View) {
    if (!profileState?.profile && next !== "profile") return;
    if (next === view && !editing) return;
    if (measurementsDirty && !confirm("Les mensurations ne sont pas enregistrées. Quitter cette page ?")) return;
    if (
      workoutDirty &&
      !confirm(
        "Les performances ne sont pas encore enregistrées sur le serveur. Quitter ?",
      )
    )
      return;
    if (
      editing &&
      !confirm("Quitter l’éditeur ? Vérifie que ton bloc est enregistré.")
    )
      return;
    setEditing(null);
    setView(next);
    history.replaceState(
      null,
      "",
      next === "stats" ? "#stats" : next === "profile" ? "#profil" : next === "workouts"
        ? "#seance"
        : next === "catalog"
          ? "#illustrations"
          : "#blocs",
    );
    window.scrollTo(0, 0);
  }
  async function save(c: Cycle) {
    const result = await api<Cycle>(
      "/cycles" + (c.id ? "/" + c.id : ""),
      c.id ? "PUT" : "POST",
      c,
    );
    await refresh();
    return result;
  }
  async function action(fn: () => Promise<unknown>) {
    try {
      await fn();
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const effectiveView:View=profileState?.profile?view:"profile";
  const activeDomain=domains.find(d=>d.views.some(v=>v.view===effectiveView))!;
  return (
    <div className="app-shell">
      {accountOpen&&<AccountPanel user={user} onClose={()=>setAccountOpen(false)} onEnded={onSessionEnded} legacyAvailable={legacyAvailable} beforeLogout={()=>!(editing||workoutDirty||measurementsDirty)||confirm("Des modifications ne sont pas enregistrées. Te déconnecter quand même ?")}/>}
      <header className="site-header">
        <div className="header-inner">
          <a className="brand" href="/" aria-label="CoachConnect, accueil">
            <span className="brand-mark">
              <Icon name="workout" size={23} />
            </span>
            <span>CoachConnect</span>
          </a>
          <nav className="main-navigation" aria-label="Navigation principale">
            {domains.map(domain => {
              const selected=domain.id===activeDomain.id;
              return <button key={domain.id} aria-label={domain.label} disabled={!profileState?.profile&&domain.id!=="tracking"} className={selected?"selected":""} aria-current={selected?"page":undefined} onClick={()=>{if(!selected)navigate(lastDomainViews.current[domain.id]);}}>
                <Icon name={domain.icon} size={20}/><span>{domain.label}</span>
              </button>;
            })}
          </nav>
          <button className="account-button" aria-label="Mon compte" onClick={()=>setAccountOpen(true)}><Icon name="account" size={18}/><span>Mon compte</span></button>
        </div>
      </header>
      <div className="workspace">
        <main>
          {activeDomain.views.length>1&&<nav className="domain-navigation" aria-label={"Rubriques · "+activeDomain.label}>
            {activeDomain.views.map(item=><button key={item.view} aria-label={item.label} aria-current={effectiveView===item.view?"page":undefined} className={effectiveView===item.view?"selected":""} disabled={!profileState?.profile&&item.view!=="profile"} onClick={()=>navigate(item.view)}><Icon name={item.icon} size={17}/><span>{item.label}</span></button>)}
          </nav>}
          {loading ? (
            <div className="loading-state">
              <Icon name="activity" size={28} />
              <p>Chargement de ton entraînement…</p>
            </div>
          ) : (
            <>
              {error && (
                <p className="error" role="alert">
                  {error}
                </p>
              )}
              {!profileState ? <button onClick={() => location.reload()}>Réessayer le chargement</button> : !profileState.profile || view === "profile" ? (
                <Profile state={profileState} onSaved={(s) => {setProfileState(s);setView("profile");history.replaceState(null,"","#profil");}} />
              ) : view === "stats" ? (
                <Stats />
              ) : view === "blocks" ? (
                editing ? (
                  <BlockEditor
                    key={editing.id ?? "new"}
                    initial={editing}
                    onSave={save}
                    onClose={() => setEditing(null)}
                  />
                ) : (
                  <BlockLibrary
                    cycles={cycles}
                    workouts={workouts}
                    onCreate={() => setEditing(newCycle())}
                    onEdit={setEditing}
                    onWorkout={() => navigate("workouts")}
                    onCopy={async c => { await save(c); }}
                    onDuplicate={(c) =>
                      action(async () => {
                        await api("/cycles/" + c.id + "/duplicate", "POST");
                        await refresh();
                      })
                    }
                    onDelete={(c) => {
                      if (
                        confirm(
                          "Supprimer ce bloc ? Les performances réalisées seront conservées.",
                        )
                      )
                        action(async () => {
                          await api(
                            "/cycles/" + c.id + "?revision=" + c.revision,
                            "DELETE",
                          );
                          await refresh();
                        });
                    }}
                  />
                )
              ) : view === "workouts" ? (
                <WorkoutLog
                  accountId={user.id}
                  cycles={cycles}
                  history={workouts}
                  onRefresh={refresh}
                  onSave={(w) => api<Workout>("/workouts/" + w.id, "PUT", w)}
                  onDelete={(w) =>
                    api<void>(
                      "/workouts/" + w.id + "?revision=" + w.revision,
                      "DELETE",
                    )
                  }
                />
              ) : (
                <Catalog />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
