using CoachConnect.Training.Shared;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
namespace CoachConnect.Training.Features.Catalog;

public sealed class CatalogClient(HttpClient http)
{
    public async Task<JsonObject> Exercise(string id, CancellationToken ct) => JsonNode.Parse(await Fetch("/exercises/" + Uri.EscapeDataString(id), ct, true))!.AsObject();
    public Task<byte[]> Search(IQueryCollection query, CancellationToken ct)
    {
        var allowed = new[] { "q", "equipment", "muscle", "limit", "offset", "with_media", "catalog" };
        var args = string.Join("&", query.Where(p => allowed.Contains(p.Key)).Select(p => Uri.EscapeDataString(p.Key) + "=" + Uri.EscapeDataString(p.Value.ToString())));
        return Fetch("/exercises?" + args, ct);
    }
    public Task<byte[]> Coverage(CancellationToken ct) => Fetch("/media-coverage", ct);
    public Task<byte[]> Asset(string filename, CancellationToken ct)
    {
        if (!Regex.IsMatch(filename, @"\A[a-f0-9]{64}\.(png|jpg|webp|svg)\z")) throw new ApiError(404, "Visuel introuvable.");
        return Fetch("/media/assets/" + filename, ct);
    }
    async Task<byte[]> Fetch(string path, CancellationToken ct, bool exercise = false)
    {
        try
        {
            using var response = await http.GetAsync(path, HttpCompletionOption.ResponseHeadersRead, ct);
            if (response.StatusCode == System.Net.HttpStatusCode.NotFound) throw new ApiError(exercise ? 400 : 404, exercise ? "L’exercice choisi n’existe plus dans le catalogue." : "Visuel introuvable.");
            if ((int)response.StatusCode == 422) throw new ApiError(400, "Filtres de catalogue invalides.");
            if (!response.IsSuccessStatusCode) throw new ApiError(502, "Le catalogue est indisponible.");
            await response.Content.LoadIntoBufferAsync(2_000_000, ct);
            return await response.Content.ReadAsByteArrayAsync(ct);
        }
        catch (HttpRequestException) { throw new ApiError(502, "Le catalogue est indisponible. Réessaie dans quelques instants."); }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested) { throw new ApiError(502, "Le catalogue met trop de temps à répondre."); }
    }
}
