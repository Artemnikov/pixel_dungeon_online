import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.base import UnstableSpellbook, Action
from app.engine.entities.item_catalog import make_catalog_item
from app.engine.manager import GameInstance
import app.engine.entities.artifact_actions as aa


def _upgrade(book, times):
    for _ in range(times):
        book.level += 1
        book.on_upgrade()


def _game_with_book(level=0):
    g = GameInstance("t")
    p = g.add_player("p1", "Hero", "warrior")
    # Strip starter scrolls so infuse tests are deterministic.
    for it in list(p.belongings.all_items()):
        if getattr(it, "kind", "").startswith("scroll_of_"):
            p.belongings.backpack.detach_all(it.id)
    book = UnstableSpellbook(id="book1")
    _upgrade(book, level)
    p.belongings.backpack.items.append(book)
    return g, p, book


# --- READ ------------------------------------------------------------------

def test_book_read_spends_one_charge_and_applies_immediately_at_plus_zero():
    g, p, book = _game_with_book()
    book.charge = 2
    aa.action_book_read(g, p, book)
    # +0 index holds all rollable kinds -> never exotic -> immediate apply.
    assert book.charge == 1
    assert getattr(p, "_pending_book_item_id", None) is None


def test_book_read_offers_exotic_when_rolled_kind_not_in_index(monkeypatch):
    g, p, book = _game_with_book(level=5)   # index shrunk to 4 entries
    book.charge = 2
    # Force a roll of a kind guaranteed NOT in the shrunk index.
    missing = next(k for k in [
        "scroll_of_identify", "scroll_of_remove_curse", "scroll_of_mirror_image",
        "scroll_of_recharging", "scroll_of_teleportation", "scroll_of_lullaby",
        "scroll_of_magic_mapping", "scroll_of_rage", "scroll_of_retribution",
        "scroll_of_terror",
    ] if k not in book.scroll_index)
    monkeypatch.setattr(aa, "_roll_book_scroll_kind", lambda b: missing)
    aa.action_book_read(g, p, book)
    assert book.charge == 1                          # only the first charge
    assert getattr(p, "_pending_book_item_id") == book.id
    assert any(e["type"] == "BOOK_READ_CHOICE" for e in g.events)


def test_book_read_resolve_exotic_spends_second_charge(monkeypatch):
    g, p, book = _game_with_book(level=5)
    book.charge = 2
    missing = next(k for k in [
        "scroll_of_lullaby", "scroll_of_rage", "scroll_of_terror",
        "scroll_of_teleportation",
    ] if k not in book.scroll_index)
    monkeypatch.setattr(aa, "_roll_book_scroll_kind", lambda b: missing)
    aa.action_book_read(g, p, book)
    exo = aa._REG_TO_EXO[missing]
    aa.action_book_read_resolve(g, p, book, 1)       # 1 = exotic
    assert book.charge == 0                           # second charge spent
    assert getattr(p, "_pending_book_item_id", None) is None
    # The exotic scroll must actually apply (not fizzle): BOOK_CAST for the exotic.
    assert any(e["type"] == "BOOK_CAST" and e["data"]["scroll"] == exo
               for e in g.events)


def test_book_read_resolve_normal_keeps_second_charge(monkeypatch):
    g, p, book = _game_with_book(level=5)
    book.charge = 2
    missing = next(k for k in [
        "scroll_of_lullaby", "scroll_of_rage", "scroll_of_terror",
        "scroll_of_teleportation",
    ] if k not in book.scroll_index)
    monkeypatch.setattr(aa, "_roll_book_scroll_kind", lambda b: missing)
    aa.action_book_read(g, p, book)
    aa.action_book_read_resolve(g, p, book, 0)       # 0 = normal
    assert book.charge == 1                           # no second charge
    assert getattr(p, "_pending_book_item_id", None) is None


def test_pending_choice_auto_resolves_on_reread(monkeypatch):
    g, p, book = _game_with_book(level=5)
    book.charge = 3
    missing = next(k for k in [
        "scroll_of_lullaby", "scroll_of_rage", "scroll_of_terror",
        "scroll_of_teleportation",
    ] if k not in book.scroll_index)
    monkeypatch.setattr(aa, "_roll_book_scroll_kind", lambda b: missing)
    aa.action_book_read(g, p, book)                  # -> pending (charge 2)
    assert getattr(p, "_pending_book_item_id") == book.id
    aa.action_book_read(g, p, book)                  # forces prior to normal, rerolls
    # First read's pending cleared; a fresh read consumed another charge.
    assert book.charge == 1


