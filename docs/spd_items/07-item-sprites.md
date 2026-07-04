# SPD Item Sprite Atlas Reference (Weapons / Staves / Throwables / Armor)

Source: `core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/sprites/ItemSpriteSheet.java`.
Atlas file: `core/src/main/assets/sprites/items.png` (256x512px, 16x16 cell grid = 16 cols x 32 rows),
already present in remake at `frontend/src/assets/pixel-dungeon/sprites/items.png`.

`[col, row]` below = 0-indexed cell coords, matching remake convention in
`frontend/src/rendering/sprites.js` (`coordsForItem` returns `[col, row]`).
Frontend auto-crops each cell to its alpha bounds (`spriteRects.js`), so exact
pixel w/h isn't needed for porting — only `[col, row]`. `size` column = the
`assignItemRect(w,h)` art-box size from source, given for reference/verification.

Mechanics/stats for all of these are in [01-weapons-bombs.md](01-weapons-bombs.md)
and [02-armor-wands.md](02-armor-wands.md). This doc is the asset-location companion.

---

## 1. Melee Weapons

### Tier 1 — row 6, cols 0-5
| Item | Java class | `[col,row]` | size |
|---|---|---|---|
| Worn Shortsword | `WornShortsword` | [0,6] | 13x13 |
| Cudgel | `Cudgel` | [1,6] | 15x15 |
| Gloves | `Gloves` | [2,6] | 12x16 |
| Rapier | `Rapier` | [3,6] | 13x14 |
| Dagger | `Dagger` | [4,6] | 12x13 |
| Mage's Staff | `MagesStaff` | [5,6] | 15x16 |

### Tier 2 — row 6, cols 8-13
| Item | Java class | `[col,row]` | size |
|---|---|---|---|
| Shortsword | `Shortsword` | [8,6] | 13x13 |
| Hand Axe | `HandAxe` | [9,6] | 12x14 |
| Spear | `Spear` | [10,6] | 16x16 |
| Quarterstaff | `Quarterstaff` | [11,6] | 16x16 |
| Dirk | `Dirk` | [12,6] | 13x14 |
| Sickle | `Sickle` | [13,6] | 15x15 |

(`Pickaxe` quest item reuses Tier 2 stats but has its own sprite — see Quest sprites, not covered here.)

### Tier 3 — row 7, cols 0-5
| Item | Java class | `[col,row]` | size |
|---|---|---|---|
| Sword | `Sword` | [0,7] | 14x14 |
| Mace | `Mace` | [1,7] | 15x15 |
| Scimitar | `Scimitar` | [2,7] | 13x16 |
| Round Shield | `RoundShield` | [3,7] | 16x16 |
| Sai | `Sai` | [4,7] | 16x16 |
| Whip | `Whip` | [5,7] | 14x14 |

### Tier 4 — row 7, cols 8-14
| Item | Java class | `[col,row]` | size |
|---|---|---|---|
| Longsword | `Longsword` | [8,7] | 15x15 |
| Battle Axe | `BattleAxe` | [9,7] | 16x16 |
| Flail | `Flail` | [10,7] | 14x14 |
| Runic Blade | `RunicBlade` | [11,7] | 14x14 |
| Assassin's Blade | `AssassinsBlade` | [12,7] | 14x15 |
| Crossbow | `Crossbow` | [13,7] | 15x15 |
| Katana | `Katana` | [14,7] | 15x16 |

### Tier 5 — row 8, cols 0-6
| Item | Java class | `[col,row]` | size |
|---|---|---|---|
| Greatsword | `Greatsword` | [0,8] | 16x16 |
| War Hammer | `WarHammer` | [1,8] | 16x16 |
| Glaive | `Glaive` | [2,8] | 16x16 |
| Greataxe | `Greataxe` | [3,8] | 12x16 |
| Greatshield | `Greatshield` | [4,8] | 12x16 |
| Gauntlet | `Gauntlet` | [5,8] | 13x15 |
| War Scythe | `WarScythe` | [6,8] | 14x15 |

---

## 2. Missile Weapons / Throwables — row 9, cols 0-15

