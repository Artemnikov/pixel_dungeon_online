import { TILE_SIZE, TILE_SCALE } from '../constants';

export const ITEM_SPRITES = {
  // Bombs — items.png BOMBS row (ItemSpriteSheet.BOMBS = xy(1,6) = idx 80, so
  // [col,row] = [idx%16, 5]). Listed before the generic "Bomb" so each enhanced
  // bomb matches its own sprite first (substring match returns the first hit).
  "Firebomb":         [2, 5],   // FIRE_BOMB
  "Frost Bomb":       [3, 5],   // FROST_BOMB
  "Regrowth Bomb":    [4, 5],   // REGROWTH_BOMB
  "Smoke Bomb":       [5, 5],   // SMOKE_BOMB
  "Flashbang":        [6, 5],   // FLASHBANG
  "Holy Bomb":        [7, 5],   // HOLY_BOMB
  "Woolly Bomb":      [8, 5],   // WOOLY_BOMB
  "Noisemaker":       [9, 5],   // NOISEMAKER
  "Arcane Bomb":     [10, 5],   // ARCANE_BOMB
  "Shrapnel Bomb":   [11, 5],   // SHRAPNEL_BOMB
  "Metal Shard":      [8, 29],  // SHARD (QUEST+8 = idx 472)
  "Bomb":             [0, 5],   // BOMB (generic — keep last of the bomb block)

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

  // Runestones — MUST precede generic "Stone" below (substring matching).
  "Stone of Aggression":     [0, 21],
  "Stone of Augmentation":   [1, 21],
  "Stone of Fear":           [2, 21],
  "Stone of Blast":          [3, 21],
  "Stone of Blink":          [4, 21],
  "Stone of Clairvoyance":   [5, 21],
  "Stone of Deep Sleep":     [6, 21],
  "Stone of Detect Magic":   [7, 21],
  "Stone of Enchantment":    [8, 21],
  "Stone of Flock":          [9, 21],
  "Stone of Intuition":      [10, 21],
  "Stone of Shock":          [11, 21],

  "Stone":            [3, 9],   // THROWING_STONE (MISSILE_WEP+3)

  // Armor (ARMOR = xy(1,12) = idx 176 -> row 11)
  "Cloth Armor":      [0, 11],  // ARMOR_CLOTH
  "Leather Vest":     [1, 11],  // ARMOR_LEATHER (ARMOR+1)
  "Leather":          [1, 11],
  "Broken Shield":    [2, 11],  // ARMOR_MAIL (ARMOR+2) — closest stand-in
  "Mail Armor":       [2, 11],
  "Scale Armor":      [3, 11],  // ARMOR_SCALE (ARMOR+3)
  "Plate Armor":      [4, 11],  // ARMOR_PLATE (ARMOR+4)
  "Rogue's Cloak":    [7, 11],  // ARMOR_ROGUE (ARMOR+7)

  "Dried Rose":       [4, 16],  // ARTIFACT_ROSE1
  "Holy Tome":        [7, 16],  // ARTIFACT_TOME (ARTIFACTS+23 = idx 263 = col 7, row 16)
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
  "Lost Backpack":    [1, 30],  // BACKPACK (same sprite as Bag; BAGS+1)

  // Consumables (generic first entry of each section)
  "Metamorphosis":    [5, 19],  // SCROLL_METAMORPH (SCROLLS+5 = idx 309)
  "Scroll":           [0, 19],  // SCROLLS = xy(1,20) = idx 304
  "Health Potion":    [0, 22],  // POTIONS = xy(1,23) = idx 352
  "Reviving Potion":  [0, 22],
  "Potion":           [0, 22],
  "Food":             [0, 27],  // FOOD = xy(1,28) = idx 432

  // Elixirs / brews (row 25 = BREWS xy(1,26) cols 0-5, ELIXIRS xy(9,26) cols 8-15).
  // Always known (no scrambled appearance), so name matching suffices.
  "Infernal Brew":    [0, 25],  // BREW_INFERNAL
  "Blizzard Brew":    [1, 25],  // BREW_BLIZZARD
  "Shocking Brew":    [2, 25],  // BREW_SHOCKING
  "Caustic Brew":     [3, 25],  // BREW_CAUSTIC
  "Aqua Brew":        [4, 25],  // BREW_AQUA
  "Unstable Brew":    [5, 25],  // BREW_UNSTABLE
  "Elixir of Honeyed Healing":  [8, 25],  // ELIXIR_HONEY
  "Elixir of Aquatic Rejuvenation": [9, 25],  // ELIXIR_AQUA
  "Elixir of Might":  [10, 25], // ELIXIR_MIGHT
  "Elixir of Dragon's Blood":   [11, 25], // ELIXIR_DRAGON
  "Elixir of Toxic Essence":    [12, 25], // ELIXIR_TOXIC
  "Elixir of Icy Touch":        [13, 25], // ELIXIR_ICY
  "Elixir of Arcane Armor":     [14, 25], // ELIXIR_ARCANE
  "Elixir of Feather Fall":     [15, 25], // ELIXIR_FEATHER

  // Seeds (SEEDS = xy(1,25) = idx 384 -> col0,row24; per-kind names like "Sungrass Seed")
  "Sungrass Seed":    [3, 24],  // SEED_SUNGRASS (SEEDS+3)
  "Earthroot Seed":   [8, 24],  // SEED_EARTHROOT (SEEDS+8)
  "Firebloom Seed":   [1, 24],  // SEED_FIREBLOOM (SEEDS+1)
  "Icecap Seed":      [4, 24],  // SEED_ICECAP (SEEDS+4)
  "Sorrowmoss Seed":  [6, 24],  // SEED_SORROWMOSS (SEEDS+6)
  "Dreamfoil Seed":   [7, 24],  // SEED_MAGEROYAL slot (SEEDS+7)
  "Mageroyal Seed":   [7, 24],  // SEED_MAGEROYAL (SEEDS+7)
  "Fadeleaf Seed":    [10, 24], // SEED_FADELEAF (SEEDS+10)
  "Rotberry Seed":    [0, 24],  // SEED_ROTBERRY (SEEDS+0)
  "Starflower Seed":  [9, 24],  // SEED_STARFLOWER (SEEDS+9)
  "Stormvine Seed":   [5, 24],  // SEED_STORMVINE (SEEDS+5)
  "Blindweed Seed":   [11, 24], // SEED_BLINDWEED (SEEDS+11)
  "Swiftthistle Seed":[2, 24],  // SEED_SWIFTTHISTLE (SEEDS+2)
  "Seed":             [3, 24],  // generic Seed / "Seed of Sunlight" -> SEED_SUNGRASS

  // Misc
  "Arcane Stylus":    [1, 3],   // STYLUS (MISC_CONSUMABLE+1 = idx 49 = col 1, row 3)
  "Tengu's Mask":     [11, 3],  // MASK (MISC_CONSUMABLE+11 = idx 59 = col 11, row 3 in items.png)
  "Goo Blob":         [7, 29],  // BLOB (QUEST+7, QUEST = xy(1,30) = idx 464)
  "dust of the corpse": [1, 29], // DUST (QUEST+1)
  "ceremonial candle":  [2, 29], // CANDLE (QUEST+2)
  "smoldering embers":  [3, 29], // EMBER (QUEST+3)
  "seed of the rotberry": [0, 24], // SEED_ROTBERRY (SEEDS+0)
  "Ankh":             [0, 3],   // ANKH (MISC_CONSUMABLE+0 = idx 48)
  "Dwarf Token":      [14, 29], // TOKEN (QUEST+6 = idx 470)
  "King's Crown":     [12, 3],  // CROWN (MISC_CONSUMABLE+12 = idx 60 = col 12, row 3)
  "Crystal Chest":    [6, 2],   // CRYSTAL_CHEST (CONTAINER+2 = idx 38) — before "Chest"
  "Locked Chest":     [5, 2],   // LOCKED_CHEST (CONTAINER+1 = idx 37) — before "Chest"
  "Chest":            [4, 2],   // CHEST (CONTAINER+0 = xy(5,3) = idx 36)
  // "Skeleton Key" MUST precede "Skeleton" below — substring matching would
  // otherwise match the bones-heap sprite for the Skeleton Key artifact.
  "Skeleton Key":     [8, 16],  // ARTIFACT_KEY (ARTIFACTS+24 = idx 264)
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
  "Energy Crystal":   [3, 1],   // ENERGY (UNCOLLECTIBLE+1 = idx 19)
  "Stewed Meat":      [2, 27],  // STEWED (FOOD+2 = idx 434)
  "Meat Pie":         [7, 27],  // MEAT_PIE (FOOD+7 = idx 439)
  "Mystery Meat":     [0, 27],  // MEAT (FOOD+0)
  "Phantom Meat":     [11, 27], // PHANTOM_MEAT (FOOD+11)
  "Chargrilled Meat": [1, 27],  // STEAK (FOOD+1)
  "Frozen Carpaccio": [4, 27],  // CARPACCIO (FOOD+4)
  "Small Ration":     [3, 27],  // OVERPRICED (FOOD+3)
  "Ration":           [5, 27],  // RATION (FOOD+5)
  "Pasty":            [6, 27],  // PASTY (FOOD+6)
  "Supply Ration":    [12, 27], // SUPPLY_RATION (FOOD+12)
  "Berry":            [10, 27], // BERRY (FOOD+10)
  "Blandfruit":       [8, 27],  // BLANDFRUIT (FOOD+8 = idx 440)
  "Sunfruit":         [8, 27],
  "Rotfruit":         [8, 27],
  "Earthfruit":       [8, 27],
  "Blindfruit":       [8, 27],
  "Firefruit":        [8, 27],
  "Icefruit":         [8, 27],
  "Fadefruit":        [8, 27],
  "Sorrowfruit":      [8, 27],
  "Stormfruit":       [8, 27],
  "Dreamfruit":       [8, 27],
  "Starfruit":        [8, 27],
  "Swiftfruit":       [8, 27],

  // Trinkets (TRINKETS section = xy(1,18) → [0,17], 17 trinkets + 1 catalyst)
  "Trinket Catalyst": [6, 4],   // TRINKET_CATA = MISC_CONSUMABLE+22 = [6,4]
  "Rat Skull":        [0, 17],  // TRINKETS+0
  "Parchment Scrap":  [1, 17],  // TRINKETS+1
  "Petrified Seed":   [2, 17],  // TRINKETS+2
  "Exotic Crystals":  [3, 17],  // TRINKETS+3
  "Mossy Clump":      [4, 17],  // TRINKETS+4
  "Sundial":          [5, 17],  // TRINKETS+5 (Dimensional Sundial)
  "Clover":           [6, 17],  // TRINKETS+6 (Thirteen-Leaf Clover)
  "Trap Mechanism":   [7, 17],  // TRINKETS+7
  "Mimic Tooth":      [8, 17],  // TRINKETS+8
  "Wondrous Resin":   [9, 17],  // TRINKETS+9
  "Eye of Newt":      [10, 17], // TRINKETS+10
  "Salt Cube":        [11, 17], // TRINKETS+11
  "Vial of Blood":    [12, 17], // TRINKETS+12
  "Shard of Oblivion":[13, 17], // TRINKETS+13
  "Chaotic Censer":   [14, 17], // TRINKETS+14
  "Ferret Tuft":      [15, 17], // TRINKETS+15
  "Cracked Spyglass": [0, 18],  // TRINKETS+16 = next row

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
  if (itemType === 'stylus')    return [1, 3];
  if (itemType === 'spell')     return [0, 19];
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
  if (itemType === 'trinket')   return [0, 17];  // RAT_SKULL (generic trinket fallback)
  if (itemType === 'trinket_catalyst') return [6, 4];
  if (itemType === 'runestone') return [0, 21];
  if (itemType === 'dewdrop')   return [5, 1];   // DEWDROP
  if (itemType === 'grave')     return [0, 2];   // BONES
  if (itemType === 'ankh')      return [0, 3];   // ANKH (MISC_CONSUMABLE+0)
  if (itemType === 'lost_backpack') return [1, 30]; // BACKPACK (BAGS+1)
  if (itemType === 'bomb')      return [0, 5];   // BOMB (generic)
  if (itemType === 'waterskin') return [0, 30];  // WATERSKIN (BAGS+0)
  if (itemType === 'amulet')    return [14, 4];  // AMULET (MISC_CONSUMABLE+13)
  if (itemType === 'energy_crystal') return [3, 1]; // ENERGY (UNCOLLECTIBLE+1)
  if (itemType === 'bag')       return [1, 30];  // BACKPACK (BAGS+1)
  if (itemType === 'chest')     return [4, 2];   // CHEST (CONTAINER+0)
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
  ['stewed_meat', 'food'],
  ['meat_pie', 'food'],
  ['phantom_meat', 'food'],
  ['supply_ration', 'food'],
  ['frozen_carpaccio', 'food'],
  ['dewdrop', 'dewdrop'],
  ['gold', 'gold'],
  ['wand', 'wand'],
  ['rat_skull', 'trinket'],
  ['parchment_scrap', 'trinket'],
  ['petrified_seed', 'trinket'],
  ['exotic_crystals', 'trinket'],
  ['mossy_clump', 'trinket'],
  ['dimensional_sundial', 'trinket'],
  ['thirteen_leaf_clover', 'trinket'],
  ['trap_mechanism', 'trinket'],
  ['mimic_tooth', 'trinket'],
  ['wondrous_resin', 'trinket'],
  ['eye_of_newt', 'trinket'],
  ['salt_cube', 'trinket'],
  ['vial_of_blood', 'trinket'],
  ['shard_of_oblivion', 'trinket'],
  ['chaotic_censer', 'trinket'],
  ['ferret_tuft', 'trinket'],
  ['cracked_spyglass', 'trinket'],
  ['trinket_catalyst', 'trinket_catalyst'],
  ['stone_augmentation', 'runestone'],
  ['stone_enchantment', 'runestone'],
  ['stone_intuition', 'runestone'],
  ['stone_detect_magic', 'runestone'],
  ['stone_fear', 'runestone'],
  ['stone_shock', 'runestone'],
  ['stone_flock', 'runestone'],
  ['stone_aggression', 'runestone'],
  ['stone_clairvoyance', 'runestone'],
  ['stone_deep_sleep', 'runestone'],
  ['stone_blink', 'runestone'],
  ['stone_blast', 'runestone'],
  ['stone_', 'runestone'],
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
// grid of item_icons.png. Sections: RINGS row 0, SCROLLS row 2, EXOTIC_SCROLLS
// row 3, POTIONS row 5, EXOTIC_POTIONS row 6. Matched by name substring like
// ITEM_SPRITES (first key that matches wins), so keys are distinguishing
// substrings of the identified item name. Remake-only items without an icon
// cell (Reviving/Fury potions, elixirs, brews) intentionally have no entry.
export const ITEM_GLYPHS = {
  // Potion icons — row 5 in item_icons.png (SPD Icons.POTIONS row, cols 0-11).
  "Potion of Strength":      [0, 5],   // POTION_STRENGTH
  "Health Potion":           [1, 5],   // POTION_HEALING
  "Potion of Mind Vision":   [2, 5],   // POTION_MINDVIS
  "Potion of Frost":         [3, 5],   // POTION_FROST
  "Potion of Liquid Flame":  [4, 5],   // POTION_LIQFLAME
  "Potion of Toxic Gas":     [5, 5],   // POTION_TOXICGAS
  "Potion of Haste":         [6, 5],   // POTION_HASTE
  "Potion of Invisibility":  [7, 5],   // POTION_INVIS
  "Potion of Levitation":    [8, 5],   // POTION_LEVITATE
  "Potion of Paralytic Gas": [9, 5],   // POTION_PARAGAS
  "Potion of Purity":       [10, 5],   // POTION_PURITY
  "Potion of Experience":   [11, 5],   // POTION_EXP

  // Exotic potion icons — row 6 (SPD Icons.EXOTIC_POTIONS row, cols 0-11).
  "Potion of Mastery":            [0, 6],  // POTION_MASTERY
  "Potion of Shielding":          [1, 6],  // POTION_SHIELDING
  "Potion of Magical Sight":      [2, 6],  // POTION_MAGISIGHT
  "Potion of Snap Freeze":        [3, 6],  // POTION_SNAPFREEZ
  "Potion of Dragon's Breath":    [4, 6],  // POTION_DRGBREATH
  "Potion of Corrosive Gas":      [5, 6],  // POTION_CORROGAS
  "Potion of Stamina":            [6, 6],  // POTION_STAMINA
  "Potion of Shrouding Fog":      [7, 6],  // POTION_SHROUDFOG
  "Potion of Storm Clouds":       [8, 6],  // POTION_STRMCLOUD
  "Potion of Earthen Armor":      [9, 6],  // POTION_EARTHARMR
  "Potion of Cleansing":         [10, 6],  // POTION_CLEANSE
  "Potion of Divine Inspiration":[11, 6],  // POTION_DIVINE

  // Scroll icons — row 2 in item_icons.png (SPD Icons.SCROLLS row, cols 0-11).
  // Listed by distinguishing substring; 'getItemGlyphCoords' returns first match.
  "Upgrade":         [0, 2],   // SCROLL_UPGRADE
  "Identify":        [1, 2],   // SCROLL_IDENTIFY
  "Remove Curse":    [2, 2],   // SCROLL_REMCURSE
  "Mirror Image":    [3, 2],   // SCROLL_MIRRORIMG
  "Recharging":      [4, 2],   // SCROLL_RECHARGE
  "Teleportation":   [5, 2],   // SCROLL_TELEPORT
  "Lullaby":         [6, 2],   // SCROLL_LULLABY
  "Magic Mapping":   [7, 2],   // SCROLL_MAGICMAP
  "Rage":            [8, 2],   // SCROLL_RAGE
  "Retribution":     [9, 2],   // SCROLL_RETRIB
  "Terror":         [10, 2],   // SCROLL_TERROR
  "Transmutation":  [11, 2],   // SCROLL_TRANSMUTE

  // Exotic scroll icons — row 3 (SPD Icons.EXOTIC_SCROLLS row, cols 0-11).
  // "Enchantment" covers both "Scroll of Enchantment" and the "Exotic Scroll of
  // Enchantment" variant — both are SCROLL_ENCHANT.
  "Enchantment":     [0, 3],   // SCROLL_ENCHANT
  "Divination":      [1, 3],   // SCROLL_DIVINATE
  "Anti-Magic":      [2, 3],   // SCROLL_ANTIMAGIC
  "Prismatic Image": [3, 3],   // SCROLL_PRISIMG
  "Mystical Energy": [4, 3],   // SCROLL_MYSTENRG
  "Passage":         [5, 3],   // SCROLL_PASSAGE
  "Siren's Song":    [6, 3],   // SCROLL_SIREN
  "Foresight":       [7, 3],   // SCROLL_FORESIGHT
  "Challenge":       [8, 3],   // SCROLL_CHALLENGE
  "Psionic Blast":   [9, 3],   // SCROLL_PSIBLAST
  "Dread":          [10, 3],   // SCROLL_DREAD
  "Metamorphosis":  [11, 3],   // SCROLL_METAMORPH
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
  'armor':           [1, 11],  // generic → Leather
  'cloth_armor':     [0, 11],
  'leather_armor':   [1, 11],
  'mail_armor':      [2, 11],
  'scale_armor':     [3, 11],
  'plate_armor':     [4, 11],
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
  'arcane_stylus':        [1, 3],
  'magical_infusion':     [0, 19],
  'trinket_catalyst':     [6, 4],
  'rat_skull':            [0, 17],
  'parchment_scrap':      [1, 17],
  'petrified_seed':       [2, 17],
  'exotic_crystals':      [3, 17],
  'mossy_clump':          [4, 17],
  'dimensional_sundial':  [5, 17],
  'thirteen_leaf_clover': [6, 17],
  'trap_mechanism':       [7, 17],
  'mimic_tooth':          [8, 17],
  'wondrous_resin':       [9, 17],
  'eye_of_newt':          [10, 17],
  'salt_cube':            [11, 17],
  'vial_of_blood':        [12, 17],
  'shard_of_oblivion':    [13, 17],
  'chaotic_censer':       [14, 17],
  'ferret_tuft':          [15, 17],
  'cracked_spyglass':     [0, 18],
  'energy_crystal':       [3, 1],
  'stewed_meat':          [2, 27],
  'meat_pie':             [7, 27],
  'mystery_meat':         [0, 27],
  'phantom_meat':         [11, 27],
  'chargrilled_meat':     [1, 27],
  'frozen_carpaccio':     [4, 27],
  'small_ration':         [3, 27],
  'ration':               [5, 27],
  'pasty':                [6, 27],
  'supply_ration':        [12, 27],
  'berry':                [10, 27],
};

export function coordsForKind(kind) {
  if (!kind) return [0, 0];
  if (KIND_COORDS[kind]) return KIND_COORDS[kind];
  if (kind.startsWith('scroll_'))  return [0, 19];
  if (kind.startsWith('potion_'))  return [0, 22];
  if (kind.startsWith('elixir_')) return [0, 22];
  if (kind.endsWith('_brew'))     return [0, 22];
  if (kind.startsWith('ring_'))    return [0, 14];
  if (kind.startsWith('wand_'))    return [0, 13];
  if (kind.startsWith('armor'))    return [0, 11];
  if (kind.startsWith('seed'))     return [3, 24];
  if (kind === 'trinket_catalyst') return [6, 4];
  if (kind.startsWith('trinket_')) return [0, 17];
  if (kind.startsWith('stone_'))   return [0, 21];
  if (kind === 'arcane_stylus')    return [1, 3];
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
