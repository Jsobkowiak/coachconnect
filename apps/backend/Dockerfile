FROM node:24-bookworm-slim AS frontend
WORKDIR /web
COPY apps/frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY apps/frontend/ ./
RUN npm run build
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /source
COPY apps/backend/CoachConnect.Training.csproj ./
RUN dotnet restore
COPY apps/backend/ ./
RUN dotnet publish -c Release -o /out --no-restore
FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /out ./
COPY --from=frontend /web/dist ./wwwroot
RUN mkdir -p /app/security && chown $APP_UID:$APP_UID /app/security
USER $APP_UID
ENV ASPNETCORE_URLS=http://+:8081
EXPOSE 8081
ENTRYPOINT ["dotnet","CoachConnect.Training.dll"]
