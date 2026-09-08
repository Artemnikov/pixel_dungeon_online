import type {
  RenderPlayer,
  EntitiesState,
  BlockingEntity,
  MoveResult,
} from './types';
import { MovementPredictor } from './movement/MovementPredictor';
import type { UnconfirmedStep } from './movement/MovementPredictor';
import { BlockerResolver } from './movement/BlockerResolver';

export { MovementPredictor, BlockerResolver };
export type { UnconfirmedStep };

export const instance = new MovementPredictor();

export function canPredict(player: RenderPlayer): boolean {
  return instance.canPredict(player);
}

export function getStepDuration(player?: RenderPlayer | null): number {
  return instance.getStepDuration(player);
}

export function primaryBlocker(blockers: BlockingEntity[]): BlockingEntity | null {
  return instance.getBlockerResolver().primaryBlocker(blockers);
}

export function isPending(): boolean {
  return instance.isPending();
}

export function getLastSentSeq(): number {
  return instance.getLastSentSeq();
}

export function getNextSeq(): number {
  return instance.getNextSeq();
}

export function getUnconfirmedSteps(): UnconfirmedStep[] {
  return instance.getUnconfirmedSteps();
}

export function redirectMove(
  player: RenderPlayer,
  dx: number,
  dy: number,
  playerId: string,
  grid: number[][],
  entities: EntitiesState,
): MoveResult & { seq?: number; replacedSeq?: number } {
  return instance.redirectMove(player, dx, dy, playerId, grid, entities);
}

export function predictMove(
  player: RenderPlayer,
  dx: number,
  dy: number,
  playerId: string,
  grid: number[][],
  entities: EntitiesState,
): MoveResult & { seq?: number; replacedSeq?: number } {
  return instance.predictMove(player, dx, dy, playerId, grid, entities);
}

export function paceStep(
  player: RenderPlayer,
  dx: number,
  dy: number,
  playerId: string,
  grid: number[][],
  entities: EntitiesState,
): MoveResult & { seq?: number; replacedSeq?: number } {
  return instance.paceStep(player, dx, dy, playerId, grid, entities);
}

export function startPath(
  player: RenderPlayer,
  steps: Array<{ dx: number; dy: number }>,
  playerId: string,
  grid: number[][],
  entities: EntitiesState,
): MoveResult & { seq?: number } {
  return instance.startPath(player, steps, playerId, grid, entities);
}

export function pacePathStep(
  player: RenderPlayer,
  playerId: string,
  grid: number[][],
  entities: EntitiesState,
): MoveResult & { seq?: number } {
  return instance.pacePathStep(player, playerId, grid, entities);
}

export function onMoveResult(
  data: { entity: string; seq?: number; x: number; y: number; ok: boolean },
  player: RenderPlayer | null,
): void {
  instance.onMoveResult(data, player);
}

export function reconcile(
  serverPosition: { x: number; y: number },
  player: RenderPlayer,
  lastProcessedSeq?: number,
): void {
  instance.reconcile(serverPosition, player, lastProcessedSeq);
}

export function clear(): void {
  instance.clear();
}

export function clearInFlight(): void {
  instance.clearInFlight();
}
