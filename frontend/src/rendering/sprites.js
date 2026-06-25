// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU General Public License for more details.
//
import { TILE_SIZE, TILE_SCALE } from '../constants';

// Item Sprite Mapping
// Format: { name_keyword: [col, row] } — 0-indexed column/row in items.png (16x16 cells).
//
// Coordinates are ported from the original ItemSpriteSheet.java. That file's xy(x,y)
// helper is 1-based: idx = (x-1) + 16*(y-1); an item's index is its section base xy(...)
// plus its offset, and the grid cell is [idx % 16, idx // 16]. (items.png is the same
// 256x512 / 16x32 atlas as the original game.) NOTE: the numbers in the source's
// assignItemRect(NAME, w, h) calls are the sprite's pixel width/height, NOT the cell.
//
// Matching below is substring-based (itemName.includes(key)), so more-specific keys must
// be listed before the generic ones they contain (e.g. "Scroll Holder" before "Scroll").
export const ITEM_SPRITES = {
  // Weapons — [col,row] per docs/spd_items/07-item-sprites.md §1.
  // More-specific multi-word keys must precede shorter keys they contain
  // (e.g. "Worn Shortsword" before "Shortsword"/"Sword", "Battle Axe" before "Axe").
  "Throwable Dagger": [2, 9],   // THROWING_KNIFE (MISSILE_WEP+2)
  "Throwing":         [2, 9],
  "Worn Key":         [10, 3],  // WORN_KEY (MISC_CONSUMABLE+10 = idx 58) — before "Worn"
  "Worn Shortsword":  [0, 6],   // WornShortsword (tier 1)
  "Worn":             [0, 6],
  "Mage's Staff":     [5, 6],   // MagesStaff (tier 1)
  "Magic Staff":      [5, 6],
  "Staff of":         [5, 6],   // any "Staff of <Wand>" — MagesStaff (tier 1)
  "Staff":            [5, 6],
  "Dagger":           [4, 6],   // Dagger (tier 1)
  "Gloves":           [2, 6],   // Gloves (tier 1)
  "Rapier":           [3, 6],   // Rapier (tier 1)
  "Cudgel":           [1, 6],   // Cudgel (tier 1)
  "Hand Axe":         [9, 6],   // HandAxe (tier 2)
  "Spear":            [10, 6],  // Spear (tier 2)
  "Quarterstaff":     [11, 6],  // Quarterstaff (tier 2)
  "Dirk":             [12, 6],  // Dirk (tier 2)
  "Sickle":           [13, 6],  // Sickle (tier 2)
  "Shortsword":       [8, 6],   // Shortsword (tier 2)
  "Mace":             [1, 7],   // Mace (tier 3)
  "Scimitar":         [2, 7],   // Scimitar (tier 3)
  "Round Shield":     [3, 7],   // RoundShield (tier 3)
  "Sai":              [4, 7],   // Sai (tier 3)
  "Whip":             [5, 7],   // Whip (tier 3)
  "Battle Axe":       [9, 7],   // BattleAxe (tier 4)
  "Flail":            [10, 7],  // Flail (tier 4)
  "Runic Blade":      [11, 7],  // RunicBlade (tier 4)
  "Assassin's Blade": [12, 7],  // AssassinsBlade (tier 4)
  "Crossbow":         [13, 7],  // Crossbow (tier 4)
  "Katana":           [14, 7],  // Katana (tier 4)
  "Longsword":        [8, 7],   // Longsword (tier 4)
  "Greatsword":       [0, 8],   // Greatsword (tier 5)
  "War Hammer":       [1, 8],   // WarHammer (tier 5)
  "Glaive":           [2, 8],   // Glaive (tier 5)
  "Greataxe":         [3, 8],   // Greataxe (tier 5)
  "Greatshield":      [4, 8],   // Greatshield (tier 5)
  "Gauntlet":         [5, 8],   // Gauntlet (tier 5)
  "War Scythe":       [6, 8],   // WarScythe (tier 5)
  "Sword":            [0, 7],   // Sword (tier 3)

  // Bows / ranged (MISSILE_WEP = xy(1,10) = idx 144 -> row 9)
  "Spirit Bow":       [0, 9],   // SPIRIT_BOW
  "Old Bow":          [0, 9],
  "Bow":              [0, 9],
  "Boomerang":        [12, 9],  // BOOMERANG (MISSILE_WEP+12)
  "Stone":            [3, 9],   // THROWING_STONE (MISSILE_WEP+3)

  // Armor (ARMOR = xy(1,12) = idx 176 -> row 11)
  "Cloth Armor":      [0, 11],  // ARMOR_CLOTH
  "Leather Vest":     [1, 11],  // ARMOR_LEATHER (ARMOR+1)
  "Leather":          [1, 11],
  "Broken Shield":    [2, 11],  // ARMOR_MAIL (ARMOR+2) — closest stand-in
  "Mail Armor":       [2, 11],
  "Rogue's Cloak":    [7, 11],  // ARMOR_ROGUE (ARMOR+7)

  "Dried Rose":       [4, 16],  // ARTIFACT_ROSE1
  "Petal":            [6, 1],   // PETAL (UNCOLLECTIBLE+4)

  // Wands / rings / artifacts (section bases, generic first entry)
  // Row 13: 13 individual wand sprites (WANDS = xy(1,14) = idx 208, cells 0..12)
  "Wand of Magic Missile":   [0, 13],  // WAND_MAGIC_MISSILE
  "Wand of Fireblast":       [1, 13],  // WAND_FIREBOLT
  "Wand of Frost":           [2, 13],  // WAND_FROST
  "Wand of Lightning":       [3, 13],  // WAND_LIGHTNING
  "Wand of Disintegration":  [4, 13],  // WAND_DISINTEGRATION
  "Wand of Prismatic Light": [5, 13],  // WAND_PRISMATIC_LIGHT
  "Wand of Corrosion":       [6, 13],  // WAND_CORROSION
  "Wand of Living Earth":    [7, 13],  // WAND_LIVING_EARTH
  "Wand of Blast Wave":      [8, 13],  // WAND_BLAST_WAVE
  "Wand of Corruption":      [9, 13],  // WAND_CORRUPTION
  "Wand of Warding":         [10, 13], // WAND_WARDING
  "Wand of Regrowth":        [11, 13], // WAND_REGROWTH
  "Wand of Transfusion":     [12, 13], // WAND_TRANSFUSION
  "Wand":             [0, 13],  // generic fallback
  "Ring":             [0, 14],  // RINGS = xy(1,15) = idx 224
  "Artifact":         [0, 15],  // ARTIFACTS = xy(1,16) = idx 240

  // Bags (BAGS = xy(1,31) = idx 480 -> row 30). Listed before Scroll/Potion so the
  // specialised holder/bandolier names win over the generic consumable keys.
  "Backpack":         [1, 30],  // BACKPACK
  "Velvet Pouch":     [2, 30],  // POUCH
  "Scroll Holder":    [3, 30],  // HOLDER
  "Potion Bandolier": [4, 30],  // BANDOLIER
  "Magical Holster":  [5, 30],  // HOLSTER

  // Consumables (generic first entry of each section)
  "Metamorphosis":    [5, 19],  // SCROLL_METAMORPH (SCROLLS+5 = idx 309)
  "Scroll":           [0, 19],  // SCROLLS = xy(1,20) = idx 304
  "Health Potion":    [0, 22],  // POTIONS = xy(1,23) = idx 352
  "Reviving Potion":  [0, 22],
  "Elixir of Aquatic Rejuvenation": [9, 25],  // ELIXIR_AQUA (ELIXIRS+1, ELIXIRS=xy(9,26))
  "Potion":           [0, 22],
  "Food":             [0, 27],  // FOOD = xy(1,28) = idx 432

  // Seeds (SEEDS = xy(1,25) = idx 384 -> col0,row24; per-kind names like "Sungrass Seed")
  "Sungrass Seed":    [3, 24],  // SEED_SUNGRASS (SEEDS+3)
  "Earthroot Seed":   [8, 24],  // SEED_EARTHROOT (SEEDS+8)
  "Firebloom Seed":   [1, 24],  // SEED_FIREBLOOM (SEEDS+1)
  "Icecap Seed":      [4, 24],  // SEED_ICECAP (SEEDS+4)
  "Sorrowmoss Seed":  [6, 24],  // SEED_SORROWMOSS (SEEDS+6)
  "Dreamfoil Seed":   [7, 24],  // SEED_MAGEROYAL slot (SEEDS+7) — no SPD dreamfoil seed sprite
  "Fadeleaf Seed":    [10, 24], // SEED_FADELEAF (SEEDS+10)
  "Rotberry Seed":    [0, 24],  // SEED_ROTBERRY (SEEDS+0)
  "Starflower Seed":  [9, 24],  // SEED_STARFLOWER (SEEDS+9)
  "Stormvine Seed":   [5, 24],  // SEED_STORMVINE (SEEDS+5)
  "Blindweed Seed":   [11, 24], // SEED_BLINDWEED (SEEDS+11)
  "Swiftthistle Seed":[2, 24],  // SEED_SWIFTTHISTLE (SEEDS+2)
  "Seed":             [3, 24],  // generic Seed / "Seed of Sunlight" -> SEED_SUNGRASS

  // Misc
  "Tengu's Mask":     [11, 3],  // MASK (MISC_CONSUMABLE+11 = idx 59 = col 11, row 3 in items.png)
  "Goo Blob":         [7, 29],  // BLOB (QUEST+7, QUEST = xy(1,30) = idx 464)
  "King's Crown":     [12, 3],  // CROWN (MISC_CONSUMABLE+12 = idx 60 = col 12, row 3)
  "Chest":            [4, 2],   // CHEST (CONTAINER+0 = xy(5,3) = idx 36)
  "Crystal Chest":    [6, 2],   // CRYSTAL_CHEST (CONTAINER+2 = idx 38)
  "Locked Chest":     [5, 2],   // LOCKED_CHEST (CONTAINER+1 = idx 37)
  "Tomb":             [2, 2],   // TOMB (CONTAINER+? = xy(3,3) = idx 34)
  "Grave":            [0, 2],   // BONES sprite — player death grave marker
  "Skeleton":         [0, 2],   // SKELETON (CONTAINER+? = xy(1,3) = idx 32)
  "Remains":          [1, 2],   // REMAINS (CONTAINER+? = xy(2,3) = idx 33)
  "Gold":             [2, 1],   // GOLD (UNCOLLECTIBLE+0 = xy(3,2) = idx 18)
  "Dewdrop":          [5, 1],   // DEWDROP (UNCOLLECTIBLE+3 = idx 21)
  "Waterskin":        [0, 30],  // WATERSKIN = BAGS+0 = xy(1,31) -> idx 480 -> col0,row30
  "Golden Key":       [8, 3],   // GOLDEN_KEY (MISC_CONSUMABLE+8 = idx 56)
  "Crystal Key":      [9, 3],   // CRYSTAL_KEY (MISC_CONSUMABLE+9 = idx 57)
  "Rusty Key":        [7, 3],   // IRON_KEY (MISC_CONSUMABLE+7 = idx 55)
  "Key":              [7, 3],
  "Amulet of Yendor": [14, 4],  // AMULET = MISC_CONSUMABLE+13 = xy(1,4)+13 = idx 78 -> col14,row4

  // Default fallback (SOMETHING "?" placeholder, idx 0)
  "default":          [0, 0],
};

