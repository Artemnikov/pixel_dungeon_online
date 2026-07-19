"""REST endpoints: static catalogs, lobby/room listing, and dev tooling.

The WebSocket game endpoint lives in main.py, since it's the app's actual
transport entrypoint rather than a lobby-layer concern.
"""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.connection_manager import (
    PRIVATE_ROOM_MAX_PLAYERS,
    PUBLIC_ROOM_ID,
    RoomMeta,
    manager,
)

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Online Pixel Dungeon Server is running"}


@router.get("/api/items/catalog")
async def get_items_catalog():
    from app.engine.entities.item_catalog import get_item_catalog

    return get_item_catalog()


@router.get("/api/talents/{class_type}")
async def get_talents(class_type: str):
    from app.engine.entities.subclasses import (
        TALENT_DEFS, TALENT_TITLES, TALENT_DESCRIPTIONS,
        TALENT_CLASS_REQ, ABILITY_TALENTS, TIER_UNLOCK_LEVELS,
        TIER_MAX_POINTS, CLASS_SUBCLASSES,
        T4_ABILITY_TALENTS, CLASS_ARMOR_ABILITIES, Talent,
    )
    from app.engine.entities.player import CharacterClass

    valid = {CharacterClass.WARRIOR, CharacterClass.MAGE, CharacterClass.ROGUE, CharacterClass.HUNTRESS}
    if class_type not in valid:
        return {"error": f"Unknown class: {class_type}"}, 404

    # Talents belong to a class if they're in TALENT_CLASS_REQ for that class,
    # OR their subclass_req is one of the class's subclass options.
    own_subclasses = set(CLASS_SUBCLASSES.get(class_type, ()))

    def _belongs_to_class(tid: str, sreq: Optional[str]) -> bool:
        # HEROIC_ENERGY is a shared T4 universal talent, available to any class
        # once T4 is unlocked (see TALENT_CLASS_REQ comment).
        if tid == Talent.HEROIC_ENERGY:
            return True
        if TALENT_CLASS_REQ.get(tid) == class_type:
            return True
        if sreq is not None and sreq in own_subclasses:
            return True
        return False

    tiers: dict = {}

    for talent_id, (max_pts, tier, subclass_req) in TALENT_DEFS.items():
        if not _belongs_to_class(talent_id, subclass_req):
            continue

        entry = {
            "id": talent_id,
            "name": TALENT_TITLES.get(talent_id, talent_id),
            "description": TALENT_DESCRIPTIONS.get(talent_id, ""),
            "max_pts": max_pts,
            "tier": tier,
            "subclass": subclass_req,
            "is_ability_selector": talent_id in ABILITY_TALENTS,
        }

        if talent_id in ABILITY_TALENTS:
            entry["unlocks_ability"] = ABILITY_TALENTS[talent_id]

        tier_key = str(tier)
        if tier_key not in tiers:
            tiers[tier_key] = {
                "unlock_level": TIER_UNLOCK_LEVELS.get(tier, 99),
                "max_total_points": TIER_MAX_POINTS.get(tier, 0),
                "talents": [],
            }
        tiers[tier_key]["talents"].append(entry)

    # Build ability → T4 talents map (only for ability-gated T4 talents, i.e.
    # those with subclass_req=None). Subclass-gated T4 talents appear in the
    # tier list with their subclass field and are NOT duplicated here.
    ability_to_talents: dict = {}
    universal_t4: list = []
    has_t4_mapping = False
    for tid, (_, t, sreq) in TALENT_DEFS.items():
        if t != 4 or sreq is not None or not _belongs_to_class(tid, sreq):
            continue
        ability = T4_ABILITY_TALENTS.get(tid)
        if ability is not None:
            has_t4_mapping = True
            ability_to_talents.setdefault(ability, []).append(tid)
        else:
            universal_t4.append(tid)

    if has_t4_mapping:
        # Append the class's universal T4 talent(s) (e.g. Heroic Energy) to
        # every armor ability's talent list, per SPD's ArmorAbility.talents().
        for ability in CLASS_ARMOR_ABILITIES.get(class_type, ()):
            for tid in universal_t4:
                ability_to_talents.setdefault(ability, []).append(tid)
    else:
        for tid in universal_t4:
            for ability_tid, ability in ABILITY_TALENTS.items():
                _, _, asr = TALENT_DEFS.get(ability_tid, (0, 0, None))
                a_req = TALENT_CLASS_REQ.get(ability_tid)
                if a_req == class_type or (asr and asr in own_subclasses):
                    ability_to_talents.setdefault(ability, []).append(tid)
                    break

    ability_selectors: dict = {}
    for tid, ability in ABILITY_TALENTS.items():
        _, _, sreq = TALENT_DEFS.get(tid, (0, 0, None))
        if _belongs_to_class(tid, sreq):
            ability_selectors[tid] = ability

    return {
        "class": class_type,
        "subclasses": list(own_subclasses),
        "armor_abilities": list(CLASS_ARMOR_ABILITIES.get(class_type, ())),
        "tiers": {k: tiers[k] for k in sorted(tiers.keys(), key=int)},
        "ability_selectors": ability_selectors,
        "ability_tier4": ability_to_talents,
    }


@router.get("/api/rooms")
async def list_rooms():
    def _count(room_id: str) -> int:
        return len(manager.active_connections.get(room_id, {}))

    public_count = _count(PUBLIC_ROOM_ID)
    groups = [
        {
            "room_id": room.room_id,
            "name": room.name,
            "player_count": _count(room.room_id),
            "max_players": room.max_players,
            "has_password": room.has_password,
        }
        for room in manager.rooms.values()
        if not room.is_public
    ]
    total_players = public_count + sum(g["player_count"] for g in groups)
    return {
        "total_players": total_players,
        "public": {"room_id": PUBLIC_ROOM_ID, "player_count": public_count},
        "groups": groups,
    }


class CreateRoomRequest(BaseModel):
    name: str
    password: Optional[str] = None


@router.post("/api/rooms")
async def create_room(body: CreateRoomRequest):
    name = (body.name or "").strip()
    if not name:
        return {"error": "name required"}
    room_id, resolved_name = manager._unique_room(name)
    manager.rooms[room_id] = RoomMeta(
        room_id, resolved_name, is_public=False,
        password=(body.password or None),
        max_players=PRIVATE_ROOM_MAX_PLAYERS,
    )
    return {"room_id": room_id, "name": resolved_name}


@router.post("/dev/xp/{game_id}/{player_id}/{amount}")
async def dev_grant_xp(game_id: str, player_id: str, amount: int):
    game = manager.game_instances.get(game_id)
    if not game:
        return {"error": "game not found"}
    player = game.players.get(player_id)
    if not player:
        return {"error": "player not found"}
    leveled = player.earn_exp(amount)
    if leveled:
        game.on_talent_level_up(player)
    # Debug: check serialized state
    state = game.get_state(player_id)
    serialized_player = next((p for p in state.get("players", []) if p.get("id") == player_id), None)
    return {
        "leveled": leveled,
        "level": player.level,
        "xp": player.experience,
        "talent_points": player.subclass_info.talent_points,
        "serialized_level": serialized_player.get("level") if serialized_player else None,
        "serialized_talents": serialized_player.get("subclass_info", {}).get("talent_info", {}).get("talents") if serialized_player else None,
        "serialized_talent_points": serialized_player.get("subclass_info", {}).get("talent_points") if serialized_player else None,
    }
