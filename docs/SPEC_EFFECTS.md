# Effects Spec — Re-implementation Reference

## Architecture Overview

Three visual paradigms exist for projectile/beam effects:

1. **Traveling bolts** — `MagicMissile` (emitter moves caster→target at 200px/s)
2. **Instant beams** — `Beam` subclasses (appear instantly, fade over duration)
3. **Lightning arcs** — `Lightning` group (jittering multi-segment arcs)

Area effects use **BlobEmitter** (per-cell particle emission from `Blob.cur[]` grid).

All additive-blended effects use `Blending.setLightMode()` → `Blending.setNormalMode()`.

---

## 1. LIGHTNING / ELECTRICAL EFFECTS

### 1.1 Lightning Bolt (`Lightning.java`)

**Duration:** 0.3s fixed (`DURATION`)

**Structure:** `Group` containing `Arc` objects. Each `Arc` is a `Group` with 2 `Image` children.

**Texture:** `effects.png` UV rect `(16, 0, 32, 8)` — a 16×8 px white bolt shape. Accessed via `Effects.get(Effects.Type.LIGHTNING)`.

**Arc geometry (recalculated each frame):**
- midpoint `x2 = (start.x + end.x) / 2 + Random.Float(-4, +4)`
- midpoint `y2 = (start.y + end.y) / 2 + Random.Float(-4, +4)`
- `arc1`: stretched/rotated from start → midpoint
- `arc2`: stretched/rotated from midpoint → end
- Both arc images: `origin.set(0, height/2)` (pivot at left edge center-Y)
- `scale.x = distance / arc.width`, `angle = atan2(dy, dx) * (180/π)`

**Alpha:** `arc.am = life / DURATION` — fades 1.0 → 0.0 over lifetime

**Blending:** Additive (`Blending.setLightMode()`)

**Callback:** fires when `life <= 0` (not used by WandOfLightning — callback is null there, damage happens immediately)

### 1.2 Spark Particles (`SparkParticle.java`)

**Base:** `PixelParticle` (white by default, 2px base size)

**Defaults:** `acc.set(0, +50)` — slight downward gravity

**3 factory types:**

| Factory | Lifespan | Speed | Accel | Uses |
|---------|----------|-------|-------|------|
| `FACTORY` | 0.5–1.0s | random dir, 20–40 | (+0, +50) | Moving sparks, Electricity blob, on-hit bursts |
| `STATIC` | 0.25–0.5s | (0, 0) | (0, 0) | Static hovering sparks |
| `resetAttracting()` | 0.2–0.35s | toward target at 3 tiles/s | (0, 0) | Warding, attracting sparks |

**Size:** spawned at 5px, each frame `size(Random.Float(size * left / lifespan))` — jittery shrinking.

**Blending:** All use `lightMode() = true` (additive)

**Used by:** Electricity blob (pour 0.05f), WandOfLightning on-hit burst (3), Shocking enchantment, Pylon, Tengu ShockerBlob, ShockElemental, DM100, StoneOfShock (3), ElementalBlast SPARK_CONE (0.03f rate, size 10)

### 1.3 Energy Particles (`EnergyParticle.java`)

- Color: `0xFFFFAA` (warm yellow)
- Lifespan: 1.0s
- Speed: random dir, 24–32
- Alpha: peaks mid-life (fade in then out)
- Size: `Random.Float(5 * left / lifespan)`
- Used by: StoneOfShock (10), Potential glyph (10)

### 1.4 Electricity Blob (`Electricity.java`)

**Propagation:** Spreads through **water cells only** via `PathFinder.NEIGHBOURS4` (cardinal directions). Recursive — maintains same power level as source.

**Act priority:** `MOB_PRIO - 1` (acts after mobs — gives chance to resist paralysis)

**Per-tick effects per cell:**
- Applies `Paralysis` buff (duration = `cur[cell]` value)
- Damage only on odd ticks (`cur[cell] % 2 == 1`): `Random.Float(2 + scalingDepth()/5)` per tick
- Charges wands/staves in heaps: `gainCharge(0.333f)` per tick
- Decrements: `off[cell] = cur[cell] - 1`

**Visual:** `emitter.start(SparkParticle.FACTORY, 0.05f, 0)`

### 1.5 Wand of Lightning — Chain Mechanics

