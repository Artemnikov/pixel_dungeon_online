import type { RenderPlayer, EntitiesState, SerializedItem, Ref, AnimState } from '../../net/types';
import type { GameMode } from '../../types/contract';

export interface InputContext {
  myPlayerId: string;
  myPlayer: RenderPlayer | null;
  grid: number[][];
  entities: EntitiesState;
  socket?: WebSocket | null;
  playerAnimRef?: Ref<Record<string, AnimState>>;
  floorFadeRef?: { current: unknown };
  showItemBrowserRef?: { current: boolean };
  gameMenuOpenRef?: { current: boolean };
  isRefocusingRef?: { current: boolean };
  isDraggingRef?: { current: boolean };
  onCloseItemBrowser?: () => void;
  onOpenItemBrowser?: () => void;
  setShowInventory?: (cb: (prev: boolean) => boolean) => void;
  onExamineOrReveal?: () => void;
  onCancelModes?: () => void;
  emergencyDrinkItem?: SerializedItem | null;
  onEmergencyDrink?: (item: SerializedItem) => void;
  triggerWait?: () => void;
  /**
   * Which loop the room runs. Decides the *shape* of movement handling, so it
   * is a ref read on every key event rather than a captured value.
   */
  gameModeRef?: { current: GameMode };
  /**
   * `false` while a turn-based room is waiting on somebody else. Only
   * consulted in a turn room: a turn room drops anything sent out of turn
   * without replying, so input has to stay quiet instead of firing and hoping.
   */
  canActRef?: { current: boolean };
  onOpenTalents?: () => void;
  onOpenAlchemyRef?: { current?: () => void };
  quickslot?: { slots?: Array<{ item_id?: string }> };
  itemsById?: Record<string, SerializedItem>;
  handleToolbarDoubleClick?: (item: SerializedItem) => void;
  handleToolbarClick?: (item: SerializedItem) => void;
}

export interface IKeyCommand {
  canExecute(code: string, context: InputContext): boolean;
  execute(code: string, context: InputContext, isKeyDown: boolean, e?: KeyboardEvent): void;
}
