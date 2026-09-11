"""Imports one svs_draft_v3 JSON object (the phone app's whole draft, see
mobile/www/index.html collect()/restore()) into the canonical Survey shape.

BUILD_SPEC guardrail #3: every field needs an explicit rule; anything not
recognised is preserved under legacy.unmapped rather than dropped.

Deliberately NOT resolved here (the caller — the future import endpoint,
BUILD_SPEC 5.2 POST /surveys/{id}/import-legacy-draft — does this, since it
needs a live Mongo connection to look up/create Site and Elevator records):
  - survey_number   (server-assigned per business policy)
  - site_id / elevator_id   (resolved or created from site_name/client/elev_id)
  - photo file upload        (base64 bodies are returned separately for the
                               caller to push through the storage adapter —
                               BUILD_SPEC rule: never store image bytes in
                               the survey document)

Known discrepancy vs. BUILD_SPEC section 4.4's example ("0|du.rsrp" only):
the real app also stores "<row>|loc" cells (the row's location/floor label)
in the same rf1/rf2/rf3 objects. This mapper keeps that as-is inside `cells`
rather than inventing a separate field, since the spec's own rule is "retain
the confirmed flat-key form" and this *is* that form. Flagged here per
guardrail #2 rather than silently resolved either way.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

KNOWN_FIELD_KEYS = {
    "doc_ref", "prepared_by", "date", "version", "project", "site_name",
    "client", "address", "maps_link", "elev_oem", "elev_model", "elev_id",
    "elev_maint", "plug_points", "checklist_note", "networks",
    "survey_point", "feasibility", "btn_sku", "btn_connectors", "rail_note",
}
CHECKLIST_NORMALIZE = {"N-A": "N/A"}  # legacy typo seen in older drafts
RAILING_KEYS = ("top", "rear", "left", "right")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def map_legacy_draft(draft: dict) -> dict:
    fields = draft.get("fields", {}) or {}
    unmapped = {k: v for k, v in fields.items() if k not in KNOWN_FIELD_KEYS}

    checklist_in = draft.get("checklist", {}) or {}
    checklist = {
        k: CHECKLIST_NORMALIZE.get(v, v)
        for k, v in checklist_in.items()
        if CHECKLIST_NORMALIZE.get(v, v) in ("Yes", "No", "N/A")
    }
    checklist_dropped = {
        k: v for k, v in checklist_in.items()
        if CHECKLIST_NORMALIZE.get(v, v) not in ("Yes", "No", "N/A")
    }

    rails_in = draft.get("rails", {}) or {}
    railings = {}
    for side in RAILING_KEYS:
        s = rails_in.get(side, {}) or {}
        dims_in = s.get("dims", s) or {}  # old shape stored dims at top level
        railings[side] = {
            "dimensions_mm": {k: n for k, v in dims_in.items() if (n := _num(v)) is not None},
            "drawing": s.get("draw", []) or [],
        }
    railings["note"] = fields.get("rail_note", "")

    pinout = [
        {"pin": i + 1, "use": (p or {}).get("use", ""), "color": (p or {}).get("color", "")}
        for i, p in enumerate(draft.get("pinout", []) or [])
    ]

    rf_in = draft.get("rf", {}) or {}
    rf_sections = {
        rid: {"name": name, "cells": dict(rf_in.get(rid, {}) or {})}
        for rid, name in (
            ("rf1", "Charging area + lobby"),
            ("rf2", "On top of cabin"),
            ("rf3", "Inside cabin"),
        )
    }

    photos_in = draft.get("photos", []) or []
    photo_refs, pending_uploads = [], []
    for i, p in enumerate(photos_in):
        photo_id = f"legacy-{i}"
        photo_refs.append({
            "photo_id": photo_id, "description": (p or {}).get("desc", ""),
            "filename": (p or {}).get("filename", ""), "sort_order": i,
        })
        if (p or {}).get("img"):
            pending_uploads.append({"photo_id": photo_id, "data_uri": p["img"]})

    survey_partial = {
        "survey_number": "",       # caller assigns
        "status": "draft",
        "site_id": "",             # caller resolves
        "elevator_id": "",         # caller resolves
        "header": {
            "doc_ref": fields.get("doc_ref", ""), "prepared_by": fields.get("prepared_by", ""),
            "date": fields.get("date", ""), "version": fields.get("version", ""),
            "project": fields.get("project", ""), "site_name_snapshot": fields.get("site_name", ""),
            "client_snapshot": fields.get("client", ""), "address_snapshot": fields.get("address", ""),
            "maps_link_snapshot": fields.get("maps_link", ""),
        },
        "elevator": {
            "oem": fields.get("elev_oem", ""), "model": fields.get("elev_model", ""),
            "elev_id": fields.get("elev_id", ""), "maintenance_company": fields.get("elev_maint", ""),
            "plug_points": fields.get("plug_points", ""),
        },
        "assessment": {"checklist": checklist, "note": fields.get("checklist_note", "")},
        "railings": railings,
        "rf": {
            "floor_count": int(draft.get("floorCount") or 0),
            "active_carrier": draft.get("carrier", "du"),
            "sections": rf_sections,
            "summary": {"computed_at": None, "overall": {"averages": {}, "verdict": ""},
                        "by_carrier": {}, "recommended_operator": ""},
            # imported as-is; not "computed" (server hasn't recalculated yet) — see
            # POST /surveys/{id}/recalculate-rf, call it right after import.
            "feasibility": {"value": fields.get("feasibility", ""), "source": "imported", "override_note": ""},
        },
        "integration": {
            "button_module_sku": fields.get("btn_sku", ""), "connectors": fields.get("btn_connectors", ""),
            "pinout": pinout,
        },
        "photos": photo_refs,
        "reports": [],
        "legacy": {
            "source": "svs_draft_v3", "imported_at": _now(), "original_draft_version": "v3",
            "unmapped": {**unmapped, **({"checklist_dropped": checklist_dropped} if checklist_dropped else {})},
        },
    }
    return {"survey_partial": survey_partial, "photos_pending_upload": pending_uploads}
