import type { Dispatch, SetStateAction } from 'react';
import type { Ref, VisionState, CustomTileLayer } from '../types';
import { isDoorTile, isWallTile } from '../../constants';
import { updateBlobArea, removeBlobArea } from '../../rendering/draw/blobArea';

const WALL_SHELL_OFFSETS: ReadonlyArray<readonly [number, number]> = [
  [-1, -1], [0, -1], [1, -1],
  [-1, 0], [1, 0],
  [-1, 1], [0, 1], [1, 1],
];

export interface WorldManagerRefs {
  gridRef: Ref<number[][]>;
  setGrid: Dispatch<SetStateAction<number[][]>>;
  visionRef: Ref<VisionState>;
  openDoorsRef?: Ref<Set<string>>;
  depthRef?: Ref<number>;
  setDepth?: (depth: number) => void;
  blobAreasRef?: Ref<Record<string, { type: string; cells: Map<string, number> }>>;
  customTilesRef?: Ref<CustomTileLayer[]>;
  customWallsRef?: Ref<CustomTileLayer[]>;
  torchesRef?: Ref<[number, number][]>;
  setExitPos?: (pos: [number, number] | null) => void;
}

export class WorldManager {
  private refs: WorldManagerRefs;

  constructor(refs: WorldManagerRefs) {
    this.refs = refs;
  }

  public get gridRef(): Ref<number[][]> {
    return this.refs.gridRef;
  }

  public get visionRef(): Ref<VisionState> {
    return this.refs.visionRef;
  }

  public get openDoorsRef(): Ref<Set<string>> | undefined {
    return this.refs.openDoorsRef;
  }

  public get blobAreasRef(): Ref<Record<string, { type: string; cells: Map<string, number> }>> | undefined {
    return this.refs.blobAreasRef;
  }

  public get depth(): number {
    return this.refs.depthRef?.current ?? 1;
  }

  public setDepth(depth: number): void {
    if (this.refs.depthRef) this.refs.depthRef.current = depth;
    this.refs.setDepth?.(depth);
  }

  public getGrid(): number[][] {
    return this.refs.gridRef.current;
  }

  public getTile(x: number, y: number): number | undefined {
    return this.refs.gridRef.current[y]?.[x];
  }

  public isVisible(x: number, y: number): boolean {
    return Boolean(this.refs.visionRef.current?.visible?.has(`${x},${y}`));
  }

  public isAudible(x?: number, y?: number, myPlayerId?: string | null): boolean {
    if (x === undefined || y === undefined) return true;
    if (myPlayerId === null || myPlayerId === undefined) return true;
    return this.isVisible(x, y);
  }

  public isOpenDoor(x: number, y: number): boolean {
    return Boolean(this.refs.openDoorsRef?.current?.has(`${x},${y}`));
  }

  public setFullGrid(grid: number[][]): void {
    this.refs.gridRef.current = grid;
    this.refs.setGrid(grid);
  }

  public patchGrid(
    tiles: Array<{ x: number; y: number; tile: number }>,
    onBarrelBroken?: (x: number, y: number) => void,
  ): void {
    this.refs.setGrid(prev => {
      if (!prev || prev.length === 0) return prev;
      const next = prev.map(row => row.slice());
      tiles.forEach(tilePatch => {
        const { x, y, tile } = tilePatch;
        if (y >= 0 && y < next.length && x >= 0 && x < next[y].length) {
          const wasBarrel = next[y][x] === 15 || next[y][x] === 16;
          next[y][x] = tile;
          if (wasBarrel && onBarrelBroken && this.isVisible(x, y)) {
            onBarrelBroken(x, y);
          }
        }
      });
      this.refs.gridRef.current = next;
      return next;
    });
  }

