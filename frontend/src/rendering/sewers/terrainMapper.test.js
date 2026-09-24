import test from 'node:test';
import assert from 'node:assert/strict';

import { getSewerTerrainInstructions } from './terrainMapper.js';
import { BACKEND_TILE, isGrassTile, isWallTile, isWaterStitcheable } from '../../constants.js';
import { QUADRANT, TERRAIN_INDEX, WALL_INDEX, CHASM_INDEX } from './constants.js';

const gridOfIds = (tileId, width = 3, height = 3) =>
  Array.from({ length: height }, () => Array.from({ length: width }, () => tileId));

test('maps base terrain IDs to non-empty instruction sets', () => {
  const grid = gridOfIds(BACKEND_TILE.FLOOR.id);

  const mappedIds = [
    BACKEND_TILE.FLOOR.id,
    BACKEND_TILE.FLOOR_WATER.id,
    BACKEND_TILE.FLOOR_COBBLE.id,
    BACKEND_TILE.FLOOR_GRASS.id,
    BACKEND_TILE.DOOR.id,
    BACKEND_TILE.LOCKED_DOOR.id,
    BACKEND_TILE.STAIRS_UP.id,
    BACKEND_TILE.STAIRS_DOWN.id,
  ];

  for (const tileId of mappedIds) {
    const instructions = getSewerTerrainInstructions(grid, 1, 1, tileId);
    assert.ok(instructions.length > 0, `tile id ${tileId} should render`);
  }
});

test('water surrounded by floor renders the fully-stitched shore tile', () => {
  const grid = gridOfIds(BACKEND_TILE.FLOOR.id);
  grid[1][1] = BACKEND_TILE.FLOOR_WATER.id;

  const instructions = getSewerTerrainInstructions(grid, 1, 1, BACKEND_TILE.FLOOR_WATER.id);

  assert.equal(instructions.length, 1);
  assert.equal(instructions[0].quadrant, QUADRANT.FULL);
  assert.equal(instructions[0].srcIndex, TERRAIN_INDEX.WATER_STITCH_BASE + 15);
});

test('water surrounded by water renders the plain water tile (mask 0)', () => {
  const grid = gridOfIds(BACKEND_TILE.FLOOR_WATER.id, 5, 5);

  const instructions = getSewerTerrainInstructions(grid, 2, 2, BACKEND_TILE.FLOOR_WATER.id);

  assert.equal(instructions.length, 1);
  assert.equal(instructions[0].quadrant, QUADRANT.FULL);
  assert.equal(instructions[0].srcIndex, TERRAIN_INDEX.WATER_STITCH_BASE);
});

test('water directly above CHASM renders plain water, not a shoreline edge', () => {
  // SPD's waterStitcheable() excludes CHASM: the tile over a pit must not
  // gain the bottom stitch bit (mask stays 0 when the other sides are water).
  const grid = gridOfIds(BACKEND_TILE.FLOOR_WATER.id, 5, 5);
  grid[3][2] = BACKEND_TILE.CHASM.id;

  const instructions = getSewerTerrainInstructions(grid, 2, 2, BACKEND_TILE.FLOOR_WATER.id);

  assert.equal(instructions.length, 1);
  assert.equal(instructions[0].srcIndex, TERRAIN_INDEX.WATER_STITCH_BASE);
});

test('water with CHASM on one side drops that side stitch bit', () => {
  const grid = gridOfIds(BACKEND_TILE.FLOOR.id, 5, 5);
  grid[2][2] = BACKEND_TILE.FLOOR_WATER.id;
  // FLOOR above/below/left keeps mask bits 1|4|8; CHASM on the right must
  // not contribute the +2 (right) bit -> WATER_STITCH_BASE + 13.
  grid[2][3] = BACKEND_TILE.CHASM.id;

  const instructions = getSewerTerrainInstructions(grid, 2, 2, BACKEND_TILE.FLOOR_WATER.id);

  assert.equal(instructions.length, 1);
  assert.equal(instructions[0].srcIndex, TERRAIN_INDEX.WATER_STITCH_BASE + 13);
});

