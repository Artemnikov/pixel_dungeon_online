# Copyright (C) 2026 ArtemNikov
#
"""Melee combat for GameInstance (part of MovementCombatMixin).

Bump-into-occupied-cell resolution (sheep/NPC/ally bumps, revive, parry,
melee attack roll) plus shared post-kill handling.
"""

import random
import time

from app.engine.entities.base import Position
from app.engine.entities.buffs import get_buff, remove_buff
from app.engine.entities.items.consumables import Gold
from app.engine.entities.items.potions import RevivingPotion
from app.engine.entities.mobs import DM300, Goo, Shopkeeper
from app.engine.entities.player import Mob as MobEntity, Player, hurt_warning_sound
from app.engine.entities.quest_bosses import Ghost
from app.engine.entities.rings import furor_multiplier
from app.engine.game.ai_goo import _goo_add_locked_floor_time
from app.engine.game.ai_pylon import _activate_pylon
from app.engine.systems.combat import resolve_melee_attack
from app.engine.systems.loot import roll_drops


class MeleeCombatMixin:
    def _resolve_bump(self, entity, target_entity, floor, floor_id: int) -> None:
        """Handle stepping into an occupied cell: sheep/NPC bump, ally revive,
        or melee combat (invoked from move_entity when the destination tile
        is occupied)."""
        # Sheep interaction: player bump → baa message, 1s action cost, sound
        if isinstance(entity, Player) and getattr(target_entity, "name", "") == "Sheep":
            entity.action_until = time.time() + 1.0
            baa = random.choice(["Baa!", "Baa?", "Baa.", "Baa..."])
            self.add_event("MESSAGE", {"text": baa}, floor_id=floor_id, player_id=entity.id)
            self.add_event("PLAY_SOUND", {"sound": "SHEEP",
                                           "rate": random.uniform(0.91, 1.1)},
                           floor_id=floor_id)
            sheep_buff = get_buff(target_entity.buffs, "sheep_timer")
            if sheep_buff and sheep_buff.remaining >= 20:
                sheep_buff.remaining = 0
            return

        # Push past an owned ally (Mirror Image / Ghost Hero) instead of
        # being blocked -- without this, reading Mirror Image in a tight
        # corridor could trap the hero behind their own clones for good,
        # since same-faction bumps don't attack and nothing else moves them.
        if (
            isinstance(entity, Player)
            and isinstance(target_entity, MobEntity)
            and entity.faction == target_entity.faction
            and getattr(target_entity, "owner_id", None) == entity.id
        ):
            entity.pos, target_entity.pos = target_entity.pos, entity.pos
            self.add_event("MOVE", {"entity": entity.id, "x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id)
            return

        if isinstance(entity, Player) and isinstance(target_entity, Shopkeeper):
            self.npc_interact(entity.id, target_entity.id)
            return

        if isinstance(entity, Player) and isinstance(target_entity, Ghost):
            self.npc_interact(entity.id, target_entity.id)
            return

        # Mirrors SPD's enemyInFOV check (Mob.java:252): a mob cannot
        # perceive an invisible player, so it treats the tile as blocked
        # rather than attacking.
        if isinstance(entity, MobEntity) and isinstance(target_entity, Player) and target_entity.invisible > 0:
            return

        if (
            isinstance(entity, Player)
            and isinstance(target_entity, Player)
            and target_entity.is_downed
            and entity.faction == target_entity.faction
        ):
            revive_potion_idx = next(
                (i for i, item in enumerate(entity.inventory) if isinstance(item, RevivingPotion)),
                -1,
            )
            if revive_potion_idx != -1:
                entity.inventory.pop(revive_potion_idx)
                target_entity.is_downed = False
                target_entity.hp = target_entity.get_total_max_hp() // 2
                self.add_event("REVIVE", {"target": target_entity.id, "source": entity.id}, floor_id=floor_id)
                return

        if entity.faction != target_entity.faction:
            if isinstance(entity, Player) and entity.is_downed:
                return

            current_time = time.time()
            cooldown = entity.attack_cooldown
            if isinstance(entity, Player):
                if entity.equipped_weapon:
                    cooldown = entity.equipped_weapon.attack_cooldown
                cooldown /= furor_multiplier(entity)

            if current_time - entity.last_attack_time < cooldown:
                return

            entity.last_attack_time = current_time

            # Parry (warrior combo move): a riposte-primed defender
            # counter-strikes the attacker before damage resolves.
            if isinstance(target_entity, Player) and target_entity.has_buff("riposte_tracker"):
                self._riposte_counter(target_entity, entity, floor, floor_id)

            if isinstance(entity, Player):
                entity._last_action = ""
            next_attack_in_ms = round(max(0.0, entity.last_attack_time + cooldown - time.time()) * 1000)
            result = resolve_melee_attack(
                entity, target_entity,
                floor.mobs, entity.pos.x, entity.pos.y,
                is_in_los=lambda a, b: self._is_in_los(a, b, floor_id=floor_id),
                floor=floor,
                add_event=lambda type, data, **kw: self.add_event(type, data, **{
                    "floor_id": floor_id,
                    "source_player_id": entity.id if isinstance(entity, Player) else None,
                    **kw,
                }),
                game=self,
            )
            if result["missed"]:
                self.add_event("MISS", {"source": entity.id, "target": target_entity.id, "defense_verb": result.get("defense_verb", "dodged")}, floor_id=floor_id)
                self.add_event("ATTACK", {
                    "source": entity.id,
                    "target": target_entity.id,
                    "damage": 0,
                    "surprise": False,
                    "next_attack_in_ms": next_attack_in_ms,
                }, floor_id=floor_id)
                return
            dmg = result["damage"]
            self.add_event("ATTACK", {
                "source": entity.id,
                "target": target_entity.id,
                "damage": dmg,
                "surprise": result["surprise"],
                "crit": result.get("crit", False),
                "grim_proc": result.get("grim_proc", False),
                "next_attack_in_ms": next_attack_in_ms,
            }, floor_id=floor_id)
            # SPD Char.java:509 plays hitSound(Random.Float(0.87f, 1.15f)),
            # then KindOfWeapon multiplies by hitSoundPitch. Mobs use the
            # default HIT/HIT_BODY at pitch 1.0 (no mob overrides hitSound).
            pitch_jitter = random.uniform(0.87, 1.15)
            if isinstance(entity, Player):
                weapon = getattr(getattr(entity, "belongings", None), "weapon", None)
                if result.get("crit"):
                    sound = "HIT_STRONG"
                    rate = pitch_jitter
                elif weapon and getattr(weapon, "hit_sound", None):
                    sound = weapon.hit_sound
                    rate = pitch_jitter * getattr(weapon, "hit_sound_pitch", 1.0)
                else:
                    sound = "HIT_SLASH"
                    rate = pitch_jitter
                self.add_event("PLAY_SOUND", {"sound": sound, "rate": rate}, floor_id=floor_id, source_player_id=entity.id)
            else:
                # Mob melee: broadcast HIT_BODY from the mob's position so
                # every player who can see it hears the hit.
                self.add_event("PLAY_SOUND", {"sound": "HIT_BODY", "rate": pitch_jitter, "x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id)
            if dmg > 0:
                self.add_event("DAMAGE", {
                    "target": target_entity.id,
                    "amount": dmg,
                    "grim_proc": result.get("grim_proc", False),
                }, floor_id=floor_id)
                if result.get("grim_proc"):
                    self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=entity.id)
                if isinstance(target_entity, Player) and isinstance(entity, Player):
                    # Friendly-fire only: mob-on-player hits are already
                    # covered by the broadcast HIT_BODY above.
                    self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id, source_player_id=target_entity.id)
                if isinstance(target_entity, Player):
                    warn_sound = hurt_warning_sound(dmg, target_entity.hp, target_entity.get_total_max_hp())
                    if warn_sound:
                        self.add_event("PLAY_SOUND", {"sound": warn_sound}, player_id=target_entity.id)
                if isinstance(target_entity, Goo) and isinstance(entity, Player):
                    _goo_add_locked_floor_time(self, floor_id, entity, dmg)

            self._maybe_trigger_dm300_supercharge(target_entity, floor, floor_id, entity.pos)

            # Warrior subclass: combo / berserk events after successful damage
            if isinstance(entity, Player) and dmg > 0:
                if entity.subclass_info.subclass == "gladiator":
                    self.add_event("COMBO_UPDATE", {"player": entity.id, "count": entity.combo_count}, floor_id=floor_id, source_player_id=entity.id)
                    if entity.combo_count in (2, 4, 6, 8, 10):
                        moves = {2: "clobber", 4: "slam", 6: "parry", 8: "crush", 10: "fury"}
                        self.add_event("COMBO_MOVE_UNLOCKED", {"player": entity.id, "move": moves[entity.combo_count]}, floor_id=floor_id, source_player_id=entity.id)
                if entity.subclass_info.subclass == "berserker":
                    self.add_event("RAGE_CHANGED", {"player": entity.id, "power": entity.berserk_power}, floor_id=floor_id, source_player_id=entity.id)

            if not target_entity.is_alive:
                self._finish_kill(entity, target_entity, floor, floor_id)

    def _finish_kill(self, attacker, target_entity, floor, floor_id: int) -> None:
        """Shared post-death handling for a combat kill (melee bump or
        ranged/thrown attack), once the killing blow has already brought
        target_entity.is_alive to False: boss/quest death hooks, mob.die(),
        warrior kill procs (Lethal Momentum), and loot/gold drops."""
        target_is_mob = isinstance(target_entity, MobEntity)
        attacker_is_player = isinstance(attacker, Player)
        if target_is_mob:
            self.process_death_mark_kill(attacker, target_entity, floor, floor_id)
        if attacker_is_player:
            self.on_kill(attacker, target_entity, floor.mobs, floor_id)
            # Lethal Momentum (warrior T2): a killing blow that procced the
            # free follow-up doesn't consume the attack's cooldown, allowing
            # an immediate re-attack.
            if remove_buff(attacker.buffs, "lethal_momentum_tracker"):
                attacker.last_attack_time = 0.0
        self.add_event("DEATH", {"target": target_entity.id}, floor_id=floor_id)
        if target_is_mob:
            # die() must run before handle_mob_death(): some death hooks
            # (e.g. Necromancer's linked-skeleton kill) depend on die()'s
            # side effects having already landed.
            target_entity.die(
                attacker=attacker,
                floor_mobs=floor.mobs,
                tile_x=target_entity.pos.x,
                tile_y=target_entity.pos.y,
                players=list(self._players_on_floor(floor_id)),
            )
            self.handle_mob_death(target_entity, floor, floor_id)
        if attacker_is_player and target_is_mob:
            self._award_kill_xp(attacker, target_entity, floor_id)
            drops = roll_drops(target_entity, self.drop_counters, target_entity.pos.x, target_entity.pos.y, players=list(self._players_on_floor(floor_id)))
            for item in drops:
                floor.items[item.id] = item
            if any(isinstance(d, Gold) for d in drops):
                self.add_event("GOLD_DROP", {"x": target_entity.pos.x, "y": target_entity.pos.y}, floor_id=floor_id)

    def _maybe_trigger_dm300_supercharge(self, target: "MobEntity", floor, floor_id: int, near_pos: Position):
        """Trigger DM300 pylon activation if target is DM300 with pending activation."""
        if isinstance(target, DM300) and target.pending_pylon_activation:
            target.pending_pylon_activation = False
            self.add_event("DM300_SUPERCHARGE", {"mob": target.id}, floor_id=floor_id)
            _activate_pylon(self, floor, floor_id, near_pos=near_pos)
