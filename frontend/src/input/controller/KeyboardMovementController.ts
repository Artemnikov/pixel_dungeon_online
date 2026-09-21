import type { InputContext } from './IKeyCommand';
import { KeyActionRegistry } from './KeyActionRegistry';
import { DirectionalMoveCommand } from './commands/DirectionalMoveCommand';
import { QuickslotCommand } from './commands/QuickslotCommand';
import { InventoryToggleCommand } from './commands/InventoryToggleCommand';
import { TalentsToggleCommand } from './commands/TalentsToggleCommand';
import { WaitEmergencyDrinkCommand } from './commands/WaitEmergencyDrinkCommand';
import { ExamineCommand } from './commands/ExamineCommand';
import { CancelModesCommand } from './commands/CancelModesCommand';
import { AdminBrowserCommand } from './commands/AdminBrowserCommand';
import { isFloorFadeActive } from '../../rendering/floorTransition';
import { getVector } from '../directionUtils';
import { windowManager } from '../../game/window/WindowManager';

export class KeyboardMovementController {
  private pressedKeys = new Set<string>();
  private registry = new KeyActionRegistry();
  private directionalMoveCmd: DirectionalMoveCommand;
  private quickslotCmd: QuickslotCommand;
  private pumpRaf: number | null = null;
  private boundKeyDown: ((e: KeyboardEvent) => void) | null = null;
  private boundKeyUp: ((e: KeyboardEvent) => void) | null = null;
  private getContext: () => InputContext;

  constructor(getContext: () => InputContext) {
    this.getContext = getContext;
    this.directionalMoveCmd = new DirectionalMoveCommand(this.pressedKeys, (hasHeld) => {
      if (hasHeld) {
        this.ensurePumping();
      } else {
        this.stopPumping();
      }
    });
    this.quickslotCmd = new QuickslotCommand();

    this.registry.register(this.directionalMoveCmd);
    this.registry.register(this.quickslotCmd);
    this.registry.register(new InventoryToggleCommand());
    this.registry.register(new TalentsToggleCommand());
    this.registry.register(new WaitEmergencyDrinkCommand());
    this.registry.register(new ExamineCommand());
    this.registry.register(new CancelModesCommand());
    this.registry.register(new AdminBrowserCommand());
  }

  public attach(win: Window = window): void {
    this.boundKeyDown = (e: KeyboardEvent) => this.handleKeyDown(e);
    this.boundKeyUp = (e: KeyboardEvent) => this.handleKeyUp(e);

    win.addEventListener('keydown', this.boundKeyDown);
    win.addEventListener('keyup', this.boundKeyUp);
  }

  public detach(win: Window = window): void {
    if (this.boundKeyDown) win.removeEventListener('keydown', this.boundKeyDown);
    if (this.boundKeyUp) win.removeEventListener('keyup', this.boundKeyUp);
    this.stopPumping();
    this.pressedKeys.clear();
    this.directionalMoveCmd.reset();
    this.quickslotCmd.reset();
  }

  private handleKeyDown(e: KeyboardEvent): void {
    if (e.repeat) return;
    const context = this.getContext();

    const tag = (e.target as HTMLElement)?.tagName;
    const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable;

    if (isInput) {
      if (e.code === 'Escape') {
        (e.target as HTMLElement)?.blur();
      }
      return;
    }

    if (windowManager.hasActiveWindows()) {
      const consumed = windowManager.handleKeyDown(e.code, e, context);
      if (consumed) {
        return;
      }
    }

    if (isFloorFadeActive(context.floorFadeRef)) return;

    this.pressedKeys.add(e.code);
    this.registry.dispatch(e.code, context, true, e);
  }

  private handleKeyUp(e: KeyboardEvent): void {
    this.pressedKeys.delete(e.code);
    const context = this.getContext();

    if (windowManager.hasActiveWindows()) {
      const consumed = windowManager.handleKeyUp(e.code, e, context);
      if (consumed) return;
    }

    this.registry.dispatch(e.code, context, false, e);
  }

  private ensurePumping(): void {
    if (this.pumpRaf === null) {
      this.pumpRaf = requestAnimationFrame(() => this.pumpSteps());
    }
  }

  private stopPumping(): void {
    if (this.pumpRaf !== null) {
      cancelAnimationFrame(this.pumpRaf);
      this.pumpRaf = null;
    }
  }

  private pumpSteps(): void {
    this.pumpRaf = null;
    const context = this.getContext();
    if (!isFloorFadeActive(context.floorFadeRef)) {
      this.directionalMoveCmd.paceStep(context);
    }
    const { dx, dy } = getVector(this.pressedKeys);
    if (dx !== 0 || dy !== 0) {
      this.pumpRaf = requestAnimationFrame(() => this.pumpSteps());
    }
  }
}
