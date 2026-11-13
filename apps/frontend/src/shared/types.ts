export interface License {
  author: string;
  name: string;
  url: string;
  source_url: string;
  ai_generated?: boolean;
}
export interface Media {
  title: string;
  source: string;
  license: License;
  images: { filename: string; license?: License }[];
}
export interface Exercise {
  id: string;
  name: string;
  equipment: string;
  primary_muscles: string[];
  description?: string;
  instructions: string[];
  common_mistakes?: string[];
  required_equipment?: string[];
  media?: Media;
  aliases?: string[];
}
export interface Prescription {
  partId?: string;
  id: string;
  exerciseId: string;
  snapshot: Exercise;
  mode: "reps" | "time" | "distance";
  sets: number;
  repsMin: number;
  repsMax: number;
  durationSeconds?: number | null;
  distanceMeters?: number | null;
  restSeconds: number;
  loadKg: number | null;
  percent1RM?: number | null;
  rpe?: number | null;
  rir?: number | null;
  tempo?: string;
  group?: string;
  notes?: string;
}
export interface SessionPart {
  id: string; title: string; format: string; timeCapMinutes?: number | null; notes?: string;
}
export interface Session {
  parts?: SessionPart[];
  id: string;
  title: string;
  day: number;
  format: string;
  durationMinutes: number;
  timeCapMinutes?: number | null;
  warmup?: string;
  cooldown?: string;
  notes?: string;
  exercises: Prescription[];
}
export interface Week {
  number: number;
  focus: string;
  notes: string;
  deload: boolean;
  sessions: Session[];
}
export interface Cycle {
  id?: string;
  revision?: number;
  name: string;
  goal: string;
  notes: string;
  discipline: string;
  status: string;
  startDate: string | null;
  endDate?: string | null;
  durationWeeks: number;
  weeks: Week[];
}
export interface PerformedSet {
  number: number;
  reps: number | null;
  loadKg: number | null;
  durationSeconds: number | null;
  distanceMeters: number | null;
  rpe: number | null;
  completed: boolean;
}
export interface Workout {
  id: string;
  revision: number;
  cycleId: string;
  weekNumber: number;
  sessionId: string;
  performedOn: string;
  status: "in_progress" | "completed";
  notes: string;
  exercises: { prescriptionId: string; sets: PerformedSet[] }[];
  plannedSession: Session;
}
