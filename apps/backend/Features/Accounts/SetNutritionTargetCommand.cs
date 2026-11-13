using System.Security.Claims;
using System.Text.Json;
using CoachConnect.Training.Features.Nutrition;
using CoachConnect.Training.Shared;
using Microsoft.AspNetCore.Identity;
namespace CoachConnect.Training.Features.Accounts;

// Trusted local administration only, following the measurement import command.
public static class SetNutritionTargetCommand
{
    public static async Task Run(IServiceProvider services,string email,CancellationToken ct)
    {
        var user=await services.GetRequiredService<UserManager<TrainingUser>>().FindByEmailAsync(email)??throw new ApiError(404,"Compte destinataire introuvable.");
        var json=await Console.In.ReadToEndAsync(ct);
        if(json.Length>10000)throw new ApiError(400,"Objectif trop volumineux.");
        var input=JsonSerializer.Deserialize<MacroTargetInput>(json,new JsonSerializerOptions(JsonSerializerDefaults.Web))??throw new ApiError(400,"Objectif invalide.");
        services.GetRequiredService<IHttpContextAccessor>().HttpContext=new DefaultHttpContext{User=new ClaimsPrincipal(new ClaimsIdentity([new Claim(ClaimTypes.NameIdentifier,user.Id.ToString())],"LocalAdminImport"))};
        await services.GetRequiredService<MacroTargetService>().Save(input,ct);
        Console.WriteLine("Objectif nutrition enregistré sur le compte destinataire ; profil et mensurations conservés.");
    }
}
