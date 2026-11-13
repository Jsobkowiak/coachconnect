using CoachConnect.Training.Features.Accounts;
using System.Text.Json;
using Npgsql;
using NpgsqlTypes;
using CoachConnect.Training.Shared;
namespace CoachConnect.Training.Features.Nutrition;
public sealed class NutritionRepository(NpgsqlDataSource database, CurrentAccount account)
{
    static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    public async Task Initialize(CancellationToken ct)
    {
        await using var cmd = database.CreateCommand("""
          CREATE TABLE IF NOT EXISTS training_nutrition_settings (
            cycle_id uuid PRIMARY KEY,revision integer NOT NULL DEFAULT 1,document jsonb NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now());
          """);
        await cmd.ExecuteNonQueryAsync(ct);
    }
    public async Task<NutritionSettings?> Get(Guid cycleId, CancellationToken ct)
    {
        await using var cmd = database.CreateCommand("SELECT revision,document FROM training_nutrition_settings WHERE cycle_id=$1 AND owner_id=$2");
        cmd.Parameters.AddWithValue(cycleId); cmd.Parameters.AddWithValue(account.Id); await using var reader=await cmd.ExecuteReaderAsync(ct);
        return await reader.ReadAsync(ct) ? new(reader.GetInt32(0),JsonSerializer.Deserialize<NutritionInput>(reader.GetString(1),Json)!) : null;
    }
    public async Task<NutritionSettings> Save(Guid cycleId,NutritionInput input,CancellationToken ct)
    {
        await using var cmd=database.CreateCommand(input.Revision==0
          ? "INSERT INTO training_nutrition_settings(cycle_id,document,owner_id) VALUES ($1,$2,$3) ON CONFLICT(cycle_id) DO NOTHING"
          : "UPDATE training_nutrition_settings SET document=$2,revision=revision+1,updated_at=now() WHERE cycle_id=$1 AND revision=$3 AND owner_id=$4");
        cmd.Parameters.AddWithValue(cycleId);cmd.Parameters.AddWithValue(NpgsqlDbType.Jsonb,JsonSerializer.Serialize(input,Json));
        if(input.Revision>0)cmd.Parameters.AddWithValue(input.Revision);cmd.Parameters.AddWithValue(account.Id);
        if(await cmd.ExecuteNonQueryAsync(ct)!=1)throw new ApiError(409,"Les réglages caloriques ont changé. Recharge la page avant d’enregistrer.");
        return new(input.Revision+1,input);
    }
}
