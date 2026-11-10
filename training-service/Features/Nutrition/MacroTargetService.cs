using CoachConnect.Training.Features.Profile;
using CoachConnect.Training.Services;
namespace CoachConnect.Training.Features.Nutrition;

public sealed record MacroTargetInput(int Revision, DateOnly StartDate, decimal WeightKg, int MaintenanceKcal,
    int DeficitKcal, decimal ProteinPerKg, decimal FatPerKg, string MaintenanceSource);
public sealed record MacroTarget(int Revision, MacroTargetInput Settings, int TargetKcal, int ProteinGrams,
    int FatGrams, decimal CarbGrams, DateTimeOffset UpdatedAt);

public sealed class MacroTargetService(MacroTargetRepository repository, ProfileService profiles)
{
    public Task<MacroTarget?> Get(CancellationToken ct) => repository.Get(ct);
    public async Task<MacroTarget> Preview(MacroTargetInput input, CancellationToken ct)
    {
        var profile = await profiles.Get(ct);
        if (profile.Profile is null || profile.AgeYears is null or <18) throw new ApiError(400,"Un profil adulte est nécessaire pour définir cet objectif.");
        if (input.Revision < 0 || input.StartDate.Year is <2000 or >2100 || input.WeightKg is <25 or >350 || decimal.Round(input.WeightKg,2)!=input.WeightKg ||
            input.MaintenanceKcal is <1000 or >10000 || input.DeficitKcal is <0 or >1000 || input.ProteinPerKg is <1 or >3 || input.FatPerKg is <0.5m or >2 ||
            decimal.Round(input.ProteinPerKg,2)!=input.ProteinPerKg || decimal.Round(input.FatPerKg,2)!=input.FatPerKg || input.MaintenanceSource is not ("estimated" or "observed"))
            throw new ApiError(400,"Vérifie le poids, le maintien, le déficit et les ratios de macros.");
        var kcal=input.MaintenanceKcal-input.DeficitKcal;
        if (kcal<1200 || input.DeficitKcal>input.MaintenanceKcal*0.3m) throw new ApiError(400,"Cette cible est trop basse pour ce calcul automatique. Revois le maintien ou le déficit.");
        var protein=(int)decimal.Round(input.WeightKg*input.ProteinPerKg,0,MidpointRounding.AwayFromZero);
        var fat=(int)decimal.Round(input.WeightKg*input.FatPerKg,0,MidpointRounding.AwayFromZero);
        var carbs=decimal.Round((kcal-protein*4-fat*9)/4m,1,MidpointRounding.AwayFromZero);
        if(carbs<0)throw new ApiError(400,"Les protéines et lipides dépassent la cible calorique. Revois les réglages.");
        return new(input.Revision,input,kcal,protein,fat,carbs,default);
    }
    public async Task<MacroTarget> Save(MacroTargetInput input,CancellationToken ct) => await repository.Save(await Preview(input,ct),ct);
}
