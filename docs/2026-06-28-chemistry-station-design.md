# Chemistry Station — Design Spec

**Date:** 2026-06-28  
**Scope:** SPD-faithful alchemy pot: map rendering, interaction, UI, recipes.

---

## 1. Root Cause & Current State

- `LaboratoryRoom` / `SecretLaboratoryRoom` correctly place `ALCHEMY` terrain tiles during level gen; coordinates stored in `FloorState.alchemy_pots`.
- `spd_adapter.py` maps `spd_terrain.ALCHEMY → TileType.FLOOR` — pot renders as plain floor (invisible).
- `alchemy_pots` is **not included in `InitMessage`** — client knows nothing about pot locations.
- Seeds have no `ALCHEMIZE` action; the seed→potion recipe is unimplemented on the backend.
- No `WndAlchemy` modal exists on the frontend.

---

## 2. Architecture Overview

Five self-contained pieces, each with one clear responsibility:

| # | Piece | Responsibility |
|---|-------|----------------|
| 1 | **InitMessage** | Send pot coordinates to client |
| 2 | **drawAlchemyPots** | Render pot sprite on map |
| 3 | **describeCell + WndInfoCell** | Examine-mode info + "Use" button |
| 4 | **WndAlchemy** | Ingredient picker, recipe preview, Brew |
| 5 | **USE_ALCHEMY_POT handler** | Backend recipe execution |

---

## 3. Backend Changes

### 3.1 InitMessage — send pot coordinates

Add `alchemy_pots: List[Tuple[int, int]] = []` to `InitMessage` in `backend/app/schemas/envelopes.py`.

In `backend/app/engine/game/spd_adapter.py` (the function that builds `InitMessage`), include `floor.alchemy_pots` in the payload. Already tracked on `FloorState`; only the serialization is missing.

### 3.2 New message: `USE_ALCHEMY_POT`

Add to `backend/app/schemas/messages.py`:
```python
class UseAlchemyPot(BaseModel):
    type: Literal["USE_ALCHEMY_POT"]
    item_ids: List[str]   # 1–3 item IDs from player inventory
```

Add routing in `backend/app/main.py` (alongside `EXECUTE_ITEM_ACTION`):
```python
elif message.type == "USE_ALCHEMY_POT":
    game.use_alchemy_pot(player_id, message.item_ids)
```

### 3.3 `use_alchemy_pot` on `GameInstance`

Add to `backend/app/engine/game/items.py`:

```
def use_alchemy_pot(player_id, item_ids):
    1. Validate player alive, not downed.
    2. Validate player position is in floor.alchemy_pots.
    3. Resolve all item_ids → items from player inventory (fail silently on any missing).
    4. Route to recipe by item types (in priority order):
       a. TrinketCatalyst (1 item) → existing TrinketCatalyst recipe
       b. Trinket + duplicate (2 same type) → existing trinket-upgrade recipe
       c. GooBlob + HealthPotion (2 items) → existing ElixirOfAquaticRejuvenation recipe
       d. 3× Seed → seed_to_potion recipe (see §3.4)
       e. No match → no-op (server logs warning)
    5. Emit ALCHEMIZE event as usual.
```

The existing per-action `ALCHEMIZE` dispatch on individual items (GooBlob, TrinketCatalyst) is **kept** for backward compatibility.

### 3.4 Seed → Potion Recipe (SPD `Potion.SeedToPotion`)

Implement in `backend/app/engine/entities/item_actions.py` as `action_seed_to_potion(game, player, seeds)`:

**Requirements:** exactly 3 Seed items total (quantity can be stacked — `qty >= 1` per item, sum = 3).

**SPD-faithful randomness logic:**
```
distinct_types = number of unique plant_type values among the 3 seeds
if distinct_types == 1:
    result_type = that seed's mapped potion
    result_identified = True   # auto-identified when all same
elif distinct_types == 2:
    if random.randint(0, 3) == 0:   # 25% chance
        result_type = random potion from full pool
    else:
        result_type = mapped potion of a randomly-chosen one of the 3 seeds
elif distinct_types == 3:
    if random.randint(0, 1) == 0:   # 50% chance
        result_type = random potion from full pool
    else:
        result_type = mapped potion of a randomly-chosen one of the 3 seeds
```

**Anti-farming (SPD Dungeon.LimitedDrops):**  
If the result is `HealthPotion`, reroll with probability `random.randint(0, 9) < floor.cooking_hp_count`. If rerolled, pick a different random potion (not HealthPotion). If HealthPotion survives the reroll, increment `floor.cooking_hp_count`. Add `cooking_hp_count: int = 0` to `FloorState`.

