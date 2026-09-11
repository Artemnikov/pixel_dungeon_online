import type {
  Ref,
  EntitiesState,
  RenderPlayer,
  RenderMob,
  DyingMob,
  SerializedItem,
  RenderTrap,
  RenderPlant,
} from '../types';
import * as movementPredictor from '../movementPredictor';

export interface EntityManagerRefs {
  entitiesRef: Ref<EntitiesState>;
  dyingMobsRef?: Ref<Record<string, DyingMob>>;
  myPlayerIdRef: Ref<string | null>;
  setMyPlayerId?: (id: string) => void;
  wasDownedRef?: Ref<boolean | undefined>;
  selectedEnemyIdRef?: Ref<string | null>;
}

export class EntityManager {
  private refs: EntityManagerRefs;

  constructor(refs: EntityManagerRefs) {
    this.refs = refs;
  }

  public get entitiesRef(): Ref<EntitiesState> {
    return this.refs.entitiesRef;
  }

  public get dyingMobsRef(): Ref<Record<string, DyingMob>> | undefined {
    return this.refs.dyingMobsRef;
  }

  public get myPlayerIdRef(): Ref<string | null> {
    return this.refs.myPlayerIdRef;
  }

  public get wasDownedRef(): Ref<boolean | undefined> | undefined {
    return this.refs.wasDownedRef;
  }

  public get selectedEnemyIdRef(): Ref<string | null> | undefined {
    return this.refs.selectedEnemyIdRef;
  }

  public getMyPlayerId(): string | null {
    return this.refs.myPlayerIdRef.current;
  }

  public setMyPlayerId(id: string): void {
    this.refs.myPlayerIdRef.current = id;
    this.refs.setMyPlayerId?.(id);
  }

  public getMyPlayer(): RenderPlayer | undefined {
    const id = this.getMyPlayerId();
    return id ? this.refs.entitiesRef.current.players[id] : undefined;
  }

  public getPlayer(id: string): RenderPlayer | undefined {
    return this.refs.entitiesRef.current.players[id];
  }

  public getPlayers(): Record<string, RenderPlayer> {
    return this.refs.entitiesRef.current.players;
  }

  public getMob(id: string): RenderMob | undefined {
    return this.refs.entitiesRef.current.mobs[id];
  }

  public getMobs(): Record<string, RenderMob> {
    return this.refs.entitiesRef.current.mobs;
  }

  public getEntity(id: string): RenderPlayer | RenderMob | undefined {
    return this.getPlayer(id) ?? this.getMob(id);
  }

  public getItems(): SerializedItem[] {
    return this.refs.entitiesRef.current.items || [];
  }

  public setItems(items: SerializedItem[]): void {
    this.refs.entitiesRef.current.items = items;
  }

  public getTraps(): RenderTrap[] {
    return this.refs.entitiesRef.current.traps || [];
  }

  public setTraps(traps: RenderTrap[]): void {
    this.refs.entitiesRef.current.traps = traps;
  }

  public getPlants(): RenderPlant[] {
    return this.refs.entitiesRef.current.plants || [];
  }

  public setPlants(plants: RenderPlant[]): void {
    this.refs.entitiesRef.current.plants = plants;
  }

  public getDyingMobs(): Record<string, DyingMob> {
    return this.refs.dyingMobsRef?.current || {};
  }

  public recordDyingMob(id: string, mob: RenderMob): void {
    if (this.refs.dyingMobsRef && !this.refs.dyingMobsRef.current[id]) {
      this.refs.dyingMobsRef.current[id] = {
        ...mob,
        renderPos: { ...mob.renderPos },
        deathStart: performance.now(),
      };
    }
  }

  public reconcileLocalMovement(serverPos: { x: number; y: number }, lastSeq?: number): void {
    const myPlayer = this.getMyPlayer();
    if (myPlayer) {
      movementPredictor.reconcile(serverPos, myPlayer, lastSeq);
    }
  }

  public getSelectedEnemyId(): string | null | undefined {
    return this.refs.selectedEnemyIdRef?.current;
  }

  public setSelectedEnemyId(id: string | null): void {
    if (this.refs.selectedEnemyIdRef) {
      this.refs.selectedEnemyIdRef.current = id;
    }
  }
}
