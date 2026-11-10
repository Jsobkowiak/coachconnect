using System.Text.Json;
using CoachConnect.Training.Features.Accounts;
using CoachConnect.Training.Services;
using Npgsql;
using NpgsqlTypes;
namespace CoachConnect.Training.Features.Nutrition;

public sealed class MacroTargetRepository(NpgsqlDataSource database, CurrentAccount account)
{
    static readonly JsonSerializerOptions Json=new(JsonSerializerDefaults.Web);
    public async Task Initialize(CancellationToken ct)
    {
        await using var cmd=database.CreateCommand("""
            CREATE TABLE IF NOT EXISTS training_macro_targets (
              owner_id uuid PRIMARY KEY REFERENCES training_identity."AspNetUsers"("Id"),
              revision integer NOT NULL, document jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now());
            """);
        await cmd.ExecuteNonQueryAsync(ct);
    }
    static MacroTarget Read(NpgsqlDataReader reader) => JsonSerializer.Deserialize<MacroTarget>(reader.GetString(0),Json)! with {Revision=reader.GetInt32(1),UpdatedAt=reader.GetFieldValue<DateTimeOffset>(2)};
    public async Task<MacroTarget?> Get(CancellationToken ct)
    {
        await using var cmd=database.CreateCommand("SELECT document,revision,updated_at FROM training_macro_targets WHERE owner_id=$1");
        cmd.Parameters.AddWithValue(account.Id);await using var reader=await cmd.ExecuteReaderAsync(ct);
        return await reader.ReadAsync(ct)?Read(reader):null;
    }
    public async Task<MacroTarget> Save(MacroTarget target,CancellationToken ct)
    {
        await using var cmd=database.CreateCommand(target.Revision==0
            ? "INSERT INTO training_macro_targets(owner_id,revision,document) VALUES($1,1,$2) ON CONFLICT(owner_id) DO NOTHING RETURNING document,revision,updated_at"
            : "UPDATE training_macro_targets SET document=$2,revision=revision+1,updated_at=now() WHERE owner_id=$1 AND revision=$3 RETURNING document,revision,updated_at");
        cmd.Parameters.AddWithValue(account.Id);cmd.Parameters.AddWithValue(NpgsqlDbType.Jsonb,JsonSerializer.Serialize(target,Json));
        if(target.Revision>0)cmd.Parameters.AddWithValue(target.Revision);
        await using var reader=await cmd.ExecuteReaderAsync(ct);
        if(!await reader.ReadAsync(ct))throw new ApiError(409,"Ton objectif a changé. Recharge la page avant d’enregistrer.");
        return Read(reader);
    }
}
