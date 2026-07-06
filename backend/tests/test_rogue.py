"""Rogue class mechanics: starter gear, Cloak of Shadows stealth, Assassin
Preparation, Freerunner Momentum, and talent/subclass gating."""

from app.engine.manager import GameInstance
from app.engine.entities.base import Position
from app.engine.entities.player import Mob as MobEntity
from app.engine.entities.subclasses import Subclass, Talent, ArmorAbilityType
from app.engine.systems.combat import resolve_melee_attack
from app.engine.game.rogue import (
    prep_tier, prep_blink_range, prep_ko_threshold,
    CLOAK_DRAIN_INTERVAL, CLOAK_RECHARGE_INTERVAL, MOMENTUM_DECAY_INTERVAL,
)


def _level_up(game, player, level):
    player.level = level
    game.on_talent_level_up(player)


def _rogue(game, pid="rogue"):
    return game.add_player(pid, "Rogue", "rogue")


def _mob(hp=20, max_hp=20, **kw):
    return MobEntity(id="m", name="Rat", pos=Position(x=2, y=1),
                     hp=hp, max_hp=max_hp, attack=2, defense=0,
                     defense_skill=0, dr_min=0, dr_max=0, **kw)


# --- starter gear ----------------------------------------------------------
def test_rogue_starting_gear():
    g = GameInstance("t")
    p = _rogue(g)
    assert p.belongings.weapon.kind == "dagger"
    assert p.belongings.artifact.kind == "cloak_of_shadows"
    assert p.belongings.armor.name == "Cloth Armor"
    names = [i.name for i in p.belongings.backpack.items]
    assert "Throwing Knife" in names


def test_cloak_offers_stealth_action():
    g = GameInstance("t")
    p = _rogue(g)
    assert "STEALTH" in p.belongings.artifact.actions(p)


# --- cloak of shadows ------------------------------------------------------
def test_toggle_stealth_makes_invisible():
    g = GameInstance("t")
    p = _rogue(g)
    assert g.toggle_cloak_stealth(p.id) is True
    assert p.cloak_stealth_active and p.invisible > 0


def test_stealth_drains_charge_over_time():
    g = GameInstance("t")
    p = _rogue(g)
    p.belongings.artifact.charge = 3
    g.toggle_cloak_stealth(p.id)
    g._tick_cloak(p, CLOAK_DRAIN_INTERVAL + 0.01)
    assert p.belongings.artifact.charge == 2


def test_stealth_ends_when_charge_depleted():
    g = GameInstance("t")
    p = _rogue(g)
    p.belongings.artifact.charge = 1
    g.toggle_cloak_stealth(p.id)
    g._tick_cloak(p, CLOAK_DRAIN_INTERVAL + 0.01)
    assert not p.cloak_stealth_active
    assert p.invisible == 0


def test_cloak_recharges_when_not_stealthed():
    g = GameInstance("t")
    p = _rogue(g)
    cloak = p.belongings.artifact
    cloak.charge = 0
    cloak.charge_cap = 3
    g._tick_cloak(p, CLOAK_RECHARGE_INTERVAL + 0.01)
    assert cloak.charge == 1


def test_attacking_breaks_stealth():
    g = GameInstance("t")
    p = _rogue(g)
    p.pos = Position(x=1, y=1)
    p.attack_skill = 100
    g.toggle_cloak_stealth(p.id)
    mob = _mob()
    resolve_melee_attack(p, mob, {}, p.pos.x, p.pos.y)
    assert not p.cloak_stealth_active
    assert p.invisible == 0


# --- preparation tiers -----------------------------------------------------
def test_prep_tier_thresholds():
    assert prep_tier(0.0) == -1
    assert prep_tier(1.0) == 0
    assert prep_tier(3.0) == 1
    assert prep_tier(5.0) == 2
    assert prep_tier(9.0) == 3


def test_prep_blink_scales_with_reach():
    assert prep_blink_range(9.0, 0) == 4
    assert prep_blink_range(9.0, 3) == 10


def test_assassin_ko_executes_wounded_foe():
    g = GameInstance("t")
    p = _rogue(g)
    p.attack_skill = 100
    p.subclass_info.subclass = Subclass.ASSASSIN
    p.invisible = 1
    p.prep_seconds = 9.0  # tier 4 -> 50% KO threshold
    mob = _mob(hp=5, max_hp=20)  # 25% < 50%
    res = resolve_melee_attack(p, mob, {}, p.pos.x, p.pos.y)
    assert res.get("ko") is True
    assert not mob.is_alive


