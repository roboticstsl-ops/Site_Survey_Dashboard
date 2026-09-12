"""Survey read endpoints for the dashboard: summary, list (search/filter/sort/
paginate), one survey, its reports, and an authenticated DOCX download.

Every filter here is a fixed, whitelisted query shape — never string-built
from client input (BUILD_SPEC section 5.2)."""
from __future__ import annotations

import mimetypes
from datetime import datetime
from typing import Any, Literal

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.storage.local import LocalFileStorage

router = APIRouter(prefix="/api/v1", tags=["surveys"])

Verdict = Literal["Good", "Acceptable", "Poor"]
SortField = Literal["date", "site", "verdict", "floors"]


def _json_safe(value: Any) -> Any:
    """Mongo docs carry ObjectId/datetime — make them JSON-serializable without
    a full Pydantic round-trip (the stored shape already matches models.py)."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey not found")


def _get_storage() -> LocalFileStorage:
    settings = get_settings()
    if settings.file_storage_backend != "local":
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Only local file storage is wired up in this phase")
    return LocalFileStorage(settings.file_storage_root)


# ---- dashboard summary -----------------------------------------------------

class DashboardSummary(BaseModel):
    total: int
    good: int
    acceptable: int
    poor: int


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(db: AsyncIOMotorDatabase = Depends(get_db)):
    match = {"is_deleted": {"$ne": True}}
    total = await db.surveys.count_documents(match)
    counts = {"Good": 0, "Acceptable": 0, "Poor": 0}
    cursor = db.surveys.aggregate([
        {"$match": match},
        {"$group": {"_id": "$rf.summary.overall.verdict", "n": {"$sum": 1}}},
    ])
    async for row in cursor:
        if row["_id"] in counts:
            counts[row["_id"]] = row["n"]
    return DashboardSummary(total=total, good=counts["Good"], acceptable=counts["Acceptable"], poor=counts["Poor"])


# ---- list -------------------------------------------------------------------

class SurveyListItem(BaseModel):
    id: str
    survey_number: str
    status: str
    date: str
    site: str
    client: str
    elevator_id: str
    oem: str
    model: str
    floors: int
    verdict: str
    connector_type: str | None = None


class SurveyListResponse(BaseModel):
    items: list[SurveyListItem]
    total: int
    page: int
    page_size: int


_SORT_MAP = {
    "date": "header.date",
    "site": "header.site_name_snapshot",
    "verdict": "rf.summary.overall.verdict",
    "floors": "rf.floor_count",
}


class SurveyFacets(BaseModel):
    models: list[str]
    connector_types: list[str]


@router.get("/surveys/facets", response_model=SurveyFacets)
async def survey_facets(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Distinct filter-dropdown values across ALL surveys, not just the current
    page -- so 'All Models'/'All Connector Types' stay correct under pagination."""
    match = {"is_deleted": {"$ne": True}}
    models = await db.surveys.distinct("elevator.model", match)
    connector_types = await db.surveys.distinct("integration.connector.type", match)
    return SurveyFacets(
        models=sorted(m for m in models if m),
        connector_types=sorted(c for c in connector_types if c),
    )