def test_reg_to_exo_covers_all_rollable_kinds():
    rollable = {
        "scroll_of_identify", "scroll_of_remove_curse", "scroll_of_mirror_image",
        "scroll_of_recharging", "scroll_of_teleportation", "scroll_of_lullaby",
        "scroll_of_magic_mapping", "scroll_of_rage", "scroll_of_retribution",
        "scroll_of_terror",
    }
    assert rollable <= set(aa._REG_TO_EXO.keys())


# --- INFUSE ----------------------------------------------------------------

def test_book_infuse_levels_up_and_removes_kind():
    g, p, book = _game_with_book()
    target_kind = book.scroll_index[0]
    scroll = make_catalog_item(target_kind)
    scroll.id = "s1"
    scroll.level_known = True
    p.belongings.backpack.items.append(scroll)

    aa.action_book_infuse(g, p, book)

    assert book.level == 1
    assert target_kind not in book.scroll_index
    assert p.belongings.get_item("s1") is None       # scroll consumed


def test_book_infuse_rejects_unidentified_scroll():
    g, p, book = _game_with_book()
    target_kind = book.scroll_index[0]
    scroll = make_catalog_item(target_kind)
    scroll.id = "s1"
    scroll.level_known = False                        # unidentified
    p.belongings.backpack.items.append(scroll)

    aa.action_book_infuse(g, p, book)

    assert book.level == 0                            # unchanged
    assert p.belongings.get_item("s1") is not None


# --- charge cap ------------------------------------------------------------

def test_charge_cap_formula_and_starts_full():
    book = UnstableSpellbook()
    assert book.charge_cap == 2          # floor(0*0.6)+2
    assert book.charge == 2              # starts full
    _upgrade(book, 5)
    assert book.charge_cap == 5          # floor(5*0.6)+2 = 5
    _upgrade(book, 5)                    # -> level 10
    assert book.charge_cap == 8          # floor(10*0.6)+2 = 8


# --- scroll index ----------------------------------------------------------

def test_scroll_index_contents_at_plus_zero():
    book = UnstableSpellbook()
    idx = set(book.scroll_index)
    assert "scroll_of_transmutation" not in idx
    assert "scroll_of_upgrade" not in idx      # weight 0 -> never added
    assert len(book.scroll_index) == 10
    assert idx == {
        "scroll_of_identify", "scroll_of_remove_curse", "scroll_of_mirror_image",
        "scroll_of_recharging", "scroll_of_teleportation", "scroll_of_lullaby",
        "scroll_of_magic_mapping", "scroll_of_rage", "scroll_of_retribution",
        "scroll_of_terror",
    }


def test_scroll_index_shrinks_on_upgrade():
    book = UnstableSpellbook()
    assert len(book.scroll_index) == 10   # no shrink at construction
    _upgrade(book, 1)
    assert len(book.scroll_index) == 8    # level_cap-1-level = 10-1-1 = 8
    _upgrade(book, 4)                     # level 5
    assert len(book.scroll_index) == 4    # 10-1-5 = 4
    _upgrade(book, 4)                     # level 9
    assert len(book.scroll_index) == 0    # 10-1-9 = 0


def test_passive_recharge_accrues_and_clamps():
    from app.engine.game.artifacts import ArtifactsMixin, _SPELLBOOK_RECHARGE
    book = UnstableSpellbook()
    book.charge = 0
    ArtifactsMixin._tick_spellbook(None, None, book, _SPELLBOOK_RECHARGE + 0.01)
    assert book.charge == 1
    ArtifactsMixin._tick_spellbook(None, None, book, _SPELLBOOK_RECHARGE * 10)
    assert book.charge == book.charge_cap   # never exceeds cap


def test_scroll_index_shrinks_from_front():
    book = UnstableSpellbook()
    first_two = book.scroll_index[:2]
    _upgrade(book, 1)
    # 10 -> 8: the two front entries are the ones removed.
    assert first_two[0] not in book.scroll_index
    assert first_two[1] not in book.scroll_index