test('water on the last grid row renders plain water (real out-of-bounds path)', () => {
  // getTile() returns VOID for out-of-bounds neighbours, so water on the map
  // edge must also skip the fake shoreline edge, matching SPD's wall-bordered
  // map. Cell (1,2) of a 3x3 grid has only water neighbours in-bounds; the
  // cell below it is genuinely out of bounds.
  const grid = gridOfIds(BACKEND_TILE.FLOOR_WATER.id, 3, 3);

  const instructions = getSewerTerrainInstructions(grid, 1, 2, BACKEND_TILE.FLOOR_WATER.id);

  assert.equal(instructions.length, 1);
  assert.equal(instructions[0].srcIndex, TERRAIN_INDEX.WATER_STITCH_BASE);
});

test('grass center uses center tiles when surrounded by grass', () => {
  const grid = gridOfIds(BACKEND_TILE.FLOOR_GRASS.id, 5, 5);
  const instructions = getSewerTerrainInstructions(grid, 2, 2, BACKEND_TILE.FLOOR_GRASS.id);
  const quadrants = instructions.filter((item) => item.quadrant !== QUADRANT.FULL);

  assert.equal(quadrants.length, 4);
  for (const inst of quadrants) {
    assert.ok(TERRAIN_INDEX.GRASS_CENTER.includes(inst.srcIndex));
  }
});

test('isolated grass on depth <= 15 uses GRASS_EDGE corner tiles', () => {
  const grid = gridOfIds(BACKEND_TILE.FLOOR.id, 5, 5);
  grid[2][2] = BACKEND_TILE.FLOOR_GRASS.id;
  const instructions = getSewerTerrainInstructions(grid, 2, 2, BACKEND_TILE.FLOOR_GRASS.id, new Set(), 1);
  const quadrants = instructions.filter((item) => item.quadrant !== QUADRANT.FULL);

  assert.equal(quadrants.length, 4);
  const edgeValues = Object.values(TERRAIN_INDEX.GRASS_EDGE);
  for (const inst of quadrants) {
    assert.ok(edgeValues.includes(inst.srcIndex));
  }
});

test('isolated grass on depth > 15 (City/Halls) uses safe center tiles to avoid legacy edge slot artifacts', () => {
  const grid = gridOfIds(BACKEND_TILE.FLOOR.id, 5, 5);
  grid[2][2] = BACKEND_TILE.FLOOR_GRASS.id;
  const instructions = getSewerTerrainInstructions(grid, 2, 2, BACKEND_TILE.FLOOR_GRASS.id, new Set(), 16);
  const quadrants = instructions.filter((item) => item.quadrant !== QUADRANT.FULL);

  assert.equal(quadrants.length, 4);
  for (const inst of quadrants) {
    assert.ok(TERRAIN_INDEX.GRASS_CENTER.includes(inst.srcIndex));
  }
});

test('top-facing door (walls L+R, floor above) renders the regular door sprite', () => {
  const grid = gridOfIds(BACKEND_TILE.FLOOR.id);
  grid[1][0] = BACKEND_TILE.WALL.id;
  grid[1][2] = BACKEND_TILE.WALL.id;

  const instructions = getSewerTerrainInstructions(grid, 1, 1, BACKEND_TILE.DOOR.id);

  assert.equal(instructions.length, 1);
  assert.equal(instructions[0].srcIndex, WALL_INDEX.RAISED_DOOR);
});

test('side door (wall above) renders the RAISED_DOOR_SIDEWAYS body sprite', () => {
  const grid = gridOfIds(BACKEND_TILE.FLOOR.id);
  grid[0][1] = BACKEND_TILE.WALL.id;
  grid[2][1] = BACKEND_TILE.WALL.id;

  const instructions = getSewerTerrainInstructions(grid, 1, 1, BACKEND_TILE.DOOR.id);

  assert.equal(instructions.length, 1);
  assert.equal(instructions[0].srcIndex, WALL_INDEX.RAISED_DOOR_SIDEWAYS);
});

