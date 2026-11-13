using CoachConnect.Training.Features.Accounts;
using Npgsql;
using NpgsqlTypes;
using System.Text.Json;
using CoachConnect.Training.Shared;
namespace CoachConnect.Training.Features.Profile;

public sealed class ProfileRepository(NpgsqlDataSource database, CurrentAccount account)
{
    static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    public async Task Initialize(CancellationToken ct)
    {
        await using var cmd = database.CreateCommand("""
            CREATE TABLE IF NOT EXISTS training_profiles (
              id uuid PRIMARY KEY, scope varchar(64) NOT NULL UNIQUE, revision integer NOT NULL DEFAULT 1,
              document jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
            CREATE TABLE IF NOT EXISTS training_body_measurements (
              id uuid PRIMARY KEY, profile_id uuid NOT NULL REFERENCES training_profiles(id), profile_revision integer NOT NULL,
              weight_kg numeric(6,2) NOT NULL, height_cm numeric(5,2) NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now(),
              UNIQUE(profile_id,profile_revision));
            CREATE INDEX IF NOT EXISTS training_measurements_date_idx ON training_body_measurements(profile_id,recorded_at DESC);
            """);
        await cmd.ExecuteNonQueryAsync(ct);
    }
    async Task<NpgsqlDataReader> ReadOwned(NpgsqlCommand cmd,CancellationToken ct){cmd.Parameters.AddWithValue(account.Id);return await cmd.ExecuteReaderAsync(ct);}
    static StoredProfile Read(NpgsqlDataReader r) => new(r.GetGuid(0), r.GetInt32(1), JsonSerializer.Deserialize<ProfileData>(r.GetString(2), Json)!, r.GetFieldValue<DateTimeOffset>(3), r.GetFieldValue<DateTimeOffset>(4));
    public async Task<StoredProfile?> Get(CancellationToken ct)
    {
        await using var cmd = database.CreateCommand("SELECT id,revision,document,created_at,updated_at FROM training_profiles WHERE owner_id=$1");
        cmd.Parameters.AddWithValue(account.Id);
        await using var reader = await cmd.ExecuteReaderAsync(ct);
        return await reader.ReadAsync(ct) ? Read(reader) : null;
    }
    public async Task<StoredProfile> Save(int revision, ProfileData data, CancellationToken ct)
    {
        await using var connection = await database.OpenConnectionAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(ct);
        StoredProfile? old;
        await using (var read = new NpgsqlCommand("SELECT id,revision,document,created_at,updated_at FROM training_profiles WHERE owner_id=$1 FOR UPDATE", connection, transaction))
        await using (var reader = await ReadOwned(read, ct)) old = await reader.ReadAsync(ct) ? Read(reader) : null;
        if (old is not null && revision == 0 && old.Data == data) { await transaction.CommitAsync(ct); return old; }
        if ((old is null && revision != 0) || (old is not null && old.Revision != revision))
            throw new ApiError(409, "Ton profil a changé dans un autre onglet. Recharge la page avant d’enregistrer.");
        var id = old?.Id ?? Guid.NewGuid();
        await using (var cmd = new NpgsqlCommand(old is null
            ? "INSERT INTO training_profiles(id,scope,document,owner_id) VALUES ($1,$3,$2,$4) ON CONFLICT DO NOTHING"
            : "UPDATE training_profiles SET document=$2,revision=revision+1,updated_at=now() WHERE id=$1 AND owner_id=$3", connection, transaction))
        {
            cmd.Parameters.AddWithValue(id); cmd.Parameters.AddWithValue(NpgsqlDbType.Jsonb, JsonSerializer.Serialize(data, Json));
            if(old is null){cmd.Parameters.AddWithValue(account.Scope);cmd.Parameters.AddWithValue(account.Id);}else cmd.Parameters.AddWithValue(account.Id);
            if (await cmd.ExecuteNonQueryAsync(ct) != 1) throw new ApiError(409, "Un profil vient d’être créé. Recharge la page.");
        }
        if (old is null || old.Data.WeightKg != data.WeightKg || old.Data.HeightCm != data.HeightCm)
        {
            await using var measurement = new NpgsqlCommand("INSERT INTO training_body_measurements(id,profile_id,profile_revision,weight_kg,height_cm) VALUES ($1,$2,$3,$4,$5)", connection, transaction);
            measurement.Parameters.AddWithValue(Guid.NewGuid()); measurement.Parameters.AddWithValue(id); measurement.Parameters.AddWithValue(revision + 1);
            measurement.Parameters.AddWithValue(data.WeightKg); measurement.Parameters.AddWithValue(data.HeightCm);
            await measurement.ExecuteNonQueryAsync(ct);
        }
        StoredProfile result;
        await using (var read = new NpgsqlCommand("SELECT id,revision,document,created_at,updated_at FROM training_profiles WHERE id=$1 AND owner_id=$2", connection, transaction))
        {
            read.Parameters.AddWithValue(id); read.Parameters.AddWithValue(account.Id);
            await using var reader = await read.ExecuteReaderAsync(ct); await reader.ReadAsync(ct); result = Read(reader);
        }
        await transaction.CommitAsync(ct); return result;
    }
    public async Task<List<BodyMeasurement>> Measurements(CancellationToken ct)
    {
        await using var cmd = database.CreateCommand("SELECT m.id,m.profile_revision,m.weight_kg,m.height_cm,m.recorded_at FROM training_body_measurements m JOIN training_profiles p ON p.id=m.profile_id WHERE p.owner_id=$1 ORDER BY recorded_at DESC,id DESC LIMIT 100");
        cmd.Parameters.AddWithValue(account.Id);
        await using var reader = await cmd.ExecuteReaderAsync(ct); var result = new List<BodyMeasurement>();
        while (await reader.ReadAsync(ct)) result.Add(new(reader.GetGuid(0),reader.GetInt32(1),reader.GetDecimal(2),reader.GetDecimal(3),reader.GetFieldValue<DateTimeOffset>(4)));
        return result;
    }
}
