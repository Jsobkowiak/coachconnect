using System.Security.Claims;
using System.Security.Cryptography;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.DataProtection;
using Npgsql;
namespace CoachConnect.Training.Features.Accounts;
public sealed class TrainingTicketStore(NpgsqlDataSource database,IDataProtectionProvider protection) : ITicketStore
{
    readonly IDataProtector protector=protection.CreateProtector("CoachConnect.Training.ServerTickets.v1");
    public async Task<string> StoreAsync(AuthenticationTicket ticket)
    {
        var id=RandomNumberGenerator.GetHexString(32);
        await using var cleanup=database.CreateCommand("DELETE FROM training_auth_sessions WHERE expires_at<now()");await cleanup.ExecuteNonQueryAsync();
        await using var cmd=database.CreateCommand("INSERT INTO training_auth_sessions(id,owner_id,ticket,expires_at) VALUES($1,$2,$3,$4)");
        cmd.Parameters.AddWithValue(id);cmd.Parameters.AddWithValue(Guid.Parse(ticket.Principal.FindFirstValue(ClaimTypes.NameIdentifier)!));
        cmd.Parameters.AddWithValue(protector.Protect(TicketSerializer.Default.Serialize(ticket)));cmd.Parameters.AddWithValue(ticket.Properties.ExpiresUtc??DateTimeOffset.UtcNow.AddHours(12));
        await cmd.ExecuteNonQueryAsync();return id;
    }
    public async Task RenewAsync(string key,AuthenticationTicket ticket)
    {
        await using var cmd=database.CreateCommand("UPDATE training_auth_sessions SET ticket=$2,expires_at=$3 WHERE id=$1");
        cmd.Parameters.AddWithValue(key);cmd.Parameters.AddWithValue(protector.Protect(TicketSerializer.Default.Serialize(ticket)));cmd.Parameters.AddWithValue(ticket.Properties.ExpiresUtc??DateTimeOffset.UtcNow.AddHours(12));await cmd.ExecuteNonQueryAsync();
    }
    public async Task<AuthenticationTicket?> RetrieveAsync(string key)
    {
        await using var cmd=database.CreateCommand("SELECT ticket FROM training_auth_sessions WHERE id=$1 AND expires_at>now()");cmd.Parameters.AddWithValue(key);
        var value=await cmd.ExecuteScalarAsync();if(value is not byte[] bytes)return null;
        try{return TicketSerializer.Default.Deserialize(protector.Unprotect(bytes));}catch(CryptographicException){return null;}
    }
    public async Task RemoveAsync(string key)
    {await using var cmd=database.CreateCommand("DELETE FROM training_auth_sessions WHERE id=$1");cmd.Parameters.AddWithValue(key);await cmd.ExecuteNonQueryAsync();}
}
