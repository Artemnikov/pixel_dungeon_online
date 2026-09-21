export const WindowLevel = {
  BASE: 500,
  SECONDARY: 600,
  DIALOG: 700,
  SYSTEM: 800,
  FLOATING: 900,
} as const;

export type WindowLevelValue = (typeof WindowLevel)[keyof typeof WindowLevel] | number;

export const WindowBackdrop = {
  DIM: 'dim',
  DARK: 'dark',
  NONE: 'none',
  CUSTOM: 'custom',
} as const;

export type WindowBackdropValue = (typeof WindowBackdrop)[keyof typeof WindowBackdrop];

export type KeyHandlerResult = boolean | void;

export interface IWindowKeyHandler {
  onKeyDown?(code: string, e?: KeyboardEvent, context?: unknown): KeyHandlerResult;
  onKeyUp?(code: string, e?: KeyboardEvent, context?: unknown): KeyHandlerResult;
}

export interface WindowEntry extends IWindowKeyHandler {
  id: string;
  level?: WindowLevelValue;
  onClose?: () => void;
  closeOnEscape?: boolean;
  closeOnBackdrop?: boolean;
  backdrop?: WindowBackdropValue;
  order?: number;
  /**
   * Whether unhandled keyboard events should be trapped by the modal layer.
   * Defaults to true.
   */
  modal?: boolean;
  /**
   * Action callbacks mapped to 1-based digit keys (Digit1 -> index 0, Digit2 -> index 1, etc.).
   */
  digitActions?: Array<((e?: KeyboardEvent) => void) | null>;
}