**Arcing (recursive):**
- Range: 1 tile (2 if target in water; +1 if user has `LightningCharge`)
- Builds distance map, finds all chars within range
- Hero: only zapped if **adjacent** (distance == 1)
- Recurses: from each new hit, arc() again
- `DwarfKing` check: sets `qualifiedForBossChallengeBadge = false`

**Damage multiplier:** `0.4 + (0.6 / affected.size())` — per-target falloff. If **main target in water**: multiplier = 1.0 for ALL targets.

**Self-damage:** halved (`* 0.5f`)

**Staff melee proc:** charges `LightningCharge` (25%→40%→50% at lvl0→1→2), burst 10 SparkParticles, flash, LIGHTNING sound.

**Staff fx particles:** white `0xFFFFFF`, alpha 0.6, lifespan 0.6s, accelerated downward.

**Audio:** `sounds/lightning.mp3`

### 1.6 Shocking Enchantment

- 33% proc chance
- Chain radius: 2 tiles from defender (range = 2, or 1 if defender in water and not flying)
- Chain damage: 50% of weapon damage to all enemies except original defender
- Visual: 3 SparkParticles burst, flash, `Lightning(arcs, null)`, LIGHTNING sound
- Glow: white 50% alpha

### 1.7 All Lightning Sound Users

`sounds/lightning.mp3`: WandOfLightning, Shocking enchantment, ShockingDart, Pylon, ShockElemental, Tengu, DM300, StoneOfShock, ShockingBrew, ShockingTrap, StormTrap, CursedWand, FlashBang, WildEnergy, ReclaimTrap, DM100Sprite, CavesBossLevel, AlchemyScene

**Screen shake:** `PixelScene.shake(2, 0.3f)` when hero hit by lightning.

---

## 2. FIRE EFFECTS

### 2.1 Flame Particle (`FlameParticle.java`)

**Base:** `PixelParticle.Shrinking` (size shrinks proportionally over life)

**Color:** `0xEE7722` (orange-red)

**Lifespan:** 0.6s

**Acceleration:** `(0, -80)` — strong upward float

**Size:** 4px at spawn

**Speed:** `(0, 0)` — no initial velocity, only acceleration drift

**Alpha:** `am = p > 0.8f ? (1-p)*5 : 1` — fades in during first 20% (0→1), then fully opaque

**Blending:** `lightMode() = true` (additive)

**Used by:** Fire blob emitter (pour 0.03f), CharSprite BURNING state (0.06f), MagicMissile FIRE/CONE (0.01f/0.03f, size 4/10), Firebomb burst, Firebloom burst (5), Burning/Blazing Trap burst, WandOfFireblast visual, Torch ambience (0.15f), PotionOfDragonsBreath

### 2.2 Elmo Particle (`ElmoParticle.java`) — Green Fire

**Same as FlameParticle except:**
- Color: `0x22EE66` (green)
- Used for: burnt item heaps (`Heap.burnFX`), Eternal Fire, Newborn Fire Elemental, Vault Flame Traps, cursed wand `MagicMissile.ELMO`

### 2.3 Ground Fire Blob (`Fire.java`)

**Act priority:** `BLOB_PRIO`

**Initial intensity:** 4 ticks when spreading

**Decay:** `cur[cell] - 1` per evolution tick

**Propagation (per cell):**
- If `cur[cell] > 0`: burn cell, decrement. If reaches 0 on flamable tile: destroy tile.
- If `cur[cell] == 0` AND flamable AND any cardinal neighbor has fire: seed fire (intensity 4).
- Blocked by `Freezing` blob on same cell.

**`burn(pos)` static method:**
- Char → `Buff.affect(Burning.class).reignite(ch)` (if not immune)
- Heap → `heap.burn()`
- Plant → `plant.wither()`

**Flamable tiles:** Barricades, bookshelves, grass (`Dungeon.level.flamable[]`)

**Visual:** `emitter.pour(FlameParticle.FACTORY, 0.03f)`

### 2.4 Burning Buff (`Burning.java`)

**Duration:** 8s default (8 turns)

**Damage per turn:** `Random.NormalIntRange(1, 3 + scalingDepth()/4)`

**Water extinguishes:** If standing in water AND not flying: detaches Burning.

**Ground ignition:** Each act, if flamable cell + no Fire blob: seeds Fire (intensity 4).