test('side locked door also uses RAISED_DOOR_SIDEWAYS body (state shown via overlay)', () => {
  const grid = gridOfIds(BACKEND_TILE.FLOOR.id);
  grid[0][1] = BACKEND_TILE.WALL.id;
  grid[2][1] = BACKEND_TILE.WALL.id;

  const instructions = getSewerTerrainInstructions(grid, 1, 1, BACKEND_TILE.LOCKED_DOOR.id);

  assert.equal(instructions.length, 1);
  assert.equal(instructions[0].srcIndex, WALL_INDEX.RAISED_DOOR_SIDEWAYS);
});

test('open side door still renders RAISED_DOOR_SIDEWAYS body (open state shown via wall caps, not this sprite)', () => {
  const grid = gridOfIds(BACKEND_TILE.FLOOR.id);
  grid[0][1] = BACKEND_TILE.WALL.id;
  grid[2][1] = BACKEND_TILE.WALL.id;

  const instructions = getSewerTerrainInstructions(grid, 1, 1, BACKEND_TILE.OPEN_DOOR.id, new Set(['1,1']));

  assert.equal(instructions.length, 1);
  assert.equal(instructions[0].srcIndex, WALL_INDEX.RAISED_DOOR_SIDEWAYS);
});

test('HIGH_GRASS renders floor base, grass quadrants using HIGH_GRASS_CENTER, and underhang', () => {
  const grid = gridOfIds(BACKEND_TILE.HIGH_GRASS.id, 5, 5);
  const instructions = getSewerTerrainInstructions(grid, 2, 2, BACKEND_TILE.HIGH_GRASS.id);

  const full = instructions.filter((i) => i.quadrant === QUADRANT.FULL);
  const quadrants = instructions.filter((i) => i.quadrant !== QUADRANT.FULL);

  assert.equal(full.length, 2, 'floor base and raised grass underhang');
  assert.ok(
    full.some((i) => i.srcIndex === WALL_INDEX.HIGH_GRASS_UNDERHANG || i.srcIndex === WALL_INDEX.HIGH_GRASS_UNDERHANG_ALT),
    'includes high grass underhang'
  );
  assert.equal(quadrants.length, 4, 'four terrain quadrants');
  for (const q of quadrants) {
    assert.ok(
      TERRAIN_INDEX.HIGH_GRASS_CENTER.includes(q.srcIndex),
      `HIGH_GRASS surrounded by HIGH_GRASS should use HIGH_GRASS_CENTER sprite, got ${q.srcIndex}`
    );
  }
});

test('FURROWED_GRASS renders floor base, grass quadrants using FURROWED_GRASS_CENTER, and underhang', () => {
  const grid = gridOfIds(BACKEND_TILE.FURROWED_GRASS.id, 5, 5);
  const instructions = getSewerTerrainInstructions(grid, 2, 2, BACKEND_TILE.FURROWED_GRASS.id);

  const full = instructions.filter((i) => i.quadrant === QUADRANT.FULL);
  const quadrants = instructions.filter((i) => i.quadrant !== QUADRANT.FULL);

  assert.equal(full.length, 2, 'floor base and furrowed grass underhang');
  assert.ok(
    full.some((i) => i.srcIndex === WALL_INDEX.FURROWED_UNDERHANG || i.srcIndex === WALL_INDEX.FURROWED_UNDERHANG_ALT),
    'includes furrowed grass underhang'
  );
  assert.equal(quadrants.length, 4, 'four terrain quadrants');
  for (const q of quadrants) {
    assert.ok(
      TERRAIN_INDEX.FURROWED_GRASS_CENTER.includes(q.srcIndex),
      `FURROWED_GRASS surrounded by FURROWED_GRASS should use FURROWED_GRASS_CENTER sprite, got ${q.srcIndex}`
    );
  }
});

test('EMPTY_DECO renders a single variant from EMPTY_DECO_VARIANTS', () => {
  const grid = gridOfIds(BACKEND_TILE.FLOOR.id);
  grid[1][1] = BACKEND_TILE.EMPTY_DECO.id;
  const instructions = getSewerTerrainInstructions(grid, 1, 1, BACKEND_TILE.EMPTY_DECO.id);

  assert.equal(instructions.length, 1, 'single full-tile pick');
  assert.ok(
    TERRAIN_INDEX.EMPTY_DECO_VARIANTS.includes(instructions[0].srcIndex),
    `expected an EMPTY_DECO_VARIANTS sprite, got ${instructions[0].srcIndex}`
  );
});

