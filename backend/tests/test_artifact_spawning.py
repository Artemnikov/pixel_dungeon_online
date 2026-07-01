import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.dungeon.spd_levelgen.generator import (
    RolledItem, SPDRandom, init_generator_state, _random_artifact, _ARTIFACT,
)
from app.engine.game.spd_adapter import _rolled_item_to_item
from app.engine.entities.base import (
    AlchemistsToolkit, CapeOfThorns, ChaliceOfBlood, CloakOfShadows, DriedRose,
    EtherealChains, HolyTome, HornOfPlenty, LloydsBeacon, MasterThievesArmband,
    SandalsOfNature, SkeletonKey, TalismanOfForesight, TimekeepersHourglass,
    UnstableSpellbook, Chest,
)


def _artifact_roll(item_index, cursed=False):
    return RolledItem(category="ARTIFACT", is_artifact=True,
                      is_upgradable=False, level=0, item_index=item_index,
                      cursed=cursed)


# --- adapter: index -> concrete class --------------------------------------

def test_artifact_index_maps_to_concrete_class():
    cases = {
        0: AlchemistsToolkit,
        1: ChaliceOfBlood,
        3: DriedRose,
        4: EtherealChains,
        6: HornOfPlenty,
        7: MasterThievesArmband,
        8: SandalsOfNature,
        9: SkeletonKey,
        10: TalismanOfForesight,
        11: TimekeepersHourglass,
        12: UnstableSpellbook,
    }
    for idx, cls in cases.items():
        item = _rolled_item_to_item(_artifact_roll(idx), 5, 5)
        assert isinstance(item, cls), f"index {idx} -> {type(item).__name__}, want {cls.__name__}"


def test_all_artifacts_are_serializable_in_item_union():
    # Every concrete artifact must be a member of the AnyItem discriminated
    # union, or it cannot be placed in a Chest / heap / backpack.
    artifacts = [
        AlchemistsToolkit(), CapeOfThorns(), ChaliceOfBlood(), CloakOfShadows(),
        DriedRose(), EtherealChains(), HolyTome(), HornOfPlenty(), LloydsBeacon(),
        MasterThievesArmband(), SandalsOfNature(), SkeletonKey(),
        TalismanOfForesight(), TimekeepersHourglass(), UnstableSpellbook(),
    ]
    for art in artifacts:
        chest = Chest(id="c", name="Chest", chest_type="CHEST", contents=[art])
        assert type(chest.contents[0]) is type(art), \
            f"{type(art).__name__} did not round-trip through the item union"


def test_artifact_cursed_flag_applied_to_instance():
    cursed = _rolled_item_to_item(_artifact_roll(1, cursed=True), 5, 5)
    assert cursed.cursed is True
    clean = _rolled_item_to_item(_artifact_roll(1, cursed=False), 5, 5)
    assert clean.cursed is False


# --- generator: captures the drawn index + cursed roll ---------------------

def _seeded_rng(seed):
    rng = SPDRandom()
    rng.push_generator(seed)
    return rng


def test_generator_captures_drawn_artifact_index():
    rng = _seeded_rng(1234)
    state = init_generator_state(rng)
    result = _random_artifact(state, rng)
    assert result is not None
    deck = state.decks["ARTIFACT"]
    decremented = [i for i in range(len(_ARTIFACT)) if deck.probs[i] < _ARTIFACT[i]]
    assert decremented == [result.item_index], \
        f"captured index {result.item_index} != decremented slot {decremented}"


def test_generator_artifact_cursed_is_deterministic_bool():
    def roll():
        rng = _seeded_rng(42)
        return _random_artifact(init_generator_state(rng), rng)
    r1, r2 = roll(), roll()
    assert isinstance(r1.cursed, bool)
    assert r1.cursed == r2.cursed
