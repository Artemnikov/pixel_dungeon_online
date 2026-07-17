// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU General Public License for more details.
//
export const SOURCE_TILE_SIZE = 16;
export const DEST_TILE_SIZE = 32;
export const ATLAS_COLUMNS = 16;

export const QUADRANT = {
  FULL: 'full',
  TL: 'tl',
  TR: 'tr',
  BL: 'bl',
  BR: 'br',
};

export const atlasIndex = (x, y) => y * ATLAS_COLUMNS + x;

export const BACKEND_TILE = {
  VOID: { id: 0, atlasIndex: null, seethrough: true },
  WALL: { id: 1, atlasIndex: atlasIndex(0, 5), seethrough: false },
  FLOOR: { id: 2, atlasIndex: null, seethrough: true },
  DOOR: { id: 3, atlasIndex: atlasIndex(8, 3), seethrough: false },
  OPEN_DOOR: { id: 22, atlasIndex: atlasIndex(9, 3), seethrough: true },
  STAIRS_UP: { id: 4, atlasIndex: atlasIndex(0, 1), seethrough: true },
  STAIRS_DOWN: { id: 5, atlasIndex: atlasIndex(1, 1), seethrough: true },
  FLOOR_WOOD: { id: 6, atlasIndex: atlasIndex(4, 0), seethrough: true },
  FLOOR_WATER: { id: 7, atlasIndex: null, seethrough: true },
  FLOOR_COBBLE: { id: 8, atlasIndex: atlasIndex(12, 0), seethrough: true },
  FLOOR_GRASS: { id: 9, atlasIndex: null, seethrough: true },
  LOCKED_DOOR: { id: 10, atlasIndex: atlasIndex(8, 3), seethrough: false },
  SECRET_TRAP: { id: 11, atlasIndex: null, seethrough: true },
  TRAP: { id: 12, atlasIndex: null, seethrough: true },
  INACTIVE_TRAP: { id: 13, atlasIndex: null, seethrough: true },
  EMBERS: { id: 14, atlasIndex: atlasIndex(3, 0), seethrough: true },
  // SPD DungeonTileSheet: FLAT_OTHER = xy(1,5) -> atlasIndex(0,4); REGION_DECO
  // = FLAT_OTHER+10, REGION_DECO_ALT = FLAT_OTHER+11. SOLID but NOT a wall --
  // seethrough so it never participates in wall fog/stitching (see Gap 1).
  REGION_DECO: { id: 15, atlasIndex: atlasIndex(10, 4), seethrough: true },
  REGION_DECO_ALT: { id: 16, atlasIndex: atlasIndex(11, 4), seethrough: true },
  WALL_DECO: { id: 17, atlasIndex: atlasIndex(1, 3), seethrough: false },
  EMPTY_DECO: { id: 18, atlasIndex: atlasIndex(3, 0), seethrough: true },
  HIGH_GRASS: { id: 19, atlasIndex: null, seethrough: false },
  SECRET_DOOR: { id: 20, atlasIndex: atlasIndex(0, 5), seethrough: false },
  LOCKED_EXIT: { id: 21, atlasIndex: atlasIndex(8, 3), seethrough: false },
  ALCHEMY: { id: 23, atlasIndex: atlasIndex(8, 7), seethrough: true, overhangIndex: atlasIndex(8, 14) },
  WELL: { id: 24, atlasIndex: null, seethrough: true },
  STATUE: { id: 25, atlasIndex: atlasIndex(0, 8), seethrough: true },
  BOOKSHELF: { id: 27, atlasIndex: atlasIndex(12, 5), seethrough: false },
  FURROWED_GRASS: { id: 30, atlasIndex: null, seethrough: false },
  CRYSTAL_DOOR: { id: 31, atlasIndex: atlasIndex(3, 7), seethrough: false },
  // Destructible wooden obstacle (StorageRoom etc.) -- looks like a wall
  // until burned away into EMBERS, same placeholder convention as SECRET_DOOR.
  BARRICADE: { id: 32, atlasIndex: atlasIndex(0, 5), seethrough: false },
  CHASM: { id: 33, atlasIndex: atlasIndex(8, 1), seethrough: true },
};