@router.get("/surveys", response_model=SurveyListResponse)
async def list_surveys(
    q: str | None = Query(None, description="Free-text search (site, client, survey number)"),
    verdict: Verdict | None = Query(None),
    model: str | None = Query(None, description="Exact elevator model match"),
    connector_type: str | None = Query(None, description="Exact match on integration.connector.type"),
    date_from: str | None = Query(None, description="header.date >= this (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="header.date <= this (YYYY-MM-DD)"),
    sort: SortField = Query("date"),
    order: Literal["asc", "desc"] = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    match: dict[str, Any] = {"is_deleted": {"$ne": True}}
    if verdict:
        match["rf.summary.overall.verdict"] = verdict
    if model:
        match["elevator.model"] = model
    if connector_type:
        match["integration.connector.type"] = connector_type
    if date_from or date_to:
        date_range: dict[str, str] = {}
        if date_from:
            date_range["$gte"] = date_from
        if date_to:
            date_range["$lte"] = date_to
        match["header.date"] = date_range
    if q:
        match["$text"] = {"$search": q}

    total = await db.surveys.count_documents(match)
    sort_key = _SORT_MAP[sort]
    sort_dir = 1 if order == "asc" else -1

    cursor = (
        db.surveys.find(match)
        .sort(sort_key, sort_dir)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    async for doc in cursor:
        header, elev, rf = doc.get("header", {}), doc.get("elevator", {}), doc.get("rf", {})
        integration = doc.get("integration", {}) or {}
        items.append(SurveyListItem(
            id=str(doc["_id"]),
            survey_number=doc.get("survey_number", ""),
            status=doc.get("status", "draft"),
            date=header.get("date", ""),
            site=header.get("site_name_snapshot", ""),
            client=header.get("client_snapshot", ""),
            elevator_id=doc.get("elevator_id", ""),
            oem=elev.get("oem", ""),
            model=elev.get("model", ""),
            floors=rf.get("floor_count", 0),
            verdict=rf.get("summary", {}).get("overall", {}).get("verdict", ""),
            connector_type=(integration.get("connector") or {}).get("type"),
        ))
    return SurveyListResponse(items=items, total=total, page=page, page_size=page_size)


# ---- one survey ---------------------------------------------------------------

@router.get("/surveys/{survey_id}")
async def get_survey(survey_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.surveys.find_one({"_id": _oid(survey_id), "is_deleted": {"$ne": True}})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey not found")
    doc["id"] = str(doc.pop("_id"))

    # Resolve each photo's byte URL from its files-collection sibling (spec:
    # PhotoRef only carries metadata, actual bytes are addressed by storage_key
    # on a files doc — matched here by filename, no schema change needed).
    photos = doc.get("photos", [])
    if photos:
        files_by_name = {}
        async for f in db.files.find({"owner_id": survey_id, "kind": "photo"}):
            files_by_name[f["original_filename"]] = f["storage_key"]
        for p in photos:
            key = files_by_name.get(p.get("filename"))
            p["url"] = f"/api/v1/files/by-key/{key}" if key else None

    return _json_safe(doc)


# ---- reports + download --------------------------------------------------------

@router.get("/surveys/{survey_id}/reports")
async def list_reports(survey_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.surveys.find_one(
        {"_id": _oid(survey_id), "is_deleted": {"$ne": True}}, {"reports": 1}
    )
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey not found")
    reports = doc.get("reports", [])

    file_ids = [ObjectId(r["file_id"]) for r in reports if ObjectId.is_valid(r.get("file_id", ""))]
    files_by_id = {}
    if file_ids:
        async for f in db.files.find({"_id": {"$in": file_ids}}):
            files_by_id[str(f["_id"])] = f

    out = []
    for r in reports:
        f = files_by_id.get(r.get("file_id"))
        out.append(_json_safe({
            **r,
            "original_filename": f.get("original_filename") if f else None,
            "byte_size": f.get("byte_size") if f else None,
        }))
    return {"items": out}


@router.get("/surveys/{survey_id}/reports/{report_id}/download")
async def download_report(
    survey_id: str,
    report_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user: dict = Depends(get_current_user),  # auth boundary — the one protected route in this phase
):
    doc = await db.surveys.find_one(
        {"_id": _oid(survey_id), "is_deleted": {"$ne": True}}, {"reports": 1}
    )
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey not found")
    report = next((r for r in doc.get("reports", []) if r.get("report_id") == report_id), None)
    if not report or not ObjectId.is_valid(report.get("file_id", "")):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")

    file_doc = await db.files.find_one({"_id": ObjectId(report["file_id"])})
    if not file_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report file not found")

    storage = _get_storage()
    try:
        handle = storage.open(file_doc["storage_key"])
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report file missing from storage")

    def _chunks(f, size: int = 64 * 1024):
        try:
            while chunk := f.read(size):
                yield chunk
        finally:
            f.close()

    filename = file_doc.get("original_filename") or f"{report_id}.docx"
    content_type = file_doc.get("content_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return StreamingResponse(
        _chunks(handle),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
