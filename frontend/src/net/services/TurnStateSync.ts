import type { GameMode, TurnState } from '../../types/contract';

/**
 * Which loop the room runs, and whose turn it is.
 *
 * Both are needed before the first gameplay frame: a turn-based room has to
 * swap out movement prediction and gate actions, and it learns the mode from
 * the connect INIT while the first turn state only arrives on the first
 * STATE_UPDATE.
 */
export const GAME_MODE_REALTIME: GameMode = 'realtime';
export const GAME_MODE_TURNBASED: GameMode = 'turnbased';

export class TurnStateSync {
  private gameMode: GameMode = GAME_MODE_REALTIME;
  private setters: {
    setGameMode?: (mode: GameMode) => void;
    setTurnState?: (state: TurnState | null) => void;
  };

  constructor(setters: TurnStateSync['setters']) {
    this.setters = setters;
  }

  /** Recorded from INIT, so it is known before the first state frame. */
  public setGameMode(mode: GameMode | null | undefined): void {
    const resolved = mode || GAME_MODE_REALTIME;
    this.gameMode = resolved;
    this.setters.setGameMode?.(resolved);
  }

  public getGameMode(): GameMode {
    return this.gameMode;
  }

  public syncTurnState(state: TurnState | null | undefined): void {
    this.setters.setTurnState?.(state ?? null);
  }
}

/**
 * Whether a client may spend time right now.
 *
 * A turn-based room is server-authoritative about this: `submit_turn_action`
 * drops anything sent out of turn with no rejection frame, so the client has
 * to stay quiet instead of firing and hoping. Real-time rooms are never gated.
 */
export function canActNow(gameMode: GameMode, turn: TurnState | null): boolean {
  if (gameMode !== GAME_MODE_TURNBASED) return true;
  return turn?.is_my_turn === true;
}
