import re
from importlib.resources import files
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse

from exercise_catalog.config import settings
from exercise_catalog.editorial import active_documents, editorial_view
from exercise_catalog.models import Equipment, ExerciseData, Muscle, normalized_name
from exercise_catalog.store import connect, initialize


@asynccontextmanager
async def lifespan(app: FastAPI):
    client, db = connect(settings())
    initialize(db)
    app.state.db = db
    try:
        yield
    finally:
        client.close()


app = FastAPI(title="CoachConnect · Catalogue d’exercices", lifespan=lifespan)


def public_document(document):
    return {"id": document["_id"], **{k: v for k, v in document.items() if k != "_id"}}


def exercise_view(document):
    return {
        "id": document["_id"],
        **document["source_data"],
        **document["overrides"],
        "source_key": document["source_key"],
        "provenance": document["provenance"],
        "media": media_view(document),
        "updated_at": document["updated_at"],
    }


@app.get("/health")
def health(request: Request):
    request.app.state.db.command("ping")
    return {"status": "ok"}


@app.get("/exercises")
def list_exercises(
    request: Request,
    q: Annotated[str | None, Query(max_length=100)] = None,
    equipment: Equipment | None = None,
    muscle: Muscle | None = None,
    with_media: bool | None = None,
    catalog: Literal["curated", "source"] | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
):
    db = request.app.state.db
    curated = active_documents(db) if catalog != "source" else None
    if curated is not None or catalog == "curated":
        views = [editorial_view(doc) for doc in (curated or [])]
        if q:
            search = normalized_name(q)
            views = [row for row in views if any(
                search in normalized_name(value) for value in [row["name"], *row["aliases"]]
            )]
        if equipment:
            views = [row for row in views if row["equipment"] == equipment.value]
        if muscle:
            views = [row for row in views if muscle.value in row["primary_muscles"]]
        if with_media is not None:
            views = [row for row in views if bool(row["media"]) == with_media]
        return {"items": views[offset:offset + limit], "total": len(views),
                "limit": limit, "offset": offset}
    filters = []
    if q:
        regex = {"$regex": re.escape(q), "$options": "i"}
        filters.append(
            {
                "$or": [
                    {"overrides.name": regex},
                    {"overrides.name": {"$exists": False}, "source_data.name": regex},
                    {"overrides.aliases": regex},
                    {"overrides.aliases": {"$exists": False}, "source_data.aliases": regex},
                ]
            }
        )
    for field, value in [("equipment", equipment), ("primary_muscles", muscle)]:
        if value is not None:
            filters.append(
                {
                    "$or": [
                        {f"overrides.{field}": value.value},
                        {
                            f"overrides.{field}": {"$exists": False},
                            f"source_data.{field}": value.value,
                        },
                    ]
                }
            )
    query = {"$and": filters} if filters else {}
    db = request.app.state.db
    if with_media is not None:
        if with_media:
            query = {"$and": [query, {"media.images.0": {"$exists": True}}]}
        views = [exercise_view(doc) for doc in db.exercises.find(query).sort("_id", 1)]
        views = [view for view in views if bool(view["media"]) == with_media]
        return {
            "items": views[offset : offset + limit],
            "total": len(views),
            "limit": limit,
            "offset": offset,
        }
    items = db.exercises.find(query).sort("_id", 1).skip(offset).limit(limit)
    return {
        "items": [exercise_view(doc) for doc in items],
        "total": db.exercises.count_documents(query),
        "limit": limit,
        "offset": offset,
    }


@app.get("/exercises/{exercise_id}")
def get_exercise(exercise_id: str, request: Request):
    curated = active_documents(request.app.state.db)
    if curated is not None:
        document = next((row for row in curated if row["exercise_id"] == exercise_id), None)
        if document:
            return editorial_view(document)
    document = request.app.state.db.exercises.find_one({"_id": exercise_id})
    if document is None:
        raise HTTPException(404, "Exercice introuvable")
    return exercise_view(document)


