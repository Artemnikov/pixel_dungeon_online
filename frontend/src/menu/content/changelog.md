## Summary

This release (v1.2.1) completes the SPD port of the Dwarf King fight, adds multiplayer party prompts for the Tengu and Dwarf King arenas, tightens DM-300 fidelity, fixes Warlock zap effects, and improves diagonal movement in turn-based mode.

## Key Changes

### Backend
- **Dwarf King Fight** — SPD-accurate Life Link and Teleport Subject, turn-by-turn phase 2 waves with a regenerating barrier and KingDamager tracking that counts every minion death, phase 3 per-turn summons and deferred-damage bleed. Fixed the double crown drop, arena re-locking after victory, abilities while paralysed, minion loot/XP, and turn-based pacing.
- **Dwarf King Idle Pacing** — In real-time rooms the shielded King's clock runs 4x faster while none of his minions are alive.
- **Dwarf King Party Prompt** — Players on Floor 20 are prompted to join the fight and teleported into the arena.
- **DM-300 Fidelity Pass** — SPD ability cooldowns, gas cone line-of-sight, supercharged wall breaking, and arena sealing.
- **Tengu Boss Party Prompt & Decisions** — Unlocking the Floor 10 cell door prompts active players on the floor to join. The unlocker can start without decliners or wait; participating players are teleported horizontally inside the cell (with floor trap clearance underfoot) and non-participants stay as spectators.
- **Turn-Based Game Mode (`turn_based`)** — Server-authoritative turn-based mode powered by `TurnScheduler`, calculating fractional action costs for movement, attacks, item consumption, scroll reading, thrown items, and waiting.
- **Turn-Based Mob Brains & Ability Pacing** — Implemented `TurnMobActor` hierarchy (`WallClockGatedMobActor`, `TickCounterMobActor`, `RangedMobActor`, and boss actors) ensuring special abilities (Shaman zap, Goo charge, DM-300 gas vent) pace correctly across turns.
- **Authoritative Mob Floor Tracking** — Stamped `floor_id` on mobs across all spawn routines, ensuring scheduler correctly resolves entities on deep boss floors.
- **Boss Arena Layouts & Mechanics** — Ported dedicated boss layouts for Caves (DM-300), City (Dwarf King), and Halls (Yog-Dzewa) with arena hazards and presence guards.

### Frontend
- **Dwarf King VFX** — Pedestal summon telegraphs for the whole summon delay, SPD-coloured summon bursts, and "invulnerable" / "deferred N" status text; `WndDwarfKingPrompt` party dialog.
- **Warlock Zap** — SPD shadow-particle bolt (also Wand of Corruption), real zap sound played once, and Degrade sound.
- **Tengu Boss Prompts UI** — Added `WndTenguJoinPrompt` and `WndTenguPartyStatus` modal dialogs with full English and Russian translations.
- **Turn Input & Diagonal Movement** — Fixed chorded diagonal key inputs in turn-based mode to reliably dispatch diagonal steps.
- **Turn UI & Indicators** — Added `TurnIndicator` showing active turn owner, energy, and turn queue previews.
- **Room Selection Mode Toggle** — Added game mode selector to `RoomSelection` supporting both Real-Time and Turn-Based rooms.
- **Boss Hazards & VFX** — Added `rockfallTargetedCells` renderer for falling debris warnings, spark particles, and `rocks.mp3` audio.

## Release Version: 1.2.1
