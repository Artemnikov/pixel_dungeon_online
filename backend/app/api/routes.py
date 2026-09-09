"""REST endpoints: static catalogs, lobby/room listing, and dev tooling.

The WebSocket game endpoint lives in main.py, since it's the app's actual
transport entrypoint rather than a lobby-layer concern.
"""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.connection_manager import (
    PRIVATE_ROOM_MAX_PLAYERS,
    PUBLIC_ROOM_ID,
    RoomMeta,
    manager,
)

router = APIRouter()


class FeedbackRequest(BaseModel):
    feedback_type: str  # "good" | "bad" | "general"
    message: str
    contact: Optional[str] = None
    context: Optional[str] = None
    screenshot: Optional[str] = None  # data URL e.g. "data:image/png;base64,..."


@router.post("/api/feedback")
async def send_feedback(body: FeedbackRequest):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        raise HTTPException(status_code=503, detail="Telegram bot feedback is not configured on the server")

    message_text = (body.message or "").strip()
    if not message_text:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    emoji = "💬"
    if body.feedback_type == "good":
        emoji = "🟢"
    elif body.feedback_type == "bad":
        emoji = "🔴"

    caption_lines = [
        f"<b>Feedback Submission</b> {emoji}",
        f"<b>Type:</b> {body.feedback_type.capitalize()}",
    ]
    if body.contact:
        caption_lines.append(f"<b>Contact:</b> {body.contact.strip()}")
    if body.context:
        caption_lines.append(f"<b>Context:</b> {body.context.strip()}")

    caption_lines.append("\n<b>Message:</b>")
    caption_lines.append(message_text)

    caption = "\n".join(caption_lines)

    # If screenshot is attached and valid
    screenshot_str = body.screenshot or ""
    if screenshot_str.startswith("data:image/") and ";base64," in screenshot_str:
        try:
            _, encoded = screenshot_str.split(";base64,", 1)
            img_bytes = base64.b64decode(encoded)

            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            body_parts = []

            # chat_id field
            body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode("utf-8"))

            # caption field
            body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode("utf-8"))

            # parse_mode field
            body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nHTML\r\n".encode("utf-8"))

            # photo field
            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"screenshot.png\"\r\nContent-Type: image/png\r\n\r\n".encode("utf-8")
                + img_bytes
                + b"\r\n"
            )

            body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
            payload = b"".join(body_parts)

            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"success": True}
        except urllib.error.HTTPError as http_err:
            error_body = http_err.read().decode('utf-8', errors='ignore')
            raise HTTPException(status_code=502, detail=f"Telegram API HTTP error {http_err.code}: {error_body}")
        except Exception as e:
            # Fall back to text sendMessage if photo upload fails
            pass

    # Send text message
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload_dict = {
        "chat_id": chat_id,
        "text": caption,
        "parse_mode": "HTML",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload_dict).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return {"success": True}
            raise HTTPException(status_code=502, detail="Telegram API error")
    except urllib.error.HTTPError as http_err:
        error_body = http_err.read().decode('utf-8', errors='ignore')
        raise HTTPException(status_code=502, detail=f"Telegram API HTTP error {http_err.code}: {error_body}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to send telegram message: {str(e)}")


@router.get("/")
async def root():
    return {"message": "Online Pixel Dungeon Server is running"}


@router.get("/api/items/catalog")
async def get_items_catalog():
    from app.engine.entities.items.catalog import get_item_catalog

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
            "ability": T4_ABILITY_TALENTS.get(talent_id),
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
