# DM-300 (Floor 15) Boss — Full Animation Stack, VFX/SFX & Game Flow

Source reference from upstream Shattered Pixel Dungeon (`shattered-pixel-dungeon/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/`):
- `actors/mobs/DM300.java`
- `sprites/DM300Sprite.java`
- `actors/mobs/Pylon.java`
- `sprites/PylonSprite.java`
- `levels/CavesBossLevel.java`
- `actors/mobs/DelayedRockFall.java`
- `effects/TargetedCell.java`
- `effects/particles/SparkParticle.java`, `EarthParticle.java`, `BlastParticle.java`
- `effects/Speck.java`, `MagicMissile.java`, `Lightning.java`
- `ui/BossHealthBar.java`

---

## 1. Sprite Sheets & Animation Stack

### 1.1 `DM300Sprite` (`sprites/dm300.png`)
- **Texture dimensions**: `256 × 64` px
- **Frame grid**: `TextureFilm(texture, 25, 22)` — 10 frames per row across 2 rows:
  - **Row 0 (indices `0..9`, `c = 0`)**: Normal state
  - **Row 1 (indices `10..19`, `c = 10`)**: Supercharged / Enraged state (`updateChargeState(true)`)
- **Destination / scale (in 32×32 remake tile space)**: `dw = 50, dh = 44, dx = -9, dy = -6` (2× pixel scale)
- **Z-order**: `place()` calls `parent.bringToFront(this)` so DM-300 renders above normal actors.
- **Blood / Hit particle color**: `blood()` returns `0xFFFFFF88` (pale yellow-white sparks instead of red blood).

| Animation | FPS | Looping | Frames (Normal `c=0`) | Frames (Supercharged `c=10`) | Notes & Callbacks |
|---|---:|---|---|---|---|
| `idle` | `10` (normal) / `15` (enraged) | Yes | `[0, 1]` | `[10, 11]` | Default state; `updateChargeState` switches active row and speed. |
| `run` | `10` (normal) / `15` (enraged) | Yes | `[0, 2]` | `[10, 12]` | Played while moving between cells. |
| `attack` | `15` | No | `[3, 4, 5]` | `[13, 14, 15]` | Melee drill strike (~200 ms total). |
| `slam` | `15` | No | `[3, 4, 5]` | `[13, 14, 15]` | Cloned from `attack`. Turns to target cell, plays `Assets.Sounds.ROCKS`, shakes camera `PixelScene.shake(3, 0.7f)`. On complete → `idle()` and `((DM300)ch).onSlamComplete()` (triggers `dropRocks(enemy)`). |
| `zap` | `15` | No | `[6, 7, 7, 6]` | `[6, 7, 7, 6]` | Unaffected by enrage state (~267 ms). Fires `MagicMissile.boltFromChar(..., MagicMissile.SPECK + Speck.TOXIC, this, cell, callback)` and plays `Assets.Sounds.GAS`. On anim complete → `idle()`; on missile arrival callback → `((DM300)ch).onZapComplete()` (`ventGas(enemy)`). |
| `charge` | `4` | Yes | `[0, 10]` | `[0, 10]` | Alternates between normal frame `0` (row 0 col 0) and supercharged frame `10` (row 1 col 0) at 250 ms/frame during the supercharge startup pause (`3f` normal / `2f` stronger bosses). |
| `die` | `20` | No | `[0, 10] × 10` (20 frames) | `[0, 10] × 10` (20 frames) | Rapidly flashes between row 0 col 0 and row 1 col 0 at 50 ms/frame for 1.0s. On complete → plays `Assets.Sounds.BLAST`, bursts `BlastParticle.FACTORY` (100 particles), and calls `killAndErase()`. |

#### Ambient Emitter (`superchargeSparks`)
- Created in `link(Char ch)`: `superchargeSparks = emitter(); superchargeSparks.autoKill = false; superchargeSparks.pour(SparkParticle.STATIC, 0.05f); superchargeSparks.on = false;`
- Toggled via `updateChargeState(boolean enraged)`: `superchargeSparks.on = enraged`.
- Synced to sprite visibility each frame (`superchargeSparks.visible = visible`), disabled in `die()`, and erased in `kill()`.

---

### 1.2 `PylonSprite` (`sprites/pylon.png`)
- **Texture dimensions**: `30 × 20` px
- **Frame grid**: `TextureFilm(texture, 10, 20)` — 3 static frames (`0`, `1`, `2`)
- **Perspective & Shadow**: `perspectiveRaise = 5/16f` (1 px lower than standard mobs), `renderShadow = false`
- **Destination / scale (in 32×32 remake tile space)**: `dw = 20, dh = 40, dx = 6, dy = -8`
- **Z-order**: `place()` calls `parent.bringToFront(this)`.
- **Blood / Hit particle color**: `blood()` returns `0xFFFFFF88`.

