# Warrior Talent Tree (from original SPD source)

Source: `shattered-pixel-dungeon/core/.../actors/hero/Talent.java`,
`actors/hero/abilities/warrior/*`, `actors/hero/HeroClass.java`,
`items/BrokenSeal.java`, `actors/buffs/Berserk.java`, `actors/buffs/Combo.java`,
strings in `core/src/main/assets/messages/actors/actors.properties`.

## Class basics

- Starting kit: Worn Shortsword, Throwing Stones (quickslot 0), Potion of
  Healing identified, Scroll of Rage identified. Starting armor has a
  **Broken Seal** affixed (`HeroClass.initWarrior`).
- STR starts at 10 (same as all classes); Warrior talents can boost it.
- Subclasses: **Berserker** / **Gladiator**, chosen via the Tome of Mastery
  (`TengusMask` → `WndChooseSubclass`), one-time pick, available once T3
  talents unlock (hero level 13).
- Armor abilities (pick one, each has its own T4 talents):
  **Heroic Leap**, **Shockwave**, **Endure**.

### Broken Seal (passive, all Warriors)

- Affixed to armor; can be moved between armors and carries **one upgrade**
  (and, with Runic Transference, glyphs) with it.
- When the Warrior is about to take damage that would bring him to ≤50% HP,
  the seal grants instant shielding (`WarriorShield` buff).
  - `maxShield = 3 + 2*armorTier + pointsInTalent(IRON_WILL)`.
  - Shield doesn't decay over time, but ends if no enemies are nearby for a
    few turns; unused shield on end reduces cooldown (up to 50%).
  - Base cooldown after triggering: 150 turns (can go negative via
    Lethal Defense, down to -150 = instant re-trigger).

## Talent tier thresholds

`tierLevelThresholds = {0, 2, 7, 13, 21, 31}` → T1 unlocks at hero level 2,
T2 at 7, T3 at 13, T4 at 21. Each talent point is spent individually; T1/T2
talents max at +2, T3/T4 talents max at +3/+4 respectively (see `maxPoints`).

---

## Tier 1 (level 2) — pick from 4

| Talent | +1 | +2 |
|---|---|---|
| **Hearty Meal** | Eating food heals 4 HP if at/below 33% HP | heals 6 HP |
| **Veteran's Intuition** | ID weapons 1.75x faster, armor 2.5x faster | weapons 2.5x faster, armor IDs on equip |
| **Provoked Anger** | When a shield buff on the Warrior is broken by damage, next physical attack deals +3 bonus dmg | +5 bonus dmg |
| **Iron Will** | Broken Seal max shield +1 | +2 (if a non-Warrior gains this via metamorphosis, grants a passive 1/2-shield version of the seal effect) |

## Tier 2 (level 7) — pick from 5