// Placeholder sprites shown in empty equip slots (ItemSpriteSheet PLACEHOLDERS row,
// base idx 0 -> row 0). Keyed by InventoryPane equip-slot key.
export const HOLDER_SPRITES = {
  weapon:   [1, 0],  // WEAPON_HOLDER
  armor:    [2, 0],  // ARMOR_HOLDER
  artifact: [6, 0],  // ARTIFACT_HOLDER
  misc:     [7, 0],  // TRINKET_HOLDER
  ring:     [5, 0],  // RING_HOLDER
};

export const getItemSpriteCoords = (itemName, itemType) => {
  for (const key in ITEM_SPRITES) {
    if (itemName && itemName.includes(key)) {
      return ITEM_SPRITES[key];
    }
  }
  // Type fallbacks — also cover unidentified potions/scrolls (masked name, kept type).
  if (itemType === 'weapon')    return [8, 6];
  if (itemType === 'wearable')  return [0, 11];
  if (itemType === 'potion')    return [0, 22];
  if (itemType === 'scroll')    return [0, 19];
  if (itemType === 'wand')      return [0, 13];
  if (itemType === 'ring')      return [0, 14];
  if (itemType === 'artifact')  return [0, 15];
  if (itemType === 'throwable') return [3, 9];
  if (itemType === 'food')      return [0, 27];
  if (itemType === 'key')       return [7, 3];
  if (itemType === 'gold')      return [2, 1];
  if (itemType === 'seed')      return [3, 24];  // SEED_SUNGRASS
  if (itemType === 'dewdrop')   return [5, 1];   // DEWDROP
  if (itemType === 'grave')     return [0, 2];   // BONES
  return ITEM_SPRITES["default"];
};