| Animation | FPS | Looping | Frame | Notes |
|---|---:|---|---|---|
| `idle` (inactive) | `1` | No | `[0]` | Shown when `alignment == NEUTRAL` (invulnerable, passive). |
| `activeIdle` (active) | `1` | No | `[1]` | Activated via `activate()` when `alignment == ENEMY`. |
| `run` / `attack` | `1` | No | Cloned from `idle` | `onComplete(attack)` calls `flash()`. |
| `die` | `1` | No | `[2]` | `play(die)` calls `turnTo(ch.pos, ch.pos+1)` (always faces right to align with custom tiles), bursts `BlastParticle.FACTORY` (20 particles), and plays `Assets.Sounds.BLAST`. |

---

## 2. Arena Layout & Custom Tilemaps (`CavesBossLevel.java`)

### 2.1 Level Geometry
- **Dimensions**: `WIDTH = 33`, `HEIGHT = 42`
- **Key Rectangles** (exclusive right/bottom in `Rect`):
  - `mainArena = Rect(5, 14, 28, 37)` — filled as an ellipse with `Terrain.EMPTY`
  - `diggableArea = Rect(2, 11, 31, 40)` — bounds where supercharged DM-300 is allowed to smash walls
  - `gate = Rect(14, 13, 19, 14)` — 5-tile horizontal metal gate at `x = 14..18, y = 13`, initially `Terrain.CUSTOM_DECO` (solid)
- **Pylon Coordinates (`pylonPositions`)**:
  - Top-Left: `(4, 13)`
  - Top-Right: `(28, 13)`
  - Bottom-Left: `(4, 37)`
  - Bottom-Right: `(28, 37)`
  - Surrounded by 3×3 `Terrain.EMPTY_SP` recesses from the 4 symmetric 10×10 corner templates (`corner1..4`).
- **Entrance**: `(16, 25)` — center of a 4-way mirrored 8×8 entrance structure (`entrance1..4`).
- **Exit**: `(16, 2)` inside `Rect(15, 0, 18, 3)` (`CityEntrance` area above the gate).
- **Water & Exposed Wires**:
  - Generated for `y >= 14`: `Patch.generate(width, height-14, 0.15f, 2, true)` places `Terrain.WATER`.
  - Remaining `Terrain.EMPTY` tiles have a `1/8` chance (`1/4` with `Challenges.STRONGER_BOSSES`) to become `Terrain.INACTIVE_TRAP` ("Exposed wiring").
  - Reachability check: flood-fills from `(16, 25)` using only `EMPTY`, `EMPTY_SP`, `EMPTY_DECO` (excluding water and wires); if any of the 4 pylons is unreachable without stepping on water/wires, `build()` rejects and regenerates.

### 2.2 Custom Tilemaps (`custom_tiles/caves_boss.png`, 8 columns per row)
1. **`CityEntrance`** (`customTiles`, `Rect(0, 0, 33, 11)`):
   - Renders the Dwarven Metropolis entryway (`x = 14..18, y = 0..10`) and overrides cave walls on rows `y = 2` (tile `13`) and `y = 3` (tile `21`, except columns `9` and `23` which have `REGION_DECO_ALT` metal structures).
2. **`EntranceOverhang`** (`customWalls`, `Rect(0, 0, 33, 11)`):
   - Renders the overhead arch (`tiles 0, 4, 7, 15, 23`) and statue overhangs (`tiles 6, 14` on rows `y = 4, 6, 8`) above the exit corridor.
3. **`ArenaVisuals`** (`customTiles`, `Rect(0, 12, 33, 27)`):
   - **Pylon recesses** (`Terrain.EMPTY_SP` around each pylon):
     - Adjacent 8 cells around each pylon `k`: tile index `54 + (j % w + 8 * (j / w)) - (k % w + 8 * (k / w))` (metal platform border).
     - Pylon center cell `k`: `-1` while the `Pylon` mob is alive (or before `locked`), switching to tile **`38`** (destroyed pylon base) once `locked && !(Actor.findChar(k) instanceof Pylon)`.
   - **Exposed wiring** (`Terrain.INACTIVE_TRAP`): tile **`37`**.
   - **Metal gate** (`gate` rect `x = 14..18, y = 13`):
     - Intact (`solid[j]`): tiles **`40, 41, 42, 43, 44`**
     - Destroyed (`!solid[j]` after `unseal()`): tiles **`32, 33, 34, 35, 36`**

---

