import random
from typing import Dict, List, Optional

from app.engine.entities.player import Player
from app.engine.entities.buffs import add_buff, get_buff, remove_buff
from app.engine.entities.subclasses import (
    Subclass,
    Talent,
    TALENT_DEFS,
    TALENT_CLASS_REQ,
    ArmorAbilityType,
    ABILITY_TALENTS,
    T4_ABILITY_TALENTS,
    CLASS_SUBCLASSES,
    CLASS_ARMOR_ABILITIES,
    COMBO_MOVES,
)

# Tier unlock thresholds: tier N unlocks at TIER_THRESHOLDS[N] (SPD Hero.java).
TIER_THRESHOLDS: List[int] = [0, 2, 7, 13, 21, 31]


class TalentsMixin:

    MILESTONE_LEVELS: List[int] = [2, 7, 13, 21]

    def talent_points_available(self, player: Player, tier: int) -> int:
        lvl = player.level
        info = player.subclass_info
        if lvl < TIER_THRESHOLDS[tier] - 1:
            return 0
        if tier == 3 and info.subclass is None:
            return 0
        if tier == 4 and not player.armor_ability:
            return 0

        # Max earnable points per tier (SPD grants exactly 5 per tier).
        max_for_tier = min(TIER_THRESHOLDS[tier + 1] - TIER_THRESHOLDS[tier], 5)

        # SPD grants 1 point per level-up within the tier's range, capped
        # at max_for_tier once the next tier unlocks (Hero.talentPointsAvailable).
        if lvl >= TIER_THRESHOLDS[tier + 1]:
            earned = max_for_tier
        else:
            earned = 1 + lvl - TIER_THRESHOLDS[tier]

        bonus = info.bonus_talent_points.get(tier, 0)
        spent = sum(
            pts for tid, pts in info.talent_info.talents.items()
            if TALENT_DEFS.get(tid, (0, 0, None))[1] == tier
        )
        return earned - spent + bonus

    def _recompute_talent_points(self, player: Player) -> None:
        info = player.subclass_info
        info.talent_points = {t: self.talent_points_available(player, t) for t in (1, 2, 3, 4)}

    def on_talent_level_up(self, player: Player) -> None:
        self._recompute_talent_points(player)
        emitted = player.subclass_info.emitted_milestones

        tier_unlocked = None

        for mlvl in self.MILESTONE_LEVELS:
            if player.level < mlvl or mlvl in emitted:
                continue
            emitted.add(mlvl)

            if mlvl == 2:
                tier_unlocked = 1

            elif mlvl == 7:
                tier_unlocked = 2

            elif mlvl == 13:
                tier_unlocked = 3

            elif mlvl == 21:
                tier_unlocked = 4

        self.add_event("LEVEL_UP", {
            "player": player.id, "level": player.level,
            "tier_unlocked": tier_unlocked,
            "talent_points": dict(player.subclass_info.talent_points),
            "can_choose_armor_ability": False,
            "can_choose_subclass": False,
        }, floor_id=player.floor_id, source_player_id=player.id)

    def choose_subclass(self, player_id: str, subclass: str) -> bool:
        player = self.players.get(player_id)
        if not player:
            return False
        if player.subclass_info.subclass is not None:
            return False
        if subclass not in CLASS_SUBCLASSES.get(player.class_type, ()):
            return False
        player.subclass_info.subclass = subclass
        if subclass == Subclass.BERSERKER:
            add_buff(player.buffs, "berserk_ready", duration=0, level=1)
        elif subclass == Subclass.GLADIATOR:
            player.combo_count = 0
            player.combo_timer = 0.0
        self._recompute_talent_points(player)
        self.add_event("SUBCLASS_CHOSEN", {"player": player.id, "subclass": subclass}, floor_id=player.floor_id, source_player_id=player.id)
        return True

    def choose_armor_ability(self, player_id: str, ability: str) -> bool:
        player = self.players.get(player_id)
        if not player:
            return False
        if player.armor_ability:
            return False
        if ability not in CLASS_ARMOR_ABILITIES.get(player.class_type, ()):
            return False
        player.armor_ability = ability
        self._recompute_talent_points(player)
        self.add_event("ARMOR_ABILITY_CHOSEN", {"player": player.id, "ability": ability}, floor_id=player.floor_id, source_player_id=player.id)
        return True

    def upgrade_talent(self, player_id: str, talent_name: str) -> bool:
        player = self.players.get(player_id)
        if not player:
            return False
        info = player.subclass_info
        if info is None:
            return False
        tal = TALENT_DEFS.get(talent_name)
        if tal is None:
            return False
        max_pts, tier, subclass_req = tal

        # Class check (talents not in the map are class-agnostic)
        class_req = TALENT_CLASS_REQ.get(talent_name)
        if class_req is not None and player.class_type != class_req:
            return False

        # Subclass / tier-3 gate check
        if tier == 3 and info.subclass is None:
            return False
        if subclass_req is not None and info.subclass != subclass_req:
            return False

        # Tier-4 gate: requires a chosen armor ability, and (if listed)
        # the talent must belong to the chosen ability's tree.
        if tier == 4:
            if not player.armor_ability:
                return False
            req_ability = T4_ABILITY_TALENTS.get(talent_name)
            if req_ability is not None and player.armor_ability != req_ability:
                return False

        # Already maxed
        current = info.talent_info.get(talent_name)
        if current >= max_pts:
            return False

        # Available talent points check
        avail = self.talent_points_available(player, tier)
        if avail <= 0:
            return False

        info.talent_info.talents[talent_name] = current + 1

        # Armor ability selection (first point in any selector locks the choice)
        if talent_name in ABILITY_TALENTS:
            player.armor_ability = ABILITY_TALENTS[talent_name]

        self._recompute_talent_points(player)

        self.add_event("TALENT_UPGRADED", {"player": player.id, "talent": talent_name, "level": current + 1}, floor_id=player.floor_id, source_player_id=player.id)
        return True

    def trigger_berserk(self, player_id: str) -> bool:
        player = self.players.get(player_id)
        if not player:
            return False
        if player.subclass_info.subclass != Subclass.BERSERKER:
            return False
        if player.berserk_active:
            return False
        if player.berserk_cooldown > 0:
            return False

        player.berserk_active = True
        player.berserk_power = max(player.berserk_power, 0.2)
        player.berserk_trigger_power = player.berserk_power
        add_buff(player.buffs, "berserk", duration=10.0, level=1)
        remove_buff(player.buffs, "berserk_ready")
        player.add_shield("berserk", player.get_berserk_shield_amount(), priority=2, decay=40)
        self.add_event("BERSERK_ACTIVATED", {"player": player.id}, floor_id=player.floor_id, source_player_id=player.id)
        return True

    def end_berserk(self, player: Player) -> None:
        """Berserk ends when its shield is depleted (or the buff expires).
        Power resets to 0 (RECOVERING); the post-Berserk cooldown is reduced
        by Deathless Fury and, if rage was >100% (Endless Rage), scaled down
        further (each 1% over 100 trims ~1% off the cooldown)."""
        player.berserk_active = False
        player.berserk_power = 0.0
        df = player.subclass_info.talent_info.level(Talent.DEATHLESS_FURY)
        cooldown = 200 - 50 * df
        if player.berserk_trigger_power > 1.0:
            cooldown = round(cooldown * (2.0 - player.berserk_trigger_power))
        player.berserk_cooldown = max(0, cooldown)
        player.berserk_trigger_power = 0.0
        remove_buff(player.buffs, "berserk")
        existing = player.get_shield("berserk")
        if existing is not None:
            player.shields = [s for s in player.shields if s.name != "berserk"]

    def update_berserk(self, player: Player) -> None:
        if player.subclass_info.subclass != Subclass.BERSERKER:
            return
        if not player.berserk_active:
            return
        berserk_buff = get_buff(player.buffs, "berserk")
        if berserk_buff is None or player.get_shield("berserk") is None:
            self.end_berserk(player)

    def update_combo(self, player: Player, dt: float) -> None:
        if player.subclass_info.subclass != Subclass.GLADIATOR:
            return
        if player.combo_count <= 0:
            return
        player.combo_timer -= dt * player.get_hold_fast_decay_factor()
        if player.combo_timer <= 0:
            player.combo_count = 0
            player.combo_timer = 0.0
            player.clobber_used = False
            player.parry_used = False

    def use_combo_move(self, player_id: str, move: str, target_x: Optional[int] = None, target_y: Optional[int] = None) -> bool:
        player = self.players.get(player_id)
        if not player or not player.is_alive:
            return False
        if player.subclass_info.subclass != Subclass.GLADIATOR:
            return False
        move_def = COMBO_MOVES.get(move)
        if move_def is None or player.combo_count < move_def["count"]:
            return False

        from app.engine.entities.base import Faction
        from app.engine.systems.combat import resolve_melee_attack

        floor_id = player.floor_id
        floor = self._get_or_create_floor(floor_id)
        ti = player.subclass_info.talent_info
        enhanced = ti.level(Talent.ENHANCED_COMBO)
        count = player.combo_count

        target = None
        if target_x is not None and target_y is not None:
            target = next((
                m for m in floor.mobs.values()
                if m.is_alive and m.faction != Faction.PLAYER
                and m.pos.x == target_x and m.pos.y == target_y
            ), None)

        is_in_los = lambda a, b: self._is_in_los(a, b, floor_id=floor_id)

        if move == "clobber":
            if player.clobber_used or target is None:
                return False
            player.clobber_used = True
            knock = 3 if (enhanced > 0 and count >= 7) else 2
            dx = target.pos.x - player.pos.x
            dy = target.pos.y - player.pos.y
            for _ in range(knock):
                nx, ny = target.pos.x + (1 if dx > 0 else -1 if dx < 0 else 0), target.pos.y + (1 if dy > 0 else -1 if dy < 0 else 0)
                if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                    break
                if floor.flags and not floor.flags.passable[ny][nx]:
                    break
                if any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values()):
                    break
                target.pos.x, target.pos.y = nx, ny
            if enhanced > 0 and count >= 7:
                add_buff(target.buffs, "vertigo", duration=5.0, level=1)
            self.add_event("COMBO_MOVE_USED", {"player": player.id, "move": move, "target": target.id}, floor_id=floor_id, source_player_id=player.id)

        elif move == "slam":
            if target is None:
                return False
            if enhanced >= 3:
                self._combo_leap_to_target(player, target, floor)
            dr_roll = random.randint(player.get_dr_min(), player.get_dr_max())
            dmg_bonus = round(dr_roll * count / 5)
            self._combo_strike(player, target, floor, floor_id, move, dmg_bonus=dmg_bonus, is_in_los=is_in_los)

        elif move == "parry":
            if player.parry_used:
                return False
            player.parry_used = True
            player.combo_timer = max(player.combo_timer, 5.0)
            if target is not None:
                target.invisible = 0
                remove_buff(target.buffs, "invisibility")
                remove_buff(target.buffs, "shadows")
            add_buff(player.buffs, "riposte_tracker", duration=5.0, level=1)
            self.add_event("COMBO_MOVE_USED", {"player": player.id, "move": move}, floor_id=floor_id, source_player_id=player.id)

        elif move == "crush":
            if target is None:
                return False
            if enhanced >= 3:
                self._combo_leap_to_target(player, target, floor)
            self._combo_strike(player, target, floor, floor_id, move, dmg_multi=0.25 * count, is_in_los=is_in_los)
            for mob in list(floor.mobs.values()):
                if not mob.is_alive or mob.faction == Faction.PLAYER or mob.id == target.id:
                    continue
                if max(abs(mob.pos.x - target.pos.x), abs(mob.pos.y - target.pos.y)) > 3:
                    continue
                dmg_roll = random.randint(player.get_damage_min(), player.get_damage_max())
                dr_roll = random.randint(mob.get_dr_min(), mob.get_dr_max())
                dmg = round(dmg_roll * 0.25 * count) // 2 - dr_roll
                if getattr(mob, "vulnerable", 0) > 0:
                    dmg = int(dmg * 1.33)
                dmg = max(0, dmg)
                if dmg <= 0:
                    continue
                hp_before = mob.hp
                mob.take_damage(dmg)
                self.add_event("DAMAGE", {"target": mob.id, "amount": dmg}, floor_id=floor_id)
                if not mob.is_alive:
                    self.on_kill(player, mob, floor.mobs, floor_id)
                    self._apply_lethal_defense(player)
                    self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)
                    self.handle_mob_death(mob, floor, floor_id)
                elif hp_before > 0:
                    self.add_berserk_power(player, dmg)

        elif move == "fury":
            if target is None:
                return False
            if enhanced >= 3:
                self._combo_leap_to_target(player, target, floor)
            for _ in range(count):
                if not target.is_alive or not player.is_alive:
                    break
                self._combo_strike(player, target, floor, floor_id, move, dmg_multi=0.6, is_in_los=is_in_los)

        else:
            return False

        player.combo_count = 0
        player.combo_timer = 0.0
        return True

    def _combo_strike(self, player: Player, target, floor, floor_id: int, move: str,
                       dmg_multi: float = 1.0, dmg_bonus: int = 0, is_in_los=None) -> None:
        from app.engine.systems.combat import resolve_melee_attack

        result = resolve_melee_attack(
            player, target, floor.mobs, player.pos.x, player.pos.y,
            is_in_los=is_in_los, dmg_multi=dmg_multi, dmg_bonus=dmg_bonus, guaranteed_hit=True,
            add_event=lambda t, d: self.add_event(t, d, floor_id=floor_id, source_player_id=player.id),
            floor=floor, game=self,
        )
        dmg = result["damage"]
        self.add_event("ATTACK", {
            "source": player.id, "target": target.id, "damage": dmg,
            "surprise": result["surprise"], "crit": result.get("crit", False),
            "grim_proc": result.get("grim_proc", False),
        }, floor_id=floor_id)
        self.add_event("COMBO_MOVE_USED", {"player": player.id, "move": move, "target": target.id}, floor_id=floor_id, source_player_id=player.id)
        if dmg > 0:
            self.add_event("DAMAGE", {"target": target.id, "amount": dmg, "grim_proc": result.get("grim_proc", False)}, floor_id=floor_id)
            self.add_berserk_power(player, dmg)
        if not target.is_alive:
            self.on_kill(player, target, floor.mobs, floor_id)
            self._apply_lethal_defense(player)
            self.add_event("DEATH", {"target": target.id}, floor_id=floor_id)
            self.handle_mob_death(target, floor, floor_id)

    def _combo_leap_to_target(self, player: Player, target, floor) -> None:
        """Enhanced Combo +3 (warrior T3 gladiator): Slam/Crush/Fury can leap
        the player up to combo_count // 3 tiles toward a target that's out of
        melee range, mirroring Heroic Leap's tile-validity checks."""
        dist = max(abs(target.pos.x - player.pos.x), abs(target.pos.y - player.pos.y))
        if dist <= 1:
            return
        max_tiles = player.combo_count // 3
        if max_tiles <= 0:
            return
        dx = target.pos.x - player.pos.x
        dy = target.pos.y - player.pos.y
        step_x = (dx > 0) - (dx < 0)
        step_y = (dy > 0) - (dy < 0)
        x, y = player.pos.x, player.pos.y
        for _ in range(min(max_tiles, dist - 1)):
            nx, ny = x + step_x, y + step_y
            if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                break
            if not floor.flags or not floor.flags.passable[ny][nx] or floor.flags.solid[ny][nx]:
                break
            if any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values()):
                break
            x, y = nx, ny
        player.pos.x, player.pos.y = x, y

    def _riposte_counter(self, player: Player, attacker, floor, floor_id: int) -> None:
        """Parry's counter-attack (warrior combo move, T3 Enhanced Combo +2):
        while riposte_tracker is active, an incoming attack is met with a free
        counter-strike. At Enhanced Combo +2 (combo was >=9 when Parry was
        used), riposte_tracker isn't consumed and can counter multiple
        attacks until its duration runs out."""
        if not attacker.is_alive or not player.is_alive:
            return
        is_in_los = lambda a, b: self._is_in_los(a, b, floor_id=floor_id)
        self._combo_strike(player, attacker, floor, floor_id, "parry", is_in_los=is_in_los)
        enhanced = player.subclass_info.talent_info.level(Talent.ENHANCED_COMBO)
        if enhanced < 2:
            remove_buff(player.buffs, "riposte_tracker")

    def _apply_lethal_defense(self, player: Player) -> None:
        """Lethal Defense (warrior T3 gladiator): a combo-move kill reduces
        the Broken Seal's cooldown by 50/100/150 turns, down to -150 (instant
        re-trigger)."""
        if player.subclass_info.subclass != Subclass.GLADIATOR:
            return
        ld = player.subclass_info.talent_info.level(Talent.LETHAL_DEFENSE)
        if ld <= 0:
            return
        player.seal_cooldown = max(-150, player.seal_cooldown - 50 * ld)

    def add_berserk_power(self, player: Player, damage: int) -> None:
        if player.subclass_info.subclass != Subclass.BERSERKER:
            return
        # Recovery period (after Berserk ends): no rage gain until it expires.
        if player.berserk_cooldown > 0:
            return
        endless_level = player.subclass_info.talent_info.level(Talent.ENDLESS_RAGE)
        max_power = 1.0 + 0.1667 * endless_level
        power_gain = damage / max(player.get_total_max_hp() * 4, 1)
        player.berserk_power = min(max_power, player.berserk_power + power_gain)

    # ------------------------------------------------------------------
    # Metamorphosis (Scroll of Metamorphosis)
    # ------------------------------------------------------------------

    def _eligible_replacements(self, player, old_talent: str) -> list:
        """Return list of talent IDs that can replace `old_talent` via metamorphosis."""
        def_ = TALENT_DEFS.get(old_talent)
        if not def_:
            return []
        _, tier, _ = def_
        owned = set(player.subclass_info.talent_info.talents.keys())
        meta_replaced = set(player.subclass_info.metamorphed_talents.values())
        player_class = player.class_type

        def _belongs_to_class(tid):
            c = TALENT_CLASS_REQ.get(tid)
            return c is not None and c == player_class

        eligible = []
        for tid, (mpts, tt, sreq) in TALENT_DEFS.items():
            if tt != tier:
                continue
            if _belongs_to_class(tid):
                continue
            if tid in owned:
                continue
            if tid in meta_replaced:
                continue
            if sreq is not None and player.subclass_info.subclass != sreq:
                continue
            eligible.append(tid)
        return eligible

    def metamorph_choose(self, player_id: str, old_talent: str) -> bool:
        """Player selected a talent to replace via metamorphosis."""
        player = self.players.get(player_id)
        if not player:
            return False
        owned = player.subclass_info.talent_info.level(old_talent)
        if owned <= 0:
            return False  # player doesn't have this talent
        options = self._eligible_replacements(player, old_talent)
        if not options:
            return False
        self.add_event("METAMORPH_OPTIONS", {
            "player": player.id, "old_talent": old_talent, "options": options,
        }, floor_id=player.floor_id, source_player_id=player.id)
        return True

    def metamorph_replace(self, player_id: str, old_talent: str, new_talent: str) -> bool:
        """Swap old_talent for new_talent via metamorphosis."""
        player = self.players.get(player_id)
        if not player:
            return False
        info = player.subclass_info
        old_lvl = info.talent_info.level(old_talent)
        if old_lvl <= 0:
            return False
        if new_talent not in self._eligible_replacements(player, old_talent):
            return False
        new_def = TALENT_DEFS.get(new_talent)
        if not new_def:
            return False
        max_new = new_def[0]
        # Transfer points, capped at new talent's max
        transfer = min(old_lvl, max_new)
        # Remove old talent
        del info.talent_info.talents[old_talent]
        # Add new talent at transferred level
        info.talent_info.talents[new_talent] = transfer
        # Record metamorphosis
        info.metamorphed_talents[old_talent] = new_talent
        # If the old talent was an armor ability selector, clear the armor ability
        if old_talent in ABILITY_TALENTS and player.armor_ability == ABILITY_TALENTS.get(old_talent):
            player.armor_ability = None
        self._recompute_talent_points(player)
        self.add_event("TALENT_METAMORPHED", {
            "player": player.id, "old_talent": old_talent, "new_talent": new_talent,
        }, floor_id=player.floor_id, source_player_id=player.id)
        return True

    # ------------------------------------------------------------------
    # Talent effect callbacks — called from item_actions, combat, tick
    # ------------------------------------------------------------------

    _CURE_DEBUFFS = (
        "poison", "blindness", "bleeding", "weakness",
        "slow", "cripple", "burning", "chill", "frost",
    )

    def _apply_food_effects(self, player: Player, food_item) -> None:
        """Apply food-specific on-eat effects (SPD Food.satisfy overrides).

        Called from on_food_eaten after hunger satisfaction, before talent
        callbacks.  Each food kind maps to its intrinsic effect; foods with
        no special effect are no-ops.
        """
        kind = getattr(food_item, "kind", "")

        if kind == "mystery_meat":
            roll = random.randint(0, 4)
            if roll == 0:
                add_buff(player.buffs, "burning", duration=10.0)
            elif roll == 1:
                add_buff(player.buffs, "roots", duration=10.0, stack_mode="extend")
            elif roll == 2:
                poison_dmg = max(1, player.get_total_max_hp() // 5)
                add_buff(player.buffs, "poison", duration=float(poison_dmg), level=1)
            elif roll == 3:
                add_buff(player.buffs, "slow", duration=10.0)

        elif kind == "frozen_carpaccio":
            roll = random.randint(0, 4)
            if roll == 0:
                add_buff(player.buffs, "invisibility", duration=20.0)
            elif roll == 1:
                armor = max(1, player.get_total_max_hp() // 4)
                add_buff(player.buffs, "barkskin", duration=6.0, level=armor)
            elif roll == 2:
                for debuff in self._CURE_DEBUFFS:
                    remove_buff(player.buffs, debuff)
            elif roll == 3:
                heal = max(1, player.get_total_max_hp() // 4)
                player.hp = min(player.get_total_max_hp(), player.hp + heal)

        elif kind == "phantom_meat":
            # All four FrozenCarpaccio buffs simultaneously (SPD PhantomMeat.effect)
            armor = max(1, player.get_total_max_hp() // 4)
            add_buff(player.buffs, "barkskin", duration=6.0, level=armor)
            add_buff(player.buffs, "invisibility", duration=20.0)
            heal = max(1, player.get_total_max_hp() // 4)
            player.hp = min(player.get_total_max_hp(), player.hp + heal)
            for debuff in self._CURE_DEBUFFS:
                remove_buff(player.buffs, debuff)

        elif kind == "meat_pie":
            add_buff(player.buffs, "well_fed", duration=50.0, level=1)

        elif kind == "supply_ration":
            heal = min(5, player.get_total_max_hp() - player.hp)
            if heal > 0:
                player.hp += heal
            cloak = player.belongings.artifact
            if cloak is not None and getattr(cloak, "kind", "") == "cloak_of_shadows":
                cloak.charge = min(cloak.charge_cap, cloak.charge + 1)

        elif kind == "berry":
            # SeedCounter: every 2 berries eaten drops a random seed on the floor
            counter = add_buff(player.buffs, "seed_counter", duration=99999.0,
                               level=1, stack_mode="stack")
            if counter.level >= 2:
                remove_buff(player.buffs, "seed_counter")
                floor = self._get_or_create_floor(player.floor_id)
                from app.engine.game.terrain_effects import _drop_seed
                _drop_seed(floor, (player.pos.x, player.pos.y))

    def on_food_eaten(self, player: Player, food_item) -> None:
        energy = getattr(food_item, "energy", 0)
        if energy > 0:
            player.hunger = max(0.0, player.hunger - energy)

        self._apply_food_effects(player, food_item)

        ti = player.subclass_info.talent_info

        # Hearty Meal (warrior T1): heal when HP < 1/3, +2 HP per point
        hearty_meal = ti.level(Talent.HEARTY_MEAL)
        if hearty_meal > 0 and player.hp / max(player.get_total_max_hp(), 1) < 0.334:
            healing = 2 + 2 * hearty_meal
            player.hp = min(player.get_total_max_hp(), player.hp + healing)

        # Iron Stomach (warrior T2): temporary immunity to hunger after eating
        iron_stomach = ti.level(Talent.IRON_STOMACH)
        if iron_stomach > 0:
            add_buff(player.buffs, "iron_stomach_immunity", duration=20.0 * iron_stomach, level=1)

        # Cached Rations (rogue T1): heal +2 per point on eat
        cached = ti.level(Talent.CACHED_RATIONS)
        if cached > 0:
            player.set_heal(float(4 + 4 * cached), 0.25, 0)

        # Empowering Meal (mage T1): gain wand charge per point
        empowering = ti.level(Talent.EMPOWERING_MEAL)
        if empowering > 0:
            from app.engine.entities.items_wands import Wand
            for w in player.belongings.all_items():
                if isinstance(w, Wand) and w.charges < w.max_charges:
                    w.charges = min(w.max_charges, w.charges + empowering)

        # Mystical Meal (rogue T2): cloak charge on eat
        mystical = ti.level(Talent.MYSTICAL_MEAL)
        if mystical > 0:
            cloak = player.belongings.artifact
            if cloak is not None and getattr(cloak, "kind", "") == "cloak_of_shadows":
                cloak.charge = min(cloak.charge_cap, cloak.charge + mystical)

        # Energizing Meal (mage T2): recharge wand charges on eat
        energizing = ti.level(Talent.ENERGIZING_MEAL)
        if energizing > 0:
            from app.engine.entities.items_wands import Wand as WandCls
            for item in player.belongings.all_items():
                if isinstance(item, WandCls) and item.max_charges > 0:
                    item.charges = min(item.max_charges, item.charges + energizing)

        # Invigorating Meal (huntress T2): speed boost on eat
        invigorating = ti.level(Talent.INVIGORATING_MEAL)
        if invigorating > 0:
            add_buff(player.buffs, "haste", duration=5.0 + 5.0 * invigorating, level=1)

    def on_potion_drunk(self, player: Player, potion_item) -> None:
        ti = player.subclass_info.talent_info

        # Liquid Willpower (warrior T2): shield on potion use
        liquid_willpower = ti.level(Talent.LIQUID_WILLPOWER)
        if liquid_willpower > 0:
            shield_amt = round(player.get_total_max_hp() * (0.030 + 0.035 * liquid_willpower))
            if shield_amt > 0:
                player.add_shield("liquid_willpower", shield_amt, priority=1, decay=300)

        # Backup Barrier (mage T1): shield on potion use
        barrier = ti.level(Talent.BACKUP_BARRIER)
        if barrier > 0:
            player.add_shield("backup_barrier", 3 + 3 * barrier, priority=1, decay=600)

        # Lingering Magic (mage T1): prolong buff durations
        lingering = ti.level(Talent.LINGERING_MAGIC)
        if lingering > 0:
            for b in player.buffs:
                if b.type in ("haste", "healing", "shield"):
                    b.duration *= 1.0 + 0.15 * lingering

        # Inscribed Power (mage T2): gain wand charges on potion
        inscribed = ti.level(Talent.INSCRIBED_POWER)
        if inscribed > 0:
            from app.engine.entities.items_wands import Wand as WandCls
            for item in player.belongings.all_items():
                if isinstance(item, WandCls) and item.max_charges > 0:
                    item.charges = min(item.max_charges, item.charges + inscribed)

    def on_kill(self, player: Player, target, floor_mobs: dict, floor_id: int) -> None:
        player.kills_count += 1
        ti = player.subclass_info.talent_info

        # Cleave (warrior T3 gladiator): extend combo timer on kill
        if player.subclass_info.subclass == Subclass.GLADIATOR and player.combo_count > 0:
            cleave = ti.level(Talent.CLEAVE)
            player.combo_timer = 15.0 + 15.0 * cleave

        # Lethal Momentum (warrior T2): chance for a free follow-up attack on kill
        lethal_momentum = ti.level(Talent.LETHAL_MOMENTUM)
        if lethal_momentum > 0 and random.random() < 0.34 + 0.33 * lethal_momentum:
            add_buff(player.buffs, "lethal_momentum_tracker", duration=5.0, level=1)
            self.add_event("LETHAL_MOMENTUM", {"player": player.id}, floor_id=floor_id, source_player_id=player.id)

        # Soul Eater (mage T3 warlock): heal on kill
        soul_eater = ti.level(Talent.SOUL_EATER)
        if soul_eater > 0:
            healing = 2 + 2 * soul_eater
            player.hp = min(player.get_total_max_hp(), player.hp + healing)
            self.add_event("HEAL", {"target": player.id, "amount": healing, "x": player.pos.x, "y": player.pos.y}, floor_id=floor_id)
