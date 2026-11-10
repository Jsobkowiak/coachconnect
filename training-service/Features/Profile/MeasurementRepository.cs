using CoachConnect.Training.Features.Accounts;
using System.Text.Json;
using Npgsql;
using NpgsqlTypes;
using CoachConnect.Training.Services;
namespace CoachConnect.Training.Features.Profile;

public sealed class MeasurementRepository(NpgsqlDataSource database, CurrentAccount account)
{
    static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    public async Task Initialize(CancellationToken ct)
    {
        await using var cmd = database.CreateCommand("""
            CREATE TABLE IF NOT EXISTS training_measurement_entries (
              id uuid PRIMARY KEY, profile_id uuid NOT NULL REFERENCES training_profiles(id),
              measured_on date NOT NULL, document jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
            CREATE INDEX IF NOT EXISTS training_measurement_entries_date_idx
              ON training_measurement_entries(profile_id, measured_on DESC, created_at DESC);
            """);
        await cmd.ExecuteNonQueryAsync(ct);
    }
    async Task<NpgsqlDataReader> ReadOwned(NpgsqlCommand cmd,CancellationToken ct){cmd.Parameters.AddWithValue(account.Id);return await cmd.ExecuteReaderAsync(ct);}
    static MeasurementEntry Read(NpgsqlDataReader r)
    {
        var input = JsonSerializer.Deserialize<MeasurementInput>(r.GetString(0), Json)!;
        return new(input.Id, input.MeasuredOn, input.Values!, input.Notes, input.UpdateProfile, r.GetFieldValue<DateTimeOffset>(1), input.DatePrecision);
    }
    public async Task<List<MeasurementEntry>> All(CancellationToken ct)
    {
        await using var cmd = database.CreateCommand("""
            SELECT m.document,m.created_at FROM training_measurement_entries m
            JOIN training_profiles p ON p.id=m.profile_id WHERE p.owner_id=$1
            ORDER BY m.measured_on DESC,m.created_at DESC,m.id DESC
            """);
        cmd.Parameters.AddWithValue(account.Id);
        await using var reader = await cmd.ExecuteReaderAsync(ct);
        var result = new List<MeasurementEntry>();
        while (await reader.ReadAsync(ct)) result.Add(Read(reader));
        return result;
    }
    public async Task<MeasurementEntry> Add(MeasurementInput input, CancellationToken ct)
    {
        await using var connection = await database.OpenConnectionAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(ct);
        Guid profileId; int revision; ProfileData data;
        // The profile lock serializes retries and profile updates in the same transaction.
        await using (var cmd = new NpgsqlCommand("SELECT id,revision,document FROM training_profiles WHERE owner_id=$1 FOR UPDATE", connection, transaction))
        await using (var reader = await ReadOwned(cmd, ct))
        {
            if (!await reader.ReadAsync(ct)) throw new ApiError(409, "Crée ton profil avant d’ajouter des mensurations.");
            profileId = reader.GetGuid(0); revision = reader.GetInt32(1);
            data = JsonSerializer.Deserialize<ProfileData>(reader.GetString(2), Json)!;
        }
        await using (var existing = new NpgsqlCommand("SELECT document,created_at FROM training_measurement_entries WHERE id=$1 AND profile_id=$2", connection, transaction))
        {
            existing.Parameters.AddWithValue(input.Id); existing.Parameters.AddWithValue(profileId);
            await using var reader = await existing.ExecuteReaderAsync(ct);
            if (await reader.ReadAsync(ct))
            {
                var entry = Read(reader);
                if (entry.DatePrecision != input.DatePrecision || entry.MeasuredOn != input.MeasuredOn || entry.Notes != input.Notes || entry.UpdatedProfile != input.UpdateProfile ||
                    entry.Values.Count != input.Values!.Count || entry.Values.Any(v => !input.Values.TryGetValue(v.Key, out var x) || x != v.Value))
                    throw new ApiError(409, "Cette mesure a déjà été enregistrée avec un autre contenu.");
                return entry;
            }
        }
        if (input.UpdateProfile)
        {
            if (revision != input.ProfileRevision) throw new ApiError(409, "Le profil a changé. Recharge la page avant d’actualiser ton poids.");
            var updated = data with { WeightKg = input.Values!.GetValueOrDefault("weightKg", data.WeightKg), HeightCm = input.Values!.GetValueOrDefault("heightCm", data.HeightCm) };
            if (updated != data)
            {
                await using var cmd = new NpgsqlCommand("UPDATE training_profiles SET document=$1,revision=revision+1,updated_at=now() WHERE id=$2", connection, transaction);
                cmd.Parameters.AddWithValue(NpgsqlDbType.Jsonb, JsonSerializer.Serialize(updated, Json)); cmd.Parameters.AddWithValue(profileId);
                await cmd.ExecuteNonQueryAsync(ct);
                await using var history = new NpgsqlCommand("INSERT INTO training_body_measurements(id,profile_id,profile_revision,weight_kg,height_cm) VALUES($1,$2,$3,$4,$5)", connection, transaction);
                history.Parameters.AddWithValue(Guid.NewGuid()); history.Parameters.AddWithValue(profileId); history.Parameters.AddWithValue(revision + 1);
                history.Parameters.AddWithValue(updated.WeightKg); history.Parameters.AddWithValue(updated.HeightCm);
                await history.ExecuteNonQueryAsync(ct);
            }
        }
        MeasurementEntry result;
        await using (var cmd = new NpgsqlCommand("INSERT INTO training_measurement_entries(id,profile_id,measured_on,document) VALUES($1,$2,$3,$4) ON CONFLICT(id) DO NOTHING RETURNING document,created_at", connection, transaction))
        {
            cmd.Parameters.AddWithValue(input.Id); cmd.Parameters.AddWithValue(profileId); cmd.Parameters.AddWithValue(input.MeasuredOn);
            cmd.Parameters.AddWithValue(NpgsqlDbType.Jsonb, JsonSerializer.Serialize(input, Json));
            await using var reader = await cmd.ExecuteReaderAsync(ct); if(!await reader.ReadAsync(ct))throw new ApiError(409,"Cet identifiant de mesure est déjà utilisé."); result = Read(reader);
        }
        await transaction.CommitAsync(ct); return result;
    }
}