## 3. Complete Fight Lifecycle & Game Flow

### Phase 0: Pre-Fight & Arena Seal
1. **Pre-fight state**:
   - Before the level is sealed and while the gate is intact (`map[14 + 13*width] == Terrain.CUSTOM_DECO`), level music is **silent** (`Music.INSTANCE.end()`).
   - The 4 `Pylon` mobs are spawned at `createMobs()` in `PASSIVE` state with `Alignment.NEUTRAL`. (In upstream SPD, `DM300` is spawned inside `seal()`; in the online remake, `DM300` is pre-spawned at generation time using the exact same `mainArena` RNG roll so players can see it before sealing.)
2. **Trigger (`CavesBossLevel.occupyCell`)**:
   - When a hero steps onto a cell within Chebyshev distance `<= 3` of any of the 4 `pylonPositions` while `!locked` and the gate is still solid, `seal()` is called.
3. **`CavesBossLevel.seal()`**:
   - Sets `Statistics.qualifiedForBossChallengeBadge = true`.
   - Applies `LockedFloor` buff to hero.
   - Replaces `entrance()` `(16, 25)` with `Terrain.WALL`.
   - **Heap displacement**: Any items on `entrance()` are picked up and dropped onto a random passable 8-neighbor (`NEIGHBOURS8`), preserving `heap.seen`.
   - **Character displacement**: Any character standing on `entrance()` is moved to a random passable 8-neighbor.
   - **Seal VFX & SFX**:
     - `CellEmitter.get(entrance).start(Speck.factory(Speck.ROCK), 0.07f, 10)`
     - `PixelScene.shake(3, 0.7f)`
     - `Sample.INSTANCE.play(Assets.Sounds.ROCKS)`
     - Starts boss music: `Music.INSTANCE.play(Assets.Music.CAVES_BOSS, true)` (`caves_boss.ogg`).
4. **`DM300.notice()`**:
   - Triggered when DM-300 first notices the hero (or takes damage):
   - `BossHealthBar.assignBoss(this)` — displays the Boss Health Bar (stays assigned for the entire fight regardless of whether DM-300 is currently in hero FOV).
   - `turnsSinceLastAbility = 0`
   - Yells `Messages.get(this, "notice")`: **`"UNAUTHORIZED PERSONNEL DETECTED!"`**
   - If `DriedRose.GhostHero` is present, calls `sayBoss()`.

---

### Phase 1: Normal Combat State (`!supercharged`)

#### Stats & Immunities
- **HP**: `300` (`400` with `STRONGER_BOSSES`)
- **Attack Skill**: `20` | **Defense Skill**: `15` | **EXP**: `30`
- **Melee Damage**: `Random.NormalIntRange(15, 25)`
- **DR**: `Random.NormalIntRange(0, 10)`
- **Properties**: `BOSS`, `INORGANIC`, `LARGE`
- **Immunities**: `Sleep` (plus `INORGANIC` immunities: `Bleeding`, `ToxicGas`, `Poison`)
- **Resistances**: `Terror`, `Charm`, `Vertigo`, `Cripple`, `Chill`, `Frost`, `Roots`, `Slow`

#### Movement & Exposed Wire Shielding (`DM300.move`)
- **Footstep Screen Shake**: Every step (`travelling == true`) triggers `PixelScene.shake(supercharged ? 3 : 1, 0.25f)`.
- **Wire Shielding**:
  - Condition: `!flying && map[pos] == Terrain.INACTIVE_TRAP && state == HUNTING` and `PylonEnergy.volumeAt(pos) == 0` (the wire is **not** currently energized by a pylon).
  - Sets (replaces) `Barrier` shield to **`30 + (HT - HP) / 10`**: `Buff.affect(this, Barrier.class).setShield(30 + (HT - HP)/10)`.
  - If `heroFOV[pos]`:
    - If DM-300 had no `Barrier` buff prior to this step, logs warning: **`"DM-300 pulls power from the exposed wires and shields itself!"`**
    - Plays `Assets.Sounds.LIGHTNING`
    - Emits static sparks on DM-300: `sprite.emitter().start(SparkParticle.STATIC, 0.05f, 20)`
    - Shows floating shield number: `sprite.showStatusWithIcon(CharSprite.POSITIVE, Integer.toString(30 + (HT - HP)/10), FloatingText.SHIELDING)`

