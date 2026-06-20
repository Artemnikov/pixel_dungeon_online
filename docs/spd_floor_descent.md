# Floor Descent/Ascent Animation & Sound — SPD Source Reference

Source: `shattered-pixel-dungeon/core/.../scenes/InterlevelScene.java`,
`scenes/GameScene.java`, `levels/Level.java`, `levels/features/LevelTransition.java`,
`levels/features/Chasm.java`, `actors/hero/Hero.java` (`actTransition`), `Assets.java`.

## Two distinct flows
SPD has two separate mechanisms that both end up changing `Dungeon.depth`:
1. **Stairs / regular transition** — hero walks onto a stairs tile, triggers
   `LevelTransition` (`Level.activateTransition`). Always cooperative/instant
   (no fall damage), goes through `InterlevelScene`.
2. **Chasm / trapdoor fall** (`levels/features/Chasm.java`) — hero is forced
   down a level (trapdoor trap, chasm tile, jumping into a chasm gap). Also
   routes through `InterlevelScene` (`Mode.FALL`), but has its own sound,
   no fade-choice UI, and **fall damage** on landing.

## Trigger: stairs (`Hero.actTransition` → `Level.activateTransition`)
- `Hero.actTransition` (`Hero.java:1380`) checks the hero is standing inside
  a `LevelTransition` rect (`transition.inside(pos)`); `rooted` hero just
  screen-shakes and refuses.
- `Level.activateTransition` (`Level.java:566`):
  - Calls `beforeTransition()` — flushes time-freeze/time-bubble pending
    presses, detaches `WarriorFoodImmunity`/`ChallengeArena`/`Awareness`
    buffs (these don't persist across floors), spends the hero's partial
    turn so no carry-over between floors, leaves behind any `IMMOVABLE`
    stasis ally with a log warning.
  - Sets `InterlevelScene.curTransition` + `InterlevelScene.mode`
    (`DESCEND` for `REGULAR_EXIT`/`BRANCH_EXIT`, `ASCEND` otherwise).
  - `Game.switchScene(InterlevelScene.class)` — **no fade-out on the
    gameplay scene itself**; the scene swap is instant, `InterlevelScene`
    does all the fading.

## Trigger: falling (`Chasm.heroFall`)
- Plays `Assets.Sounds.FALLING` **immediately**, before the scene switch
  (distinct from the stairs `DESCEND` sound).
- `InterlevelScene.mode = FALL`; flags `fallIntoPit` if the room is a
  `WeakFloorRoom` (changes landing cell selection, see `Level.fallCell`).
- Landing (`Chasm.heroLand`, called once back in `GameScene` via the
  `Falling` buff) does the actual damage: `PixelScene.shake(4, 1f)`,
  applies `Cripple`, `Bleeding` scaled to current HP%, and HP damage
  (`max(HP/2, NormalIntRange(HP/2, HT/4))`) — unless an
  `ElixirOfFeatherFall` buff intercepts it (negates damage, plays a
  particle burst instead).
- Falling is **resisted by `rooted`/flying**, and chasm-jumping requires
  confirmation (`Chasm.heroJump` → `WndOptions` yes/no popup) before the
  fall actually starts.

## `InterlevelScene` — the loading/fade scene
Modes: `DESCEND, ASCEND, CONTINUE, RESURRECT, RETURN, FALL, RESET, NONE`.

### Fade timing (`fadeTime`, 3 tiers)
- `SLOW_FADE = 1f` (.33 in / 1.33 hold / .33 out = 2s) — entering a **new
  region** (depths 6/11/16/21/26) for the first time, or first descent ever
  (no hero yet / new game).
- `NORM_FADE = 0.67f` (1.33s total) — default: normal descend/fall/return/
  loading-a-save.
- `FAST_FADE = 0.50f` (1s total) — ascending, or descending to a floor
  **already visited** (`Statistics.deepestFloor >= loadingDepth`).
- All reduced to `0f` when `DeviceCompat.isDebug()`.
- Phases: `FADE_IN → STATIC (holds until level-gen thread finishes, min the
  fade time) → FADE_OUT`, then `Game.switchScene(GameScene.class)`.

### Visuals while loading
- Full-screen region splash art (`Assets.Splashes.SEWERS/PRISON/CAVES/
  CITY/HALLS`) with a randomized horizontal focal point (seeded by
  `Dungeon.seed + region`, so consistent per run/region) and a soft
  left/right edge gradient + vignette.
- "Descending...""Ascending..." etc. text (animated trailing dots) bottom
  right (`Messages.get(Mode.class, mode.name())`), localized per `Mode`.
  `FALL` mode additionally jitters the text position every frame (small
  random shake, screen-space).
- **Story intro popup**: only on `DESCEND`, region ≤ 5, not debug, and only
  the *first* time the hero reaches depth 1/6/11/16/21 of a region
  (`loadingDepth % 5 == 1 && loadingDepth > Statistics.deepestFloor`, or no
  hero yet). Shows `Document.INTROS` page text in a shadow box with a
  "Continue" button (stairs icon) gating the fade-out — player must
  dismiss it before the level loads in. Can be collapsed to a small chevron
  toggle. This is the "new region intro lore" screen, separate from the
  per-floor fade.
- Actual level generation happens on a **background thread** started in
  `create()`; if it's slow (>10s) SPD fires a non-fatal error report (assumed
  stuck on I/O, not levelgen logic) — generation is otherwise synchronous
  with the fade timer, whichever takes longer wins.