def test_assassin_no_ko_on_healthy_foe():
    g = GameInstance("t")
    p = _rogue(g)
    p.attack_skill = 100
    p.subclass_info.subclass = Subclass.ASSASSIN
    p.invisible = 1
    p.prep_seconds = 1.0  # tier 1 -> 3% threshold
    mob = _mob(hp=20, max_hp=20)
    res = resolve_melee_attack(p, mob, {}, p.pos.x, p.pos.y)
    assert not res.get("ko")


# --- sucker punch (T1) -----------------------------------------------------
def test_sucker_punch_adds_surprise_damage():
    g = GameInstance("t")
    p = _rogue(g)
    p.attack_skill = 100
    p.invisible = 1  # surprise
    p.talent_info.talents[Talent.SUCKER_PUNCH] = 2
    # No subclass -> no preparation; isolates the sucker punch bonus.
    mob = _mob(hp=99, max_hp=99)
    res = resolve_melee_attack(p, mob, {}, p.pos.x, p.pos.y)
    assert res["damage"] > 0


# --- momentum (Freerunner) -------------------------------------------------
def test_momentum_builds_on_move_and_decays():
    g = GameInstance("t")
    p = _rogue(g)
    p.subclass_info.subclass = Subclass.FREERUNNER
    g.gain_momentum(p)
    g.gain_momentum(p)
    assert p.momentum_stacks == 2
    g._tick_momentum(p, MOMENTUM_DECAY_INTERVAL + 0.01, moved=False)
    assert p.momentum_stacks == 1


def test_non_freerunner_gains_no_momentum():
    g = GameInstance("t")
    p = _rogue(g)
    g.gain_momentum(p)
    assert p.momentum_stacks == 0


# --- talent / subclass gating ---------------------------------------------
def test_rogue_can_choose_assassin_not_berserker():
    g = GameInstance("t")
    p = _rogue(g)
    p.level = 6
    assert g.choose_subclass(p.id, Subclass.BERSERKER) is False
    assert g.choose_subclass(p.id, Subclass.ASSASSIN) is True


def test_warrior_cannot_take_rogue_talent():
    g = GameInstance("t")
    w = g.add_player("w", "War", "warrior")
    w.level = 30
    assert g.upgrade_talent("w", Talent.SUCKER_PUNCH) is False


def test_rogue_can_take_rogue_talent():
    g = GameInstance("t")
    p = _rogue(g)
    p.level = 30
    assert g.upgrade_talent(p.id, Talent.SUCKER_PUNCH) is True


# --- armor abilities -------------------------------------------------------
def _passable_neighbor(floor, x, y):
    for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
        nx, ny = x + ddx, y + ddy
        if 0 <= nx < floor.width and 0 <= ny < floor.height and floor.flags.passable[ny][nx]:
            return nx, ny
    return None


def _place_player_on_floor(g, p):
    floor = g._get_or_create_floor(p.floor_id)
    for y in range(floor.height):
        for x in range(floor.width):
            if floor.flags.passable[y][x] and _passable_neighbor(floor, x, y):
                p.pos = Position(x=x, y=y)
                return floor
    raise AssertionError("no passable cell")


def test_smoke_bomb_blinks_and_costs_charge():
    g = GameInstance("t")
    p = _rogue(g)
    p.armor_charge = 100
    floor = _place_player_on_floor(g, p)
    tx, ty = _passable_neighbor(floor, p.pos.x, p.pos.y)
    g.use_armor_ability(p.id, "smoke_bomb", tx, ty)
    assert (p.pos.x, p.pos.y) == (tx, ty)
    assert p.armor_charge == 50


def test_death_mark_applies_buff_and_amp():
    g = GameInstance("t")
    p = _rogue(g)
    p.armor_charge = 100
    floor = _place_player_on_floor(g, p)
    mx, my = _passable_neighbor(floor, p.pos.x, p.pos.y)
    mob = _mob()
    mob.pos = Position(x=mx, y=my)
    floor.mobs[mob.id] = mob
    g.use_armor_ability(p.id, "death_mark", mx, my)
    assert mob.has_buff("death_mark")
    assert p.armor_charge == 75


def test_shadow_clone_spawns_ally():
    g = GameInstance("t")
    p = _rogue(g)
    p.armor_charge = 100
    _place_player_on_floor(g, p)
    floor = g._get_or_create_floor(p.floor_id)
    g.use_armor_ability(p.id, "shadow_clone")
    clones = [m for m in floor.mobs.values() if m.type == "shadow_clone"]
    assert len(clones) == 1
    assert clones[0].faction == "player"
    assert p.armor_charge == 65


