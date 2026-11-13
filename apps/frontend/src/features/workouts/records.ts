import type { Prescription, Workout } from "../../shared/types";

export interface LoadRecord {
  loadKg: number;
  reps: number;
  performedOn: string;
}

// A record is an observed set, never a prescribed load or an estimated 1RM.
export function loadRecord(
  workouts: Workout[],
  exerciseId: string,
): LoadRecord | null {
  let best: LoadRecord | null = null;
  for (const workout of workouts) {
    for (const entry of workout.exercises) {
      const prescription = workout.plannedSession.exercises.find(
        (p) => p.id === entry.prescriptionId,
      );
      if (
        prescription?.exerciseId !== exerciseId ||
        prescription.mode !== "reps"
      )
        continue;
      for (const set of entry.sets) {
        if (
          !set.completed ||
          set.loadKg === null ||
          !Number.isFinite(set.loadKg) ||
          set.loadKg < 0 ||
          set.reps === null ||
          !Number.isInteger(set.reps) ||
          set.reps < 1
        )
          continue;
        const candidate = {
          loadKg: set.loadKg,
          reps: set.reps,
          performedOn: workout.performedOn,
        };
        if (
          !best ||
          candidate.loadKg > best.loadKg ||
          (candidate.loadKg === best.loadKg && candidate.reps > best.reps) ||
          (candidate.loadKg === best.loadKg &&
            candidate.reps === best.reps &&
            candidate.performedOn > best.performedOn)
        ) {
          best = candidate;
        }
      }
    }
  }
  return best;
}

export function improvesRecord(
  candidate: LoadRecord | null,
  saved: LoadRecord | null,
): boolean {
  return (
    candidate !== null &&
    (saved === null ||
      candidate.loadKg > saved.loadKg ||
      (candidate.loadKg === saved.loadKg && candidate.reps > saved.reps))
  );
}

export function showsLoadRecord(prescription: Prescription): boolean {
  return prescription.mode === "reps";
}
