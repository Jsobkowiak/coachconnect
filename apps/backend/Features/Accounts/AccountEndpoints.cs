using Microsoft.AspNetCore.Antiforgery;
namespace CoachConnect.Training.Features.Accounts;
public sealed class AccountCsrfFilter(IAntiforgery antiforgery) : IEndpointFilter
{
    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext context,EndpointFilterDelegate next)
    {
        if(!HttpMethods.IsGet(context.HttpContext.Request.Method)&&!HttpMethods.IsHead(context.HttpContext.Request.Method))
        {
            try{await antiforgery.ValidateRequestAsync(context.HttpContext);}
            catch(AntiforgeryValidationException){throw new Shared.ApiError(403,"La session du formulaire a expiré. Recharge la page avant de réessayer.");}
        }
        return await next(context);
    }
}
public static class AccountEndpoints
{
    public static void MapAccounts(this RouteGroupBuilder api)
    {
        api.MapGet("/auth/session",async(HttpContext context,IAntiforgery csrf,AccountService service,AccountRepository repository,CancellationToken ct)=>
        {
            var user=await service.Current(context.User,ct);
            return Results.Ok(new{user,csrfToken=csrf.GetAndStoreTokens(context).RequestToken,legacyDataAvailable=await repository.LegacyAvailable(ct)});
        }).AllowAnonymous();
        api.MapPost("/auth/register",async(AccountCredentials input,AccountService service,CancellationToken ct)=>{await service.Register(input,ct);return Results.NoContent();}).AllowAnonymous().RequireRateLimiting("register");
        api.MapPost("/auth/login",async(AccountCredentials input,AccountService service,CancellationToken ct)=>{await service.Login(input,ct);return Results.NoContent();}).AllowAnonymous().RequireRateLimiting("login");
        api.MapPost("/auth/logout",async(AccountService service)=>{await service.Logout();return Results.NoContent();});
        api.MapPost("/auth/password",async(PasswordChange input,CurrentAccount user,AccountService service,CancellationToken ct)=>{await service.ChangePassword(user.Id,input,ct);return Results.NoContent();}).RequireRateLimiting("login");
        api.MapPost("/auth/claim",async(ClaimRequest input,CurrentAccount user,AccountRepository repository,CancellationToken ct)=>
        {if(string.IsNullOrWhiteSpace(input.Token))throw new Shared.ApiError(400,"Renseigne le code local de récupération.");await repository.Claim(user.Id,input.Token,ct);return Results.NoContent();}).RequireRateLimiting("register");
    }
}
