## Summary

This release (v1.0.4) introduces the full Seeds & Plants system ported from SPD, synchronized attack cooldowns with instant combat hit effects, reliable subclass and armor ability choice dialog delivery, streamlined talent upgrade visuals, locked door/chest audio, and backend code cleanups.

## Key Changes

### Backend
- **Seeds & Plants System** — Full port of SPD seeds and plants (Firebloom, Icecap, Earthroot, Sorrowmoss, Starflower, Fadeleaf, Rotberry, Sungrass, Blindweed, Stormvine, Dreamfoil, Blandfruit Bush). Plants grow on tiles, trigger when stepped on or hit by thrown items, apply status effects/hazards/buffs, and integrate with Wand of Regrowth and Wandmaker quests.
- **Combat Cooldown Synchronization** — Calculates and sends exact `next_attack_in_ms` cooldowns in `ATTACK` and `RANGED_ATTACK` events for accurate client-side timing.
- **Choice Dialog Reliability** — Fixed WebSocket delivery and reconnect re-emission of subclass and armor ability choice dialogs upon equipping Tengu's Mask and King's Crown.
- **Entity & Code Cleanup** — Cleaned up entity hierarchies (`base.py`, `consumables.py`, `equip.py`, `union.py`), scroll predicates, and unused imports.
- **Event-driven WebSocket architecture** — Replaced vibe-coded WS handling with a clean event-driven flow using `WebSocketConnectionManager` and `MessageDispatcher`
- **OOP game entities** — Refactored player, items (bombs, consumables, scrolls), and base entity classes into proper OOP structures
- **Movement system overhaul** — New movement controller with block resolution, chest handling, and tick-based movement logic
- **Serialization improvements** — Enhanced serialization for players, inventory, and game state
- **Talent System Overhaul** — Complete talent system with registry-based architecture (`TalentEffectRegistry`, `EffectContext`), handler modules for `on_eat`, `on_kill`, `on_potion`, `on_step`, passive stats, rogue tick. New talents: Hearty Meal, Iron Stomach, Cashed Rations, Empowering Meal, Mystical Meal, Energizing Meal, Invigorating Meal, Cleave, Lethal Momentum, Soul Eater, Deathly Durability
- **Player Tick Refactoring** — Major refactoring of `player_tick.py` with improved tick logic for player actions, movement validation, and interaction handling
- **Chest System Rewrite** — Complete rewrite of chest handling in the movement system with proper open/close state management and animation support
- **AI Improvements** — Updated Eye and Tengu AI behaviors; blob overrides (Web, Key Ward, Light Wall, Eternal Fire) now correctly applied during terrain changes

### Frontend
- **Seeds & Plants Integration** — Added `PlantsSynchronizer`, plant tile rendering with blooming animations and particle effects, `plant.mp3` audio, and plant inspection info window (`WndInfoPlant`).
- **Immediate Combat Hit FX** — Removed artificial timeouts so hit animations, damage numbers, blood splatters, and particle bursts trigger instantly upon receiving combat events. Added attack readiness checks (`isAttackReady`, `consumeAttackCooldown`).
- **Talent Upgrade Visuals** — Star-burst upgrade particles now managed imperatively by `VisualEffectsManager` on `TALENT_UPGRADED` event, removing component state overhead. Added `TALENT` sprite icon.
- **Audio Improvements** — Added dedicated `locked.mp3` audio effect for locked doors and chests.
- **New input controller system** — Replaced direct canvas controls with a command-based architecture (`KeyActionRegistry`, `DirectionalMoveCommand`, etc.)
- **Movement prediction** — New `MovementPredictor` and `BlockerResolver` for client-side movement prediction
- **Combat event refactoring** — Major rewrite of combat events with proper state management
- **Animation pipeline** — New `HeroAnimationPipeline` for smooth character animations
- **UI simplification** — Removed obsolete overlays (AlchemyOverlay, DangerIndicator, VictoryScreen, etc.) and simplified remaining UI components
- **Event Dispatcher Architecture** — New `GameEventDispatcher` and `defaultEventDispatcher` replacing inline handlers. Events registered via factory functions (`createBossEventHandlers`, `createWorldEventHandlers`, etc.)
- **Window Manager Rewrite** — Complete rewrite with new `WindowManager` class supporting registration, level-based ordering, escape handling with fallback, and subscription-based updates
- **Entity Manager & Services** — New centralized services: `EntityManager`, `GameCallbacks`, `HeroStateSync`, `VisualEffectsManager`, `WorldManager`
- **Synchronizer Layer** — Dedicated synchronizers for Environment, Items, Mobs, Players, SelfPlayer, Traps, and Vision replacing the monolithic sync state approach
- **Animation Manager** — New `ItemAnimationManager` for handling item animations with proper lifecycle management
- **Trap Rendering** — Enhanced trap rendering system with new visual effects
- **Talent UI Hooks** — New talent query hooks (`useTalentData`, `useTalentUI`, `useTalents`) replacing the old `useTalentFlow` system

## Release Version: 1.0.4
