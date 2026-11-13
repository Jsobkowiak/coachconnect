using CoachConnect.Training.Features.Measurements;
using CoachConnect.Training.Features.Catalog;
using CoachConnect.Training.Features.Blocks;
using CoachConnect.Training.Features.Accounts;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.RateLimiting;
using System.Threading.RateLimiting;
using System.Text.Json;
using System.Text.Json.Nodes;
using CoachConnect.Training.Shared;
using CoachConnect.Training.Features.Workouts;
using CoachConnect.Training.Features.Profile;
using CoachConnect.Training.Features.Nutrition;
using CoachConnect.Training.Features.Stats;
using Npgsql;
if (args.Contains("--healthcheck"))
{
    try { using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(3) }; using var response = await client.GetAsync("http://localhost:8081/api/health"); Environment.Exit(response.IsSuccessStatusCode ? 0 : 1); }
    catch { Environment.Exit(1); }
    return;
}
var builder = WebApplication.CreateBuilder(args);
builder.WebHost.ConfigureKestrel(k => k.Limits.MaxRequestBodySize = 2_000_000);
var connection = new NpgsqlConnectionStringBuilder { Host = builder.Configuration["TRAINING_DB_HOST"] ?? "localhost", Port = int.Parse(builder.Configuration["TRAINING_DB_PORT"] ?? "55433"), Database = builder.Configuration["TRAINING_DB_NAME"] ?? "coachconnect_training", Username = "training", Password = builder.Configuration["TRAINING_DB_PASSWORD"] ?? throw new InvalidOperationException("TRAINING_DB_PASSWORD requis") };
builder.Services.AddSingleton(NpgsqlDataSource.Create(connection.ConnectionString));
builder.Services.AddHttpContextAccessor();builder.Services.AddScoped<CurrentAccount>();
builder.Services.AddDbContext<TrainingIdentityDbContext>(o=>o.UseNpgsql(connection.ConnectionString,n=>n.MigrationsHistoryTable("__EFMigrationsHistory","training_identity")));
builder.Services.AddIdentityCore<TrainingUser>(o=>{
    o.User.RequireUniqueEmail=true;o.Password.RequiredLength=12;o.Password.RequiredUniqueChars=4;
    o.Password.RequireDigit=false;o.Password.RequireLowercase=false;o.Password.RequireUppercase=false;o.Password.RequireNonAlphanumeric=false;
    o.Lockout.MaxFailedAccessAttempts=5;o.Lockout.DefaultLockoutTimeSpan=TimeSpan.FromMinutes(15);
}).AddRoles<IdentityRole<Guid>>().AddEntityFrameworkStores<TrainingIdentityDbContext>().AddSignInManager().AddDefaultTokenProviders();
builder.Services.AddAuthentication(IdentityConstants.ApplicationScheme).AddIdentityCookies();
builder.Services.AddAuthorization();
builder.Services.Configure<SecurityStampValidatorOptions>(o=>o.ValidationInterval=TimeSpan.Zero);
var secureCookies=builder.Configuration.GetValue("TRAINING_HTTPS",false);
builder.Services.ConfigureApplicationCookie(o=>{
    o.Cookie.Name="COACHCONNECT_TRAINING_SESSION";o.Cookie.HttpOnly=true;o.Cookie.SameSite=SameSiteMode.Lax;
    o.Cookie.SecurePolicy=secureCookies?CookieSecurePolicy.Always:CookieSecurePolicy.SameAsRequest;
    o.ExpireTimeSpan=TimeSpan.FromHours(12);o.SlidingExpiration=true;
    o.Events.OnRedirectToLogin=c=>{c.Response.StatusCode=401;return c.Response.WriteAsJsonAsync(new{message="Connecte-toi pour accéder à l’application."});};
    o.Events.OnRedirectToAccessDenied=c=>{c.Response.StatusCode=403;return c.Response.WriteAsJsonAsync(new{message="Accès refusé."});};
});
var keyDirectory=builder.Configuration["TRAINING_KEY_DIRECTORY"]??Path.Combine(builder.Environment.ContentRootPath,"..","..",".local","training-auth","keys");
Directory.CreateDirectory(keyDirectory);
builder.Services.AddDataProtection().SetApplicationName("CoachConnect.Training.Identity").PersistKeysToFileSystem(new DirectoryInfo(keyDirectory));
builder.Services.AddSingleton<TrainingTicketStore>();
builder.Services.AddOptions<CookieAuthenticationOptions>(IdentityConstants.ApplicationScheme).Configure<TrainingTicketStore>((o,store)=>o.SessionStore=store);
builder.Services.AddScoped<AccountRepository>();builder.Services.AddScoped<AccountService>();
builder.Services.AddAntiforgery(o=>{o.HeaderName="X-CSRF-TOKEN";o.Cookie.Name="COACHCONNECT_TRAINING_CSRF";o.Cookie.HttpOnly=true;o.Cookie.SameSite=SameSiteMode.Strict;o.Cookie.SecurePolicy=secureCookies?CookieSecurePolicy.Always:CookieSecurePolicy.SameAsRequest;});
builder.Services.AddRateLimiter(o=>{
    o.RejectionStatusCode=429;
    o.OnRejected=async(c,ct)=>await c.HttpContext.Response.WriteAsJsonAsync(new{message="Trop de tentatives. Attends quelques minutes avant de réessayer."},ct);
    o.AddPolicy("login",c=>RateLimitPartition.GetFixedWindowLimiter(c.Connection.RemoteIpAddress?.ToString()??"local",_=>new FixedWindowRateLimiterOptions{PermitLimit=Math.Clamp(builder.Configuration.GetValue("TRAINING_LOGIN_RATE_LIMIT",30),1,1000),Window=TimeSpan.FromMinutes(1),QueueLimit=0}));
    o.AddPolicy("register",c=>RateLimitPartition.GetFixedWindowLimiter(c.Connection.RemoteIpAddress?.ToString()??"local",_=>new FixedWindowRateLimiterOptions{PermitLimit=Math.Clamp(builder.Configuration.GetValue("TRAINING_REGISTRATION_RATE_LIMIT",12),1,1000),Window=TimeSpan.FromHours(1),QueueLimit=0}));
});