  public patchCustomTiles(
    patches: Array<{ texture: string; layer_y: number; row: number; col: number; tile: number }>,
  ): void {
    if (!this.refs.customTilesRef?.current || !patches?.length) return;
    for (const p of patches) {
      for (const layer of this.refs.customTilesRef.current) {
        if (layer.texture === p.texture && layer.y === p.layer_y && layer.tiles?.[p.row]) {
          layer.tiles[p.row][p.col] = p.tile;
        }
      }
    }
  }

  public updateVision(
    visibleTiles: Array<[number, number]> | undefined,
    mappedTiles?: Array<[number, number]>,
    isAdmin = false,
  ): void {
    if (visibleTiles) {
      const newVisible = new Set(visibleTiles.map(t => `${t[0]},${t[1]}`));
      const grid = this.refs.gridRef.current;
      const isShellTile = (tile: number | undefined) => isWallTile(tile) || isDoorTile(tile);

      for (const t of visibleTiles) {
        const x = t[0], y = t[1];
        if (isShellTile(grid[y]?.[x])) continue;
        for (const [dx, dy] of WALL_SHELL_OFFSETS) {
          const nx = x + dx, ny = y + dy;
          if (isShellTile(grid[ny]?.[nx])) newVisible.add(`${nx},${ny}`);
        }
      }
      this.refs.visionRef.current.visible = newVisible;
      newVisible.forEach(t => this.refs.visionRef.current.discovered.add(t));
    }

    if (mappedTiles && mappedTiles.length > 0) {
      mappedTiles.forEach(t => this.refs.visionRef.current.discovered.add(`${t[0]},${t[1]}`));
    }

    if (isAdmin && this.refs.gridRef.current.length > 0) {
      const allTiles = new Set<string>();
      for (let y = 0; y < this.refs.gridRef.current.length; y++) {
        for (let x = 0; x < this.refs.gridRef.current[0].length; x++) {
          allTiles.add(`${x},${y}`);
        }
      }
      this.refs.visionRef.current.visible = allTiles;
      allTiles.forEach(t => this.refs.visionRef.current.discovered.add(t));
    }
  }

  public updateOpenDoors(openDoors: Array<[number, number]> | undefined): void {
    if (openDoors && this.refs.openDoorsRef) {
      this.refs.openDoorsRef.current = new Set(openDoors.map(d => `${d[0]},${d[1]}`));
    }
  }

  public updateBlob(id: string, type: string, cells: Array<[number, number, number]>): void {
    if (this.refs.blobAreasRef) {
      updateBlobArea(this.refs.blobAreasRef, id, type, cells);
    }
  }

  public removeBlob(id: string): void {
    if (this.refs.blobAreasRef) {
      removeBlobArea(this.refs.blobAreasRef, id);
    }
  }

  public clearBlobs(): void {
    if (this.refs.blobAreasRef) {
      this.refs.blobAreasRef.current = {};
    }
  }

  /** Replace the custom tile overlays (e.g. HallsBossLevel's centre piece on unseal). */
  public setCustomLayers(customTiles?: CustomTileLayer[], customWalls?: CustomTileLayer[]): void {
    if (customTiles && this.refs.customTilesRef) this.refs.customTilesRef.current = customTiles;
    if (customWalls && this.refs.customWallsRef) this.refs.customWallsRef.current = customWalls;
  }

  public initFloor(data: {
    grid: number[][];
    depth?: number;
    customTiles?: CustomTileLayer[];
    customWalls?: CustomTileLayer[];
    torches?: [number, number][];
    exitPos?: [number, number] | null;
  }): void {
    this.setFullGrid(data.grid);
    this.refs.visionRef.current.discovered = new Set();
    if (this.refs.customTilesRef) this.refs.customTilesRef.current = data.customTiles || [];
    if (this.refs.customWallsRef) this.refs.customWallsRef.current = data.customWalls || [];
    if (this.refs.torchesRef) this.refs.torchesRef.current = data.torches || [];
    if (typeof data.depth === 'number') this.setDepth(data.depth);
    if (this.refs.setExitPos) this.refs.setExitPos(data.exitPos ?? null);
    this.clearBlobs();
  }
}
