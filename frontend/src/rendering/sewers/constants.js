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

  RAISED_HIGH_GRASS: atlasIndex(10, 7),
  RAISED_HIGH_GRASS_ALT: atlasIndex(13, 7),
  RAISED_FURROWED_GRASS: atlasIndex(11, 7),
  RAISED_FURROWED_ALT: atlasIndex(14, 7),

  HIGH_GRASS_OVERHANG: atlasIndex(10, 14),
  HIGH_GRASS_OVERHANG_ALT: atlasIndex(13, 14),
  FURROWED_OVERHANG: atlasIndex(11, 14),
  FURROWED_OVERHANG_ALT: atlasIndex(14, 14),

  HIGH_GRASS_UNDERHANG: atlasIndex(10, 15),
  HIGH_GRASS_UNDERHANG_ALT: atlasIndex(13, 15),
  FURROWED_UNDERHANG: atlasIndex(11, 15),
  FURROWED_UNDERHANG_ALT: atlasIndex(14, 15),
};

export const TERRAIN_INDEX = {
  FLOOR_VARIANTS: [atlasIndex(0, 0), atlasIndex(1, 0), atlasIndex(2, 0)],
  FLOOR_ALT_VARIANTS: [atlasIndex(6, 0), atlasIndex(7, 0), atlasIndex(8, 0)],

  EMPTY_DECO_VARIANTS: [atlasIndex(1, 0), atlasIndex(7, 0)],

  GRASS_BASE: [atlasIndex(2, 0), atlasIndex(8, 0)],
  EMBERS_BASE: [atlasIndex(3, 0), atlasIndex(9, 0)],

  GRASS_CENTER: [atlasIndex(2, 4), atlasIndex(5, 4)],
  HIGH_GRASS_CENTER: [atlasIndex(10, 7), atlasIndex(13, 7)],
  FURROWED_GRASS_CENTER: [atlasIndex(11, 7), atlasIndex(14, 7)],
  GRASS_EDGE: {
    tl: atlasIndex(1, 2),
    tr: atlasIndex(2, 2),
    bl: atlasIndex(3, 2),
    br: atlasIndex(4, 2),
  },

  WATER_STITCH_BASE: atlasIndex(0, 2),
};