export const toAtlasCoords = (index) => ({
  x: index % ATLAS_COLUMNS,
  y: Math.floor(index / ATLAS_COLUMNS),
});

export const hashCell = (x, y) => ((x * 73856093) ^ (y * 19349663)) >>> 0;

export const TERRAIN_INDEX = {
  FLOOR_VARIANTS: [atlasIndex(0, 0), atlasIndex(1, 0), atlasIndex(2, 0)],
  FLOOR_ALT_VARIANTS: [atlasIndex(6, 0), atlasIndex(7, 0), atlasIndex(8, 0)],

  // SPD DungeonTileSheet: FLOOR_DECO = GROUND+1, FLOOR_DECO_ALT = GROUND+7.
  // EMPTY_DECO renders as one of these full-tile decorated floor variants,
  // picked by hashCell for per-cell but stable variation.
  EMPTY_DECO_VARIANTS: [atlasIndex(1, 0), atlasIndex(7, 0)],

  GRASS_CENTER: [atlasIndex(2, 4), atlasIndex(5, 4), atlasIndex(6, 4)],
  HIGH_GRASS_CENTER: [atlasIndex(10, 7), atlasIndex(13, 7)],
  FURROWED_GRASS_CENTER: [atlasIndex(11, 7), atlasIndex(12, 7)],
  GRASS_EDGE: {
    tl: atlasIndex(1, 2),
    tr: atlasIndex(2, 2),
    bl: atlasIndex(3, 2),
    br: atlasIndex(4, 2),
  },

  // SPD DungeonTileSheet: WATER = xy(1,3) (16-slot block). Tile is picked by a
  // 4-bit mask of the 4 cardinal neighbours: +1 top, +2 right, +4 bottom,
  // +8 left if that neighbour is "ground-like" (stitcheable). Mask 0 = pure
  // water (no overlay needed).
  WATER_STITCH_BASE: atlasIndex(0, 2),
};

/*
 * WALL_INDEX — atlas base indices for SPD's two-layer wall architecture.
 *
 * Layout (mirrors SPD DungeonTileSheet constants, translated from 1-indexed
 * xy(col, row) to 0-indexed atlasIndex(x, y)):
 *
 *   RAISED_WALL         y=5, cols 0-3   (front-face: +1 open right, +2 open left)
 *   RAISED_WALL_DECO    y=5, cols 4-7
 *   RAISED_WALL_DOOR    y=5, col 8      (wall cell directly above a door)
 *   RAISED_WALL_ALT     y=6, cols 0-3   (alt visual row — hash picks between)
 *   RAISED_WALL_DECO_ALT y=6, cols 4-7
 *
 *   WALL_INTERNAL       y=9, cols 0-15  (wall top when surrounded by walls —
 *                                        4-bit mask: +1 right, +2 rightBelow,
 *                                        +4 leftBelow, +8 left)
 *   WALL_INTERNAL_DECO  y=10, cols 0-15
 *
 *   WALL_OVERHANG       y=12, cols 0-3  (wall top bleeding into the floor cell
 *                                        above it — 2-bit mask: +1 rightBelow
 *                                        non-wall, +2 leftBelow non-wall)
 *   WALL_OVERHANG_DECO  y=12, cols 4-7
 *
 *   DOOR_SIDEWAYS_OVERHANG          y=13, cols 0-3   (door on a vertical wall,
 *                                                     seen from the floor above)
 *   DOOR_SIDEWAYS_OVERHANG_CLOSED   y=13, cols 4-7
 *   DOOR_SIDEWAYS_OVERHANG_LOCKED   y=13, cols 8-11
 *
 *   DOOR_OVERHANG               y=14, col 0   (top cap of a horizontal door)
 *   DOOR_OVERHANG_OPEN          y=14, col 1
 *   DOOR_SIDEWAYS               y=14, col 3   (wall cell directly above a
 *                                              vertical door — no stitching)
 *   DOOR_SIDEWAYS_LOCKED        y=14, col 4
 *
 *   RAISED_DOOR_SIDEWAYS        y=7, col 4    (the side-door body itself,
 *                                              drawn at the door cell when
 *                                              it sits between two walls)
 *
 * The "raised" naming comes from SPD's 3D look: the wall cell at (x, y) draws
 * only its FRONT FACE (lower half of the sprite hangs below the top-of-wall
 * line). The wall's top-of-wall surface is drawn ONE CELL UP from its grid
 * row — in what is, logically, the floor cell above it — as WALL_OVERHANG.
 * That's how walls visually obscure characters standing behind them.
 */
