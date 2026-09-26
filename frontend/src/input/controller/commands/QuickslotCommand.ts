import type { IKeyCommand, InputContext } from '../IKeyCommand';
import { DoubleTapTracker } from '../DoubleTapTracker';

const QUICKSLOT_DIGITS = new Set(['Digit1', 'Digit2', 'Digit3', 'Digit4', 'Digit5', 'Digit6']);

export class QuickslotCommand implements IKeyCommand {
  private doubleTapTracker: DoubleTapTracker;

  constructor(doubleTapTracker = new DoubleTapTracker()) {
    this.doubleTapTracker = doubleTapTracker;
  }

  public canExecute(code: string, context: InputContext): boolean {
    if (!QUICKSLOT_DIGITS.has(code)) return false;
    // Using an item spends a turn, so a turn room must not hear it out of turn.
    if (context.gameModeRef?.current === 'turnbased' && context.canActRef?.current === false) {
      return false;
    }
    return true;
  }

  public execute(code: string, context: InputContext, isKeyDown: boolean): void {
    if (!isKeyDown) return;
    const index = parseInt(code.slice(-1)) - 1;
    const slot = context.quickslot?.slots?.[index];
    const itemId = slot?.item_id;
    const item = itemId ? (context.itemsById?.[itemId] || null) : null;
    if (!item) return;

    if (this.doubleTapTracker.isDoubleTap(code)) {
      context.handleToolbarDoubleClick?.(item);
    } else {
      context.handleToolbarClick?.(item);
    }
  }

  public reset(): void {
    this.doubleTapTracker.reset();
  }
}
