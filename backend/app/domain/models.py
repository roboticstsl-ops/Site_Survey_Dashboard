"""Pydantic schemas for the canonical survey model — BUILD_SPEC section 4.
Field names mirror the spec's Mongo document shapes exactly so API responses,
Mongo documents and this file stay in lock-step."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Actor(BaseModel):
    user_id: str
    name: str


class AuditFields(BaseModel):
    schema_version: int = 1
    created_at: datetime
    created_by: Actor
    updated_at: datetime
    updated_by: Actor
    revision: int = 1
    is_deleted: bool = False


# ---- users --------------------------------------------------------------

Role = Literal["admin", "manager", "engineer", "viewer"]


class User(BaseModel):
    email: str
    display_name: str
    role: Role
    password_hash: str
    is_active: bool = True
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ---- sites / elevators ---------------------------------------------------

class Site(AuditFields):
    site_code: str | None = None
    name: str
    client: str
    address: str
    maps_link: str | None = None
    status: Literal["active", "inactive"] = "active"
    search_text: str = ""


class Elevator(AuditFields):
    site_id: str
    elevator_id: str
    oem: str = ""
    model: str = ""
    maintenance_company: str = ""
    plug_points: str = ""
    status: Literal["active", "inactive"] = "active"
    search_text: str = ""


# ---- surveys --------------------------------------------------------------

class SurveyHeader(BaseModel):
    doc_ref: str = ""
    prepared_by: str = ""
    date: str = ""
    version: str = ""
    project: str = ""
    site_name_snapshot: str = ""
    client_snapshot: str = ""
    address_snapshot: str = ""
    maps_link_snapshot: str = ""


class SurveyElevator(BaseModel):
    oem: str = ""
    model: str = ""
    elev_id: str = ""
    maintenance_company: str = ""
    plug_points: str = ""


class Assessment(BaseModel):
    checklist: dict[str, Literal["Yes", "No", "N/A"]] = Field(default_factory=dict)
    note: str = ""


class RailingSide(BaseModel):
    dimensions_mm: dict[str, float] = Field(default_factory=dict)
    drawing: list[dict[str, Any]] = Field(default_factory=list)


class Railings(BaseModel):
    top: RailingSide = Field(default_factory=RailingSide)
    rear: RailingSide = Field(default_factory=RailingSide)
    left: RailingSide = Field(default_factory=RailingSide)
    right: RailingSide = Field(default_factory=RailingSide)
    note: str = ""


class RFSection(BaseModel):
    name: str
    # flat "<row>|<carrier>.<metric>" keys — preserved verbatim, see BUILD_SPEC 4.4
    cells: dict[str, float | str] = Field(default_factory=dict)


class CarrierAverages(BaseModel):
    averages: dict[str, float] = Field(default_factory=dict)
    verdict: Literal["Good", "Acceptable", "Poor", ""] = ""


class RFSummary(BaseModel):
    computed_at: datetime | None = None
    overall: CarrierAverages = Field(default_factory=CarrierAverages)
    by_carrier: dict[str, CarrierAverages] = Field(default_factory=dict)
    recommended_operator: str = ""


class RF(BaseModel):
    floor_count: int = 0
    active_carrier: Literal["du", "et"] = "du"
    sections: dict[str, RFSection] = Field(default_factory=dict)   # rf1/rf2/rf3
    summary: RFSummary = Field(default_factory=RFSummary)
    feasibility: dict[str, str] = Field(default_factory=lambda: {
        "value": "", "source": "computed", "override_note": "",
    })


class PinoutEntry(BaseModel):
    pin: int
    use: str = ""
    color: str = ""


ConnectorType = Literal[
    "JST-XH", "JST-PH", "JST-SM", "Molex Mini-Fit", "Molex KK", "Dupont",
    "Phoenix Contact", "Wago", "Other",
]
ConnectorGender = Literal["male", "female", "unknown"]


class ConnectorInfo(BaseModel):
    """Structured connector data, additive alongside Integration.connectors
    (free text) -- never inferred from other fields; every value here is
    either what the field engineer entered or None. `type` is a controlled
    list plus "Other"; when "Other" is chosen, compatible_part_note is where
    the exact observed value/part number goes (not re-derived elsewhere)."""
    type: ConnectorType | None = None
    positions: int | None = Field(default=None, gt=0, description="Pin/position count, e.g. 4")
    pitch_mm: float | None = Field(default=None, gt=0, description="Contact pitch in millimetres, e.g. 2.5")
    gender: ConnectorGender | None = None
    compatible_part_note: str | None = None


class Integration(BaseModel):
    button_module_sku: str = ""
    connectors: str = ""  # free text -- kept as-is for backward compatibility, never overwritten by `connector`
    connector: ConnectorInfo | None = None
    pinout: list[PinoutEntry] = Field(default_factory=list)


class PhotoRef(BaseModel):
    photo_id: str
    description: str = ""
    filename: str = ""
    captured_at: datetime | None = None
    sort_order: int = 0


class TelegramResult(BaseModel):
    attempted_at: datetime | None = None
    result: Literal["sent", "failed", "not_attempted"] = "not_attempted"
    message: str = ""


class ReportRef(BaseModel):
    report_id: str
    file_id: str
    template_version: str = ""
    format: Literal["docx"] = "docx"
    created_at: datetime
    created_by: Actor
    telegram: TelegramResult = Field(default_factory=TelegramResult)


class LegacyProvenance(BaseModel):
    source: str = "svs_draft_v3"
    imported_at: datetime
    original_draft_version: str = "v3"
    unmapped: dict[str, Any] = Field(default_factory=dict)


Status = Literal["draft", "submitted", "reviewed", "exported", "archived"]


class Survey(AuditFields):
    survey_number: str
    status: Status = "draft"
    site_id: str
    elevator_id: str
    header: SurveyHeader = Field(default_factory=SurveyHeader)
    elevator: SurveyElevator = Field(default_factory=SurveyElevator)
    assessment: Assessment = Field(default_factory=Assessment)
    railings: Railings = Field(default_factory=Railings)
    rf: RF = Field(default_factory=RF)
    integration: Integration = Field(default_factory=Integration)
    photos: list[PhotoRef] = Field(default_factory=list)
    reports: list[ReportRef] = Field(default_factory=list)
    legacy: LegacyProvenance | None = None


# ---- files / audit ---------------------------------------------------------

class ImageMeta(BaseModel):
    width: int | None = None
    height: int | None = None
    quality_profile: str = "test-low"


class FileMeta(BaseModel):
    owner_type: Literal["survey"] = "survey"
    owner_id: str
    kind: Literal["photo", "report_docx", "attachment"]
    storage_key: str
    original_filename: str
    content_type: str
    byte_size: int
    sha256: str
    image: ImageMeta | None = None
    created_at: datetime
    created_by: Actor
    is_deleted: bool = False


class AuditEvent(BaseModel):
    event_type: str
    entity_type: str
    entity_id: str
    revision: int
    actor: Actor
    at: datetime
    request_id: str
    summary: dict[str, Any] = Field(default_factory=dict)
