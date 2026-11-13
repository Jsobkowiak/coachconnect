using System.Security.Claims;
using CoachConnect.Training.Shared;
namespace CoachConnect.Training.Features.Accounts;
public sealed class CurrentAccount(IHttpContextAccessor accessor)
{
    public Guid Id => Guid.TryParse(accessor.HttpContext?.User.FindFirstValue(ClaimTypes.NameIdentifier),out var id)
        ? id : throw new ApiError(401,"Connecte-toi pour accéder à tes données.");
    public string Scope => "u:"+Id.ToString("N");
}