def test_deathly_durability_barrier_on_marked_kill():
    g = GameInstance("t")
    p = _rogue(g)
    p.subclass_info.subclass = Subclass.ASSASSIN
    p.talent_info.talents[Talent.DEATHLY_DURABILITY] = 2
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(hp=1, max_hp=40)
    mob.add_buff("death_mark", duration=5.0)
    g.process_death_mark_kill(p, mob, floor, p.floor_id)
    assert p.get_shield("death_mark") is not None


# --- talent tier gating (T1-T4) --------------------------------------------
def test_rogue_tier3_locked_without_subclass():
    g = GameInstance("t")
    p = _rogue(g)
    _level_up(g, p, 13)
    assert g.talent_points_available(p, 3) == 0


def test_rogue_tier3_unlocked_with_subclass():
    g = GameInstance("t")
    p = _rogue(g)
    _level_up(g, p, 13)
    g.choose_subclass(p.id, Subclass.ASSASSIN)
    assert g.talent_points_available(p, 3) == 1


def test_rogue_tier4_locked_without_armor_ability():
    g = GameInstance("t")
    p = _rogue(g)
    _level_up(g, p, 21)
    g.choose_subclass(p.id, Subclass.ASSASSIN)
    assert g.talent_points_available(p, 4) == 0


def test_rogue_choose_armor_ability_all_three():
    for ability in (ArmorAbilityType.SMOKE_BOMB, ArmorAbilityType.DEATH_MARK, ArmorAbilityType.SHADOW_CLONE):
        g = GameInstance("t")
        p = _rogue(g)
        _level_up(g, p, 25)
        g.choose_subclass(p.id, Subclass.ASSASSIN)
        assert g.choose_armor_ability(p.id, ability) is True
        assert p.armor_ability == ability
        assert g.talent_points_available(p, 4) == 5


def test_rogue_t4_talent_gated_to_chosen_ability():
    g = GameInstance("t")
    p = _rogue(g)
    _level_up(g, p, 22)
    g.choose_subclass(p.id, Subclass.ASSASSIN)
    g.choose_armor_ability(p.id, ArmorAbilityType.SMOKE_BOMB)
    # Smoke Bomb talent: allowed.
    assert g.upgrade_talent(p.id, Talent.HASTY_RETREAT) is True
    # Death Mark talent: not allowed under Smoke Bomb.
    assert g.upgrade_talent(p.id, Talent.DOUBLE_MARK) is False
    # HEROIC_ENERGY: universal T4, allowed regardless of ability.
    assert g.upgrade_talent(p.id, Talent.HEROIC_ENERGY) is True


# --- Body Replacement (Ninja Log) -------------------------------------------
def test_body_replacement_spawns_ninja_log():
    g = GameInstance("t")
    p = _rogue(g)
    p.armor_charge = 100
    p.talent_info.talents[Talent.BODY_REPLACEMENT] = 2
    floor = _place_player_on_floor(g, p)
    origin = (p.pos.x, p.pos.y)
    tx, ty = _passable_neighbor(floor, p.pos.x, p.pos.y)
    g.use_armor_ability(p.id, "smoke_bomb", tx, ty)
    logs = [m for m in floor.mobs.values() if m.type == "ninja_log"]
    assert len(logs) == 1
    assert (logs[0].pos.x, logs[0].pos.y) == origin
    assert logs[0].max_hp == 40


# --- Inscribed Stealth -------------------------------------------------------
def test_inscribed_stealth_grants_invisibility_on_scroll_read():
    from app.engine.entities.item_actions import action_read
    from app.engine.entities.items_scrolls import Scroll

    g = GameInstance("t")
    p = _rogue(g)
    p.talent_info.talents[Talent.INSCRIBED_STEALTH] = 1
    scroll = Scroll(id="s1", name="Scroll of Identify")
    p.belongings.backpack.items.append(scroll)
    action_read(g, p, scroll)
    assert p.invisible > 0


# --- Wide Search --------------------------------------------------------------
def test_wide_search_widens_distance():
    g = GameInstance("t")
    p = _rogue(g)
    p.talent_info.talents[Talent.WIDE_SEARCH] = 1
    floor = g._get_or_create_floor(p.floor_id)
    p.pos = Position(x=5, y=5)
    g.search(p.id)
    events = [e for e in g.events if e.get("type") == "SEARCH"]
    assert events
    cells = events[-1]["data"]["cells"]
    # At +1, search is circular with radius 3 -> includes a cell at distance 3
    # along an axis, but not the (3,3) corner.
    assert [8, 5] in cells
    assert [8, 8] not in cells
