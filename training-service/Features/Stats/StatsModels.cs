namespace CoachConnect.Training.Features.Stats;
public sealed record StatsPoint(DateOnly Date, decimal Value, string? Detail = null, string DatePrecision = "day");
public sealed record RecentComparison(decimal? PreviousMean, decimal? RecentMean, decimal? Change, decimal? Percent, int PreviousCount, int RecentCount);
public sealed record StatsSeries(string Key, string Label, string Unit, List<StatsPoint> Points, RecentComparison Recent);
public sealed record ExerciseStats(string Id, string Name, string Mode, int Days, List<StatsSeries> Series);
public sealed record StatsReport(int Months, DateOnly? From, DateOnly To, int CompletedWorkouts, int ExcludedInProgress,
    int MeasurementDays, List<StatsPoint> Attendance, List<ExerciseStats> Exercises, List<StatsSeries> Measurements);