export const WALL_INDEX = {
  RAISED_WALL: atlasIndex(0, 5),
  RAISED_WALL_DECO: atlasIndex(4, 5),
  RAISED_WALL_DOOR: atlasIndex(8, 5),
  RAISED_WALL_ALT: atlasIndex(0, 6),
  RAISED_WALL_DECO_ALT: atlasIndex(4, 6),
  RAISED_WALL_BOOKSHELF: atlasIndex(12, 5),

  WALL_INTERNAL: atlasIndex(0, 9),
  WALL_INTERNAL_DECO: atlasIndex(0, 10),
  WALL_INTERNAL_WOODEN: atlasIndex(0, 11),

  WALL_OVERHANG: atlasIndex(0, 12),
  WALL_OVERHANG_DECO: atlasIndex(4, 12),
  WALL_OVERHANG_WOODEN: atlasIndex(8, 12),

  DOOR_SIDEWAYS_OVERHANG: atlasIndex(0, 13),
  DOOR_SIDEWAYS_OVERHANG_CLOSED: atlasIndex(4, 13),
  DOOR_SIDEWAYS_OVERHANG_LOCKED: atlasIndex(8, 13),
  DOOR_SIDEWAYS_OVERHANG_CRYSTAL: atlasIndex(12, 13),

  DOOR_OVERHANG: atlasIndex(0, 14),
  DOOR_OVERHANG_OPEN: atlasIndex(1, 14),
  DOOR_OVERHANG_CRYSTAL: atlasIndex(2, 14),
  DOOR_SIDEWAYS: atlasIndex(3, 14),
  DOOR_SIDEWAYS_LOCKED: atlasIndex(4, 14),
  DOOR_SIDEWAYS_CRYSTAL: atlasIndex(5, 14),
  EXIT_UNDERHANG: atlasIndex(6, 14),

  RAISED_DOOR: atlasIndex(0, 7),
  RAISED_DOOR_OPEN: atlasIndex(1, 7),
  RAISED_DOOR_LOCKED: atlasIndex(2, 7),
  RAISED_DOOR_CRYSTAL: atlasIndex(3, 7),
  RAISED_DOOR_SIDEWAYS: atlasIndex(4, 7),
  RAISED_BARRICADE: atlasIndex(9, 7),
};

// SPD DungeonTileSheet.CHASM block (verified present in every region atlas
// at this exact offset): an 8-slot row, base void + 4 "stitched" variants
// picked by whatever terrain sits directly above the chasm cell.
export const CHASM_INDEX = {
  BASE: atlasIndex(8, 1),
  FLOOR: atlasIndex(9, 1),
  FLOOR_SP: atlasIndex(10, 1),
  WALL: atlasIndex(11, 1),
  WATER: atlasIndex(12, 1),
};

export const WATER_SCROLL_PX_PER_SEC = 10;

export const QUADRANT_NEIGHBORS = {
  tl: [
    [0, 0],
    [-1, 0],
    [0, -1],
    [-1, -1],
  ],
  tr: [
    [0, 0],
    [1, 0],
    [0, -1],
    [1, -1],
  ],
  bl: [
    [0, 0],
    [-1, 0],
    [0, 1],
    [-1, 1],
  ],
  br: [
    [0, 0],
    [1, 0],
    [0, 1],
    [1, 1],
  ],
};

// Used by rendering + game logic: WALL, WALL_DECO, and SECRET_DOOR all
// render as walls (SECRET_DOOR is indistinguishable from WALL to the player
// until revealed).
export const isWallTile = (tile) =>
  tile === BACKEND_TILE.WALL.id ||
  tile === BACKEND_TILE.WALL_DECO.id ||
  tile === BACKEND_TILE.SECRET_DOOR.id ||
  tile === BACKEND_TILE.BOOKSHELF.id;

