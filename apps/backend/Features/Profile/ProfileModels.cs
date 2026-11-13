namespace CoachConnect.Training.Features.Profile;

public sealed record ProfileData(string? DisplayName, DateOnly BirthDate, decimal WeightKg, decimal HeightCm,
    string Sex, string ActivityLevel, string Goal, string Experience, int WeeklySessions,
    decimal? TargetWeightKg, string? TrainingNotes, bool CalorieEstimatesEnabled);
public sealed record ProfileRequest(int Revision, ProfileData Data);
public sealed record StoredProfile(Guid Id, int Revision, ProfileData Data, DateTimeOffset CreatedAt, DateTimeOffset UpdatedAt);
public sealed record BodyMeasurement(Guid Id, int ProfileRevision, decimal WeightKg, decimal HeightCm, DateTimeOffset RecordedAt);
public sealed record CalorieRange(int Min, int Max);
public sealed record EnergyEstimate(string Method, decimal ActivityFactor, CalorieRange RestingKcal, CalorieRange MaintenanceKcal,
    int ProfileRevision, DateOnly CalculatedOn, string SourceUrl);
public sealed record ProfileState(StoredProfile? Profile, int? AgeYears, EnergyEstimate? Estimates, string? EstimateNote);