@app.get("/quality-issues")
def list_issues(
    request: Request,
    status: Literal["open", "resolved"] = "open",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    db = request.app.state.db
    query = {"status": status}
    documents = db.quality_issues.find(query).sort("_id", 1).skip(offset).limit(limit)
    return {
        "items": [public_document(doc) for doc in documents],
        "total": db.quality_issues.count_documents(query),
    }


@app.get("/import-runs")
def list_runs(request: Request, limit: Annotated[int, Query(ge=1, le=100)] = 25):
    documents = request.app.state.db.import_runs.find().sort("started_at", -1).limit(limit)
    return {"items": [public_document(doc) for doc in documents]}


@app.get("/quality-issues/{issue_id}")
def get_issue(issue_id: str, request: Request):
    from exercise_catalog.review import inspect_issue

    try:
        context = inspect_issue(request.app.state.db, issue_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
    return {
        "issue": public_document(context["issue"]),
        "raw": public_document(context["raw"]) if context["raw"] else None,
        "candidates": [exercise_view(doc) for doc in context["candidates"]],
    }


@app.get("/quality-reviews")
def list_reviews(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    db = request.app.state.db
    documents = db.quality_reviews.find().sort("created_at", -1).skip(offset).limit(limit)
    return {
        "items": [public_document(doc) for doc in documents],
        "total": db.quality_reviews.count_documents({}),
    }


def media_view(document):
    media = document.get("media")
    if not media:
        return None
    current = ExerciseData.model_validate(
        {**document["source_data"], **document.get("overrides", {})}
    )
    return media if media.get("target_hash") == current.content_hash() else None


@app.get("/media-coverage")
def media_coverage(request: Request, catalog: Literal["curated", "source"] | None = None):
    db = request.app.state.db
    curated = active_documents(db) if catalog != "source" else None
    if curated is not None or catalog == "curated":
        documents = curated or []
        sources = {}
        for doc in documents:
            if doc.get("media"):
                source = doc["media"]["source"]
                sources[source] = sources.get(source, 0) + 1
        illustrated = sum(bool(doc.get("media")) for doc in documents)
        return {"total": len(documents), "illustrated": illustrated,
                "missing": len(documents) - illustrated, "pending_exercises": 0,
                "sources": sources, "language": "fr"}
    documents = list(db.exercises.find())
    valid = {doc["_id"]: media_view(doc) for doc in documents}
    sources = {}
    for media in valid.values():
        if media:
            sources[media["source"]] = sources.get(media["source"], 0) + 1
    pending_exercises = set()
    hashes = {
        doc["_id"]: ExerciseData.model_validate(
            {**doc["source_data"], **doc.get("overrides", {})}
        ).content_hash()
        for doc in documents
    }
    for match in db.media_matches.find({"status": "pending"}):
        identifier = match["exercise_id"]
        if not valid.get(identifier) and hashes.get(identifier) == match["target_hash"]:
            pending_exercises.add(identifier)
    illustrated = sum(bool(media) for media in valid.values())
    return {
        "total": len(documents),
        "illustrated": illustrated,
        "missing": len(documents) - illustrated,
        "pending_exercises": len(pending_exercises),
        "sources": sources,
    }


@app.get("/media/assets/{filename}")
def get_media_asset(filename: str):
    if not re.fullmatch(r"[a-f0-9]{64}\.(png|jpg|webp|svg)", filename):
        raise HTTPException(404, "Visuel introuvable")
    bundled = files("exercise_catalog").joinpath("data/illustrations/" + filename)
    path = (files("exercise_catalog").joinpath("data/diagrams/" + filename)
            if filename.endswith(".svg") else bundled if bundled.is_file()
            else settings().media_directory / filename)
    if not path.is_file():
        raise HTTPException(404, "Visuel introuvable")
    return FileResponse(
        str(path),
        media_type={"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp", "svg": "image/svg+xml"}[
            filename.rsplit(".", 1)[-1]
        ],
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/media-matches")
def list_media_matches(
    request: Request,
    status: Literal["pending", "approved", "rejected"] = "pending",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    db = request.app.state.db
    query = {"status": status}
    documents = db.media_matches.find(query).sort("exercise_name", 1).skip(offset).limit(limit)
    return {
        "items": [public_document(doc) for doc in documents],
        "total": db.media_matches.count_documents(query),
    }
