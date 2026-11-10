using System.Text.Json.Nodes;
using CoachConnect.Training.Services;
namespace CoachConnect.Training.Features.Stats;

public sealed class StatsService(StatsRepository repository, TimeProvider clock)
{
    static readonly (string Key, string Label, string Unit)[] BodyMetrics = [
        ("weightKg","Poids","kg"),("heightCm","Taille · stature","cm"),("waistCm","Tour de taille","cm"),
        ("hipsCm","Tour de hanches","cm"),("chestCm","Tour de poitrine","cm"),("neckCm","Tour de cou","cm"),
        ("armUnspecifiedCm","Bras · contraction et côté non précisés","cm"),("armFlexedCm","Bras contracté · côté non précisé","cm"),
        ("thighCm","Cuisse · côté non précisé","cm"),("calfCm","Mollet · côté non précisé","cm"),
        ("armLeftCm","Bras gauche","cm"),("armRightCm","Bras droit","cm"),
        ("thighLeftCm","Cuisse gauche","cm"),("thighRightCm","Cuisse droite","cm"),
        ("calfLeftCm","Mollet gauche","cm"),("calfRightCm","Mollet droit","cm")];
    static string Text(JsonNode? node) => node?.ToString() ?? "";
    static decimal? Number(JsonNode? node) => node is JsonValue v && v.TryGetValue<decimal>(out var n) ? n : null;
    static JsonArray Items(JsonNode? node) => node as JsonArray ?? [];
    static bool Done(JsonNode? node) => node is JsonValue v && v.TryGetValue<bool>(out var b) && b;
    static decimal Round(decimal value) => decimal.Round(value, 2, MidpointRounding.AwayFromZero);
    sealed record SetReading(DateOnly Date, decimal? Reps, decimal? Load, decimal? Seconds, decimal? Meters);
    sealed record ExerciseBucket(string Id, string Name, string Mode, List<SetReading> Sets);
    public async Task<StatsReport> Get(int months, int? minReps, int? maxReps, CancellationToken ct, bool includeReferenceMeasurements = false)
    {
        if (months is not (0 or 1 or 3 or 6 or 12)) throw new ApiError(400,"Choisis 1, 3, 6, 12 mois ou toute la période.");
        if (minReps is < 1 or > 1000 || maxReps is < 1 or > 1000 || (minReps.HasValue && maxReps.HasValue && minReps > maxReps))
            throw new ApiError(400,"Vérifie la plage de répétitions (1 à 1 000).");
        var today = DateOnly.FromDateTime(TimeZoneInfo.ConvertTimeBySystemTimeZoneId(clock.GetUtcNow(),"Europe/Paris").DateTime);
        DateOnly? from = months == 0 ? null : today.AddMonths(-months);
        bool InRange(DateOnly date) => date <= today && (from is null || date >= from);
        var snapshot = await repository.Read(ct);
        var buckets = new Dictionary<string, ExerciseBucket>(); var attendance = new List<DateOnly>(); var excluded = 0;
        foreach (var workout in snapshot.Workouts)
        {
            if (!DateOnly.TryParseExact(Text(workout["performedOn"]),"yyyy-MM-dd",out var date) || date > today) continue;
            if (Text(workout["status"]) != "completed") { if (InRange(date)) excluded++; continue; }
            if (InRange(date)) attendance.Add(date);
            var plan = Items(workout["plannedSession"]?["exercises"]);
            foreach (var exercise in Items(workout["exercises"]))
            {
                if (exercise is null) continue;
                var prescription = plan.FirstOrDefault(p => Text(p?["id"]) == Text(exercise["prescriptionId"]));
                if (prescription is null) continue;
                var id = Text(prescription["exerciseId"]); var mode = Text(prescription["mode"]);
                if (id.Length == 0 || mode is not ("reps" or "time" or "distance")) continue;
                var key = id + ":" + mode;
                if (!buckets.TryGetValue(key, out var bucket))
                {
                    bucket = new(id,Text(prescription["snapshot"]?["name"]) is { Length: > 0 } name ? name : "Exercice",mode,[]);
                    buckets.Add(key,bucket);
                }
                if (!InRange(date)) continue;
                foreach (var set in Items(exercise["sets"]))
                {
                    if (set is null || !Done(set["completed"])) continue;
                    var reps = Number(set["reps"]); var seconds = Number(set["durationSeconds"]); var meters = Number(set["distanceMeters"]);
                    if (mode == "reps" && (reps is null or <= 0 || (minReps.HasValue && reps < minReps) || (maxReps.HasValue && reps > maxReps))) continue;
                    if ((mode == "time" && seconds is null or <= 0) || (mode == "distance" && meters is null or <= 0)) continue;
                    bucket.Sets.Add(new(date,reps,Number(set["loadKg"]),seconds,meters));
                }
            }
        }
        StatsSeries Series(string key,string label,string unit,List<StatsPoint> points) => new(key,label,unit,points,Compare(points,today));
        var exercises = new List<ExerciseStats>();
        foreach (var bucket in buckets.Values.OrderBy(b=>b.Name,StringComparer.Create(System.Globalization.CultureInfo.GetCultureInfo("fr-FR"),true)).ThenBy(b=>b.Id).ThenBy(b=>b.Mode=="reps"?0:b.Mode=="time"?1:2))
        {
            var groups = bucket.Sets.GroupBy(s=>s.Date).OrderBy(g=>g.Key).ToList(); var series = new List<StatsSeries>();
            List<StatsPoint> Points(Func<List<SetReading>,decimal?> value,Func<List<SetReading>,string?>? detail=null) => groups.Select(g => {
                var list=g.ToList(); var n=value(list); return n.HasValue ? new StatsPoint(g.Key,Round(n.Value),detail?.Invoke(list)) : null;
            }).OfType<StatsPoint>().ToList();
            series.Add(Series("sets","Séries validées par jour","séries",Points(s=>s.Count)));
            if (bucket.Mode == "reps")
            {
                SetReading? Best(List<SetReading> sets) => sets.Where(s=>s.Load.HasValue).OrderByDescending(s=>s.Load).ThenByDescending(s=>s.Reps).FirstOrDefault();
                series.Insert(0,Series("load","Charge maximale","kg",Points(s=>Best(s)?.Load,s=>Best(s) is {} best ? $"{best.Reps} répétitions · charge saisie, hors poids du corps" : null)));
                series.Add(Series("maxReps","Répétitions · meilleure série","rép.",Points(s=>s.Max(v=>v.Reps))));
                series.Add(Series("totalReps","Répétitions totales par jour","rép.",Points(s=>s.Sum(v=>v.Reps))));
                series.Add(Series("volume","Volume externe par jour","kg·rép.",Points(s=>s.All(v=>v.Load.HasValue) ? s.Sum(v=>v.Load*v.Reps) : null)));
            }
            else if (bucket.Mode == "time")
            {
                series.Insert(0,Series("duration","Durée · meilleure série","s",Points(s=>s.Max(v=>v.Seconds))));
                series.Add(Series("totalDuration","Durée totale par jour","s",Points(s=>s.Sum(v=>v.Seconds))));
            }
            else
            {
                series.Insert(0,Series("distance","Distance · meilleure série","m",Points(s=>s.Max(v=>v.Meters))));
                series.Add(Series("totalDistance","Distance totale par jour","m",Points(s=>s.Sum(v=>v.Meters))));
            }
            exercises.Add(new(bucket.Id,bucket.Name,bucket.Mode,groups.Count,series));
        }
        // One point per date and metric. Explicit diary readings take priority over profile history.
        var body = new Dictionary<(DateOnly Date,string Key,string Precision),(decimal Value,string Source)>();
        foreach (var legacy in snapshot.Legacy)
        {
            var date=DateOnly.FromDateTime(TimeZoneInfo.ConvertTimeBySystemTimeZoneId(legacy.RecordedAt,"Europe/Paris").DateTime);
            if (!InRange(date)) continue;
            body[(date,"weightKg","day")]=(legacy.WeightKg,"Historique du profil"); body[(date,"heightCm","day")]=(legacy.HeightCm,"Historique du profil");
        }
        foreach (var entry in snapshot.Measurements.OrderBy(m=>m.CreatedAt).ThenBy(m=>m.Id))
        {
            if (!InRange(entry.MeasuredOn) && !(includeReferenceMeasurements && entry.MeasuredOn > today && (from is null || entry.MeasuredOn >= from))) continue;
            foreach (var (key,value) in entry.Values) body[(entry.MeasuredOn,key,entry.DatePrecision)]=(value,(entry.MeasuredOn > today ? "Date de référence à venir · Carnet de mensurations" : "Carnet de mensurations")+(string.IsNullOrWhiteSpace(entry.Notes)?"":" · "+entry.Notes));
        }
        var measurements=BodyMetrics.Select(m=>Series(m.Key,m.Label,m.Unit,body.Where(b=>b.Key.Key==m.Key).OrderBy(b=>b.Key.Date).Select(b=>new StatsPoint(b.Key.Date,b.Value.Value,b.Value.Source,b.Key.Precision)).ToList())).ToList();
        var allDates = attendance.Concat(body.Keys.Select(k=>k.Date)).ToList();
        var start=from ?? (allDates.Count>0 ? allDates.Min() : today);
        var firstMonday=start.AddDays(-(((int)start.DayOfWeek+6)%7));
        var weekly=new List<StatsPoint>();
        for (var date=firstMonday;date<=today;date=date.AddDays(7)) weekly.Add(new(date,attendance.Count(d=>d>=date&&d<date.AddDays(7)),"Séances terminées · semaine du lundi"));
        return new(months,from,today,attendance.Count,excluded,body.Keys.Select(k=>k.Date).Distinct().Count(),weekly,exercises,measurements);
    }
    static RecentComparison Compare(List<StatsPoint> points,DateOnly today)
    {
        var recent=points.Where(p=>p.DatePrecision=="day"&&p.Date>=today.AddDays(-27)&&p.Date<=today).ToList();
        var previous=points.Where(p=>p.DatePrecision=="day"&&p.Date>=today.AddDays(-55)&&p.Date<today.AddDays(-27)).ToList();
        decimal? a=previous.Count>=3 ? Round(previous.Average(p=>p.Value)) : null;
        decimal? b=recent.Count>=3 ? Round(recent.Average(p=>p.Value)) : null;
        var delta=a.HasValue&&b.HasValue ? Round(b.Value-a.Value) : (decimal?)null;
        return new(a,b,delta,delta.HasValue&&a!=0 ? Round(delta.Value/a!.Value*100m) : null,previous.Count,recent.Count);
    }
}
