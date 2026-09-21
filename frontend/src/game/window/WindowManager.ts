import { WindowLevel } from './WindowTypes';
import type { WindowEntry } from './WindowTypes';

export type EscapeFallback = () => boolean;

export class WindowManager {
  private windows: Map<string, WindowEntry> = new Map();
  private seq = 0;
  private fallbackHandler: EscapeFallback | null = null;
  private listeners: Set<() => void> = new Set();

  public register(entry: WindowEntry): void {
    const existing = this.windows.get(entry.id);
    entry.order = entry.order ?? existing?.order ?? ++this.seq;
    entry.level = entry.level ?? existing?.level ?? WindowLevel.BASE;
    this.windows.set(entry.id, entry);
    this.notify();
  }

  public update(id: string, partial: Partial<WindowEntry>): void {
    const existing = this.windows.get(id);
    if (!existing) return;
    Object.defineProperties(existing, Object.getOwnPropertyDescriptors(partial));
    this.notify();
  }

  public unregister(id: string): void {
    if (this.windows.delete(id)) {
      this.notify();
    }
  }

  public getWindows(): WindowEntry[] {
    return Array.from(this.windows.values()).sort((a, b) => {
      const levelDiff = (b.level ?? WindowLevel.BASE) - (a.level ?? WindowLevel.BASE);
      if (levelDiff !== 0) return levelDiff;
      return (b.order ?? 0) - (a.order ?? 0);
    });
  }

  public getTopWindow(): WindowEntry | null {
    const sorted = this.getWindows();
    return sorted.length > 0 ? sorted[0] : null;
  }

  public hasActiveWindows(): boolean {
    return this.windows.size > 0;
  }

  public setFallbackHandler(handler: EscapeFallback | null): () => void {
    this.fallbackHandler = handler;
    return () => {
      if (this.fallbackHandler === handler) {
        this.fallbackHandler = null;
      }
    };
  }

  public handleEscape(): boolean {
    const top = this.getTopWindow();
    if (top) {
      if (top.closeOnEscape === false) {
        return true;
      }
      if (typeof top.onClose === 'function') {
        top.onClose();
        return true;
      }
    }

    if (this.fallbackHandler) {
      return this.fallbackHandler();
    }

    return false;
  }

  public handleKeyDown(code: string, e?: KeyboardEvent, context?: unknown): boolean {
    const top = this.getTopWindow();
    if (!top) return false;

    if (/^Digit[1-9]$/.test(code) && top.digitActions && top.digitActions.length > 0) {
      const digit = parseInt(code.replace('Digit', ''), 10);
      const actionIndex = digit - 1;
      if (actionIndex >= 0 && actionIndex < top.digitActions.length) {
        const action = top.digitActions[actionIndex];
        if (typeof action === 'function') {
          action(e);
          return true;
        }
      }
    }

    if (typeof top.onKeyDown === 'function') {
      const handled = top.onKeyDown(code, e, context);
      if (handled === true) return true;
    }

    if (code === 'Escape') {
      return this.handleEscape();
    }

    return top.modal ?? true;
  }

  public handleKeyUp(code: string, e?: KeyboardEvent, context?: unknown): boolean {
    const top = this.getTopWindow();
    if (!top) return false;

    if (typeof top.onKeyUp === 'function') {
      const handled = top.onKeyUp(code, e, context);
      if (handled === true) return true;
    }

    return false;
  }

  public clear(): void {
    this.windows.clear();
    this.notify();
  }

  public subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify(): void {
    for (const listener of this.listeners) {
      try {
        listener();
      } catch (err) {
        void err;
      }
    }
  }
}

export const windowManager = new WindowManager();