#### Ability Scheduler (`DM300.act`)
- `MIN_COOLDOWN = 5`, `MAX_COOLDOWN = 9` (`7` with `STRONGER_BOSSES`).
- Increments `turnsSinceLastAbility` by 1 each act when `>= 0`.
- **Case A — Target Unreachable (`!canReach`)**:
  - Triggers when `turnsSinceLastAbility >= MIN_COOLDOWN` (`5` turns).
  - Evaluates a 30° `ConeAOE(new Ballistica(pos, enemy.pos, Ballistica.WONT_STOP), Float.POSITIVE_INFINITY, 30, Ballistica.STOP_SOLID)` to allow trickshotting gas around corners.
  - If `aim.cells.contains(enemy.pos)` and enemy is not `INORGANIC` → uses **`GAS`**.
  - Otherwise, if `enemy.paralysed <= 0` (prevents stunlocking) → uses **`ROCKS`**.
- **Case B — Target Reachable & in FOV (`canReach && fieldOfView[enemy.pos]`)**:
  - Triggers when `turnsSinceLastAbility > abilityCooldown`.
  - Selection probabilities based on `lastAbility`:
    - `NONE`: 50% `GAS`, 50% `ROCKS`
    - `GAS`: 25% `GAS`, 75% `ROCKS`
    - `ROCKS`: 75% `GAS`, 25% `ROCKS`
    - Override: if `enemy` has `Property.INORGANIC` → always `ROCKS`.
  - **Free-action rule**: Only spends `TICK` if `Dungeon.level.adjacent(pos, enemy.pos)`; when enemy is at distance `>= 2`, casting the ability does **not** spend a turn (`spend(TICK)` is skipped so DM-300 also moves/acts on the same turn).
  - Resets `turnsSinceLastAbility = 0` and rolls a new `abilityCooldown = Random.NormalIntRange(MIN_COOLDOWN, MAX_COOLDOWN)`.

#### Ability 1: `ventGas(Char target)` (`GAS`)
1. **Animation & Projectile**:
   - `sprite.zap(enemy.pos)` faces target, plays `zap` frames `[6, 7, 7, 6]` at 15 fps, plays `Assets.Sounds.GAS`, and launches `MagicMissile.SPECK + Speck.TOXIC` (200 px/s) to `enemy.pos`.
2. **Gas Seeding**:
   - Computes `Ballistica trajectory = new Ballistica(pos, target.pos, Ballistica.STOP_TARGET)`.
   - Multiplier: `gasMulti = STRONGER_BOSSES ? 2 : 1`.
   - Seeds `100 * gasMulti` `ToxicGas` at `trajectory.collisionPos`.
   - Seeds `20 * gasMulti` `ToxicGas` along every cell in `trajectory.subPath(0, trajectory.dist)` (including `collisionPos`), tracking `gasVented += 20 * gasMulti`.
   - If `gasVented < 250 * gasMulti`: distributes the remainder `ceil((250 * gasMulti - gasVented) / 8f)` into each of the 8 neighbors (`NEIGHBOURS8`) around DM-300.

#### Ability 2: `dropRocks(Char target)` (`ROCKS`)
1. **Animation & Camera**:
   - `((DM300Sprite)sprite).slam(enemy.pos)` turns to target, plays `slam` frames `[3, 4, 5]` at 15 fps, plays `Assets.Sounds.ROCKS`, and shakes screen `PixelScene.shake(3, 0.7f)`.
2. **Knockback (on slam complete)**:
   - Interrupts hero (`Dungeon.hero.interrupt()`).
   - If `adjacent(pos, target.pos)` (dist == 1): knocks target back **2 tiles** along `Ballistica(target.pos, target.pos + (target.pos - pos), MAGIC_BOLT)` via `WandOfBlastWave.throwChar(..., 2, false, false, this)` (no wall-slam damage). `rockCenter` is the landing cell along the trajectory (`min(dist, 2)`).
   - Else if `fieldOfView[target.pos] && distance(pos, target.pos) == 2`: knocks target back **1 tile** (`rockCenter` at `min(dist, 1)`).
   - Else: no knockback; `rockCenter = target.pos`.
