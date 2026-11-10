using System.Security.Claims;
using System.Text.Json;
using CoachConnect.Training.Features.Profile;
using CoachConnect.Training.Services;
using Microsoft.AspNetCore.Identity;
namespace CoachConnect.Training.Features.Accounts;

// Local administrative command only. It exposes no HTTP endpoint and never creates a session.
public static class ImportMeasurementsCommand
{
    public static async Task Run(IServiceProvider services,string email,CancellationToken ct)
    {
        var users=services.GetRequiredService<UserManager<TrainingUser>>();
        var user=await users.FindByEmailAsync(email)??throw new ApiError(404,"Compte destinataire introuvable.");
        var input=await Console.In.ReadToEndAsync(ct);
        if(input.Length>100_000)throw new ApiError(400,"Import trop volumineux.");
        var entries=JsonSerializer.Deserialize<List<MeasurementInput>>(input,new JsonSerializerOptions(JsonSerializerDefaults.Web))??throw new ApiError(400,"Liste de mesures invalide.");
        if(entries.Count is <1 or >100 || entries.Any(e=>e.UpdateProfile))throw new ApiError(400,"L’import ajoute de 1 à 100 relevés sans modifier le profil courant.");
        var accessor=services.GetRequiredService<IHttpContextAccessor>();
        accessor.HttpContext=new DefaultHttpContext{User=new ClaimsPrincipal(new ClaimsIdentity([new Claim(ClaimTypes.NameIdentifier,user.Id.ToString())],"LocalAdminImport"))};
        var profile=await services.GetRequiredService<ProfileRepository>().Get(ct);
        if(profile is null)throw new ApiError(409,"Le compte destinataire doit posséder un profil.");
        var measurements=services.GetRequiredService<MeasurementService>();
        foreach(var entry in entries)await measurements.Add(entry,ct,allowFutureReference:true);
        Console.WriteLine($"Import terminé : {entries.Count} relevé(s), profil et autres comptes inchangés.");
    }
}
