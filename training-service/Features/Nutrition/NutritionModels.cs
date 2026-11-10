namespace CoachConnect.Training.Features.Nutrition;
public sealed record SessionEnergyInput(Guid SessionId, string Activity, int DurationMinutes);
public sealed record NutritionInput(int Revision, int CycleRevision, string DailyActivity, List<SessionEnergyInput> Sessions);
public sealed record NutritionSettings(int Revision, NutritionInput Data);
public sealed record EnergyActivity(string Id, string Label, decimal Met, string SourceUrl);
public sealed record DailyActivity(string Id, string Label, decimal Factor);
public sealed record Kcal(decimal Min, decimal Max);
public sealed record PlannedEnergySession(Guid Id, string Title, int Week, int Day, string Format, int DurationMinutes, string? Activity, bool Inferred, bool Empty, decimal? GrossKcal);
public sealed record EnergyDay(int Number, DateOnly? Date, string Status, List<PlannedEnergySession> Sessions, Kcal? Maintenance, Kcal? TrainingExtra);
public sealed record EnergyWeek(int Number, string? Focus, bool Deload, bool Complete, int MissingSessions, int TrainingDays, int TrainingMinutes, Kcal? WeeklyMaintenance, Kcal? DailyAverage, List<EnergyDay> Days);
public sealed record NutritionReport(Guid CycleId, string CycleName, int CycleRevision, int DurationWeeks, int ProfileRevision,
    int SettingsRevision, bool NeedsReview, string DailyActivity, List<SessionEnergyInput> Overrides, List<DailyActivity> DailyActivities,
    List<EnergyActivity> Activities, Kcal Baseline, bool Complete, int MissingSessions, Kcal? BlockMaintenance, Kcal? DailyAverage,
    string? ProfileNote, DateTimeOffset CalculatedAt, List<EnergyWeek> Weeks);