3. **7×7 Rock Pattern & Safe Cell**:
   - Picks `safeCell` from the 8 neighbors of `rockCenter` (`NEIGHBOURS8`), re-rolling while:
     - `safeCell == pos` (never DM-300's own cell), OR
     - `solid[safeCell] && Random.Int(2) == 0` (50% retry if wall), OR
     - `PylonEnergy.volumeAt(safeCell) > 0 && Random.Int(2) == 0` (50% retry if energized).
   - Iterates over the 7×7 grid centered on `rockCenter` (`dx, dy in -3..+3`):
     - Adds cell `p` to `rockCells` if `insideMap(p) && !solid[p] && p != safeCell && Random.Int(distance(rockCenter, p)) == 0` (where Chebyshev distance `0` has `Random.Int(0) == 0`, so `rockCenter` and `distance == 1` are always included except `safeCell`, `distance == 2` has 50% chance, `distance == 3` has 33.3% chance).
4. **Telegraph VFX (`TargetedCell` + `DelayedRockFall.fx`)**:
   - Spawns `new TargetedCell(i, 0xFF0000)` on every cell in `rockCells` (red target reticle `Icons.TARGET` that shrinks and fades over lifetime).
   - Attaches `FallingRockBuff` for `GameMath.gate(TICK, ceil(target.cooldown()), 3*TICK)` turns, which pours `EarthParticle.FALLING` (`0.1f` interval) from the upper portion of each threatened cell.
5. **Impact (`DelayedRockFall.act` & `FallingRockBuff.affectChar`)**:
   - On every cell in `rockPositions`:
     - Emits `CellEmitter.get(i).start(Speck.factory(Speck.ROCK), 0.07f, 10)`
     - Any character on the cell (except `DM300` and `Pylon`, which are immune) takes **`6–12`** damage (`Random.NormalIntRange(6, 12)`, or **`10–20`** with `STRONGER_BOSSES`) and is inflicted with **`Paralysis`** for **`3`** turns (**`5`** turns with `STRONGER_BOSSES`).
   - Shakes screen `PixelScene.shake(3, 0.7f)` and plays `Assets.Sounds.ROCKS`.

---

### Phase 2: Supercharge Transitions & Active Pylon Phase

#### Triggering Supercharge (`DM300.damage` → `DM300.supercharge`)
- **Total Pylons to Activate**: `totalPylonsToActivate() = STRONGER_BOSSES ? 3 : 2`.
- **HP Thresholds**:
  - Normal (300 HT, 2 pylons): `threshold = HT / 3 * (2 - pylonsActivated)` → **200 HP** (1st pylon) and **100 HP** (2nd pylon).
  - `STRONGER_BOSSES` (400 HT, 3 pylons): `threshold = HT / 4 * (3 - pylonsActivated)` → **300 HP**, **200 HP**, and **100 HP**.
- When `HP <= threshold && threshold > 0`:
  - Clamps `HP = threshold` (DM-300 cannot be killed before all required pylons have been activated and destroyed; `isAlive()` also returns `true` while `pylonsActivated < totalPylonsToActivate()`).
  - Calls `supercharge()`:
    - `supercharged = true`
    - Calls `((CavesBossLevel)Dungeon.level).activatePylon()`
    - `pylonsActivated++`
    - Spends **`3f` turns** (**`2f` turns** with `STRONGER_BOSSES`) charging in place.
    - Yells `Messages.get(this, "charging")`: **`"SUSTAINING DAMAGE! ACTIVATING POWER PYLON!"`**
    - Shows floating status: `sprite.showStatus(CharSprite.POSITIVE, "invulnerable")`
    - Sprite switches to supercharged state: `((DM300Sprite)sprite).updateChargeState(true)` (enables `superchargeSparks` emitter, switches animations to row 1) and plays `charge()` (`[0, 10]` at 4 fps).
    - Sets `chargeAnnounced = false`.

#### Pylon Selection & `PylonEnergy` Seeding (`CavesBossLevel.activatePylon`)
- Collects all living inactive (`Alignment.NEUTRAL`) `Pylon` mobs.
- If more than 1 inactive pylon exists, finds the pylon **closest** (`trueDistance`) to the hero, **removes it from the candidate list**, and activates a random pylon from the remaining candidates (guaranteeing the hero must traverse the arena).
- Seeds `PylonEnergy` blob (`volume = 1`) on all cells with `y >= mainArena.top - 1` (`y >= 13`) where terrain is `Terrain.INACTIVE_TRAP` (wires), `Terrain.WATER`, or `Terrain.CUSTOM_DECO` (gate).

#### `PylonEnergy` Blob Behavior & `DIRECTED_SPARKS` VFX (`CavesBossLevel.PylonEnergy`)
- **Spread**: Every evolution tick, `PylonEnergy` persists (`off[cell] = cur[cell]`) and instantly spreads to any `water[cell]` (`off[cell] = 1`).
- **Damage**: Any non-flying character (`!ch.flying && !(ch instanceof DM300)`) standing in `PylonEnergy` takes **`6–12`** electricity damage (`Random.NormalIntRange(6, 12)`), flashes (`sprite.flash()`), and plays `Assets.Sounds.LIGHTNING`.
  - **Score & Badge Penalty**: If `ch == Dungeon.hero`, deducts **`200` points** from `Statistics.bossScores[2]`, and if `energySourceSprite instanceof PylonSprite` (i.e. DM-300 is currently supercharged), sets `Statistics.qualifiedForBossChallengeBadge = false`.
- **Directed Sparks VFX (`DIRECTED_SPARKS`)**:
  - Pours at `0.08f` interval from the blob emitter.
  - Resolves `energySourceSprite` to the active `Pylon`'s sprite (while a pylon is active) or `DM300`'s sprite (after all pylons are destroyed in the finale phase).
  - Emits `SparkParticle.resetAttracting(x, y, energySourceSprite)` moving at `3 tiles/s` toward the energy source, with higher emission density closer to the source (`dist = gate(0, max(|dx|, |dy|) - 40, 320); Random.Float(360) > dist`) so players can follow the spark flow to locate the active pylon.

#### Supercharged DM-300 Behavior
- **First Act After Charge (`!chargeAnnounced`)**:
  - Yells `Messages.get(this, "supercharged")`: **`"DESTROY! DESTROY! DESTROY!"`**
  - Sets `chargeAnnounced = true`, beckons hero, and forces `state = HUNTING; enemy = Dungeon.hero` (if hero is not invisible).
- **Invulnerability**:
  - `isInvulnerable()` returns `true`. The first time the hero attacks DM-300 while supercharged (`!invulnWarned`), logs warning: **`"DM-300 is invulnerable while it is being energized by a pylon!"`**
- **Speed & Melee**:
  - Moves at **2× speed** (`speed() = super.speed() * 2`).
  - Footstep shake increases to `PixelScene.shake(3, 0.25f)`.
  - Does **not** use `GAS` or `ROCKS` abilities while supercharged.
  - If supercharged DM-300 attacks the hero in melee, sets `Statistics.qualifiedForBossChallengeBadge = false`.
- **Tunneling / Wall Smash (`DM300.getCloser`)**:
  - If standard pathfinding (`super.getCloser(target)`) fails while `supercharged && state == HUNTING && !rooted && !adjacent(pos, target)`:
  - Checks `NEIGHBOURS8` for an unoccupied cell (`Actor.findChar(pos+i) == null`) with strictly smaller Euclidean distance (`trueDistance`) to `target`.
  - If found:
    - Plays `Assets.Sounds.ROCKS`.
    - Iterates `NEIGHBOURS9` (3×3 around DM-300):
      - Converts `Terrain.WALL` and `Terrain.WALL_DECO` to `Terrain.EMPTY_DECO`, **except**:
        - Gate protection: `p.y < gate.bottom && p.x >= gate.left - 2 && p.x < gate.right + 2` (`y < 14` and `12 <= x < 21`)
        - Arena bounds: `!CavesBossLevel.diggableArea.inside(p)` (must be within `2 <= x < 31, 11 <= y < 40`)
      - Clears any `WallOfLight.LightWall` blob on those 9 cells.
    - Rebuilds wall/openSpace flags, updates map & FOV, and spends **`3f` turns** (**`2f` turns** with `STRONGER_BOSSES`).
    - Re-evaluates `NEIGHBOURS8` for an unoccupied cell with `openSpace[pos+i]` that reduces `trueDistance` to `target`, moves into it, and shakes screen **`PixelScene.shake(5, 1f)`**.

#### Active Pylon Behavior (`Pylon.java`)
- **Stats**:
  - **HP**: `50` (`80` with `STRONGER_BOSSES`)
  - **Properties**: `MINIBOSS`, `BOSS_MINION`, `INORGANIC`, `ELECTRIC`, `IMMOVABLE`, `STATIC`
  - **Damage Cap / Compression**: Incoming damage `>= 15` is compressed via:
    $$\text{dmg} = 14 + \left\lfloor \frac{\sqrt{8(\text{dmg} - 14) + 1} - 1}{2} \right\rfloor$$
    (takes 15 / 16 / 17 / 18 / 19 / 20 damage at 15 / 17 / 20 / 24 / 29 / 36 incoming damage).
  - Extends hero's `LockedFloor` timer by `dmg` (`dmg / 2f` with `STRONGER_BOSSES`).
- **Rotating Lightning Arcs (`Pylon.act`)**:
  - Maintains `targetNeighbor` (`0..7` index into `PathFinder.CIRCLE8`, initialized randomly at spawn) and increments `targetNeighbor = (targetNeighbor + 1) % 8` every turn (clockwise rotation).
  - **Shocked cells per turn**:
    - Normal: **2 opposite cells** — `CIRCLE8[targetNeighbor]` and `CIRCLE8[(targetNeighbor + 4) % 8]`.
    - `STRONGER_BOSSES`: **3 cells** — `CIRCLE8[targetNeighbor]`, `CIRCLE8[(targetNeighbor + 3) % 8]`, and `CIRCLE8[(targetNeighbor + 5) % 8]`.
  - Flashes pylon sprite (`sprite.flash()`), draws `Lightning` arc from pylon center to each shocked cell, bursts 3 `SparkParticle.FACTORY` per cell, and plays `Assets.Sounds.LIGHTNING`.
  - Any character on a shocked cell (except `DM300`) flashes and takes **`10–20`** electricity damage (`Random.NormalIntRange(10, 20)`).
  - **Score & Badge Penalty**: If `ch == Dungeon.hero`, sets `Statistics.qualifiedForBossChallengeBadge = false` and deducts **`100` points** from `Statistics.bossScores[2]`.

---

### Phase 3: Pylon Destruction & Finale Phase (`CavesBossLevel.eliminatePylon` & `DM300.loseSupercharge`)
1. When an active `Pylon` reaches 0 HP (`Pylon.die`):
   - `PylonSprite` turns right, switches to frame `2`, bursts 20 `BlastParticle`s, and plays `Assets.Sounds.BLAST`.
   - `ArenaVisuals.updateState()` sets the custom tile at the pylon's cell to **`38`** (broken pylon base).
2. `CavesBossLevel.eliminatePylon()`:
   - Calls `dm300.loseSupercharge()` and sets `PylonEnergy.energySourceSprite = dm300.sprite`.
   - Counts remaining living `Pylon` mobs (`pylonsRemaining`).
   - `finalPylonsRemaining = STRONGER_BOSSES ? 1 : 2`.
   - If `pylonsRemaining > finalPylonsRemaining` (i.e. after the 1st pylon dies in normal mode, or 1st/2nd in `STRONGER_BOSSES`): calls `blobs.get(PylonEnergy.class).fullyClear()` (wires and water stop sparking).
   - Once the **final required pylon** is destroyed (`pylonsRemaining == finalPylonsRemaining`): `PylonEnergy` is **NOT** cleared — wires and water remain permanently energized for the rest of the fight, with `DIRECTED_SPARKS` now streaming toward **DM-300 itself**!
3. `DM300.loseSupercharge()`:
   - `supercharged = false`
   - `((DM300Sprite)sprite).updateChargeState(false)` (turns off `superchargeSparks`, switches back to row 0 frames at 10 fps).
   - Clamps ability timer so DM-300 doesn't immediately fire an ability on the very next turn: `turnsSinceLastAbility = Math.min(turnsSinceLastAbility, MIN_COOLDOWN - 3)` (`<= 2`).
   - **If more pylons remain to be activated** (`pylonsActivated < totalPylonsToActivate()`):
     - Yells `Messages.get(this, "charge_lost")`: **`"PYLON DESTROYED! REVERTING TO LOCAL POWER!"`**
   - **If all required pylons have been destroyed** (`pylonsActivated >= totalPylonsToActivate()`):
     - Yells `Messages.get(this, "pylons_destroyed")`: **`"ALERT! INSTABILITY DETECTED IN POWER GRID!"`**
     - Enables Boss Health Bar bleeding: **`BossHealthBar.bleed(true)`** (red-tinted skull icon + dripping blood emitter).
     - Crossfades music (`0.5f` fade out) to **`Assets.Music.CAVES_BOSS_FINALE`** (`caves_boss_finale.ogg`, looping).

---

### Phase 4: Boss Death & Arena Unseal (`DM300.die` & `CavesBossLevel.unseal`)
1. When DM-300 reaches 0 HP after all required pylons have been destroyed:
   - `GameScene.bossSlain()` displays the "Boss Slain!" banner.
   - Calls `Dungeon.level.unseal()`.
   - **Loot drops**:
     - Drops **2 to 4 `MetalShard`s** (60% chance of 2, 30% chance of 3, 10% chance of 4; average 2.5) onto random passable 8-neighbors around DM-300 (`NEIGHBOURS8`).
   - **Score & Badges**:
     - Awards `Statistics.bossScores[2] += 3000`.
     - Validates `BOSS_SLAIN_3` badge (and `BOSS_CHALLENGE_3` if `qualifiedForBossChallengeBadge` remained true).
   - Yells `Messages.get(this, "defeated")`: **`"CRITICAL DAMAGE! ATTEMPTING SHUTDO-"`**
   - **Death Animation**:
     - Plays `die` (20 frames alternating row 0 col 0 and row 1 col 0 at 20 fps = 1.0s), then plays `Assets.Sounds.BLAST` and bursts `100` `BlastParticle`s.
2. **`CavesBossLevel.unseal()`**:
   - Clears all `PylonEnergy` blobs (`blobs.get(PylonEnergy.class).fullyClear()`).
   - Restores `entrance()` `(16, 25)` to `Terrain.ENTRANCE`.
   - Breaks open the 5-tile metal gate (`x = 14..18, y = 13`):
     - Sets terrain to `Terrain.EMPTY`.
     - If in `heroFOV`, bursts `CellEmitter.get(i+j).burst(BlastParticle.FACTORY, 10)` on each of the 5 gate cells.
     - `ArenaVisuals.updateState()` updates the 5 gate custom tiles from `40..44` to **`32..36`** (broken gate pieces).
   - Fades out boss music over `5f` seconds (`Music.INSTANCE.fadeOut(5f, ...)`).

---

## 4. Audio & Dialogue Quick Reference

### 4.1 Sound Effects (`Assets.Sounds`)
| Event | Sound Key | Asset |
|---|---|---|
| Arena seal / Rockfall slam / Rockfall impact / Wall smash | `ROCKS` | `sounds/rocks.mp3` |
| Toxic gas zap / Gas vent | `GAS` | `sounds/gas.mp3` |
| Wire shield gain / Pylon shock arc / `PylonEnergy` shock | `LIGHTNING` | `sounds/lightning.mp3` |
| Pylon death explosion / DM-300 death explosion | `BLAST` | `sounds/blast.mp3` |

### 4.2 Music Tracks (`Assets.Music`)
| State | Track | Behavior |
|---|---|---|
| Pre-fight (unsealed, gate closed) | None (silence) | `Music.INSTANCE.end()` |
| Fight started (`seal()`) through Pylon phases | `caves_boss.ogg` | Loops continuously |
| Final phase (all required pylons destroyed) | `caves_boss_finale.ogg` | `0.5f` fade-out from `caves_boss`, then loops |
| Post-fight (`unseal()`) | Ambient `caves_1..3.ogg` | `5f` fade-out after boss death |

### 4.3 Canonical Yells & Log Messages (`actors.properties`)
| Key | Type | Text |
|---|---|---|
| `dm300.notice` | Boss Yell | `"UNAUTHORIZED PERSONNEL DETECTED!"` |
| `dm300.shield` | Warning Log (`GLog.w`) | `"DM-300 pulls power from the exposed wires and shields itself!"` |
| `dm300.charging` | Boss Yell | `"SUSTAINING DAMAGE! ACTIVATING POWER PYLON!"` |
| `dm300.invulnerable` | Floating Status (`POSITIVE`) | `"invulnerable"` |
| `dm300.charging_hint` | Warning Log (`GLog.w`) | `"DM-300 is invulnerable while it is being energized by a pylon!"` |
| `dm300.supercharged` | Boss Yell | `"DESTROY! DESTROY! DESTROY!"` |
| `dm300.charge_lost` | Boss Yell | `"PYLON DESTROYED! REVERTING TO LOCAL POWER!"` |
| `dm300.pylons_destroyed` | Boss Yell | `"ALERT! INSTABILITY DETECTED IN POWER GRID!"` |
| `dm300.defeated` | Boss Yell | `"CRITICAL DAMAGE! ATTEMPTING SHUTDO-"` |

---

## 5. Online Pixel Dungeon Implementation Map

| Subsystem | File(s) |
|---|---|
| Level generation & custom tilemaps | `backend/app/engine/dungeon/spd_levelgen/caves_boss_layout.py` |
| DM-300 & Pylon entity models | `backend/app/engine/entities/mobs/caves.py`, `backend/app/engine/entities/mobs/spawners.py` |
| DM-300 AI, abilities, seal/unseal, wall smash, wire shield | `backend/app/engine/game/ai_dm300.py`, `backend/app/engine/game/mob_ai_dispatch.py` |
| Pylon AI, activation & `PylonEnergy` blob | `backend/app/engine/game/ai_pylon.py`, `backend/app/engine/game/blobs.py` |
| Pylon & DM-300 death handling, custom tile updates, score/badges | `backend/app/engine/game/mob_death.py` |
| Sprite frames & animation state machine | `frontend/src/rendering/mobs.js`, `frontend/src/rendering/draw/mobs.js` |
| Boss events, particles, rockfall telegraph & `PylonEnergy` sparks | `frontend/src/net/events/boss.ts`, `frontend/src/rendering/draw/rockfallTargetedCells.js`, `frontend/src/rendering/draw/blobArea.js`, `frontend/src/rendering/draw/sparkParticle.js` |
| Boss Health Bar bleeding & music transitions | `frontend/src/ui/BossHealthBar.jsx`, `frontend/src/hooks/gameHooks.js`, `frontend/src/audio/useMusicByDepth.js` |