// Quickslot placeholders (depleted stackables) only carry a `kind`, not a
// `name`/`type`/`appearance`. Map kind prefixes to a generic item-type sprite
// so the slot shows a recognizable (dimmed) icon instead of going blank.
const PLACEHOLDER_TYPE_BY_KIND_PREFIX = [
  ['potion', 'potion'],
  ['scroll', 'scroll'],
  ['stone', 'throwable'],
  ['boomerang', 'throwable'],
  ['throwable_dagger', 'throwable'],
  ['seed', 'seed'],
  ['mystery_meat', 'food'],
  ['berry', 'food'],
  ['small_ration', 'food'],
  ['ration', 'food'],
  ['pasty', 'food'],
  ['chargrilled_meat', 'food'],
  ['dewdrop', 'dewdrop'],
  ['gold', 'gold'],
  ['wand', 'wand'],
];

// Resolve a serialized item to its sprite cell: server-sent per-run appearance
// (potion colour / scroll rune) first, then the name/type lookup table.
export const coordsForItem = (item) => {
  if (!item) return null;
  if (item.appearance) return [item.appearance.col, item.appearance.row];
  if (item.is_placeholder && item.kind) {
    const match = PLACEHOLDER_TYPE_BY_KIND_PREFIX.find(([prefix]) => item.kind.startsWith(prefix));
    if (match) return getItemSpriteCoords(null, match[1]);
  }
  // "Staff of <WandName>" → show the imbued wand's sprite
  if (item.name && item.name.startsWith('Staff of ')) {
    const wandName = 'Wand of ' + item.name.slice(9);
    for (const key in ITEM_SPRITES) {
      if (wandName.includes(key)) return ITEM_SPRITES[key];
    }
  }
  return getItemSpriteCoords(item.name, item.type);
};

