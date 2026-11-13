using System.Security.Cryptography;
using System.Text;
using CoachConnect.Training.Shared;
using Npgsql;
namespace CoachConnect.Training.Features.Accounts;

public sealed class AccountRepository(NpgsqlDataSource database, IConfiguration config)
{
    public async Task Initialize(CancellationToken ct)
    {
        await using var cmd=database.CreateCommand("""
            ALTER TABLE training_cycles ADD COLUMN IF NOT EXISTS owner_id uuid REFERENCES training_identity."AspNetUsers"("Id");
            ALTER TABLE training_workouts ADD COLUMN IF NOT EXISTS owner_id uuid REFERENCES training_identity."AspNetUsers"("Id");
            ALTER TABLE training_profiles ADD COLUMN IF NOT EXISTS owner_id uuid REFERENCES training_identity."AspNetUsers"("Id");
            ALTER TABLE training_nutrition_settings ADD COLUMN IF NOT EXISTS owner_id uuid REFERENCES training_identity."AspNetUsers"("Id");
            CREATE INDEX IF NOT EXISTS training_cycles_owner_idx ON training_cycles(owner_id,updated_at DESC);
            CREATE INDEX IF NOT EXISTS training_workouts_owner_idx ON training_workouts(owner_id,updated_at DESC);
            CREATE UNIQUE INDEX IF NOT EXISTS training_profiles_owner_idx ON training_profiles(owner_id) WHERE owner_id IS NOT NULL;
            CREATE TABLE IF NOT EXISTS training_account_setup (
              id boolean PRIMARY KEY DEFAULT true CHECK(id), token_hash text NOT NULL,
              owner_id uuid REFERENCES training_identity."AspNetUsers"("Id"), claimed_at timestamptz);
            CREATE TABLE IF NOT EXISTS training_auth_sessions (
              id varchar(64) PRIMARY KEY,owner_id uuid NOT NULL REFERENCES training_identity."AspNetUsers"("Id"),
              ticket bytea NOT NULL,expires_at timestamptz NOT NULL);
            CREATE INDEX IF NOT EXISTS training_sessions_owner_idx ON training_auth_sessions(owner_id);
            """);
        await cmd.ExecuteNonQueryAsync(ct);
        var hash=config["TRAINING_BOOTSTRAP_TOKEN_HASH"];
        if (!string.IsNullOrWhiteSpace(hash))
        {
            if(hash.Length!=64||!hash.All(Uri.IsHexDigit))throw new InvalidOperationException("TRAINING_BOOTSTRAP_TOKEN_HASH doit être un SHA-256 hexadécimal.");
            await using var setup=database.CreateCommand("INSERT INTO training_account_setup(id,token_hash) VALUES(true,$1) ON CONFLICT(id) DO NOTHING");
            setup.Parameters.AddWithValue(hash.ToUpperInvariant());await setup.ExecuteNonQueryAsync(ct);
        }
    }
    public async Task<bool> LegacyAvailable(CancellationToken ct)
    {
        await using var cmd=database.CreateCommand("SELECT EXISTS(SELECT 1 FROM training_account_setup WHERE owner_id IS NULL) AND (EXISTS(SELECT 1 FROM training_profiles WHERE owner_id IS NULL) OR EXISTS(SELECT 1 FROM training_cycles WHERE owner_id IS NULL) OR EXISTS(SELECT 1 FROM training_workouts WHERE owner_id IS NULL))");
        return (bool)(await cmd.ExecuteScalarAsync(ct))!;
    }
    public async Task<bool> OwnsLegacy(Guid id,CancellationToken ct)
    {
        await using var cmd=database.CreateCommand("SELECT EXISTS(SELECT 1 FROM training_account_setup WHERE owner_id=$1)");cmd.Parameters.AddWithValue(id);
        return (bool)(await cmd.ExecuteScalarAsync(ct))!;
    }
    public async Task Claim(Guid id,string token,CancellationToken ct)
    {
        if(token.Length>256)throw new ApiError(400,"Code de récupération invalide.");
        await using var connection=await database.OpenConnectionAsync(ct);
        await using var tx=await connection.BeginTransactionAsync(ct);
        string? hash=null; Guid? owner=null;
        await using(var read=new NpgsqlCommand("SELECT token_hash,owner_id FROM training_account_setup WHERE id=true FOR UPDATE",connection,tx))
        await using(var reader=await read.ExecuteReaderAsync(ct))
        {
            if(await reader.ReadAsync(ct)){hash=reader.GetString(0);owner=reader.IsDBNull(1)?null:reader.GetGuid(1);}
        }
        var actual=Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(token)));
        if(hash is null||!CryptographicOperations.FixedTimeEquals(Encoding.ASCII.GetBytes(hash),Encoding.ASCII.GetBytes(actual)))
            throw new ApiError(403,"Le code local de récupération est invalide.");
        if(owner==id){await tx.CommitAsync(ct);return;}
        if(owner.HasValue)throw new ApiError(409,"Les données locales ont déjà été récupérées.");
        await using(var check=new NpgsqlCommand("SELECT EXISTS(SELECT 1 FROM training_profiles WHERE owner_id=$1)",connection,tx))
        {check.Parameters.AddWithValue(id);if((bool)(await check.ExecuteScalarAsync(ct))!)throw new ApiError(409,"Ce compte possède déjà un profil. La récupération nécessite un compte sans profil pour conserver les deux historiques.");}
        foreach(var table in new[]{"training_profiles","training_cycles","training_workouts","training_nutrition_settings"})
        {
            // The table names above are constants, never request input.
            await using var assign=new NpgsqlCommand($"UPDATE {table} SET owner_id=$1 WHERE owner_id IS NULL",connection,tx);
            assign.Parameters.AddWithValue(id);await assign.ExecuteNonQueryAsync(ct);
        }
        await using(var mark=new NpgsqlCommand("UPDATE training_account_setup SET owner_id=$1,claimed_at=now() WHERE id=true",connection,tx))
        {mark.Parameters.AddWithValue(id);await mark.ExecuteNonQueryAsync(ct);}
        await tx.CommitAsync(ct);
    }
    public async Task RevokeAll(Guid owner,CancellationToken ct)
    {
        await using var cmd=database.CreateCommand("DELETE FROM training_auth_sessions WHERE owner_id=$1");cmd.Parameters.AddWithValue(owner);await cmd.ExecuteNonQueryAsync(ct);
    }
}
