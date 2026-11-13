import test from "node:test";
import assert from "node:assert/strict";
import {
  loadRecord,
  improvesRecord,
} from "../src/features/workouts/records.ts";
import type { Workout } from "../src/shared/types.ts";
function workout(
  id: string,
  loadKg: number | null,
  reps: number | null,
  completed = true,
  exerciseId = "bench",
  mode = "reps",
): Workout {
  return {
    id,
    performedOn: "2026-10-16",
    plannedSession: { exercises: [{ id: "p", exerciseId, mode }] },
    exercises: [{ prescriptionId: "p", sets: [{ loadKg, reps, completed }] }],
  } as Workout;
}
test("charge maximale réalisée, répétitions et variantes distinctes", () => {
  const history = [
    workout("1", 60, 8),
    workout("2", 80, 3),
    workout("3", 80, 5),
    workout("4", 100, 1, false),
    workout("5", 200, 1, true, "other"),
  ];
  assert.deepEqual(loadRecord(history, "bench"), {
    loadKg: 80,
    reps: 5,
    performedOn: "2026-10-16",
  });
});
test("ne compte ni séries ratées, ni charge absente, ni prescription au temps", () => {
  assert.equal(
    loadRecord(
      [
        workout("1", 100, 0),
        workout("2", null, 8),
        workout("3", 150, 8, true, "bench", "time"),
      ],
      "bench",
    ),
    null,
  );
  assert.equal(loadRecord([workout("4", 0, 10)], "bench")?.loadKg, 0);
});
test("progrès : charge supérieure ou davantage de répétitions à charge égale", () => {
  const saved = { loadKg: 80, reps: 5, performedOn: "2026-10-15" };
  assert.equal(
    improvesRecord({ ...saved, loadKg: 82.5, reps: 1 }, saved),
    true,
  );
  assert.equal(improvesRecord({ ...saved, reps: 6 }, saved), true);
  assert.equal(improvesRecord({ ...saved, reps: 4 }, saved), false);
  assert.equal(
    improvesRecord({ ...saved, loadKg: 60, reps: 20 }, saved),
    false,
  );
  assert.equal(improvesRecord(saved, null), true);
});