// Type-glyph overlay sprites — the small 8x8 icons SPD draws on an *identified*
// ring/scroll/potion/wand slot (ItemSpriteSheet.Icons). [col, row] in the 16x8
// grid of item_icons.png. Sections: RINGS row 0, SCROLLS row 2, POTIONS row 5.
// Matched by name substring like ITEM_SPRITES. The remake's consumable taxonomy
// is currently thin, so only the items that have a concrete identity map here;
// add entries as more real subtypes land.
export const ITEM_GLYPHS = {
  "Health Potion": [1, 5],  // POTION_HEALING

  // Scroll icons — row 2 in item_icons.png (SPD Icons.SCROLLS row, cols 0-11).
  // Listed by distinguishing substring; 'getItemGlyphCoords' returns first match.
  "Magic Mapping":   [7, 2],   // SCROLL_MAGICMAP
  "Mirror Image":    [3, 2],   // SCROLL_MIRRORIMG
  "Remove Curse":    [2, 2],   // SCROLL_REMCURSE
  "Teleportation":   [5, 2],   // SCROLL_TELEPORT
  "Transmutation":  [11, 2],   // SCROLL_TRANSMUTE
  "Metamorphosis":  [11, 3],   // SCROLL_METAMORPH (exotic row)
  "Retribution":     [9, 2],   // SCROLL_RETRIB
  "Recharging":      [4, 2],   // SCROLL_RECHARGE
  "Identify":        [1, 2],   // SCROLL_IDENTIFY
  "Upgrade":         [0, 2],   // SCROLL_UPGRADE
  "Lullaby":         [6, 2],   // SCROLL_LULLABY
  "Terror":         [10, 2],   // SCROLL_TERROR
  "Rage":            [8, 2],   // SCROLL_RAGE
};