**Seed → Potion mapping** (from SPD `Potion.SeedToPotion`):

| `plant_type` | Potion class |
|---|---|
| `sungrass` | `HealthPotion` |
| `fadeleaf` | `MindVisionPotion` |
| `icecap` | `FrostPotion` |
| `firebloom` | `LiquidFlamePotion` |
| `sorrowmoss` | `ToxicGasPotion` |
| `swiftthistle` | `HastePotion` |
| `blindweed` | `InvisibilityPotion` |
| `stormvine` | `LevitationPotion` |
| `earthroot` | `ParalyticGasPotion` |
| `mageroyal` | `PurityPotion` |
| `starflower` | `ExperiencePotion` |
| `rotberry` | `StrengthPotion` |

After crafting: consume all 3 seed items (decrement quantity, detach if qty reaches 0), collect result potion into player backpack. Quickslot placeholders for consumed items as usual.

---

## 4. Frontend — Map Rendering

### 4.1 Store pot coordinates

In `frontend/src/net/useGameSocket.ts`, on `INIT` message:
```ts
alchemyPotsRef.current = data.alchemy_pots || [];
```

Add `alchemyPotsRef: Ref<[number, number][]>` to the socket hook refs (same pattern as `torchesRef`). Wire through `App.jsx` and `useGameRenderer.js`.

### 4.2 Draw pass: `drawAlchemyPots`

New file: `frontend/src/rendering/draw/alchemyPots.js`

Pattern: identical to `drawTorches.js` — iterate coordinates, skip if not `discovered`, draw sprite.

**Sprite source:** region tileset (same atlas used for the current floor, e.g. `tiles_sewers.png`).  
Pot sprite is at `atlasIndex(12, 4)` — SPD's `FLAT_OTHER + 12` position in the dungeon tile sheet.

```js
export function drawAlchemyPots(ctx, { alchemyPots, assetImages, visionRef, regionAtlas }) {
  // regionAtlas = assetImages.tiles (current region's tileset)
  // Draw: floor base tile first, then pot overlay at atlasIndex(12,4)
  for (const [x, y] of alchemyPots) {
    if (!visionRef.current.discovered.has(`${x},${y}`)) continue;
    // 1. floor base (same as getFloorBase — pick FLOOR_VARIANTS[0] for simplicity)
    drawAtlasTile(ctx, regionAtlas, FLOOR_ATLAS_INDEX, x, y);
    // 2. pot sprite overlay
    drawAtlasTile(ctx, regionAtlas, POT_ATLAS_INDEX, x, y);
  }
}
```

Call in `useGameRenderer.js` after `drawGrid` and before `drawItems`.

**Visibility:** discovered tiles show pot (dimmed via existing discovered-vs-visible filter); visible tiles show pot at full brightness. Matches SPD behavior (pot visible once room discovered).

---

## 5. Frontend — Interaction

### 5.1 describeCell — alchemy pot tile

In `frontend/src/input/describeCell.js`:

Add `alchemyPotsRef` parameter. Before falling through to tile description, check:
```js
for (const [px, py] of alchemyPotsRef.current) {
  if (px === tileX && py === tileY) {
    return {
      kind: 'alchemy_pot',
      name: i18n.t('tile.alchemy'),
      sub: null,
      anchor: tileAnchor,
    };
  }
}
```

### 5.2 WndInfoCell — alchemy pot case

