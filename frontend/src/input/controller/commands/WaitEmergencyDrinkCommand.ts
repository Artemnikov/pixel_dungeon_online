import type { IKeyCommand, InputContext } from '../IKeyCommand';

export class WaitEmergencyDrinkCommand implements IKeyCommand {
  public canExecute(code: string, context: InputContext): boolean {
    if (code !== 'Space') return false;
    if (context.gameModeRef?.current === 'turnbased' && context.canActRef?.current === false) {
      return false;
    }
    return true;
  }

  public execute(_code: string, context: InputContext, isKeyDown: boolean, e?: KeyboardEvent): void {
    if (!isKeyDown) return;
    e?.preventDefault();
    if (context.emergencyDrinkItem && context.onEmergencyDrink) {
      context.onEmergencyDrink(context.emergencyDrinkItem);
    } else if (context.triggerWait) {
      context.triggerWait();
    }
  }
}
