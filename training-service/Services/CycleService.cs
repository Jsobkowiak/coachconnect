using System.Text.Json.Nodes;
namespace CoachConnect.Training.Services;

public sealed class CycleService(CycleRepository repository, CatalogClient catalog)
{
    public async Task<JsonObject> Save(Guid? id, JsonObject input, CancellationToken ct)
    {
        var previous = id is not null ? await repository.Get(id.Value, ct) : null;
        CycleRules.Validate(input);
        if (input.ToJsonString().Length > 2_000_000) throw new ApiError(413, "Ce cycle est trop volumineux.");
        var revision = 0;
        if (id is not null) { if (input["revision"] is not JsonValue n || !n.TryGetValue<int>(out revision) || revision < 1) throw new ApiError(400, "La version du cycle est requise."); }
        var data = input.DeepClone().AsObject();
        Keep(data, "name", "goal", "notes", "discipline", "status", "startDate", "durationWeeks", "weeks");
        var snapshots = previous is null ? new Dictionary<string, JsonNode>() : CycleRules.Prescriptions(previous)
            .Where(p => p["snapshot"] is JsonObject).GroupBy(p => p["exerciseId"]!.ToString()).ToDictionary(g => g.Key, g => g.First()["snapshot"]!.DeepClone());
        foreach (var p in CycleRules.Prescriptions(data))
        {
            var key = p["exerciseId"]!.ToString();
            if (!snapshots.ContainsKey(key)) snapshots[key] = await catalog.Exercise(key, ct);
            Keep(p, "id", "partId", "exerciseId", "mode", "sets", "repsMin", "repsMax", "durationSeconds", "distanceMeters", "restSeconds", "loadKg", "percent1RM", "rpe", "rir", "tempo", "group", "notes");
            p["snapshot"] = snapshots[key].DeepClone();
        }
        foreach (var session in data["weeks"]!.AsArray().SelectMany(w => w!["sessions"]!.AsArray()).Select(CycleRules.Object))
        {
            if (session["parts"] is not JsonArray parts) continue;
            foreach (var part in parts.Select(CycleRules.Object)) Keep(part, "id", "title", "format", "timeCapMinutes", "notes");
            var order = parts.Select((p, i) => (Id: p!["id"]!.ToString(), Index: i)).ToDictionary(p => p.Id, p => p.Index);
            var sorted = session["exercises"]!.AsArray().OrderBy(p => order[p!["partId"]!.ToString()]).Select(p => p!.DeepClone()).ToArray();
            session["exercises"] = new JsonArray(sorted);
        }
        data["endDate"] = DateOnly.TryParse(data["startDate"]?.ToString(), out var date) ? date.AddDays((int)data["durationWeeks"]! * 7 - 1).ToString("yyyy-MM-dd") : null;
        return await repository.Save(id, revision, data, ct);
    }
    public async Task<JsonObject> Duplicate(Guid id, CancellationToken ct)
    {
        var data = await repository.Get(id, ct); var name = data["name"] + " · copie"; data["name"] = name[..Math.Min(120, name.Length)];
        data["status"] = "draft"; data["startDate"] = null; data["endDate"] = null;
        foreach (var s in data["weeks"]!.AsArray().SelectMany(w => w!["sessions"]!.AsArray()))
        {
            s!["id"] = Guid.NewGuid().ToString();
            if (s["parts"] is not JsonArray parts) continue;
            var ids = parts.ToDictionary(p => p!["id"]!.ToString(), _ => Guid.NewGuid().ToString());
            foreach (var part in parts) part!["id"] = ids[part["id"]!.ToString()];
            foreach (var p in s["exercises"]!.AsArray()) p!["partId"] = ids[p["partId"]!.ToString()];
        }
        foreach (var p in CycleRules.Prescriptions(data)) p["id"] = Guid.NewGuid().ToString();
        foreach (var k in new[] { "id", "revision", "createdAt", "updatedAt" }) data.Remove(k);
        CycleRules.Validate(data); return await repository.Save(null, 0, data, ct);
    }
    static void Keep(JsonObject data, params string[] keys) { foreach (var k in data.Select(p => p.Key).Where(k => !keys.Contains(k)).ToArray()) data.Remove(k); }
}
