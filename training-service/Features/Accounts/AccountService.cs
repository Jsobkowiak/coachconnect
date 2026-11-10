using System.ComponentModel.DataAnnotations;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Authentication;
using CoachConnect.Training.Services;
namespace CoachConnect.Training.Features.Accounts;
public sealed record AccountCredentials(string? Email,string? Password,bool RememberMe=false,string? ClaimToken=null);
public sealed record PasswordChange(string? CurrentPassword,string? NewPassword);
public sealed record ClaimRequest(string? Token);
public sealed record AccountUser(Guid Id,string Email,bool OwnsLegacyData);
public sealed class AccountService(UserManager<TrainingUser> users,SignInManager<TrainingUser> signIn,AccountRepository repository,TimeProvider clock)
{
    static string Email(string? input)
    {
        var email=input?.Trim();if(string.IsNullOrEmpty(email)||email.Length>254||!new EmailAddressAttribute().IsValid(email))throw new ApiError(400,"Renseigne une adresse e-mail valide.");return email;
    }
    static void Password(string? value)
    {if(value is null||value.Length<12||value.Length>128)throw new ApiError(400,"Utilise un mot de passe de 12 à 128 caractères.");}
    public async Task<AccountUser?> Current(System.Security.Claims.ClaimsPrincipal principal,CancellationToken ct)
    {
        if(principal.Identity?.IsAuthenticated!=true)return null;
        var user=await users.GetUserAsync(principal);return user is null?null:await View(user,ct);
    }
    Task<AccountUser> View(TrainingUser user,CancellationToken ct)=>ViewAsync(user,ct);
    async Task<AccountUser> ViewAsync(TrainingUser user,CancellationToken ct)=>new(user.Id,user.Email!,await repository.OwnsLegacy(user.Id,ct));
    public async Task Register(AccountCredentials input,CancellationToken ct)
    {
        var email=Email(input.Email);Password(input.Password);
        // Data recovery is separate from registration: a failed recovery never leaves a half-created account.
        if(!string.IsNullOrEmpty(input.ClaimToken))throw new ApiError(400,"Crée le compte puis récupère tes données depuis l’écran prévu.");
        var user=new TrainingUser{Id=Guid.NewGuid(),UserName=email,Email=email};
        IdentityResult result;
        try{result=await users.CreateAsync(user,input.Password!);}
        catch(DbUpdateException e) when(e.InnerException is PostgresException {SqlState:"23505"})
        {throw new ApiError(400,"Impossible de créer ce compte. Vérifie l’adresse e-mail ou essaie de te connecter.");}
        if(!result.Succeeded)throw new ApiError(400,"Impossible de créer ce compte. Vérifie l’adresse e-mail et le mot de passe, ou essaie de te connecter.");
        await Enter(user,input.RememberMe);
    }
    public async Task Login(AccountCredentials input,CancellationToken ct)
    {
        var email=Email(input.Email);
        if(string.IsNullOrEmpty(input.Password)||input.Password.Length>128)throw new ApiError(401,"Adresse e-mail ou mot de passe incorrect.");
        var user=await users.FindByEmailAsync(email);
        if(user is null){_ = new PasswordHasher<TrainingUser>().HashPassword(new(),input.Password);throw new ApiError(401,"Adresse e-mail ou mot de passe incorrect.");}
        var result=await signIn.CheckPasswordSignInAsync(user,input.Password,true);
        if(!result.Succeeded)throw new ApiError(401,"Adresse e-mail ou mot de passe incorrect, ou connexion temporairement bloquée après plusieurs essais.");
        await Enter(user,input.RememberMe);
    }
    async Task Enter(TrainingUser user,bool remember)=>await signIn.SignInAsync(user,new AuthenticationProperties{IsPersistent=remember,ExpiresUtc=clock.GetUtcNow().Add(remember?TimeSpan.FromDays(14):TimeSpan.FromHours(12))});
    public Task Logout()=>signIn.SignOutAsync();
    public async Task ChangePassword(Guid userId,PasswordChange input,CancellationToken ct)
    {
        Password(input.NewPassword);
        if(string.IsNullOrEmpty(input.CurrentPassword)||input.CurrentPassword.Length>128)throw new ApiError(400,"Renseigne ton mot de passe actuel.");
        var user=await users.FindByIdAsync(userId.ToString())??throw new ApiError(401,"Reconnecte-toi.");
        var result=await users.ChangePasswordAsync(user,input.CurrentPassword,input.NewPassword!);
        if(!result.Succeeded)throw new ApiError(400,"Le mot de passe actuel est incorrect ou le nouveau mot de passe est invalide.");
        await repository.RevokeAll(userId,ct);await signIn.SignOutAsync();
    }
}
