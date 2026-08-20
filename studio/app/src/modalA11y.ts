export type ModalA11yErrorCode = "modal_background_missing" | "modal_inert_unsupported";

export class ModalA11yError extends Error {
  readonly code: ModalA11yErrorCode;

  constructor(code: ModalA11yErrorCode, message: string = code) {
    super(message);
    this.name = "ModalA11yError";
    this.code = code;
  }
}

export type ModalA11yOptions = {
  getDialog: () => HTMLElement | undefined;
  getBackground: () => HTMLElement | undefined;
  requestClose: () => void;
  getInitialFocus?: () => HTMLElement | undefined;
  getFallbackFocus?: () => HTMLElement | undefined;
};

export type ModalA11y = {
  open: (trigger?: HTMLElement) => void;
  close: () => void;
  onKeyDown: (event: KeyboardEvent) => void;
  onOutsidePointer: (event: { target: EventTarget | null; currentTarget: EventTarget | null }) => void;
  dispose: () => void;
  isOpen: () => boolean;
};

const TABBABLE_SELECTOR = "a[href],button,input,textarea,select,summary,[tabindex]";

function availableInTree(element: HTMLElement, boundary?: HTMLElement): boolean {
  if (!element || element.isConnected === false) return false;
  let current: HTMLElement | null = element;
  while (current) {
    if (current.hidden || current.inert || current.getAttribute("aria-hidden") === "true") return false;
    if (typeof window !== "undefined" && typeof window.getComputedStyle === "function") {
      const style = window.getComputedStyle(current);
      if (style.display === "none" || style.visibility === "hidden" || style.visibility === "collapse") return false;
    }
    if (current === boundary) break;
    current = current.parentElement;
  }
  return true;
}

function focusable(element: HTMLElement, boundary?: HTMLElement): boolean {
  if (!availableInTree(element, boundary)) return false;
  if (element.hasAttribute("disabled") || ("disabled" in element && Boolean(element.disabled))) return false;
  if (typeof element.matches === "function" && element.matches(":disabled")) return false;
  return element.tabIndex >= 0;
}

export function collectTabStops(dialog: HTMLElement): HTMLElement[] {
  return Array.from(dialog.querySelectorAll<HTMLElement>(TABBABLE_SELECTOR)).filter((element) => focusable(element, dialog));
}

function safeFocus(element: HTMLElement | undefined, allowProgrammatic = false): boolean {
  if (!element || !availableInTree(element) || (!allowProgrammatic && !focusable(element))) return false;
  try {
    element.focus();
    return true;
  } catch {
    return false;
  }
}

function backgroundSnapshot(background: HTMLElement) {
  return {
    inert: Boolean(background.inert),
    hasAriaHidden: background.hasAttribute("aria-hidden"),
    ariaHidden: background.getAttribute("aria-hidden"),
  };
}

function restoreBackground(background: HTMLElement, snapshot: ReturnType<typeof backgroundSnapshot>) {
  background.inert = snapshot.inert;
  if (snapshot.hasAriaHidden) background.setAttribute("aria-hidden", snapshot.ariaHidden ?? "");
  else background.removeAttribute("aria-hidden");
}

export function createModalA11y(options: ModalA11yOptions): ModalA11y {
  let active = false;
  let generation = 0;
  let opener: HTMLElement | undefined;
  let background: HTMLElement | undefined;
  let snapshot: ReturnType<typeof backgroundSnapshot> | undefined;

  const close = () => {
    if (!active) return;
    const closeGeneration = ++generation;
    active = false;
    const ownedBackground = background;
    const ownedSnapshot = snapshot;
    const returnTarget = opener;
    background = undefined;
    snapshot = undefined;
    opener = undefined;
    if (ownedBackground && ownedSnapshot) restoreBackground(ownedBackground, ownedSnapshot);
    options.requestClose();
    queueMicrotask(() => {
      if (generation !== closeGeneration) return;
      if (safeFocus(returnTarget)) return;
      safeFocus(options.getFallbackFocus?.());
    });
  };

  const open = (trigger?: HTMLElement) => {
    if (active) return;
    const nextBackground = options.getBackground();
    if (!nextBackground) throw new ModalA11yError("modal_background_missing", "modal background is unavailable");
    if (!("inert" in nextBackground)) throw new ModalA11yError("modal_inert_unsupported", "modal background inert is unavailable");

    active = true;
    const openGeneration = ++generation;
    background = nextBackground;
    snapshot = backgroundSnapshot(nextBackground);
    const currentActive = typeof document === "undefined" ? undefined : document.activeElement;
    opener = trigger ?? (typeof HTMLElement !== "undefined" && currentActive instanceof HTMLElement ? currentActive : undefined);
    nextBackground.inert = true;

    queueMicrotask(() => {
      if (!active || generation !== openGeneration) return;
      const dialog = options.getDialog();
      const initial = options.getInitialFocus?.();
      if (!dialog || (!safeFocus(initial) && !safeFocus(dialog, true))) {
        close();
        return;
      }
      if (background && snapshot) background.setAttribute("aria-hidden", "true");
    });
  };

  const onKeyDown = (event: KeyboardEvent) => {
    if (!active) return;
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close();
      return;
    }
    if (event.key !== "Tab") return;
    const dialog = options.getDialog();
    if (!dialog) return;
    const stops = collectTabStops(dialog);
    event.preventDefault();
    if (!stops.length) {
      safeFocus(dialog, true);
      return;
    }
    const current = typeof document === "undefined" ? undefined : document.activeElement;
    const index = current ? stops.indexOf(current as HTMLElement) : -1;
    const next = event.shiftKey
      ? stops[(index <= 0 ? stops.length : index) - 1]
      : stops[(index < 0 || index === stops.length - 1 ? 0 : index + 1)];
    safeFocus(next);
  };

  const onOutsidePointer = (event: { target: EventTarget | null; currentTarget: EventTarget | null }) => {
    if (event.target === event.currentTarget) close();
  };

  const dispose = () => {
    if (!active) return;
    ++generation;
    active = false;
    if (background && snapshot) restoreBackground(background, snapshot);
    background = undefined;
    snapshot = undefined;
    opener = undefined;
  };

  return { open, close, onKeyDown, onOutsidePointer, dispose, isOpen: () => active };
}