| Talent | +1 | +2 |
|---|---|---|
| **Iron Stomach** | Eating food takes 1 turn, 75% dmg resistance while eating | 100% dmg resistance while eating |
| **Liquid Willpower** | Drinking/throwing a potion/brew/elixir grants shield = 6.5% max HP (doubled for Potion of Strength/Experience and crafted items requiring them) | 10% max HP |
| **Runic Transference** | Broken Seal can also transfer regular glyphs (must've been applied while seal attached) | also transfers powerful & curse glyphs |
| **Lethal Momentum** | Killing blow with a physical weapon has 67% chance to take 0 turns | 100% chance |
| **Improvised Projectiles** | Throwing any non-thrown-weapon item blinds target for 2 turns (50-turn cooldown) | blinds for 3 turns |

## Tier 3 (level 13) — class-shared pair + subclass-specific trio

### Shared T3 (any Warrior, max +3)

| Talent | +1 | +2 | +3 |
|---|---|---|---|
| **Hold Fast** | Waiting grants 1-2 armor and slows combo/shield decay by 50% until moving | 2-4 armor, 75% slow | 3-6 armor, 100% slow (no decay while still) |
| **Strongman** | STR +8% (rounded down) | +13% | +18% |

### Berserker-only T3

Pick after choosing Berserker subclass.

| Talent | +1 | +2 | +3 |
|---|---|---|---|
| **Endless Rage** | Max rage 116% | 133% | 150% — each % rage above 100 adds +1% berserk shield and -1% cooldown, but dmg bonus caps at +50% |
| **Deathless Fury** | Berserk auto-triggers on lethal hit if rage ≥100%, then 3-hero-level cooldown | 2-level cooldown | 1-level cooldown (hero still dies if HP hits 0 when berserk ends) |
| **Enraged Catalyst** | Weapon enchants/curses trigger up to 15% more often, scaling with rage to 100% rage | up to 30% more | up to 45% more |

### Gladiator-only T3

Pick after choosing Gladiator subclass.

| Talent | +1 | +2 | +3 |
|---|---|---|---|
| **Cleave** | Bonus time on kill increased from 15 → 30 turns | → 45 turns | → 60 turns |
| **Lethal Defense** | Killing with a combo move reduces Broken Seal shield cooldown by 50 turns | by 100 | by 150 (cooldown can go to -150, i.e. instant) |
| **Enhanced Combo** | Combo ≥7: Clobber knockback range 3, inflicts vertigo, can knock into pits | also: Combo ≥9 lets Parry hit multiple attacks | also: can leap up to combo/3 tiles using Slam/Crush/Fury |

## Tier 4 (level 21) — tied to chosen armor ability (max +4 each)

### Heroic Leap talents

| Talent | +1 | +2 | +3 | +4 |
|---|---|---|---|---|
| **Body Slam** | On landing, adjacent enemies take 1-4 + 25% of DR-roll dmg | 2-8 +50% | 3-12 +75% | 4-16 +100% |
| **Impact Wave** | On landing, adjacent enemies knocked back 2 tiles, 25% chance Vulnerable 5 turns | 3 tiles, 50% | 4 tiles, 75% | 5 tiles, 100% |
| **Double Jump** | A 2nd leap within 3 turns costs 16% less charge | 30% less | 40% less | 50% less |

### Shockwave talents

| Talent | +1 | +2 | +3 | +4 |
|---|---|---|---|---|
| **Expanding Wave** | Range 5→6, cone 60°→75° | range 7, 90° | range 8, 105° | range 9, 120° |
| **Striking Wave** | 30% chance shockwave hits also proc on-hit effects (enchants/combo) | 60% | 90% | 100% + enchants get +20% power |
| **Shock Force** | +20% dmg, 25% chance to stun instead of cripple | +40%/50% | +60%/75% | +80%/100% |

### Endure talents

| Talent | +1 | +2 | +3 | +4 |
|---|---|---|---|---|
| **Sustained Retribution** | Post-endure bonus dmg 115% spread over 2 hits (vs base 100% in 1 hit) | 130% over 3 | 145% over 4 | 160% over 5 |
| **Shrug It Off** | Dmg reduction while enduring 50%→60% | →68% | →74% | →80% |
| **Even The Odds** | +5% bonus dmg per enemy within 2 tiles when enduring ends | +10% | +15% | +20% |

### Universal T4 — Heroic Energy

Available regardless of armor ability.

| +1 | +2 | +3 | +4 |
|---|---|---|---|
| Armor ability charge cost -12% | -23% | -32% | -40% |

---

## Armor abilities (base behavior, before T4 talents)

- **Heroic Leap** (`baseChargeUse = 35`): leap to a targeted tile (blocked by
  `hero.rooted`); on landing triggers a blast-wave knockback at the
  destination and dispels Invisibility. Body Slam / Impact Wave / Double Jump
  hook into the landing.
- **Shockwave** (`baseChargeUse = 35`): conical AOE (base 5 tiles, 60°) dealing
  `5 + scalingStr` to `10 + 2*scalingStr` damage (`scalingStr = STR-10`),
  cripples survivors for 5 turns. Striking Wave/Shock Force/Expanding Wave
  modify it; on a Gladiator, procs that land add Combo.
- **Endure** (`baseChargeUse = 50`): for 3 turns take half damage from all
  sources (applied before armor's resist), accumulating `damageBonus = sum(damage taken)/2`
  while enduring. If the Warrior has Combo, using Endure adds 3 turns to the
  combo timer. After enduring, the next hit(s) within 10 turns deal the
  accumulated bonus damage (split across hits per Sustained Retribution,
  scaled by Even The Odds based on nearby enemies).

---

## Subclass mechanics

### Berserker (`Berserk` buff)

- Builds **Rage** from physical damage taken (including damage blocked by
  armor). Rage decays over time, slower at low HP.
- Rage grants up to **+50% damage** (scales with rage %, capped at 100% rage
  unless Endless Rage raises the cap to 116/133/150%).
- At 100% rage, Berserk can trigger: grants shielding based on armor level and
  missing HP, **+50% damage** while active, and the shield decays every turn —
  when it hits 0, Berserk ends.
- After Berserk ends, the Berserker must **recover** (no rage gain) before
  building rage again.
- T3 talents: Endless Rage (higher rage cap + scaling bonuses), Deathless Fury
  (auto-Berserk on lethal hit, with a level-based cooldown), Enraged Catalyst
  (rage increases weapon enchant/curse proc rate).

### Gladiator (`Combo` buff)

- Builds **Combo** by +1 per successful melee/thrown-weapon hit. Resets to 0
  if no successful hit within 5 turns (15 turns after a kill — extended by
  Cleave to 30/45/60). While Combo is active, Broken Seal shielding doesn't
  decay.
- Combo unlocks guaranteed-hit special attacks at thresholds:
  - **2** — knockback (Clobber), preserves combo
  - **4** — damage scaled by armor (Crush)
  - **6** — Parry, preserves combo
  - **8** — Slam: damage target + nearby enemies
  - **10** — Fury: attack once per combo point
  - Each move usable once per combo "session"; some preserve combo, some
    consume/reset it.
- T3 talents: Lethal Defense (combo kills reduce Broken Seal cooldown),
  Enhanced Combo (boosts Clobber/Parry/Slam/Crush/Fury at high combo).

---

## Open items for the remake

- Verify exact dungeon depth/quest where Tome of Mastery (subclass choice)
  is granted — not pinned down from `TengusMask.java` alone.
- `StrikingWaveTracker` (Talent.java) referenced by Shockwave at +4 Striking
  Wave — check its full effect if Shockwave is implemented.
