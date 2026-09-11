import json
from pathlib import Path

from app.domain.legacy_mapper import map_legacy_draft

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "sample_draft_v3.json").read_text())


def test_header_and_snapshots_mapped():
    out = map_legacy_draft(FIXTURE)["survey_partial"]
    h = out["header"]
    assert h["doc_ref"] == "DR-001"
    assert h["site_name_snapshot"] == "Burj Tower"
    assert h["client_snapshot"] == "Emaar"


def test_unknown_field_preserved_not_dropped():
    out = map_legacy_draft(FIXTURE)["survey_partial"]
    assert out["legacy"]["unmapped"]["some_future_field"] == "should end up in legacy.unmapped"


def test_checklist_normalizes_legacy_na_and_drops_garbage():
    out = map_legacy_draft(FIXTURE)["survey_partial"]
    cl = out["assessment"]["checklist"]
    assert cl["3"] == "N/A"           # "N-A" normalized
    assert "12" not in cl             # garbage value dropped, not guessed
    assert out["legacy"]["unmapped"]["checklist_dropped"]["12"] == "garbage-value"


def test_railing_dims_are_numeric_and_blanks_skipped():
    out = map_legacy_draft(FIXTURE)["survey_partial"]
    top = out["railings"]["top"]
    assert top["dimensions_mm"]["A"] == 201.0
    assert "C" not in top["dimensions_mm"]     # blank string was not a measurement


def test_rf_cells_kept_verbatim_flat_key_form():
    out = map_legacy_draft(FIXTURE)["survey_partial"]
    cells = out["rf"]["sections"]["rf1"]["cells"]
    assert cells["0|du.rsrp"] == "-68"
    assert cells["0|et.rsrp"] == "-64"


def test_photos_split_into_refs_and_pending_uploads_no_base64_in_survey():
    result = map_legacy_draft(FIXTURE)
    refs = result["survey_partial"]["photos"]
    pending = result["photos_pending_upload"]
    assert refs[0]["description"] == "Wiring"
    assert "img" not in refs[0]                       # no base64 leaks into the survey doc
    assert pending[0]["data_uri"].startswith("data:image/jpeg;base64,")


def test_survey_number_and_ids_left_for_caller_to_resolve():
    out = map_legacy_draft(FIXTURE)["survey_partial"]
    assert out["survey_number"] == ""
    assert out["site_id"] == "" and out["elevator_id"] == ""