test('EMPTY_DECO variant is stable across calls for the same cell', () => {
  const grid = gridOfIds(BACKEND_TILE.EMPTY_DECO.id);
  const a = getSewerTerrainInstructions(grid, 3, 4, BACKEND_TILE.EMPTY_DECO.id);
  const b = getSewerTerrainInstructions(grid, 3, 4, BACKEND_TILE.EMPTY_DECO.id);
  assert.equal(a[0].srcIndex, b[0].srcIndex);
});

test('isWallTile recognises WALL, WALL_DECO and SECRET_DOOR', () => {
  assert.equal(isWallTile(BACKEND_TILE.WALL.id), true);
  assert.equal(isWallTile(BACKEND_TILE.WALL_DECO.id), true);
  assert.equal(isWallTile(BACKEND_TILE.SECRET_DOOR.id), true);
  assert.equal(isWallTile(BACKEND_TILE.HIGH_GRASS.id), false);
  assert.equal(isWallTile(BACKEND_TILE.FLOOR.id), false);
});

test('isGrassTile accepts both regular and high grass', () => {
  assert.equal(isGrassTile(BACKEND_TILE.FLOOR_GRASS.id), true);
  assert.equal(isGrassTile(BACKEND_TILE.HIGH_GRASS.id), true);
  assert.equal(isGrassTile(BACKEND_TILE.FLOOR.id), false);
});

test('isWaterStitcheable never blends water into pits or walls', () => {
  assert.equal(isWaterStitcheable(BACKEND_TILE.CHASM.id), false);
  assert.equal(isWaterStitcheable(BACKEND_TILE.VOID.id), false);
  assert.equal(isWaterStitcheable(BACKEND_TILE.WALL.id), false);
  assert.equal(isWaterStitcheable(BACKEND_TILE.FLOOR_WATER.id), false);
  assert.equal(isWaterStitcheable(BACKEND_TILE.FLOOR.id), true);
  assert.equal(isWaterStitcheable(BACKEND_TILE.FLOOR_GRASS.id), true);
});

test('CHASM stitches to the base void tile when nothing recognizable is above it', () => {
  const grid = gridOfIds(BACKEND_TILE.CHASM.id);
  const instructions = getSewerTerrainInstructions(grid, 1, 1, BACKEND_TILE.CHASM.id);
  assert.equal(instructions.length, 1);
  assert.equal(instructions[0].srcIndex, CHASM_INDEX.BASE);
  assert.equal(instructions[0].quadrant, QUADRANT.FULL);
});

test('CHASM stitches to the floor variant under a floor tile', () => {
  const grid = gridOfIds(BACKEND_TILE.CHASM.id);
  grid[0][1] = BACKEND_TILE.FLOOR.id;
  const instructions = getSewerTerrainInstructions(grid, 1, 1, BACKEND_TILE.CHASM.id);
  assert.equal(instructions[0].srcIndex, CHASM_INDEX.FLOOR);
});

test('CHASM stitches to the wall variant under a wall tile', () => {
  const grid = gridOfIds(BACKEND_TILE.CHASM.id);
  grid[0][1] = BACKEND_TILE.WALL.id;
  const instructions = getSewerTerrainInstructions(grid, 1, 1, BACKEND_TILE.CHASM.id);
  assert.equal(instructions[0].srcIndex, CHASM_INDEX.WALL);
});

test('CHASM stitches to the water variant under a water tile', () => {
  const grid = gridOfIds(BACKEND_TILE.CHASM.id);
  grid[0][1] = BACKEND_TILE.FLOOR_WATER.id;
  const instructions = getSewerTerrainInstructions(grid, 1, 1, BACKEND_TILE.CHASM.id);
  assert.equal(instructions[0].srcIndex, CHASM_INDEX.WATER);
});
