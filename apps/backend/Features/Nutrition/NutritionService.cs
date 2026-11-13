using CoachConnect.Training.Features.Blocks;
using System.Text.Json.Nodes;
using CoachConnect.Training.Shared;
using CoachConnect.Training.Features.Profile;
namespace CoachConnect.Training.Features.Nutrition;
public sealed class NutritionService(CycleRepository cycles,ProfileService profiles,NutritionRepository repository,TimeProvider clock)
{
    const string Conditioning="https://pacompendium.com/conditioning-exercise/";
    public static readonly List<EnergyActivity> Activities = [
        new("strength","Musculation · effort modéré",3.5m,Conditioning),new("strength_vigorous","Musculation · effort soutenu",6m,Conditioning),
        new("circuit","Circuit / WOD / Hyrox · effort modéré",5m,Conditioning),new("circuit_vigorous","Circuit · effort soutenu, peu de repos",7.5m,Conditioning),
        new("run_easy","Course · environ 6,5 km/h",6.5m,"https://pacompendium.com/running/"),new("run","Course · environ 8 km/h",8.5m,"https://pacompendium.com/running/"),
        new("rowing","Rameur · effort modéré",5m,Conditioning),new("ski","SkiErg · effort lent à modéré",10.5m,Conditioning)];
    public static readonly List<DailyActivity> DailyActivities = [new("low","Journées surtout assises",1.4m),new("moderate","Marche et déplacements réguliers",1.6m),new("active","Travail souvent debout et mobile",1.8m),new("very_active","Travail physique soutenu",2m)];
    public async Task<NutritionReport> Get(Guid id,CancellationToken ct)
    {
        var cycle=await cycles.Get(id,ct);var profile=await RequireProfile(ct);var settings=await repository.Get(id,ct);
        return Calculate(id,cycle,profile,settings);
    }
    public async Task<NutritionReport> Save(Guid id,NutritionInput input,CancellationToken ct)
    {
        var cycle=await cycles.Get(id,ct);var profile=await RequireProfile(ct);
        if(input.Revision<0 || input.CycleRevision!=(int)cycle["revision"]!)throw new ApiError(409,"Le bloc a changé. Recharge les séances avant d’enregistrer les réglages.");
        if(!DailyActivities.Any(a=>a.Id==input.DailyActivity)||input.Sessions is null || input.Sessions.Count>1456)throw new ApiError(400,"Réglages d’activité invalides.");
        var ids=AllSessions(cycle).Select(s=>Guid.Parse(s["id"]!.ToString())).ToHashSet();var seen=new HashSet<Guid>();
        foreach(var s in input.Sessions)
            if(s is null || !ids.Contains(s.SessionId) || !seen.Add(s.SessionId) || s.DurationMinutes is <1 or >300 || !Activities.Any(a=>a.Id==s.Activity))
                throw new ApiError(400,"Vérifie le type d’effort et la durée des séances du bloc.");
        // Validate cumulative durations before persisting any settings.
        Calculate(id,cycle,profile,new(input.Revision,input));
        var saved=await repository.Save(id,input,ct);
        return Calculate(id,cycle,profile,saved);
    }
    async Task<ProfileState> RequireProfile(CancellationToken ct)
    {
        var p=await profiles.Get(ct);
        if(p.Profile is null)throw new ApiError(409,"Renseigne d’abord ton profil pour calculer les kcal du bloc.");
        if(p.Estimates is null)throw new ApiError(409,p.EstimateNote??"L’estimation calorique est indisponible pour ce profil.");
        return p;
    }
    static IEnumerable<JsonNode> AllSessions(JsonObject c)=>c["weeks"]!.AsArray().SelectMany(w=>w!["sessions"]!.AsArray()).Select(s=>s!);
    static string? Infer(JsonNode s)
    {
        var exercises=s["exercises"]!.AsArray();
        if(exercises.Count==0)return null;
        if(s["format"]!.ToString()!="traditional")return "circuit";
        return exercises.All(e=>e!["snapshot"]?["category"]?.ToString() is "strength" or "powerlifting" or "olympic_weightlifting")?"strength":null;
    }
    NutritionReport Calculate(Guid id,JsonObject cycle,ProfileState profile,NutritionSettings? saved)
    {
        var input=saved?.Data;var daily=DailyActivities.Single(a=>a.Id==(input?.DailyActivity??"low"));
        var weight=profile.Profile!.Data.WeightKg;var rest=profile.Estimates!.RestingKcal;
        var baseline=new Kcal(rest.Min*daily.Factor,rest.Max*daily.Factor);
        var availableIds=AllSessions(cycle).Select(s=>Guid.Parse(s["id"]!.ToString())).ToHashSet();
        var overrides=(input?.Sessions??[]).Where(s=>availableIds.Contains(s.SessionId)).ToList();
        var lookup=overrides.ToDictionary(s=>s.SessionId);
        DateOnly? start=DateOnly.TryParse(cycle["startDate"]?.ToString(),out var date)?date:null;
        var weeks=new List<EnergyWeek>();
        foreach(var w in cycle["weeks"]!.AsArray())
        {
            var number=(int)w!["number"]!;var days=new List<EnergyDay>();
            for(var day=0;day<7;day++)
            {
                var sessions=new List<PlannedEnergySession>();
                foreach(var s in w["sessions"]!.AsArray().Where(s=>(int)s!["day"]! == day))
                {
                    var sid=Guid.Parse(s!["id"]!.ToString());lookup.TryGetValue(sid,out var configured);
                    var activity=configured?.Activity??Infer(s);var minutes=configured?.DurationMinutes??(int)s["durationMinutes"]!;
                    var model=Activities.FirstOrDefault(a=>a.Id==activity);
                    sessions.Add(new(sid,s["title"]!.ToString(),number,day,s["format"]!.ToString(),minutes,activity,configured is null && activity is not null,s["exercises"]!.AsArray().Count==0,model is null?null:model.Met*weight*minutes/60m));
                }
                var complete=sessions.All(s=>s.GrossKcal is not null);var hours=sessions.Sum(s=>s.DurationMinutes)/60m;
                if(hours>16)throw new ApiError(400,"La durée cumulée des séances d’une journée dépasse 16 heures. Vérifie le bloc.");
                Kcal? maintenance=null,extra=null;
                if(complete)
                {
                    var gross=sessions.Sum(s=>s.GrossKcal??0);
                    // Replace the average non-training energy of these hours, rather than adding exercise twice.
                    var low=decimal.Max(baseline.Min,baseline.Min*(1-hours/24m)+gross);
                    var high=decimal.Max(baseline.Max,baseline.Max*(1-hours/24m)+gross);
                    maintenance=new(low,high);extra=new(decimal.Min(low-baseline.Min,high-baseline.Max),decimal.Max(low-baseline.Min,high-baseline.Max));
                }
                days.Add(new(day,start?.AddDays((number-1)*7+day),sessions.Count==0?"rest":complete?"training":"incomplete",sessions,maintenance,extra));
            }
            var all=days.All(d=>d.Maintenance is not null);
            var total=all?new Kcal(days.Sum(d=>d.Maintenance!.Min),days.Sum(d=>d.Maintenance!.Max)):null;
            weeks.Add(new(number,w["focus"]?.ToString(),(bool)w["deload"]!,all,days.Sum(d=>d.Sessions.Count(s=>s.GrossKcal is null)),days.Count(d=>d.Sessions.Count>0),days.Sum(d=>d.Sessions.Sum(s=>s.DurationMinutes)),total,total is null?null:new(total.Min/7,total.Max/7),days));
        }
        var blockComplete=weeks.All(w=>w.Complete);var block=blockComplete?new Kcal(weeks.Sum(w=>w.WeeklyMaintenance!.Min),weeks.Sum(w=>w.WeeklyMaintenance!.Max)):null;
        return new(id,cycle["name"]!.ToString(),(int)cycle["revision"]!,weeks.Count,profile.Profile.Revision,saved?.Revision??0,
            saved is null || saved.Data.CycleRevision!=(int)cycle["revision"]!,daily.Id,overrides,DailyActivities,Activities,baseline,blockComplete,weeks.Sum(w=>w.MissingSessions),block,block is null?null:new(block.Min/(weeks.Count*7),block.Max/(weeks.Count*7)),
            profile.EstimateNote,clock.GetUtcNow(),weeks);
    }
}
