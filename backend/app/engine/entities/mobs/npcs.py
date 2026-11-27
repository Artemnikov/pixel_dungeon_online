# Copyright (C) 2026 ArtemNikov
#
from typing import ClassVar, Dict, List, Optional

from pydantic import Field

from app.engine.entities.base import Faction
from app.engine.entities.player import Mob as MobEntity, DropEntry

# ---------------------------------------------------------------------------
# NPCs / player-faction allies (RatKing, Shopkeeper, Imp, Ghost, MirrorImage)
# ---------------------------------------------------------------------------

class RatKing(MobEntity):
    """The sewer boss secret room's NPC (RatKing.java). Sleeps until a hero
    talks to him, then wanders without ever choosing an enemy; takes no damage
    and dodges everything. Trades Ratmogrify for the Dwarf King's crown."""
    name: str = "Rat King"
    type: str = "npc"
    faction: str = Faction.PLAYER
    hp: int = 1
    max_hp: int = 1
    attack_skill: int = 0
    defense_skill: int = 0
    damage_min: int = 0
    damage_max: int = 0
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    speed: float = 2.0
    loot_table: List[DropEntry] = []
    ai_state: str = "sleeping"
    # Mirrors RatKing.java chooseEnemy() returning null: the generic wake-up
    # check never fires; only talking to him wakes him (see interact()).
    never_wakes: bool = True

    LINES: ClassVar[Dict[str, str]] = {
        "not_sleeping": "I'm not sleeping!",
        "what_is_it": "What is it? I have no time for this nonsense. My kingdom won't rule itself!",
        "crown_clothes": "Put some clothes on! You're in no state to talk to royalty!",
        "crown_thankyou": "Hehehe, thank you! Now go and make your king proud!",
        "crown_fine": "Fine! It's not like I wanted it anyway...",
        "crown_after": "Enjoying your new armor? No take-backsies!",
    }

    def take_damage(self, amount: int):
        # RatKing.damage(): does nothing — immune to all damage.
        return 0

    def get_effective_defense_skill(self) -> int:
        # RatKing.defenseSkill(): INFINITE_EVASION — always dodges.
        return 10 ** 9

    def yell(self, game, player, line: str) -> None:
        game.add_event("BOSS_YELL", {
            "mob": self.id, "key": f"mobText.rat_king_{line}", "text": self.LINES[line],
            "x": self.pos.x, "y": self.pos.y,
        }, floor_id=player.floor_id, player_id=player.id)

    @staticmethod
    def _crown_of(player):
        from app.engine.entities.items.consumables import KingsCrown
        return next((i for i in player.belongings.all_items() if isinstance(i, KingsCrown)), None)

    def interact(self, game, player) -> None:
        """SPD `RatKing.interact(hero)`."""
        from app.engine.entities.talent_enum import ArmorAbilityType
        crown = self._crown_of(player)
        if self.ai_state == "sleeping":
            game.add_event("MOB_NOTICE", {"mob": self.id}, floor_id=player.floor_id)
            self.yell(game, player, "not_sleeping")
            self.ai_state = "wandering"
        elif crown is not None:
            if player.belongings.armor is None:
                self.yell(game, player, "crown_clothes")
            else:
                game.add_event("RAT_KING_DIALOGUE", {"player": player.id, "npc": self.id},
                               player_id=player.id)
        elif player.armor_ability == ArmorAbilityType.RATMOGRIFY:
            self.yell(game, player, "crown_after")
        else:
            self.yell(game, player, "what_is_it")

    def answer_crown_offer(self, game, player, accept: bool) -> None:
        """SPD `RatKing.interact` WndOptions.onSelect: "Of course!" trades the
        crown for Ratmogrify, "I'd rather not..." keeps it."""
        from app.engine.entities.talent_enum import ArmorAbilityType
        crown = self._crown_of(player)
        if crown is None or player.belongings.armor is None:
            return
        if accept:
            crown.upgrade_armor(game, player, ArmorAbilityType.RATMOGRIFY)
            self.yell(game, player, "crown_thankyou")
        else:
            self.yell(game, player, "crown_fine")


class Shopkeeper(MobEntity):
    """Friendly trader NPC (Shopkeeper.java): immune, never wakes/attacks,
    sells from a fixed stock and buys items from the player."""
    name: str = "Shopkeeper"
    type: str = "npc"
    faction: str = Faction.PLAYER
    hp: int = 1
    max_hp: int = 1
    attack_skill: int = 0
    defense_skill: int = 0
    damage_min: int = 0
    damage_max: int = 0
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    loot_table: List[DropEntry] = []
    ai_state: str = "sleeping"
    never_wakes: bool = True

    def take_damage(self, amount: int):
        # Shopkeeper.damage(): immune to all damage.
        return 0


class Imp(MobEntity):
    """Imp quest-giver NPC (actors/mobs/npcs/Imp.java): immune, never wakes
    or attacks; offers the Golem/Monk token-collection quest."""
    name: str = "Imp"
    type: str = "npc"
    faction: str = Faction.PLAYER
    hp: int = 1
    max_hp: int = 1
    attack_skill: int = 0
    defense_skill: int = 0
    damage_min: int = 0
    damage_max: int = 0
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    loot_table: List[DropEntry] = []
    ai_state: str = "sleeping"
    never_wakes: bool = True

    def take_damage(self, amount: int):
        # Imp.damage(): immune to all damage.
        return 0

    def get_effective_defense_skill(self) -> int:
        return 10 ** 9


class GhostHeroMob(MobEntity):
    """Ghost of Sir Archibald summoned by the Dried Rose (DriedRose.GhostHero).
    Player-faction ally that auto-attacks enemies and follows the owner.
    Stats are refreshed each tick from the owner's level.
    """
    type: str = "ghost_hero"
    name: str = "Ghost Hero"
    hp: int = 20
    max_hp: int = 20
    faction: str = Faction.PLAYER
    flying: bool = True
    ai_state: str = "hunting"
    owner_id: str = ""
    attack_range: int = 1
    direct_x: Optional[int] = None
    direct_y: Optional[int] = None
    immunities: List[str] = Field(default_factory=lambda: [
        "corrosive_gas", "burning", "ally_buff",
    ])
    properties: List[str] = Field(default_factory=lambda: ["UNDEAD", "INORGANIC"])


class MirrorImage(MobEntity):
    """Hero clone summoned by Scroll of Mirror Image (MirrorImage.java).

    Spawns invisible (guaranteeing a first-strike surprise attack), with
    1 HP and combat stats refreshed each tick from the owning player.
    """
    type: str = "mirror_image"
    name: str = "Mirror Image"
    hp: int = 1
    max_hp: int = 1
    faction: str = Faction.PLAYER
    ai_state: str = "hunting"
    immunities: List[str] = Field(default_factory=lambda: ["toxic_gas", "corrosive_gas", "burning", "ally_buff"])
