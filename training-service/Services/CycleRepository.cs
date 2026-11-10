using CoachConnect.Training.Features.Accounts;
using Npgsql;
using NpgsqlTypes;
using System.Text.Json.Nodes;
namespace CoachConnect.Training.Services;

public sealed class CycleRepository(NpgsqlDataSource database, CurrentAccount account)
{
    public async Task Initialize(CancellationToken ct)
    {
        await using var cmd = database.CreateCommand("""
            CREATE TABLE IF NOT EXISTS training_cycles (
              id uuid PRIMARY KEY,name varchar(120) NOT NULL,status varchar(16) NOT NULL CHECK(status IN ('draft','active','archived')),
              revision integer NOT NULL DEFAULT 1,document jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now());
            CREATE INDEX IF NOT EXISTS training_cycles_updated_idx ON training_cycles(updated_at DESC);
            CREATE TABLE IF NOT EXISTS training_workouts (
              id uuid PRIMARY KEY, cycle_id uuid NOT NULL, week_number integer NOT NULL, session_id uuid NOT NULL,
              revision integer NOT NULL DEFAULT 1,document jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now());
            CREATE INDEX IF NOT EXISTS training_workouts_cycle_idx ON training_workouts(cycle_id,updated_at DESC);
            """);
        await cmd.ExecuteNonQueryAsync(ct);
    }
    static JsonObject Read(NpgsqlDataReader row)
    {
        var data = JsonNode.Parse(row.GetString(row.GetOrdinal("document")))!.AsObject();
        data["id"] = row.GetGuid(row.GetOrdinal("id")).ToString(); data["revision"] = row.GetInt32(row.GetOrdinal("revision"));
        data["createdAt"] = row.GetDateTime(row.GetOrdinal("created_at")).ToString("O"); data["updatedAt"] = row.GetDateTime(row.GetOrdinal("updated_at")).ToString("O");
        return data;
    }
    public async Task<List<JsonObject>> All(CancellationToken ct, bool workouts = false)
    {
        await using var cmd = database.CreateCommand(workouts ? "SELECT * FROM training_workouts WHERE owner_id=$1 ORDER BY updated_at DESC" : "SELECT * FROM training_cycles WHERE owner_id=$1 ORDER BY updated_at DESC");
        cmd.Parameters.AddWithValue(account.Id);
        await using var reader = await cmd.ExecuteReaderAsync(ct); var result = new List<JsonObject>();
        while (await reader.ReadAsync(ct)) result.Add(Read(reader)); return result;
    }
    public async Task<JsonObject> Get(Guid id, CancellationToken ct, bool workout = false)
    {
        await using var cmd = database.CreateCommand(workout ? "SELECT * FROM training_workouts WHERE id=$1 AND owner_id=$2" : "SELECT * FROM training_cycles WHERE id=$1 AND owner_id=$2"); cmd.Parameters.AddWithValue(id); cmd.Parameters.AddWithValue(account.Id);
        await using var reader = await cmd.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct)) throw new ApiError(404, workout ? "Séance réalisée introuvable." : "Cycle introuvable."); return Read(reader);
    }
    public async Task<JsonObject> Save(Guid? id, int revision, JsonObject data, CancellationToken ct)
    {
        var key = id ?? Guid.NewGuid();
        await using var cmd = database.CreateCommand(id is null
            ? "INSERT INTO training_cycles(id,name,status,document,owner_id) VALUES ($1,$2,$3,$4,$5)"
            : "UPDATE training_cycles SET name=$2,status=$3,document=$4,revision=revision+1,updated_at=now() WHERE id=$1 AND revision=$5 AND owner_id=$6");
        cmd.Parameters.AddWithValue(key); cmd.Parameters.AddWithValue(data["name"]!.ToString()); cmd.Parameters.AddWithValue(data["status"]!.ToString());
        cmd.Parameters.AddWithValue(NpgsqlDbType.Jsonb, data.ToJsonString()); if (id is not null) cmd.Parameters.AddWithValue(revision); cmd.Parameters.AddWithValue(account.Id);
        if (await cmd.ExecuteNonQueryAsync(ct) == 0) throw new ApiError(409, "Ce cycle a été modifié dans un autre onglet. Recharge-le avant d’enregistrer.");
        return await Get(key, ct);
    }
    public async Task Delete(Guid id, int revision, CancellationToken ct, bool workout = false)
    {
        await Get(id, ct, workout);
        await using var cmd = database.CreateCommand(workout ? "DELETE FROM training_workouts WHERE id=$1 AND revision=$2 AND owner_id=$3" : "DELETE FROM training_cycles WHERE id=$1 AND revision=$2 AND owner_id=$3");
        cmd.Parameters.AddWithValue(id); cmd.Parameters.AddWithValue(revision); cmd.Parameters.AddWithValue(account.Id);
        if (await cmd.ExecuteNonQueryAsync(ct) == 0) throw new ApiError(409, "La version a changé. Recharge avant de supprimer.");
    }
    public async Task<JsonObject> SaveWorkout(Guid id, int revision, JsonObject data, CancellationToken ct)
    {
        // New workouts use a client-generated UUID so a lost response can be retried without duplication.
        await using var cmd = database.CreateCommand("""
            INSERT INTO training_workouts(id,cycle_id,week_number,session_id,document,owner_id)
            SELECT $1,$2,$3,$4,$5,$7 WHERE $6=0 AND EXISTS(SELECT 1 FROM training_cycles WHERE id=$2 AND owner_id=$7)
            ON CONFLICT(id) DO NOTHING;
            """);
        cmd.Parameters.AddWithValue(id); cmd.Parameters.AddWithValue(Guid.Parse(data["cycleId"]!.ToString())); cmd.Parameters.AddWithValue((int)data["weekNumber"]!);
        cmd.Parameters.AddWithValue(Guid.Parse(data["sessionId"]!.ToString())); cmd.Parameters.AddWithValue(NpgsqlDbType.Jsonb, data.ToJsonString()); cmd.Parameters.AddWithValue(revision); cmd.Parameters.AddWithValue(account.Id);
        if (await cmd.ExecuteNonQueryAsync(ct) == 1) return await Get(id, ct, true);
        var previous = await Get(id, ct, true);
        if (revision == 0)
        {
            foreach (var k in new[] { "id", "revision", "createdAt", "updatedAt" }) previous.Remove(k);
            if (JsonNode.DeepEquals(previous, data)) return await Get(id, ct, true);
            throw new ApiError(409, "Cette séance existe déjà. Recharge-la avant de modifier ses performances.");
        }
        await using var update = database.CreateCommand("UPDATE training_workouts SET document=$3,revision=revision+1,updated_at=now() WHERE id=$1 AND revision=$2 AND owner_id=$4");
        update.Parameters.AddWithValue(id); update.Parameters.AddWithValue(revision); update.Parameters.AddWithValue(NpgsqlDbType.Jsonb, data.ToJsonString()); update.Parameters.AddWithValue(account.Id);
        if (await update.ExecuteNonQueryAsync(ct) == 0) throw new ApiError(409, "Cette séance a été modifiée ailleurs. Recharge avant d’enregistrer.");
        return await Get(id, ct, true);
    }
}