Add `case 'alchemy_pot':` to `WndInfoCell.jsx`:
- Shows pot icon (from tileset sprite or placeholder), name "Alchemy Pot", description from locale (`tile.desc.alchemy`).
- If `cellInfo.playerOnPot` is true (passed from describeCell when player's position matches the pot): show a **"Use"** button that calls `onOpenAlchemy()`.
- If player is not on the pot: description only, no Use button (SPD: you must stand on it).

`describeCell` sets `playerOnPot: myPlayerPos.x === tileX && myPlayerPos.y === tileY`.

### 5.3 Interaction trigger — auto-open on self-tap

In SPD: tapping the alchemy pot tile when standing on it opens the alchemy scene immediately (no examine needed). Replicate:

In `App.jsx` move handler (where we dispatch player move on tile tap): if the tapped tile is in `alchemyPotsRef.current` AND the player is already on that tile → open `WndAlchemy` instead of sending `MOVE`.

---

## 6. Frontend — WndAlchemy Modal

New file: `frontend/src/ui/WndAlchemy.jsx`

### 6.1 Layout (SPD-faithful, simplified for web)

```
┌─────────────────────────────────────┐
│  🧪 Alchemy Pot                     │
├─────────────────────────────────────┤
│  Select up to 3 ingredients:        │
│                                     │
│  ☐  [icon] Sungrass Seed  ×3        │
│  ☐  [icon] Fadeleaf Seed  ×1        │
│  ☐  [icon] Goo Blob        ×1       │
│  ...                                │
├─────────────────────────────────────┤
│  Result: [icon] ???  (if known)     │
│                    Unknown Potion   │
├─────────────────────────────────────┤
│            [ Brew ]   [ Cancel ]    │
└─────────────────────────────────────┘
```

### 6.2 Ingredient filtering

Show only items that are valid alchemy ingredients:
- Seeds (any `type === 'seed'`)
- GooBlob (`kind === 'goo_blob'`) — shown only if player also has a HealthPotion
- TrinketCatalyst (`kind === 'trinket_catalyst'`)
- Trinkets (`type === 'trinket'`) — shown only if player has a duplicate of the same kind

### 6.3 Selection rules

- Player selects 1–3 items (checkboxes).
- Selecting a 4th disables further selection (or deselects the previous).
- "Brew" button enabled when ≥1 items selected and the combination matches a known recipe shape (seeds must total exactly 3, GooBlob requires exactly 1 HealthPotion alongside it, etc.).

### 6.4 Recipe preview

Live-update the result slot based on current selection:
- 3 same-type seeds → show the mapped potion (identified name + sprite).
- 3 mixed seeds → show "Unknown Potion" (result is probabilistic).
- GooBlob + HealthPotion → show "Elixir of Aquatic Rejuvenation".
- TrinketCatalyst → show "Random Trinket (×4 options)".
- Trinket + same-type copy → show `[TrinketName] +1`.
- Any other combination → show placeholder "?".

### 6.5 Brew button

On click: `send({ type: 'USE_ALCHEMY_POT', item_ids: selectedItemIds })`, close modal.

### 6.6 Opening the modal

`WndAlchemy` is opened via `modals.setShowAlchemy(true)` (new modal state in `GameModals.jsx`, same pattern as `showInventory`, `showShop`, etc.). Receives `playerInventory`, `send`, `onClose`.

---

## 7. Locale Strings

Add to `frontend/src/locales/en/translation.json` (already partially there):
```json
"tile": {
  "alchemy": "Alchemy Pot",
  "desc": {
    "alchemy": "This pot is filled with magical water. Items can be mixed into the pot to create something new!"
  }
},
"action": {
  "alchemize": "Alchemize"
},
"wnd": {
  "alchemy": {
    "title": "Alchemy Pot",
    "prompt": "Select up to 3 ingredients:",
    "result": "Result:",
    "brew": "Brew",
    "unknown": "Unknown Potion"
  }
}
```

---

## 8. Non-Goals (Out of Scope)

- Exotic potions, brews, elixirs, blandfruit cooking — separate future feature.
- Energy costs for alchemy — SPD v2.x feature, not in scope.
- Animated "brewing" VFX — post-MVP.
- Alchemy window for non-pot context (e.g. Scroll of Transmutation).

---

## 9. Files Changed

**Backend:**
- `backend/app/schemas/envelopes.py` — add `alchemy_pots` to `InitMessage`
- `backend/app/schemas/messages.py` — add `UseAlchemyPot`
- `backend/app/engine/game/floor_state.py` — add `cooking_hp_count`
- `backend/app/engine/game/items.py` — add `use_alchemy_pot()`
- `backend/app/engine/entities/item_actions.py` — add `action_seed_to_potion()`
- `backend/app/main.py` — route `USE_ALCHEMY_POT`

**Frontend:**
- `frontend/src/net/useGameSocket.ts` — read `alchemy_pots` from INIT
- `frontend/src/rendering/draw/alchemyPots.js` — new draw pass
- `frontend/src/rendering/useGameRenderer.js` — call `drawAlchemyPots`
- `frontend/src/input/describeCell.js` — alchemy pot cell description
- `frontend/src/ui/WndInfoCell.jsx` — alchemy pot case
- `frontend/src/ui/WndAlchemy.jsx` — new modal
- `frontend/src/ui/GameModals.jsx` — wire WndAlchemy
- `frontend/src/App.jsx` — pass `alchemyPotsRef`, auto-open on self-tap
- `frontend/src/locales/en/translation.json` — strings
