using System.Text.Json;
using System.Text.Json.Nodes;
using CoachConnect.Training.Services;
namespace CoachConnect.Training.Features.Workouts;

public sealed record PerformedSet(int Number, int? Reps, double? LoadKg, double? DurationSeconds, double? DistanceMeters, double? Rpe, bool Completed);
public sealed record PerformedExercise(Guid PrescriptionId, List<PerformedSet> Sets);
public sealed record WorkoutRequest(Guid CycleId, int WeekNumber, Guid SessionId, string PerformedOn, string Status, string? Notes, int Revision, List<PerformedExercise> Exercises);

public sealed class WorkoutService(CycleRepository repository)
{
    static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    public async Task<JsonObject> Save(Guid id, WorkoutRequest input, CancellationToken ct)
    {
        if (id == Guid.Empty || input.Revision < 0 || input.WeekNumber is < 1 or > 52 ||
           !DateOnly.TryParseExact(input.PerformedOn, "yyyy-MM-dd", out _) || input.Status is not ("in_progress" or "completed") ||
           input.Notes?.Length > 5000 || input.Exercises is null || input.Exercises.Count > 60)
            throw new ApiError(400, "Séance réalisée invalide.");
        JsonObject plan;
        if (input.Revision > 0)
        {
            var old = await repository.Get(id, ct, true);
            if (old["cycleId"]!.ToString() != input.CycleId.ToString() || (int)old["weekNumber"]! != input.WeekNumber || old["sessionId"]!.ToString() != input.SessionId.ToString())
                throw new ApiError(400, "L’origine d’une séance réalisée ne peut pas être modifiée.");
            plan = old["plannedSession"]!.DeepClone().AsObject();
        }
        else
        {
            var cycle = await repository.Get(input.CycleId, ct);
            var week = cycle["weeks"]!.AsArray().FirstOrDefault(w => (int)w!["number"]! == input.WeekNumber);
            plan = week?["sessions"]!.AsArray().FirstOrDefault(s => s!["id"]!.ToString() == input.SessionId.ToString())?.DeepClone().AsObject()
                ?? throw new ApiError(400, "Cette séance n’existe pas dans la semaine choisie.");
        }
        var prescriptions = plan["exercises"]!.AsArray().ToDictionary(p => Guid.Parse(p!["id"]!.ToString()), p => p!);
        var seen = new HashSet<Guid>();
        foreach (var e in input.Exercises)
        {
            if (e is null || !prescriptions.TryGetValue(e.PrescriptionId, out var p) || !seen.Add(e.PrescriptionId) || e.Sets is null || e.Sets.Count > 30)
                throw new ApiError(400, "Exercice ou séries invalides.");
            var numbers = new HashSet<int>();
            foreach (var s in e.Sets)
            {
                if (s is null || s.Number is < 1 or > 30 || !numbers.Add(s.Number) || s.Reps is < 0 or > 1000 ||
                   !Valid(s.LoadKg, 0, 1000) || !Valid(s.DurationSeconds, 0, 86400) || !Valid(s.DistanceMeters, 0, 100000) || !Valid(s.Rpe, 1, 10))
                    throw new ApiError(400, "Une performance contient une valeur invalide.");
                if (s.Completed && (p["mode"]!.ToString() switch { "reps" => s.Reps is null, "time" => s.DurationSeconds is null, "distance" => s.DistanceMeters is null, _ => true }))
                    throw new ApiError(400, "Renseigne la performance avant de valider la série.");
            }
        }
        if (input.Status == "completed" && !input.Exercises.Any(e => e.Sets.Any(s => s.Completed)))
            throw new ApiError(400, "Valide au moins une série avant de terminer la séance.");
        var data = JsonSerializer.SerializeToNode(input, JsonOptions)!.AsObject(); data.Remove("revision"); data["plannedSession"] = plan;
        return await repository.SaveWorkout(id, input.Revision, data, ct);
    }
    static bool Valid(double? n, double min, double max) => n is null || (double.IsFinite(n.Value) && n >= min && n <= max);
}
