# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-09-06

### Added
- **Backend — Talent System**: Complete talent system overhaul with a new registry-based architecture (`TalentEffectRegistry`, `EffectContext`). Handler modules for on_eat, on_kill, on_potion, on_step, passive stats, and rogue tick. New talents include Hearty Meal, Iron Stomach, Cashed Rations, Empowering Meal, Mystical Meal, Energizing Meal, Invigorating Meal, Cleave, Lethal Momentum, Soul Eater, and Deathly Durability.
- **Backend — Player Tick**: Major refactoring of `player_tick.py` with improved tick logic for player actions, movement validation, and interaction handling.
- **Backend — Movement & Chest**: Enhanced `MovementController` with better block resolution and tick-based movement logic. Complete rewrite of chest handling (`chest.py`) with proper open/close state management and animation support.
- **Backend — AI & Terrain**: Updated Eye and Tengu AI behaviors for improved pathfinding and targeting. Blob overrides (Web, Key Ward, Light Wall, Eternal Fire) now correctly applied during terrain changes.
- **Frontend — Event Dispatcher**: New `GameEventDispatcher` and `defaultEventDispatcher` for clean event-driven architecture replacing inline handlers. Events are now registered via factory functions (`createBossEventHandlers`, `createWorldEventHandlers`, etc.).
- **Frontend — Window Manager**: Complete rewrite of window management with new `WindowManager` class supporting registration, level-based ordering, escape handling with fallback, and subscription-based updates.
- **Frontend — Services & Sync**: New centralized services (`EntityManager`, `GameCallbacks`, `HeroStateSync`, `VisualEffectsManager`, `WorldManager`). Dedicated synchronizers for Environment, Items, Mobs, Players, SelfPlayer, Traps, and Vision replacing the monolithic sync state approach.
- **Frontend — Animation & Rendering**: New `ItemAnimationManager` for handling item animations with proper lifecycle management. Enhanced trap rendering system with new visual effects.
- **Frontend — Combat & Talents**: Major rewrite of combat events with proper state management. New talent query hooks (`useTalentData`, `useTalentUI`, `useTalents`) replacing the old `useTalentFlow` system.
- **Tests**: Added tests for universal spawns (magical sleep), talent registry, tick movement, audio events, bombs, boss pacing, crystal mimic runtime, rest regen, scrolls, sewers runtime, and domain services.

### Changed
- Merged the chore/optimizations PR: performance and code-quality improvements across the backend game engine and frontend, with expanded test coverage for audio events, bombs, boss pacing, crystal mimics, and talent mechanics.
- Audio manager now properly scoped to player movement commands on both frontend and backend.
- WebSocket sync loosened — connection manager and WS handlers updated for more flexible reconnection handling.

### Removed
- Obsolete `useTalentFlow` system replaced by new talent hooks (`useTalentData`, `useTalentUI`, `useTalents`).
- Redundant `onLogClick` handler in input hooks (clicks now pass through game log to canvas automatically).
- Stale collision/line-of-sight data after terrain changes — grid rebuilds immediately on wall destruction, plant growth, and cursed-wand effects.

## [1.0.1] - 2026-09-05

### Added
- **Frontend — Chat**: Fixed chat sizing and behavior (#114). Game log now properly doubles as the player chat panel with correct pointer-events and responsive layout.
- **Backend — Chat**: Fixed direct message echo verification for the origin player (#115) — DMs no longer incorrectly echo back to the sender.

### Changed
- Collected changelogs into a single location (#116). Translation files updated with bilingual (EN/RU) changelog entries.
- Removed hidden entrance doors on floors 1 & 2 for fresh games — doors are now always visible from the start, providing a cleaner first-room experience (#117).

## [1.0.0] - 2026-09-01

### Added
- **Backend — Networking**: Event-driven WebSocket architecture with `WebSocketConnectionManager` and `MessageDispatcher`, replacing the previous vibe-coded WS handling.
- **Backend — Game Engine**: OOP refactoring of game entities including `Player`, `ItemBase` (bombs, consumables, scrolls), and base entity classes into proper object-oriented structures.
- **Backend — Movement System**: Complete movement system overhaul with new `MovementController`, block resolution logic, chest handling, and tick-based player movement.
- **Backend — Serialization**: Enhanced serialization for players, inventory items, and full game state persistence.
- **Frontend — Input System**: New command-based input controller architecture with `KeyActionRegistry`, `DirectionalMoveCommand`, `InventoryToggleCommand`, `QuickslotCommand`, and more.
- **Frontend — Movement Prediction**: Client-side movement prediction with new `MovementPredictor` and `BlockerResolver` for smooth player movement.
- **Frontend — Combat**: Major rewrite of combat events with proper state management and event-driven architecture.
- **Frontend — Animation**: New `HeroAnimationPipeline` for smooth character animations.
- **Tests**: Comprehensive test coverage added for tick movement, inventory system, WS schemas, reconnect cleanup, no-echo events, per-player discovery, and admin tests.

### Changed
- Replaced direct canvas controls with a command-based input architecture on the frontend.
- Refactored all game entities from procedural code to OOP classes in the backend.
- Overhauled the movement system with proper block resolution and tick-based logic.

### Removed
- Obsolete frontend overlays: `AlchemyOverlay`, `DangerIndicator`, `VictoryScreen`, `GameLog`, `ToastOverlay`, `Toolbar`.
- Vibe-coded WebSocket handling flow on both frontend and backend.
- Direct canvas control input methods in favor of the new command system.