## Re-entering `GameScene` after the fade
`GameScene.create()` (called on every scene switch, including post-transition):
- **Camera snap-from-offscreen, then pan in** (`GameScene.java:584-594`):
  - `DESCEND` / `FALL` / `CONTINUE`: camera **snaps one tile above** the
    hero, then `panTo(hero.center(), 2.5f)` smoothly settles onto the hero
    — visually reads as "dropping down into view".
  - `ASCEND`: camera snaps one tile **below** the hero, pans up — "rising
    into view".
  - Other modes: snaps directly onto the hero (no pan-in).
- **`Assets.Sounds.DESCEND` ("sounds/descend.mp3") only plays when
  `Dungeon.depth == Statistics.deepestFloor` AND mode is `DESCEND` or
  `FALL`** (`GameScene.java:596-600`) — i.e. **only on breaking new ground**,
  never when stairs-diving back down through already-explored floors or
  when ascending. Paired with a heads-up log line
  (`GLog.h("descend...", depth)`) and, if any `DemonSpawner` is alive on a
  floor above, a spawner-warning log message.
  - Falling and walking-down-stairs share the exact same sound/log gate —
    SPD does not distinguish them for this cue.
- `RESURRECT` plays `Assets.Sounds.TELEPORT` + teleport VFX + ankh spell
  sprite + flare, not the descend sound (resurrection isn't a "floor"
  event, even though it can reposition you).
- `RESET` / other modes: no sound, just a log line.
- Other immediate post-load effects irrespective of sound: dropped items
  carried over from the previous floor (potions shatter, seeds replant,
  honeypots shatter) are placed at a random respawn cell; `Badges.
  validateNoKilling()` checked on `DESCEND`/`FALL` if hero is alive (pacifist
  badge tracking).

## Assets
- `Assets.Sounds.DESCEND = "sounds/descend.mp3"` — stairs/new-floor cue.
- `Assets.Sounds.FALLING` — chasm/trapdoor fall cue (separate file, plays
  the instant the fall starts, not on landing).
- `Assets.Splashes.{SEWERS,PRISON,CAVES,CITY,HALLS}` — interlevel loading
  background art, one per region.

## Summary of porting status for this project
- **Implemented**: instant stairs transition on stepping onto
  `STAIRS_DOWN`/`STAIRS_UP` tiles (`backend/app/engine/game/movement.py:335-341`),
  emits `STAIRS_DOWN`/`STAIRS_UP` events (`app/schemas/events.py`). Frontend
  plays a `descend.mp3` SFX (`frontend/src/audio/AudioManager.js:70,153`,
  `frontend/src/net/events/player.ts:258-261`) on `STAIRS_DOWN` only, for the
  triggering player only.
- **Not yet ported**:
  - No sound/event at all on `STAIRS_UP` (ascending) — SPD plays no descend
    sound on ascend either, but the remake should still confirm there's an
    intentional silence there rather than a missed wire-up.
  - No "new deepest floor" gating — remake plays the descend SFX on *every*
    `STAIRS_DOWN`, including re-descending an already-explored floor; SPD
    only plays it the first time a depth is reached
    (`Statistics.deepestFloor` check).
  - No `InterlevelScene`-equivalent fade/loading transition at all — floor
    swap is instant (grid replaced via `INIT` message, no client-side
    fade-out/in).
  - No camera snap-from-above/below + pan-in effect on floor change.
  - No chasm/trapdoor fall flow ported (no `FALLING` sound, no fall damage/
    Cripple/Bleeding on landing, no jump-confirmation prompt) — this project
    has trap types in `engine/dungeon/terrain.py` but falling-through-floor
    behavior should be checked separately if/when trapdoors are implemented.
  - No region-intro lore popup, no per-region splash art loading screen.
