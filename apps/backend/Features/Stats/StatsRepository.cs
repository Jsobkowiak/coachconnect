using CoachConnect.Training.Features.Measurements;
using CoachConnect.Training.Features.Accounts;
using System.Data;
using System.Text.Json;
using System.Text.Json.Nodes;
using CoachConnect.Training.Features.Profile;
using Npgsql;
namespace CoachConnect.Training.Features.Stats;

public sealed record LegacyReading(decimal WeightKg, decimal HeightCm, DateTimeOffset RecordedAt);
public sealed record StatsSnapshot(List<JsonObject> Workouts, List<MeasurementEntry> Measurements, List<LegacyReading> Legacy);
public sealed class StatsRepository(NpgsqlDataSource database, CurrentAccount account)
{
    async Task<NpgsqlDataReader> ReadOwned(NpgsqlCommand cmd,CancellationToken ct){cmd.Parameters.AddWithValue(account.Id);return await cmd.ExecuteReaderAsync(ct);}
    static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    // Read a consistent snapshot without updating plans, completed sessions or measurements.
    public async Task<StatsSnapshot> Read(CancellationToken ct)
    {
        await using var connection = await database.OpenConnectionAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(IsolationLevel.RepeatableRead, ct);
        var workouts = new List<JsonObject>(); var measurements = new List<MeasurementEntry>(); var legacy = new List<LegacyReading>();
        await using (var cmd = new NpgsqlCommand("SELECT document FROM training_workouts WHERE owner_id=$1", connection, transaction))
        await using (var reader = await ReadOwned(cmd, ct))
            while (await reader.ReadAsync(ct)) workouts.Add(JsonNode.Parse(reader.GetString(0))!.AsObject());
        await using (var cmd = new NpgsqlCommand("SELECT m.document,m.created_at FROM training_measurement_entries m JOIN training_profiles p ON p.id=m.profile_id WHERE p.owner_id=$1", connection, transaction))
        await using (var reader = await ReadOwned(cmd, ct))
            while (await reader.ReadAsync(ct))
            {
                var input = JsonSerializer.Deserialize<MeasurementInput>(reader.GetString(0), Json)!;
                measurements.Add(new(input.Id, input.MeasuredOn, input.Values!, input.Notes, input.UpdateProfile, reader.GetFieldValue<DateTimeOffset>(1), input.DatePrecision));
            }
        // No limit: old profile readings must remain visible beyond the latest 100 entries.
        await using (var cmd = new NpgsqlCommand("SELECT m.weight_kg,m.height_cm,m.recorded_at FROM training_body_measurements m JOIN training_profiles p ON p.id=m.profile_id WHERE p.owner_id=$1 ORDER BY m.recorded_at,m.id", connection, transaction))
        await using (var reader = await ReadOwned(cmd, ct))
            while (await reader.ReadAsync(ct)) legacy.Add(new(reader.GetDecimal(0),reader.GetDecimal(1),reader.GetFieldValue<DateTimeOffset>(2)));
        await transaction.CommitAsync(ct);
        return new(workouts, measurements, legacy);
    }
}
