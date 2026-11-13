using CoachConnect.Training.Shared;
namespace CoachConnect.Training.Features.Profile;

public sealed class ProfileService(ProfileRepository repository, TimeProvider clock)
{
    static readonly Dictionary<string, decimal> Activity = new() { ["low"] = 1.4m, ["moderate"] = 1.6m, ["active"] = 1.8m, ["very_active"] = 2m };
    DateOnly Today => DateOnly.FromDateTime(TimeZoneInfo.ConvertTimeBySystemTimeZoneId(clock.GetUtcNow(), "Europe/Paris").DateTime);
    public static int Age(DateOnly birth, DateOnly today) => today.Year - birth.Year - (birth.AddYears(today.Year - birth.Year) > today ? 1 : 0);
    public async Task<ProfileState> Get(CancellationToken ct) => View(await repository.Get(ct));
    public async Task<ProfileState> Save(ProfileRequest request, CancellationToken ct)
    {
        if (request.Data is null) throw new ApiError(400, "Renseigne les informations du profil.");
        var d = request.Data with { DisplayName = request.Data.DisplayName?.Trim(), TrainingNotes = request.Data.TrainingNotes?.Trim() };
        if (request.Revision < 0 || d.BirthDate > Today || Age(d.BirthDate, Today) is < 13 or > 110)
            throw new ApiError(400, "Renseigne une date de naissance valide (13 à 110 ans).");
        if (d.WeightKg is < 25 or > 350 || d.HeightCm is < 100 or > 250 || d.TargetWeightKg is < 25 or > 350)
            throw new ApiError(400, "Vérifie les mesures : poids de 25 à 350 kg, taille de 100 à 250 cm.");
        if (decimal.Round(d.WeightKg, 2) != d.WeightKg || decimal.Round(d.HeightCm, 2) != d.HeightCm || (d.TargetWeightKg is decimal t && decimal.Round(t, 2) != t))
            throw new ApiError(400, "Utilise au maximum deux décimales pour les mesures.");
        if (!Activity.ContainsKey(d.ActivityLevel ?? "") || d.Sex is not ("male" or "female" or "unspecified") ||
            d.Goal is not ("maintenance" or "muscle_gain" or "fat_loss" or "performance") ||
            d.Experience is not ("beginner" or "intermediate" or "advanced") || d.WeeklySessions is < 0 or > 14 ||
            d.DisplayName?.Length > 80 || d.TrainingNotes?.Length > 1000)
            throw new ApiError(400, "Vérifie l’activité, l’objectif, l’expérience et les champs du profil.");
        return View(await repository.Save(request.Revision, d, ct));
    }
    ProfileState View(StoredProfile? profile)
    {
        if (profile is null) return new(null, null, null, null);
        var d = profile.Data; var age = Age(d.BirthDate, Today);
        if (!d.CalorieEstimatesEnabled) return new(profile, age, null, "Calcul calorique désactivé dans ton profil.");
        if (age < 18) return new(profile, age, null, "L’estimation calorique automatique est réservée aux adultes.");
        var baseValue = 10m * d.WeightKg + 6.25m * d.HeightCm - 5m * age;
        var low = baseValue + (d.Sex == "male" ? 5m : -161m);
        var high = baseValue + (d.Sex == "female" ? -161m : 5m);
        var factor = Activity[d.ActivityLevel];
        static int Round(decimal value) => (int)(decimal.Round(value / 10m, 0, MidpointRounding.AwayFromZero) * 10m);
        var estimate = new EnergyEstimate("Mifflin–St Jeor", factor, new(Round(low), Round(high)), new(Round(low * factor), Round(high * factor)),
            profile.Revision, Today, "https://pubmed.ncbi.nlm.nih.gov/2305711/");
        return new(profile, age, estimate, d.Sex == "unspecified" ? "Fourchette calculée avec les deux coefficients physiologiques de la formule." : null);
    }
    public Task<List<BodyMeasurement>> Measurements(CancellationToken ct) => repository.Measurements(ct);
}
