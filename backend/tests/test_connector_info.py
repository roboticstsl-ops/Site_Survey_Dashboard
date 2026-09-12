"""ConnectorInfo validation — positions must be a positive int, pitch_mm a
positive decimal, both optional (None is always fine, never inferred)."""
import pytest
from pydantic import ValidationError

from app.domain.models import ConnectorInfo, Integration


def test_all_fields_optional():
    c = ConnectorInfo()
    assert c.type is None
    assert c.positions is None
    assert c.pitch_mm is None
    assert c.gender is None


def test_valid_connector():
    c = ConnectorInfo(type="JST-XH", positions=4, pitch_mm=2.5, gender="female")
    assert c.positions == 4
    assert c.pitch_mm == 2.5


def test_positions_must_be_positive():
    with pytest.raises(ValidationError):
        ConnectorInfo(positions=0)
    with pytest.raises(ValidationError):
        ConnectorInfo(positions=-2)


def test_pitch_must_be_positive():
    with pytest.raises(ValidationError):
        ConnectorInfo(pitch_mm=0)
    with pytest.raises(ValidationError):
        ConnectorInfo(pitch_mm=-1.5)


def test_other_type_keeps_exact_note():
    c = ConnectorInfo(type="Other", compatible_part_note="Amphenol X-42, observed on site")
    assert c.type == "Other"
    assert c.compatible_part_note == "Amphenol X-42, observed on site"


def test_integration_keeps_free_text_connectors_independent_of_structured_field():
    i = Integration(connectors="4 pin connector female")
    assert i.connectors == "4 pin connector female"
    assert i.connector is None  # never auto-filled from the free-text field

    i2 = Integration(connectors="4 pin connector female", connector=ConnectorInfo(type="JST-XH"))
    assert i2.connectors == "4 pin connector female"  # unchanged
    assert i2.connector.type == "JST-XH"
