## Summary

This release (v1.3.0) ports the Yog-Dzewa finale, the Dwarf King fight and the Rat King's Ratmogrify armor ability from SPD, adds Evil Eye, Scorpio and Ripper Demon behaviours, and adds multiplayer party prompts for the Tengu, Dwarf King and Yog-Dzewa arenas. World systems and mob turns now advance on SPD's turn clock in both room modes, and melee hit sounds, the Viscosity glyph, mob loot and DM-300 / Warlock fidelity are fixed.

## Key Changes

### Backend
- **Yog-Dzewa Fight** — 1:1 SPD port of Yog-Dzewa, its six fists and the Halls arena on the SPD act clock: telegraphed death-ray beams, summon loop, invulnerability phases that add fists at the altar, each fist's own abilities, party prompt (decliners sent back to Floor 24, late arrivals locked in), and arena reset in public rooms. Yog is always hunting.
- **Eye, Scorpio & Ripper Demon** — SPD `act()` ports: Eye death gaze along a `STOP_SOLID` path, Scorpio ranged-only with `PathFinder.getStepBack` retreat, Ripper leap with bleed. Eye and Scorpio drop SPD loot.
- **Rat King & Ratmogrify** — Talking wakes the Rat King, who trades the Dwarf King's crown for the Ratmogrify armor ability; transmogrified rats revert after 6 turns, and the Ratsistance, Ratlomacy and Ratforcements talents are ported.
- **Dwarf King Fight** — SPD-accurate Life Link and Teleport Subject, turn-by-turn phase 2 waves with a regenerating barrier and KingDamager tracking that counts every minion death, phase 3 per-turn summons and deferred-damage bleed. Fixed the double crown drop, arena re-locking after victory, abilities while paralysed, minion loot/XP, and turn-based pacing.
- **Dwarf King Idle Pacing** — In real-time rooms the shielded King's clock runs 4x faster while none of his minions are alive.
- **Boss Party Prompts** — Tengu (Floor 10), Dwarf King (Floor 20) and Yog-Dzewa (Floor 25) prompt the other players on the floor to join; participants are teleported into the arena.
- **DM-300 Fidelity Pass** — SPD ability cooldowns, gas cone line-of-sight, supercharged wall breaking, and arena sealing.
- **SPD Engine Building Blocks** — Faithful `Ballistica` port, `Random.NormalFloat` / `Random.chances`, SPD `NormalIntRange`, a once-per-SPD-turn act clock, and `LockedFloor` helpers.
- **SPD Turn Clock for World Systems** — Fire, gases, pylon energy, hallowed ground, foliage, burning, poison, corrosion and ooze advance once per SPD turn in both modes; SPD Bleeding and Viscosity deferred-damage ports (the Viscosity glyph now actually deals its deferred damage).
- **Turn-Based Mob Timing** — Mobs are charged the SPD time their turn spent (speed, attack delay and multi-turn actions now count); Tengu bombs, DM-300 rockfall and Tengu blobs fire on time in turn rooms.
- **Mob AI** — Adjacent-only generic melee, casters hold position while they can zap, Light guarantees 6-tile hero vision, and roots are checked uniformly.
- **Melee Hit Sounds** — Landed hero hit sounds are server-only and echoed back to the attacker; surprise hits add `HIT_STRONG`.
- **Contract Schema Export** — Every serialized field is marked required, so generated `entities.ts` typechecks.

### Frontend
- **Yog-Dzewa VFX & Sprites** — Targeted-cell markers, death rays, fist bolts and light rays, altar bursts, spawn tweens, Yog / fist / Ripper sprites, boss bar and floor 25 music handling; Yog party prompt windows with en/ru texts.
- **Rat King UI** — `WndRatKing` crown trade dialog, `WndInfoArmorAbility`, Ratmogrify ability and talent icons, and en/ru texts.
- **Dwarf King VFX** — Pedestal summon telegraphs for the whole summon delay, SPD-coloured summon bursts, and "invulnerable" / "deferred N" status text; `WndDwarfKingPrompt` party dialog.
- **Warlock Zap** — SPD shadow-particle bolt (also Wand of Corruption), real zap sound played once, and Degrade sound.
- **Tengu Boss Prompts UI** — Added `WndTenguJoinPrompt` and `WndTenguPartyStatus` modal dialogs with full English and Russian translations.
- **Melee Hit Sounds** — Removed the client-predicted swing sound; the attacker now hears the server's hit sound.
- **Turn Input & Diagonal Movement** — Fixed chorded diagonal key inputs in turn-based mode to reliably dispatch diagonal steps.

## Release Version: 1.3.0