**Hero item burning (after 4+ turns):** `Random.Int(3) < (burnIncrement - 3)` — burns Scroll/MysteryMeat/FrozenCarpaccio. Meat → ChargrilledMeat.

**Chill removal:** Detaches `Chill` on attach and each act.

**On attach to sprite:** `target.sprite.add(CharSprite.State.BURNING)` — starts emitter pouring `FlameParticle.FACTORY` at 0.06f, plays `sounds/burning.mp3` once.

**On detach:** `target.sprite.remove(CharSprite.State.BURNING)` — stops emitter.

### 2.5 FireImbue Buff (Positive)

**Duration:** 50s (from Elixir of Dragon's Blood)

**Effects:**
- Immunity to Burning
- 50% chance on attack to ignite enemy with Burning
- Enemy emits 2 FlameParticles burst on proc
- Each act: standing on GRASS converts to EMBERS

### 2.6 Inferno Blob (Superior Fire)

- Clears regular Fire and Freezing on same cells
- Mutual annihilation with Blizzard
- Calls `Fire.burn()` on its cells
- Destroys flamable tiles
- Spreads to adjacent flamable cells, seeding regular Fire (intensity 4)
- Visual: `Speck.INFERNO` at 0.4f rate (orange spinning specks)

### 2.7 Sacrificial Fire

- Blue flame: `SacrificialParticle` (color `0x4488EE`)
- Volume: `6 + depth * 4`
- Marks chars in 3×3 area with `Marked` buff (duration 2f)
- When marked char dies: drains fire volume as EXP; when depleted → reward

### 2.8 Fire Audio

`sounds/burning.mp3`: played once on Burning state add, Fire blob evolution, heap burning, WandOfFireblast cast, Burning/Blazing trap, Firebomb, Liquid Flame potion, Sacrificial Fire, Dragon's Blood elixir, Tengu FireBlob, etc.

### 2.9 Burning DPS Formula Reference

| Depth | Min Dmg | Max Dmg |
|-------|---------|---------|
| 1-4   | 1       | 3       |
| 5-9   | 1       | 4       |
| 10-14 | 1       | 5       |
| 15-19 | 1       | 6       |
| 20-24 | 1       | 8       |
| 25+   | 1       | 9       |

Formula: `Random.NormalIntRange(1, 3 + scalingDepth()/4)`

---

## 3. WAND ZAP / MAGIC BOLT EFFECTS

### 3.1 Base Wand FX (`Wand.fx()`)

Default implementation (line 440):
```java
MagicMissile.boltFromChar(
    curUser.sprite.parent,
    MagicMissile.MAGIC_MISSILE,   // white bolt
    curUser.sprite,
    bolt.collisionPos,
    callback);
Sample.INSTANCE.play(Assets.Sounds.ZAP);
```

Each wand **overrides `fx()`** to customize visual+audio.

### 3.2 MagicMissile — Traveling Bolt System

**Speed:** constant 200px/s

**`boltFromChar()`:** aims at `sprite.center()` for start, `sprite.destinationCenter()` if target cell has a Char (accounts for sprite height).

**Cannot be frozen:** `isFrozen() → false`

**Particle types and visual properties:**

| Type ID | Constant | Particle Color | Size | Life | Notes |
|---------|----------|----------------|------|------|-------|
| 0 | MAGIC_MISSILE | White | 4 | 0.4s | Basic white bolt |
| 1 | FROST | 0x88CCFF light blue | — | 0.5s | Ice bolt |
| 2 | FIRE | 0xEE7722 orange | 4 | 0.6s | Flame particles, upward float |
| 3 | CORROSION | Grey→orange transitioning | 3 | 0.6s | Acid cloud bolt |
| 4 | FOLIAGE | Green 0x004400→0x88CC44 | 4 | 1.2s | Leaf bolt |
| 5 | FORCE | Brown 0x664422 | — | 0.6s | Accelerates toward emitter center |
| 6 | BEACON | White 0xFFFFFF | — | 0.5s | 8 orbiting particles |
| 7 | SHADOW | Dark purple→black | 4 | 0.5s | Corruption bolt |
| 8 | RAINBOW | Random color | 4 | 0.5s | Cursed wand default |
| 9 | EARTH | Brown 0x805500 (rare yellow 0xFFF266) | 4 | 0.5s | Gravity (+40 Y accel) |
| 10 | WARD | Purple 0x8822FF | 4 | 0.6s | Shrinking |
| 11 | SHAMAN_RED | Red 0xFF4D4D→0x801A1A | 2 | 0.6s | DM-100 shaman |
| 12 | SHAMAN_BLUE | Blue 0x6699FF→0x1A3C80 | 2 | 0.6s | DM-100 shaman |
| 13 | SHAMAN_PURPLE | Purple 0xBB33FF→0x5E1A80 | 2 | 0.6s | DM-100 shaman |
| 14 | ELMO | Green 0x22EE66 | 5 | 0.6s | Green fire, upward float |
| 15 | POISON | Purple→green transitioning | 3 | 0.6s | Poison bolt |
| 16 | LIGHT_MISSILE | Yellow-tinted white (1,1,0.25) | 4 | 0.4s | Golden bolt |

**Cone variants** (ID + 100): Same particle, size=10, emission rate=0.03 (vs 0.01 for regular bolts). Used for AOE cone attacks.

**Extra cone types (100+ range only):**
- PURPLE_CONE (111): PurpleParticle.MISSILE
- SPARK_CONE (112): SparkParticle.FACTORY
- BLOOD_CONE (113): BloodParticle.FACTORY

### 3.3 Beam Effects (`Beam.java`)

**All instant** — no travel time. Appear and fade over duration.

| Subclass | Texture UV | Duration | Used By |
|----------|-----------|----------|---------|
| `DeathRay` | (16,16)→(32,24) | 0.5s | WandOfDisintegration |
| `LightRay` | (16,23)→(32,31) | 1.0s | WandOfPrismaticLight |
| `SunRay` | Same as LightRay, tinted (1,1,0.25,1) | 1.0s | PrismaticLight vs undead |
| `HealthRay` | (16,30)→(32,38) | 0.75s | WandOfTransfusion |

**Rendering:**
- Origin: `(0, height/2)` — pivot at left edge center-Y
- Rotated via `atan2(dy, dx)`, scaled horizontally to match distance
- Alpha: `p = timeLeft/duration` (fades from 1→0)
- Vertical shrink: `scale.set(scale.x, p)` (shrinks toward center)
- Blending: additive
- Audio: `sounds/ray.mp3` (not ZAP)

### 3.4 Per-Wand Audio+Visual Summary

| Wand | FX System | Missile Type | Sound | On-Hit Visual |
|------|-----------|-------------|-------|---------------|
| MagicMissile | Bolt | MAGIC_MISSILE (white) | ZAP | White burst `sprite.burst(0xFFFFFFFF, lvl/2+2)` |
| Fireblast | Cone | FIRE_CONE | ZAP + BURNING | (fire applied via Burning buff) |
| Frost | Bolt | FROST (blue) | ZAP + HIT_MAGIC(1.1×) | Light blue burst `0xFF99CCFF` |
| Lightning | Lightning arcs | — | LIGHTNING | 3 SparkParticles per target, screen shake |
| Disintegration | Beam | DeathRay (purple) | RAY | PurpleParticle.BURST along path |
| PrismaticLight | Beam | LightRay/SunRay | RAY | RainbowParticle.BURST + Speck.LIGHT if blind |
| Corrosion | Bolt | CORROSION (grey→orange) | ZAP + GAS | Speck.CORROSION burst |
| Corruption | Bolt | SHADOW (dark purple) | ZAP + HIT_MAGIC(0.8×) | Dark shadow burst |
| BlastWave | Bolt | FORCE (brown) | ZAP + BLAST | Ripple effect `Effects.Type.RIPPLE` |
| Regrowth | Cone | FOLIAGE_CONE (green) | ZAP | Creates grass/plants on hit |
| Transfusion | Beam | HealthRay (red) | RAY | BloodParticle.BURST / Speck.HEALING / Speck.HEART |
| Warding | Bolt | WARD (purple) | ZAP | WardParticle.UP burst |
| LivingEarth | Bolt | EARTH (brown/yellow) | ZAP + HIT_MAGIC(0.8-0.9×) | EarthParticle.BURST / ATTRACT |

### 3.5 Staff Aura Particles (`staffFx()`)

When imbued into Mage's Staff, each wand contributes floating particles:

| Wand | Color | Lifespan | Movement |
|------|-------|----------|----------|
| MagicMissile | White 0xFFFFFF | 1.0s | Polar random, 2f speed |
| Fireblast | Orange 0xEE7722 | 0.6s | Upward acc -40, 0 init speed |
| Frost | Light blue 0x88CCFF | 2.0s | Slow drift, acc 0/±1 |
| Lightning | White 0xFFFFFF | 0.6s | Accelerated down (+20 Y) |
| Disintegration | Dark purple 0x220022 | 1.0s | Diagonal (±10, -10) |
| PrismaticLight | Random color | 1.0s | Polar random, 2f |
| Corrosion | Grey–orange random | 1.0s | Downward acc +20 |
| Corruption | Black 0x0 | 2.0s | Downward 5f |
| BlastWave | Brown 0x664422 | 3.0s | Extremely slow 0.3f |
| Regrowth | Green random | 1.0s | No acc, shuffled |
| Transfusion | Red 0xCC0000 | 1.0s | Polar random, 2f |
| Warding | Purple 0x8822FF | 3.0s | Extremely slow 0.3f |
| LivingEarth | Brown/yellow random | 2.0s | No acc, shuffled |

### 3.6 Wand Zap Execution Flow

1. Player selects ZAP → `Wand.execute()` → `GameScene.selectCell(zapper)`
2. On cell select → `Ballistica` raycast with collision
3. `curUser.sprite.zap(cell)` — hero zap animation
4. `curWand.fx(shot, callback)` — FX + audio plays
5. Callback → `curWand.onZap(shot)` — game logic
6. `curWand.wandUsed()` — charge decrement, identification

---

## 4. SOUND ASSETS REFERENCE

| Sound | File | Used By |
|-------|------|---------|
| ZAP | `sounds/zap.mp3` | Most bolt wands |
| RAY | `sounds/ray.mp3` | Beam wands |
| LIGHTNING | `sounds/lightning.mp3` | All electrical effects |
| BURNING | `sounds/burning.mp3` | All fire effects |
| BLAST | `sounds/blast.mp3` | BlastWave, Fireblast staff proc |
| GAS | `sounds/gas.mp3` | Corrosion gas cloud |
| HIT_MAGIC | `sounds/hit_magic.mp3` | MagicMissile, Frost, Corruption, LivingEarth on-hit |
| HIT_STRONG | `sounds/hit_strong.mp3` | Empowered wand hits |
| SHATTER | `sounds/shatter.mp3` | Potion shatter, cursed ooze |

---

## 5. TEXTURE ATLAS — `effects.png`

```
Layout (16px grid):
  0,0   → 16,16   = RIPPLE (16×16)
  16,0  → 32,8    = LIGHTNING (16×8)
  16,8  → 32,16   = WOUND (16×8)
  0,16  → 6,25    = EXCLAMATION (6×9)
  6,16  → 11,22   = CHAIN (5×6)
  11,16 → 16,22   = ETHEREAL_CHAIN (5×6)
  16,16 → 32,24   = DEATH_RAY (16×8)
  16,23 → 32,31   = LIGHT_RAY (16×8)
  16,30 → 32,38   = HEALTH_RAY (16×8)
```

All beam/lightning textures are 16×8 px white shapes. Colors/tints applied via `hardlight()`.

---

## 6. KEY MECHANICAL RULES

- **Water amplifies electricity:** full damage (no falloff) in water, chain range doubles, Electricity blob propagates through water only.
- **Chain lightning falloff:** `0.4 + 0.6/targetCount` damage per target.
- **Two electrical damage systems:** instant bolt (direct `damage()` call) vs blob tick damage (`Electricity` blob alternates on odd ticks).
- **Fire propagation:** 4-cardinal-neighbor spread, blocked by Freezing. Only spreads to `flamable` tiles.
- **Fire vs water:** Fire checks Freezing blob presence (not water terrain directly). Burning buff checks water terrain each act.
- **Burning item destruction:** triggers after 4+ turns. Only non-unique Scrolls and MysteryMeat/FrozenCarpaccio.
- **Depth scaling:** Fire tick: `1 to 3+depth/4`. Electricity tick: `2 + depth/5`.
- **Additive blending** used for all energy-type effects (lightning, fire, beam, magic particles).
- **All particles shrink over lifetime** via `PixelParticle.Shrinking` or manual size interpolation.
