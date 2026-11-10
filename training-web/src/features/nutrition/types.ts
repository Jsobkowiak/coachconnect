export interface Kcal { min:number;max:number }
export interface SessionEnergyInput {sessionId:string;activity:string;durationMinutes:number}
export interface PlannedEnergySession {id:string;title:string;week:number;day:number;format:string;durationMinutes:number;activity:string|null;inferred:boolean;empty:boolean;grossKcal:number|null}
export interface EnergyDay {number:number;date:string|null;status:'rest'|'training'|'incomplete';sessions:PlannedEnergySession[];maintenance:Kcal|null;trainingExtra:Kcal|null}
export interface EnergyWeek {number:number;focus:string|null;deload:boolean;complete:boolean;missingSessions:number;trainingDays:number;trainingMinutes:number;weeklyMaintenance:Kcal|null;dailyAverage:Kcal|null;days:EnergyDay[]}
export interface NutritionReport {
 cycleId:string;cycleName:string;cycleRevision:number;durationWeeks:number;profileRevision:number;settingsRevision:number;needsReview:boolean;dailyActivity:string;overrides:SessionEnergyInput[];
 dailyActivities:{id:string;label:string;factor:number}[];activities:{id:string;label:string;met:number;sourceUrl:string}[];
 baseline:Kcal;complete:boolean;missingSessions:number;blockMaintenance:Kcal|null;dailyAverage:Kcal|null;profileNote:string|null;calculatedAt:string;weeks:EnergyWeek[];
}
