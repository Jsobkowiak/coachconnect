export interface AccountUser {id:string;email:string;ownsLegacyData:boolean}
export interface AccountSession {user:AccountUser|null;csrfToken:string;legacyDataAvailable:boolean}
