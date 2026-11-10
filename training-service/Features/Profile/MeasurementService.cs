using CoachConnect.Training.Services;
namespace CoachConnect.Training.Features.Profile;

public sealed record MeasurementInput(Guid Id, DateOnly MeasuredOn, Dictionary<string, decimal>? Values,
    string? Notes, bool UpdateProfile, int ProfileRevision, string DatePrecision = "day");
public sealed record MeasurementEntry(Guid Id, DateOnly MeasuredOn, Dictionary<string, decimal> Values,
    string? Notes, bool UpdatedProfile, DateTimeOffset CreatedAt, string DatePrecision = "day");

public sealed class MeasurementService(MeasurementRepository repository, TimeProvider clock)
{
    public Task<List<MeasurementEntry>> All(CancellationToken ct) => repository.All(ct);
    public Task<MeasurementEntry> Add(MeasurementInput input, CancellationToken ct, bool allowFutureReference = false)
    {
        var today = DateOnly.FromDateTime(TimeZoneInfo.ConvertTimeBySystemTimeZoneId(clock.GetUtcNow(), "Europe/Paris").DateTime);
        if (input.Id == Guid.Empty || input.MeasuredOn < new DateOnly(1900, 1, 1) || input.MeasuredOn > (allowFutureReference ? today.AddDays(7) : today))
            throw new ApiError(400, "Choisis une date de mesure passée ou aujourd’hui (depuis 1900).");
        if(input.DatePrecision is not ("day" or "month") || (input.DatePrecision=="month"&&input.MeasuredOn.Day!=1))
            throw new ApiError(400,"Pour un relevé mensuel, indique le mois avec un jour technique égal à 1 ; ce jour ne représente pas le jour réel de mesure.");
        if (input.Values is null || input.Values.Count == 0) throw new ApiError(400, "Renseigne au moins une mesure.");
        foreach (var (key, value) in input.Values)
        {
            var bounds = key switch {
                "weightKg" => (25m, 350m), "heightCm" => (100m, 250m),
                "waistCm" or "hipsCm" or "chestCm" => (20m, 250m),
                "neckCm" or "armUnspecifiedCm" or "armFlexedCm" or "thighCm" or "calfCm" or "armLeftCm" or "armRightCm" or "thighLeftCm" or "thighRightCm" or "calfLeftCm" or "calfRightCm" => (5m, 150m),
                _ => throw new ApiError(400, "Cette mesure n’est pas reconnue.") };
            if (value < bounds.Item1 || value > bounds.Item2 || decimal.Round(value, 2) != value)
                throw new ApiError(400, $"Vérifie {key} : de {bounds.Item1} à {bounds.Item2}, avec au maximum deux décimales.");
        }
        if (input.Notes?.Length > 1000) throw new ApiError(400, "La note est limitée à 1 000 caractères.");
        if (input.UpdateProfile && (input.DatePrecision!="day" || input.MeasuredOn != today || !input.Values.Keys.Any(k => k is "weightKg" or "heightCm")))
            throw new ApiError(400, "Pour actualiser le profil, saisis le poids ou la stature d’aujourd’hui.");
        return repository.Add(input with { Notes = input.Notes?.Trim() }, ct);
    }
}