// Used ONLY by wall-autotile stitching: any tile that should visually
// continue a wall surface. Out-of-bounds (-1) and unpainted VOID cells
// count as walls so the outer frame of the map stitches cleanly instead
// of showing jagged edges. Mirrors SPD's DungeonTileSheet.wallStitcheable.
export const isWallStitcheable = (tile) =>
  tile === -1 ||
  tile === BACKEND_TILE.VOID.id ||
  tile === BACKEND_TILE.WALL.id ||
  tile === BACKEND_TILE.WALL_DECO.id ||
  tile === BACKEND_TILE.SECRET_DOOR.id ||
  tile === BACKEND_TILE.LOCKED_EXIT.id ||
  tile === BACKEND_TILE.BOOKSHELF.id;

export const isDoorTile = (tile) =>
  tile === BACKEND_TILE.DOOR.id ||
  tile === BACKEND_TILE.OPEN_DOOR.id ||
  tile === BACKEND_TILE.LOCKED_DOOR.id ||
  tile === BACKEND_TILE.LOCKED_EXIT.id ||
  tile === BACKEND_TILE.CRYSTAL_DOOR.id;

// Mirrors SPD DungeonTileSheet.getRaisedDoorTile: a door cell is "sideways"
// when the cell above is wallStitcheable (any wall-like tile), regardless of
// the cells to the left or right. A door walled-in on both sides (e.g. the
// Goo boss arena's locked-exit pedestal alcove) is still a side door in SPD.
export const isSidewaysDoor = (grid, x, y, getTile) =>
  isWallStitcheable(getTile(grid, x, y - 1));

export const isWaterTile = (tile) => tile === BACKEND_TILE.FLOOR_WATER.id;

// Mirrors SPD's DungeonTileSheet.waterStitcheable: anything except water and
// walls counts as "ground" that water shores stitch against (including
// VOID/out-of-bounds, matching SPD's EMPTY being stitcheable).
export const isWaterStitcheable = (tile) => !isWaterTile(tile) && !isWallTile(tile);
export const isGrassTile = (tile) =>
  tile === BACKEND_TILE.FLOOR_GRASS.id ||
  tile === BACKEND_TILE.HIGH_GRASS.id ||
  tile === BACKEND_TILE.FURROWED_GRASS.id;

export const TRAP_VISUAL = {
  worn_dart: { color: 7, shape: 5 },
  tengu_dart: { color: 3, shape: 5 },
  burning_trap: { color: 1, shape: 0 },
  blazing_trap: { color: 1, shape: 3 },
  shocking_trap: { color: 2, shape: 0 },
  storm_trap: { color: 2, shape: 3 },
  chilling_trap: { color: 6, shape: 0 },
  toxic_trap: { color: 3, shape: 2 },
  poison_dart_trap: { color: 3, shape: 5 },
  confusion_trap: { color: 4, shape: 2 },
  flock_trap: { color: 6, shape: 1 },
  summoning_trap: { color: 4, shape: 1 },
  teleportation_trap: { color: 4, shape: 0 },
  gateway_trap: { color: 4, shape: 5 },
  alarm_trap: { color: 0, shape: 0 },
  ooze_trap: { color: 3, shape: 0 },
  gripping_trap: { color: 7, shape: 0 },
  geyser_trap: { color: 4, shape: 4 },
  frost_trap: { color: 6, shape: 3 },
  corrosion_trap: { color: 7, shape: 2 },
  rockfall_trap: { color: 7, shape: 4 },
  guardian_trap: { color: 0, shape: 3 },
  warping_trap: { color: 4, shape: 3 },
  pitfall_trap: { color: 0, shape: 4 },
  disintegration_trap: { color: 5, shape: 5 },
  flashing_trap: { color: 7, shape: 3 },
  weakening_trap: { color: 3, shape: 1 },
  disarming_trap: { color: 0, shape: 6 },
  cursing_trap: { color: 5, shape: 1 },
  distortion_trap: { color: 4, shape: 6 },
  grim_trap: { color: 7, shape: 6 },
  explosive_trap: { color: 1, shape: 4 },
};

export const trapSpriteIndex = (trapType) => {
  const v = TRAP_VISUAL[trapType];
  if (!v) return null;
  return v.color + v.shape * 16;
};

export const trapDisarmedIndex = (trapType) => {
  const v = TRAP_VISUAL[trapType];
  if (!v) return null;
  return 8 + v.shape * 16;
};
