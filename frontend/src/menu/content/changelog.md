## Summary

This release (v1.2.0) introduces an authoritative Turn-Based Game Mode alongside the real-time mode, featuring an SPD-accurate turn scheduler, specialized mob pacing actors, synchronized turn state, and action gating. It also delivers overhauled boss arena layouts and multi-phase encounters for DM-300, Dwarf King, and Yog-Dzewa, complete with rockfall hazards, wire conduits, and boss presence guards.

## Key Changes

### Backend
- **Turn-Based Game Mode (`turn_based`)** — Server-authoritative turn-based mode powered by `TurnScheduler`, calculating fractional action costs for movement, attacks, item consumption, scroll reading, thrown items, and waiting.
- **Turn-Based Mob Brains & Ability Pacing** — Implemented `TurnMobActor` hierarchy (`WallClockGatedMobActor`, `TickCounterMobActor`, `RangedMobActor`, and boss actors) ensuring special abilities (Shaman zap, Goo charge, DM-300 gas vent) pace correctly across turns.
- **Authoritative Mob Floor Tracking** — Stamped `floor_id` on mobs across all spawn routines, ensuring scheduler correctly resolves entities on deep boss floors.
- **Boss Arena Layouts** — Ported dedicated boss layouts for Caves (DM-300 with power pylons and wire conduits), City (Dwarf King throne room with summon pillars), and Halls (Yog-Dzewa altar with elemental fists).
- **Boss Mechanics & Phases** — Implemented DM-300 pylon supercharging and toxic gas venting, Dwarf King phased minion waves and deferred damage, and Yog-Dzewa fist battles with invulnerability shield phases.
- **Boss Respawn & Presence Guards** — Prevented duplicate boss spawns when players are already on boss levels.
- **Cleric Class Port (v1.1.0)** — Holy Tome artifact spell progression, talents across tiers 1–4, and armor abilities.

### Frontend
- **Turn UI & Indicators** — Added `TurnIndicator` showing active turn owner, energy, and turn queue previews.
- **Turn Input Gating & Taps** — Prevented out-of-turn actions with input gating in `DirectionalMoveCommand`, `QuickslotCommand`, and `WaitEmergencyDrinkCommand`; added dedicated `turnTap` routing.
- **Room Selection Mode Toggle** — Added game mode selector to `RoomSelection` supporting both Real-Time and Turn-Based rooms.
- **Boss Hazards & VFX** — Added `rockfallTargetedCells` renderer for falling debris warnings, spark particles, and `rocks.mp3` audio.
- **UI & Mobile Enhancements** — Refined hero selection centering on short viewports, updated game over screen, and extended mob sprite atlas.

## Release Version: 1.2.0
