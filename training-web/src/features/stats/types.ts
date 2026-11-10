export interface StatsPoint {date:string;value:number;detail:string|null;datePrecision?:string}
export interface RecentComparison {previousMean:number|null;recentMean:number|null;change:number|null;percent:number|null;previousCount:number;recentCount:number}
export interface StatsSeries {key:string;label:string;unit:string;points:StatsPoint[];recent:RecentComparison}
export interface ExerciseStats {id:string;name:string;mode:string;days:number;series:StatsSeries[]}
export interface StatsReport {months:number;from:string|null;to:string;completedWorkouts:number;excludedInProgress:number;measurementDays:number;attendance:StatsPoint[];exercises:ExerciseStats[];measurements:StatsSeries[]}
