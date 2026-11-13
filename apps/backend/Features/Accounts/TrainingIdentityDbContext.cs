using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
namespace CoachConnect.Training.Features.Accounts;
public sealed class TrainingUser : IdentityUser<Guid> { }
public sealed class TrainingIdentityDbContext(DbContextOptions<TrainingIdentityDbContext> options)
    : IdentityDbContext<TrainingUser, IdentityRole<Guid>, Guid>(options)
{
    protected override void OnModelCreating(ModelBuilder builder)
    {
        base.OnModelCreating(builder);
        builder.HasDefaultSchema("training_identity");
        builder.Entity<TrainingUser>().HasIndex(u=>u.NormalizedEmail).IsUnique();
    }
}
public sealed class TrainingIdentityDesignFactory : IDesignTimeDbContextFactory<TrainingIdentityDbContext>
{
    public TrainingIdentityDbContext CreateDbContext(string[] args) => new(new DbContextOptionsBuilder<TrainingIdentityDbContext>()
        .UseNpgsql("Host=localhost;Database=coachconnect_training;Username=training", o=>o.MigrationsHistoryTable("__EFMigrationsHistory","training_identity")).Options);
}
