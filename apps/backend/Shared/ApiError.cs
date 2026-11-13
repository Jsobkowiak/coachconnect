namespace CoachConnect.Training.Shared;

public sealed class ApiError(int status, string message) : Exception(message)
{
    public int Status { get; } = status;
}