// Glyph cell for an item, or null when it has no type-glyph or isn't identified.
// SPD only shows the glyph once the item's type is known; the backend masks the
// real name of unidentified potions/scrolls, so a name match here implies known.
export const getItemGlyphCoords = (item) => {
  if (!item || !item.name) return null;
  if (!item.level_known) return null;
  for (const key in ITEM_GLYPHS) {
    if (item.name.includes(key)) return ITEM_GLYPHS[key];
  }
  return null;
};

// Map backend item kind strings to [col, row] in items.png for VFX (e.g. Transmuting animation).
// Covers the kinds that appear in transmutation targets; falls back to category prefixes.
const KIND_COORDS = {
  'melee_weapon':    [0, 7],   // Sword (tier 3 generic)
  'dagger':          [4, 6],
  'worn_shortsword': [0, 6],
  'bow':             [0, 9],
  'staff':           [5, 6],
  'missile_weapon':  [2, 9],
  'armor':           [1, 11],  // Leather
  'ring':            [0, 14],
  'artifact':        [0, 15],
  'wand_magic_missile':   [0, 13],
  'wand_fireblast':       [1, 13],
  'wand_frost':           [2, 13],
  'wand_lightning':       [3, 13],
  'wand_disintegration':  [4, 13],
  'wand_prismatic_light': [5, 13],
  'wand_corrosion':       [6, 13],
  'wand_living_earth':    [7, 13],
  'wand_blast_wave':      [8, 13],
  'wand_corruption':      [9, 13],
  'wand_warding':         [10, 13],
  'wand_regrowth':        [11, 13],
  'wand_transfusion':     [12, 13],
  'wand':                 [0, 13],
};

export function coordsForKind(kind) {
  if (!kind) return [0, 0];
  if (KIND_COORDS[kind]) return KIND_COORDS[kind];
  if (kind.startsWith('scroll_'))  return [0, 19];
  if (kind.startsWith('potion_'))  return [0, 22];
  if (kind.startsWith('ring_'))    return [0, 14];
  if (kind.startsWith('wand_'))    return [0, 13];
  if (kind.startsWith('armor'))    return [0, 11];
  if (kind.startsWith('seed'))     return [3, 24];
  return [0, 0];
}

export const fallbackTileMap = {
  1: { x: 0, y: 3 }, // Wall
  2: { x: 0, y: 0 }, // Floor
};

export const drawSpriteTile = (ctx, image, coords, x, y, flipX = false) => {
  if (!image || !coords) return;
  const sx = coords.x * (TILE_SIZE / TILE_SCALE);
  const sy = coords.y * (TILE_SIZE / TILE_SCALE);
  const dx = x * TILE_SIZE;
  const dy = y * TILE_SIZE;

  if (flipX) {
    ctx.save();
    ctx.translate(dx + TILE_SIZE, dy);
    ctx.scale(-1, 1);
    ctx.drawImage(
      image,
      sx,
      sy,
      TILE_SIZE / TILE_SCALE,
      TILE_SIZE / TILE_SCALE,
      0,
      0,
      TILE_SIZE,
      TILE_SIZE
    );
    ctx.restore();
    return;
  }

  ctx.drawImage(
    image,
    sx,
    sy,
    TILE_SIZE / TILE_SCALE,
    TILE_SIZE / TILE_SCALE,
    dx,
    dy,
    TILE_SIZE,
    TILE_SIZE
  );
};
