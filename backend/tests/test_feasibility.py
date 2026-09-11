from app.domain.feasibility import summarize_cells, verdict_of


def test_verdict_thresholds_match_phone_app():
    assert verdict_of(-85, 15) == "Good"
    assert verdict_of(-90, 12) == "Good"
    assert verdict_of(-100, 8) == "Acceptable"
    assert verdict_of(-105, 5) == "Acceptable"
    assert verdict_of(-110, 2) == "Poor"
    assert verdict_of(None, None) == ""


def test_verdict_defaults_sinr_when_missing():
    # missing SINR should not itself sink an otherwise-strong RSRP
    assert verdict_of(-85, None) == "Good"


def test_summarize_cells_averages_one_carrier_only():
    cells = {
        "0|du.rsrp": -80, "0|du.sinr": 15,
        "1|du.rsrp": -90, "1|du.sinr": 9,
        "0|et.rsrp": -70, "0|et.sinr": 20,   # must not leak into du averages
    }
    out = summarize_cells(cells, "du")
    assert out["averages"]["rsrp"] == -85.0
    assert out["averages"]["sinr"] == 12.0
    assert out["verdict"] == "Good"   # avg rsrp -85 >= -90 and sinr 12 >= 12