| Item | Java class | `[col,row]` | size | Tier |
|---|---|---|---|---|
| Spirit Bow | `SpiritBow` | [0,9] | 16x16 | (Huntress unique, not in Generator) |
| Throwing Spike | `ThrowingSpike` | [1,9] | 11x10 | 1 |
| Throwing Knife | `ThrowingKnife` | [2,9] | 12x13 | 1 |
| Throwing Stone | `ThrowingStone` | [3,9] | 12x10 | 1 |
| Fishing Spear | `FishingSpear` | [4,9] | 11x11 | 2 |
| Shuriken | `Shuriken` | [5,9] | 12x12 | 2 |
| Throwing Club | `ThrowingClub` | [6,9] | 12x12 | 2 |
| Throwing Spear | `ThrowingSpear` | [7,9] | 13x13 | 3 |
| Bolas | `Bolas` | [8,9] | 15x14 | 3 |
| Kunai | `Kunai` | [9,9] | 15x15 | 3 |
| Javelin | `Javelin` | [10,9] | 16x16 | 4 |
| Tomahawk | `Tomahawk` | [11,9] | 13x13 | 4 |
| Heavy Boomerang | `HeavyBoomerang` | [12,9] | 14x14 | 4 |
| Trident | `Trident` | [13,9] | 16x16 | 5 |
| Throwing Hammer | `ThrowingHammer` | [14,9] | 12x12 | 5 |
| Force Cube | `ForceCube` | [15,9] | 11x12 | 5 |

---

## 3. Darts — row 10, cols 0-12

All darts share `[col,row]` art size 15x15. Base `Dart` + 12 `TippedDart` variants
(seed-tipped, see 01-weapons-bombs.md §4 for seed mapping).

| Item | Java class | `[col,row]` |
|---|---|---|
| Dart (plain) | `Dart` | [0,10] |
| Rot Dart | `RotDart` | [1,10] |
| Incendiary Dart | `IncendiaryDart` | [2,10] |
| Adrenaline Dart | `AdrenalineDart` | [3,10] |
| Healing Dart | `HealingDart` | [4,10] |
| Chilling Dart | `ChillingDart` | [5,10] |
| Shocking Dart | `ShockingDart` | [6,10] |
| Poison Dart | `PoisonDart` | [7,10] |
| Cleansing Dart | `CleansingDart` | [8,10] |
| Paralytic Dart | `ParalyticDart` | [9,10] |
| Holy Dart | `HolyDart` | [10,10] |
| Displacing Dart | `DisplacingDart` | [11,10] |
| Blinding Dart | `BlindingDart` | [12,10] |

---

## 4. Bombs (throwables) — row 5, cols 0-11

| Item | Java class | `[col,row]` |
|---|---|---|
| Bomb | `Bomb` | [0,5] |
| Double Bomb | `DoubleBomb` | [1,5] |
| Firebomb | `Firebomb` | [2,5] |
| Frost Bomb | `FrostBomb` | [3,5] |
| Regrowth Bomb | `RegrowthBomb` | [4,5] |
| Smoke Bomb | `SmokeBomb` | [5,5] |
| Flashbang | `FlashBangBomb` | [6,5] |
| Holy Bomb | `HolyBomb` | [7,5] |
| Woolly Bomb | `WoollyBomb` | [8,5] |
| Noisemaker | `Noisemaker` | [9,5] |
| Arcane Bomb | `ArcaneBomb` | [10,5] |
| Shrapnel Bomb | `ShrapnelBomb` | [11,5] |

---

## 5. Armor — row 11, cols 0-10

| Item | Java class | `[col,row]` | size | Tier |
|---|---|---|---|---|
| Cloth Armor | `ClothArmor` | [0,11] | 15x12 | 1 |
| Leather Armor | `LeatherArmor` | [1,11] | 14x13 | 2 |
| Mail Armor | `MailArmor` | [2,11] | 14x12 | 3 |
| Scale Armor | `ScaleArmor` | [3,11] | 14x11 | 4 |
| Plate Armor | `PlateArmor` | [4,11] | 12x12 | 5 |
| Warrior's Platemail | `WarriorArmor` | [5,11] | 12x12 | 5 (class) |
| Mage's Robe | `MageArmor` | [6,11] | 15x15 | 5 (class) |
| Rogue's Garb | `RogueArmor` | [7,11] | 14x12 | 5 (class) |
| Huntress's Cloak | `HuntressArmor` | [8,11] | 13x15 | 5 (class) |
| Duelist's Breastplate | `DuelistArmor` | [9,11] | 12x13 | 5 (class) |
| Cleric's Vestments | `ClericArmor` | [10,11] | 13x14 | 5 (class) |

