import { useEffect, useState, type FormEvent } from 'react';
import { App } from '../../App';
import { api, setApiSession } from '../../shared/api';
import { Icon } from '../../shared/Icon';
import type { AccountSession, AccountUser } from './types';
function localToken(){
 let token='';if(location.hash.startsWith('#initialisation=')){try{token=decodeURIComponent(location.hash.slice('#initialisation='.length));}catch{token='';}history.replaceState(null,'','/#inscription');}
 try{if(token)sessionStorage.setItem('coachconnect-recovery',token);return token||sessionStorage.getItem('coachconnect-recovery')||'';}catch{return token;}
}
function adoptLegacyDraft(user:AccountUser){
 if(!user.ownsLegacyData)return;
 try{const old=localStorage.getItem('coachconnect-workout-draft'),key='coachconnect-workout-draft:'+user.id;if(old&&!localStorage.getItem(key))localStorage.setItem(key,old);if(old)localStorage.removeItem('coachconnect-workout-draft');}catch{/* Keep the original draft if browser storage is unavailable. */}
}
export function AuthRoot(){
 const [session,setSession]=useState<AccountSession>(),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const [claimToken,setClaimToken]=useState(localToken),[claimBusy,setClaimBusy]=useState(false),[claimError,setClaimError]=useState('');
 function clearToken(){setClaimToken('');try{sessionStorage.removeItem('coachconnect-recovery');}catch{/* No browser storage. */}}
 async function refresh(){
  const state=await api<AccountSession>('/auth/session');setApiSession(state.user?.id??null,state.csrfToken);
  if(state.user)adoptLegacyDraft(state.user);
  setSession(state);setError('');return state;
 }
 useEffect(()=>{let live=true;api<AccountSession>('/auth/session').then(s=>{if(live){setApiSession(s.user?.id??null,s.csrfToken);if(s.user)adoptLegacyDraft(s.user);setSession(s);}}).catch(e=>{if(live)setError(e.message);}).finally(()=>{if(live)setLoading(false);});return()=>{live=false;};},[]);
 useEffect(()=>{
  const expired=()=>{history.replaceState(null,'','/#connexion');setApiSession(null,null);setSession(undefined);setLoading(true);refresh().catch(e=>setError(e.message)).finally(()=>setLoading(false));};
  const changed=(e:StorageEvent)=>{if(e.key==='coachconnect-account-event')expired();};
  window.addEventListener('training-auth-required',expired);window.addEventListener('storage',changed);
  return()=>{window.removeEventListener('training-auth-required',expired);window.removeEventListener('storage',changed);};
 },[]);
 useEffect(()=>{if(claimToken&&session?.user&&(session.user.ownsLegacyData||!session.legacyDataAvailable))clearToken();},[claimToken,session]);
 function announce(){try{localStorage.setItem('coachconnect-account-event',crypto.randomUUID());}catch{/* Cookies remain authoritative. */}}
 async function authenticated(){await refresh();announce();}
 async function ended(){history.replaceState(null,'','/#connexion');setApiSession(null,null);await refresh();announce();}
 async function recover(){setClaimBusy(true);setClaimError('');try{await api('/auth/claim','POST',{token:claimToken});clearToken();await refresh();announce();}catch(e){setClaimError((e as Error).message);}finally{setClaimBusy(false);}}
 if(loading)return <main className="auth-loading" role="status">Ouverture de ton espace…</main>;
 if(error&&!session)return <main className="auth-loading"><p className="error" role="alert">{error}</p><button onClick={()=>location.reload()}>Réessayer</button></main>;
 if(!session?.user)return <AuthScreen onAuthenticated={authenticated} recovery={!!claimToken}/>;
 if(claimToken&&session.legacyDataAvailable&&!session.user.ownsLegacyData)return <main className="auth-shell"><section className="auth-card"><p className="eyebrow">TON ESPACE PERSONNEL</p><h1>Retrouver tes données</h1><p>Tu es connecté avec <strong>{session.user.email}</strong>. Le lien local autorise à rattacher à ce compte tes blocs, séances, mensurations et réglages existants.</p>{claimError&&<p role="alert" className="error">{claimError}</p>}<button className="primary" disabled={claimBusy} onClick={recover}>{claimBusy?'Récupération…':'Récupérer mes données et continuer'}</button><button disabled={claimBusy} onClick={async()=>{await api('/auth/logout','POST');await ended();}}>Utiliser un autre compte</button><button disabled={claimBusy} onClick={clearToken}>Continuer sans récupérer</button></section></main>;
 return <App key={session.user.id} user={session.user} onSessionEnded={ended} legacyAvailable={session.legacyDataAvailable}/>;
}
function AuthScreen({onAuthenticated,recovery}:{onAuthenticated:()=>Promise<void>;recovery:boolean}){
 const [register,setRegister]=useState(recovery||location.pathname==='/register'||location.hash==='#inscription');
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 async function submit(e:FormEvent<HTMLFormElement>){
  e.preventDefault();const f=new FormData(e.currentTarget),email=String(f.get('email')??''),password=String(f.get('password')??'');
  if(register&&password!==f.get('confirmation')){setError('Les deux mots de passe doivent être identiques.');return;}
  setBusy(true);setError('');try{await api('/auth/'+(register?'register':'login'),'POST',{email,password,rememberMe:f.has('rememberMe')});await onAuthenticated();}catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 return <main className="auth-shell"><section className="auth-intro"><a className="brand" href="/"><span className="brand-mark"><Icon name="workout" size={24}/></span>CoachConnect</a><p className="eyebrow">TON ENTRAÎNEMENT, TON ESPACE</p><h1>Construis tes blocs.<br/>Suis tes progrès.</h1><p>Tes séances, tes performances et ton évolution réunies dans un espace personnel.</p><div className="auth-points"><span><Icon name="blocks"/>Tes programmes sur PC</span><span><Icon name="workout"/>Tes séries à la salle</span><span><Icon name="chart"/>Tes courbes de progression</span></div></section>
  <section className="auth-card" aria-label={register?'Inscription':'Connexion'}><p className="eyebrow">BIENVENUE CHEZ TOI</p><h2>{register?'Créer mon compte':'Me connecter'}</h2><p>{register?'Un compte personnel pour retrouver tes données sur tes appareils.':'Retrouve tes blocs, tes séances et tes stats.'}</p>{recovery&&<p className="auth-recovery-note">Après connexion, tu pourras récupérer les données existantes de cette installation.</p>}
   <form onSubmit={submit}><label>Adresse e-mail<input aria-label="Adresse e-mail" name="email" type="email" autoComplete="username" maxLength={254} required disabled={busy}/></label><label>Mot de passe<input aria-label="Mot de passe" name="password" type="password" autoComplete={register?'new-password':'current-password'} minLength={register?12:1} maxLength={128} required disabled={busy}/>{register&&<small>12 à 128 caractères. Une phrase longue est facile à retenir.</small>}</label>{register&&<label>Confirmer le mot de passe<input aria-label="Confirmer le mot de passe" name="confirmation" type="password" autoComplete="new-password" minLength={12} maxLength={128} required disabled={busy}/></label>}
    <label className="auth-checkbox"><input name="rememberMe" type="checkbox" disabled={busy}/>Rester connecté sur cet appareil</label>
    {error&&<p className="error" role="alert">{error}</p>}<button className="primary" type="submit" disabled={busy}>{busy?'Un instant…':register?'Créer mon compte':'Me connecter'}</button>
   </form><div className="auth-switch"><span>{register?'Tu as déjà un compte ?':'Pas encore de compte ?'}</span><button disabled={busy} onClick={()=>{setRegister(!register);setError('');history.replaceState(null,'',register?'/#connexion':'/#inscription');}}>{register?'Se connecter':'Créer un compte'}</button></div>
  </section></main>;
}
