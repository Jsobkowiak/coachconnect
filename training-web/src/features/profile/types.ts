export interface ProfileData {
  displayName: string; birthDate: string; weightKg: number; heightCm: number;
  sex: string; activityLevel: string; goal: string; experience: string; weeklySessions: number;
  targetWeightKg: number | null; trainingNotes: string; calorieEstimatesEnabled: boolean;
}
export interface ProfileState {
  profile: { id: string; revision: number; data: ProfileData; updatedAt: string } | null;
  ageYears: number | null;
  estimates: { method: string; activityFactor: number; restingKcal: {min:number;max:number}; maintenanceKcal: {min:number;max:number}; profileRevision: number; calculatedOn: string; sourceUrl: string } | null;
  estimateNote: string | null;
}
export interface Measurement { id: string; profileRevision:number; weightKg:number; heightCm:number; recordedAt:string }