---

## 6. Staves / Wands — row 13, cols 0-12

`MagesStaff` itself uses the Tier 1 weapon sprite ([5,6], §1). The 13 wand
heads it can imbue use the wand atlas row:

| Item | Java class | `[col,row]` |
|---|---|---|
| Wand of Magic Missile | `WandOfMagicMissile` | [0,13] |
| Wand of Fireblast | `WandOfFireblast` | [1,13] |
| Wand of Frost | `WandOfFrost` | [2,13] |
| Wand of Lightning | `WandOfLightning` | [3,13] |
| Wand of Disintegration | `WandOfDisintegration` | [4,13] |
| Wand of Prismatic Light | `WandOfPrismaticLight` | [5,13] |
| Wand of Corrosion | `WandOfCorrosion` | [6,13] |
| Wand of Living Earth | `WandOfLivingEarth` | [7,13] |
| Wand of Blast Wave | `WandOfBlastWave` | [8,13] |
| Wand of Corruption | `WandOfCorruption` | [9,13] |
| Wand of Warding | `WandOfWarding` | [10,13] |
| Wand of Regrowth | `WandOfRegrowth` | [11,13] |
| Wand of Transfusion | `WandOfTransfusion` | [12,13] |

All wand cells are 14x14 art boxes.

---

## 7. Placeholder / unidentified-state icons — row 0

Used for empty equip slots and unidentified item fallback:

| Holder | `[col,row]` | size | Use |
|---|---|---|---|
| `SOMETHING` | [0,0] | 8x13 | default/bug fallback sprite |
| `WEAPON_HOLDER` | [1,0] | 14x14 | empty weapon slot |
| `ARMOR_HOLDER` | [2,0] | 14x12 | empty armor slot |
| `MISSILE_HOLDER` | [3,0] | 15x15 | empty ammo slot |
| `WAND_HOLDER` | [4,0] | 14x14 | empty wand slot (not equippable in remake yet) |

(`ItemIcon.jsx`'s hardcoded fallback `[8, 13]` is `WAND_BLAST_WAVE`'s cell, not
`SOMETHING` [0,0] — likely should be `[0,0]` or `[1,0]`.)

---

## 8. Porting status (current remake roster)

`frontend/src/rendering/sprites.js` (`ITEM_SPRITES`) currently maps only a
handful of placeholder weapon/armor names, and several point at the wrong
cell relative to the real SPD item of that name:

| Current key | Current `[col,row]` | What's actually there | Real cell per §1/§5 |
|---|---|---|---|
| `"Sword"` | [9,6] | Hand Axe (Tier 2) | `Sword` → [0,7] |
| `"Mace"` | [10,6] | *(unassigned cell)* | `Mace` → [1,7] |
| `"Shortsword"` | [8,6] | Shortsword (Tier 2) — correct | — |
| `"Rusty Sword"` | [1,6] | Cudgel (Tier 1) | no `RustySword` class in SPD; keep as a remake-only starter stand-in, or repoint to `WornShortsword` [0,6] |
| `"Wooden Club"` / `"Club"` | [2,6] | Gloves (Tier 1) | no club-type weapon in real roster; same as above |
| `"Broken Shield"` / `"Mail Armor"` | [2,11] | Mail Armor — correct for Mail Armor; "Broken Shield" is a remake-only stand-in | — |

When porting the full weapon/armor/wand roster, add entries keyed by the real
SPD item names (e.g. `"Quarterstaff"`, `"Greatsword"`, `"Round Shield"`,
`"Scale Armor"`, `"Wand of Lightning"`, ...) using the `[col,row]` values from
§1, §2, §3, §5, §6 above — don't extend the placeholder/stand-in entries.