builder.Services.AddScoped<CycleRepository>(); builder.Services.AddScoped<CycleService>(); builder.Services.AddScoped<WorkoutService>();
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddScoped<MeasurementRepository>(); builder.Services.AddScoped<MeasurementService>();
builder.Services.AddScoped<ProfileRepository>(); builder.Services.AddScoped<ProfileService>();
builder.Services.AddScoped<StatsRepository>(); builder.Services.AddScoped<StatsService>();
builder.Services.AddScoped<MacroTargetRepository>(); builder.Services.AddScoped<MacroTargetService>();
builder.Services.AddScoped<NutritionRepository>(); builder.Services.AddScoped<NutritionService>();
builder.Services.AddHttpClient<CatalogClient>(http => { http.BaseAddress = new Uri(builder.Configuration["CATALOG_API_URL"] ?? "http://localhost:8001"); http.Timeout = TimeSpan.FromSeconds(8); });
var app = builder.Build();
app.Use(async (ctx, next) =>
{
    try { await next(ctx); }
    catch (Exception e) when (e is ApiError or JsonException or BadHttpRequestException)
    {
        if (ctx.Response.HasStarted) throw;
        var status = e is ApiError a ? a.Status : e is BadHttpRequestException b ? b.StatusCode : 400;
        var message = e is ApiError ? e.Message : "La requête contient des valeurs invalides.";
        ctx.Response.StatusCode = status;
        await ctx.Response.WriteAsJsonAsync(new { type = "about:blank", title = message, status, detail = message, message });
    }
});
app.UseDefaultFiles(); app.UseStaticFiles();
app.UseAuthentication();app.UseAuthorization();app.UseRateLimiter();
app.Use(async(context,next)=>{
    if(context.Request.Path.StartsWithSegments("/api")){
        context.Response.Headers.CacheControl="no-store";
        context.Response.Headers.XContentTypeOptions="nosniff";context.Response.Headers.XFrameOptions="DENY";
        var expected=context.Request.Headers["X-Training-User"].ToString();
        if(context.User.Identity?.IsAuthenticated==true&&!string.IsNullOrEmpty(expected)&&expected!=context.User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value)
            throw new ApiError(401,"Le compte actif a changé dans un autre onglet. Reconnecte-toi.");
    }
    await next(context);
});
app.MapGet("/api/health", () => new { status = "ok", runtime = "dotnet" });
var api = app.MapGroup("/api").RequireAuthorization().AddEndpointFilter<AccountCsrfFilter>();
api.MapAccounts();
api.MapGet("/stats", (int? months, int? minReps, int? maxReps, bool? includeReferenceMeasurements, StatsService s, CancellationToken ct) => s.Get(months ?? 3, minReps, maxReps, ct, includeReferenceMeasurements ?? false));
api.MapGet("/nutrition/target", async (MacroTargetService s, CancellationToken ct) => { var target=await s.Get(ct); return target is null ? (IResult)Results.Text("null","application/json") : Results.Json(target); });
api.MapPost("/nutrition/target/preview", (MacroTargetInput input, MacroTargetService s, CancellationToken ct) => s.Preview(input,ct));
api.MapPut("/nutrition/target", (MacroTargetInput input, MacroTargetService s, CancellationToken ct) => s.Save(input,ct));
api.MapGet("/cycles/{id}/nutrition", (string id, NutritionService s, CancellationToken ct) => s.Get(Id(id), ct));
api.MapPut("/cycles/{id}/nutrition", (string id, NutritionInput input, NutritionService s, CancellationToken ct) => s.Save(Id(id), input, ct));
api.MapGet("/profile", (ProfileService s, CancellationToken ct) => s.Get(ct));
api.MapPut("/profile", (ProfileRequest input, ProfileService s, CancellationToken ct) => s.Save(input, ct));
api.MapGet("/profile/body-measurements", (MeasurementService s, CancellationToken ct) => s.All(ct));
api.MapPost("/profile/body-measurements", (MeasurementInput input, MeasurementService s, CancellationToken ct) => s.Add(input, ct));
api.MapGet("/profile/measurements", (ProfileService s, CancellationToken ct) => s.Measurements(ct));
api.MapGet("/profile/estimates", async (ProfileService s, CancellationToken ct) => { var state = await s.Get(ct); return Results.Ok(new { state.Estimates, state.EstimateNote }); });
api.MapGet("/cycles", (CycleRepository r, CancellationToken ct) => r.All(ct));
api.MapGet("/cycles/{id}", (string id, CycleRepository r, CancellationToken ct) => r.Get(Id(id), ct));
api.MapPost("/cycles", async (JsonObject input, CycleService s, CancellationToken ct) => { var data = await s.Save(null, input, ct); return Results.Created("/api/cycles/" + data["id"], data); });
api.MapPut("/cycles/{id}", (string id, JsonObject input, CycleService s, CancellationToken ct) => s.Save(Id(id), input, ct));
api.MapDelete("/cycles/{id}", async (string id, int revision, CycleRepository r, CancellationToken ct) => { await r.Delete(Id(id), revision, ct); return Results.NoContent(); });
api.MapPost("/cycles/{id}/duplicate", async (string id, CycleService s, CancellationToken ct) => { var data = await s.Duplicate(Id(id), ct); return Results.Created("/api/cycles/" + data["id"], data); });
api.MapGet("/catalog/exercises", async (HttpRequest req, CatalogClient c, CancellationToken ct) => Results.Bytes(await c.Search(req.Query, ct), "application/json"));
api.MapGet("/catalog/exercises/{id}", (string id, CatalogClient c, CancellationToken ct) => c.Exercise(Id(id).ToString(), ct));
api.MapGet("/catalog/media-coverage", async (CatalogClient c, CancellationToken ct) => Results.Bytes(await c.Coverage(ct), "application/json"));
api.MapGet("/catalog/media/assets/{filename}", async (string filename, HttpResponse response, CatalogClient c, CancellationToken ct) =>
{
    var bytes = await c.Asset(filename, ct);
    response.Headers.CacheControl = "public, max-age=31536000, immutable"; response.Headers.XContentTypeOptions = "nosniff";
    response.Headers.ContentSecurityPolicy = "sandbox; default-src 'none'; style-src 'unsafe-inline'";
    return Results.Bytes(bytes, Path.GetExtension(filename) switch { ".svg" => "image/svg+xml", ".webp" => "image/webp", ".jpg" => "image/jpeg", _ => "image/png" });
});
api.MapGet("/workouts", (CycleRepository r, CancellationToken ct) => r.All(ct, true));
api.MapGet("/workouts/{id}", (string id, CycleRepository r, CancellationToken ct) => r.Get(Id(id), ct, true));
api.MapPut("/workouts/{id}", (string id, WorkoutRequest input, WorkoutService s, CancellationToken ct) => s.Save(Id(id), input, ct));
api.MapDelete("/workouts/{id}", async (string id, int revision, CycleRepository r, CancellationToken ct) => { await r.Delete(Id(id), revision, ct, true); return Results.NoContent(); });
app.MapFallbackToFile("index.html");
await using (var scope = app.Services.CreateAsyncScope()) await scope.ServiceProvider.GetRequiredService<CycleRepository>().Initialize(CancellationToken.None);
await using (var scope = app.Services.CreateAsyncScope()) await scope.ServiceProvider.GetRequiredService<ProfileRepository>().Initialize(CancellationToken.None);
await using (var scope = app.Services.CreateAsyncScope()) await scope.ServiceProvider.GetRequiredService<NutritionRepository>().Initialize(CancellationToken.None);
await using (var scope = app.Services.CreateAsyncScope()) await scope.ServiceProvider.GetRequiredService<MeasurementRepository>().Initialize(CancellationToken.None);
await using (var scope=app.Services.CreateAsyncScope()){
    await scope.ServiceProvider.GetRequiredService<TrainingIdentityDbContext>().Database.MigrateAsync();
    await scope.ServiceProvider.GetRequiredService<AccountRepository>().Initialize(CancellationToken.None);
}
await using (var scope=app.Services.CreateAsyncScope()) await scope.ServiceProvider.GetRequiredService<MacroTargetRepository>().Initialize(CancellationToken.None);
if(args.Contains("--set-nutrition-target")){
    var position=Array.IndexOf(args,"--set-nutrition-target");
    if(position+1>=args.Length)throw new ApiError(400,"Indique l’adresse e-mail du compte destinataire.");
    await using var scope=app.Services.CreateAsyncScope();
    await SetNutritionTargetCommand.Run(scope.ServiceProvider,args[position+1],CancellationToken.None);
    return;
}
if(args.Contains("--import-measurements")){
    var position=Array.IndexOf(args,"--import-measurements");
    if(position+1>=args.Length)throw new ApiError(400,"Indique l’adresse e-mail du compte destinataire.");
    await using var scope=app.Services.CreateAsyncScope();
    await ImportMeasurementsCommand.Run(scope.ServiceProvider,args[position+1],CancellationToken.None);
    return;
}
await app.RunAsync();
static Guid Id(string value) => Guid.TryParse(value, out var id) ? id : throw new ApiError(400, "Identifiant invalide.");
