let csrfToken: string | null = null;
let accountId: string | null = null;
export function setApiSession(userId:string|null,token:string|null){accountId=userId;csrfToken=token;}
export class ApiError extends Error { constructor(message:string,public status:number){super(message);} }
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const headers:Record<string,string> = body ? {"Content-Type":"application/json"} : {};
  if(accountId)headers['X-Training-User']=accountId;
  if(!['GET','HEAD'].includes(method.toUpperCase())){
    if(!csrfToken){
      const state=await fetch('/api/auth/session',{credentials:'same-origin',cache:'no-store'}).then(r=>r.json());
      csrfToken=state.csrfToken;
    }
    if(csrfToken)headers['X-CSRF-TOKEN']=csrfToken;
  }
  const response = await fetch("/api" + path, {
    method,
    headers,
    credentials:"same-origin",
    cache:"no-store",
    body: body ? JSON.stringify(body) : undefined,
  });
  if (response.status === 204) return undefined as T;
  const data = await response
    .json()
    .catch(() => ({ message: "Réponse du serveur illisible." }));
  if (!response.ok){
    if(response.status===401&&!['/auth/login','/auth/register','/auth/session'].includes(path)){
      setApiSession(null,null);window.dispatchEvent(new Event('training-auth-required'));
    }
    throw new ApiError(data.message ?? data.detail ?? `Erreur ${response.status}`,response.status);
  }
  return data as T;
}
export const uid = () => crypto.randomUUID();
export const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
export const days = [
  "Jour 1",
  "Jour 2",
  "Jour 3",
  "Jour 4",
  "Jour 5",
  "Jour 6",
  "Jour 7",
];
