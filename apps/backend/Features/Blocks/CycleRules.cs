using CoachConnect.Training.Shared;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
namespace CoachConnect.Training.Features.Blocks;

public static class CycleRules
{
    public static void Validate(JsonObject cycle)
    {
        Text(cycle, "name", 120, true); Text(cycle, "goal", 1000); Text(cycle, "notes", 5000);
        Choice(cycle, "discipline", "strength", "crossfit", "mixed"); Choice(cycle, "status", "draft", "active", "archived");
        if (cycle["startDate"] is not null && (!cycle["startDate"]!.AsValue().TryGetValue<string>(out var date) ||
            (!string.IsNullOrWhiteSpace(date) && !DateOnly.TryParseExact(date, "yyyy-MM-dd", out _)))) Fail("La date de début est invalide.");
        var weeks = List(cycle, "weeks", 1, 52);
        Integer(cycle, "durationWeeks", 1, 52);
        if (Number(cycle, "durationWeeks") != weeks.Count) Fail("La durée doit correspondre au nombre de semaines.");
        var seen = new HashSet<Guid>();
        for (var i = 0; i < weeks.Count; i++)
        {
            var week = Object(weeks[i]); Integer(week, "number", 1, 52);
            if (Number(week, "number") != i + 1) Fail("Les semaines doivent être numérotées dans l’ordre.");
            Text(week, "focus", 200); Text(week, "notes", 2000);
            if (week["deload"] is not JsonValue value || !value.TryGetValue<bool>(out _)) Fail("Le champ semaine allégée doit être booléen.");
            var sessions = List(week, "sessions", 0, 28);
            if (cycle["status"]!.ToString() == "active" && sessions.Count == 0) Fail("Un cycle actif doit avoir une séance dans chaque semaine.");
            foreach (var item in sessions)
            {
                var session = Object(item); Unique(session, seen);
                Text(session, "title", 120, true); Text(session, "notes", 3000); Text(session, "warmup", 2000); Text(session, "cooldown", 2000);
                Integer(session, "day", 0, 6); Integer(session, "durationMinutes", 1, 300);
                Choice(session, "format", "traditional", "circuit", "amrap", "emom", "for_time"); OptionalInteger(session, "timeCapMinutes", 1, 300);
                var exercises = List(session, "exercises", 0, 60);
                if (cycle["status"]!.ToString() == "active" && exercises.Count == 0) Fail("Chaque séance d’un cycle actif doit contenir un exercice.");
                var partIds = new HashSet<string>();
                if (session["parts"] is not null)
                {
                    foreach (var node in List(session, "parts", 1, 12))
                    {
                        var part = Object(node); Unique(part, seen);
                        partIds.Add(part["id"]!.ToString());
                        Text(part, "title", 120, true); Text(part, "notes", 2000);
                        Choice(part, "format", "traditional", "circuit", "amrap", "emom", "for_time");
                        OptionalInteger(part, "timeCapMinutes", 1, 300);
                        if (cycle["status"]!.ToString() == "active" && !exercises.Any(e => e?["partId"]?.ToString() == part["id"]!.ToString()))
                            Fail("Chaque partie d’une séance active doit contenir un exercice.");
                    }
                }
                foreach (var entry in exercises)
                {
                    var exercise = Object(entry); Unique(exercise, seen);
                    Text(exercise, "partId", 100);
                    if (partIds.Count > 0 ? !partIds.Contains(exercise["partId"]?.ToString() ?? "") : exercise["partId"] is not null)
                        Fail("Chaque exercice doit appartenir à une partie valide de sa séance."); Text(exercise, "exerciseId", 100, true);
                    if (!Guid.TryParse(exercise["exerciseId"]!.ToString(), out _)) Fail("Identifiant d’exercice invalide.");
                    Integer(exercise, "sets", 1, 30); Integer(exercise, "restSeconds", 0, 900); Choice(exercise, "mode", "reps", "time", "distance");
                    switch (exercise["mode"]!.ToString())
                    {
                        case "reps":
                            Integer(exercise, "repsMin", 1, 1000); Integer(exercise, "repsMax", 1, 1000);
                            if (Number(exercise, "repsMin") > Number(exercise, "repsMax")) Fail("La plage de répétitions est inversée."); break;
                        case "time": Integer(exercise, "durationSeconds", 1, 86400); break;
                        case "distance": Numeric(exercise, "distanceMeters", 1, 100000, true); break;
                    }
                    Numeric(exercise, "loadKg", 0, 1000); Numeric(exercise, "percent1RM", 1, 150); Numeric(exercise, "rpe", 1, 10); OptionalInteger(exercise, "rir", 0, 10);
                    if (exercise["rpe"] is not null && exercise["rir"] is not null) Fail("Choisis RPE ou RIR pour un exercice, pas les deux.");
                    if (exercise["loadKg"] is not null && exercise["percent1RM"] is not null) Fail("Choisis une charge en kg ou en % de 1RM.");
                    Text(exercise, "tempo", 40); Text(exercise, "group", 30); Text(exercise, "notes", 2000);
                }
            }
        }
    }
    public static IEnumerable<JsonObject> Prescriptions(JsonObject cycle) => cycle["weeks"]!.AsArray()
        .SelectMany(w => w!["sessions"]!.AsArray()).SelectMany(s => s!["exercises"]!.AsArray()).Select(Object);
    public static JsonObject Object(JsonNode? node) => node as JsonObject ?? throw new ApiError(400, "Structure invalide.");
    public static double Number(JsonObject data, string key) => data[key]!.GetValue<double>();
    static void Text(JsonObject data, string key, int max, bool required = false)
    {
        if (data[key] is null && !required) return;
        if (data[key] is not JsonValue v || !v.TryGetValue<string>(out var text) || text.Length > max || (required && string.IsNullOrWhiteSpace(text))) Fail($"Texte invalide pour {key}.");
    }
    static JsonArray List(JsonObject data, string key, int min, int max) => data[key] is JsonArray a && a.Count >= min && a.Count <= max ? a : throw new ApiError(400, $"Nombre d’éléments invalide pour {key}.");
    static void Choice(JsonObject data, string key, params string[] choices) { if (data[key] is not JsonValue v || !v.TryGetValue<string>(out var text) || !choices.Contains(text)) Fail($"Valeur invalide pour {key}."); }
    static void Numeric(JsonObject data, string key, double min, double max, bool required = false)
    {
        if (data[key] is null && !required) return;
        if (data[key] is not JsonValue v || !v.TryGetValue<double>(out var n) || !double.IsFinite(n) || n < min || n > max) Fail($"Valeur numérique invalide pour {key}.");
    }
    static void Integer(JsonObject d, string k, int min, int max) { Numeric(d, k, min, max, true); if (Number(d, k) % 1 != 0) Fail($"Un entier est requis pour {k}."); }
    static void OptionalInteger(JsonObject d, string k, int min, int max) { if (d[k] is not null) Integer(d, k, min, max); }
    static void Unique(JsonObject d, HashSet<Guid> seen) { Text(d, "id", 100, true); if (!Guid.TryParse(d["id"]!.ToString(), out var id) || !seen.Add(id)) Fail("Les séances et prescriptions doivent avoir des identifiants uniques et valides."); }
    static void Fail(string message) => throw new ApiError(400, message);
}
