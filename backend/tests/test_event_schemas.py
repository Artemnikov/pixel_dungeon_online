"""Schema completeness checks for app/schemas/events.py payload models."""
from app.schemas.events import RangedAttackData


def test_ranged_attack_data_declares_is_wand_field():
    """movement.py's perform_ranged_attack sends an `is_wand` flag on every
    RANGED_ATTACK event; the schema should declare it so the dev event
    validator and any generated frontend types reflect it."""
    assert "is_wand" in RangedAttackData.model_fields
