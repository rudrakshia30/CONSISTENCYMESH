export function announceToScreenReader(message: string): void {
  const element = document.createElement("div");
  element.setAttribute("aria-live", "polite");
  element.setAttribute("aria-atomic", "true");
  element.classList.add("sr-only");
  element.style.position = "absolute";
  element.style.width = "1px";
  element.style.height = "1px";
  element.style.padding = "0";
  element.style.margin = "-1px";
  element.style.overflow = "hidden";
  element.style.clip = "rect(0, 0, 0, 0)";
  element.style.whiteSpace = "nowrap";
  element.style.border = "0";
  document.body.appendChild(element);
  
  setTimeout(() => {
    element.textContent = message;
  }, 100);

  setTimeout(() => {
    document.body.removeChild(element);
  }, 3000);
}

export function trapFocus(element: HTMLElement): () => void {
  const focusableElements = element.querySelectorAll(
    'a[href], button, textarea, input[type="text"], input[type="radio"], input[type="checkbox"], select, [tabindex]:not([tabindex="-1"])'
  );
  
  if (focusableElements.length === 0) return () => {};

  const firstFocusable = focusableElements[0] as HTMLElement;
  const lastFocusable = focusableElements[focusableElements.length - 1] as HTMLElement;

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key !== 'Tab') return;

    if (e.shiftKey) {
      if (document.activeElement === firstFocusable) {
        lastFocusable.focus();
        e.preventDefault();
      }
    } else {
      if (document.activeElement === lastFocusable) {
        firstFocusable.focus();
        e.preventDefault();
      }
    }
  };

  element.addEventListener('keydown', handleKeyDown);
  
  return () => {
    element.removeEventListener('keydown', handleKeyDown);
  };
}

export const ARIA_ROLES = {
  ALERT: 'alert',
  DIALOG: 'dialog',
  PROGRESSBAR: 'progressbar',
  STATUS: 'status',
  REGION: 'region',
} as const;

export const ARIA_PROPS = {
  HIDDEN: 'aria-hidden',
  LIVE: 'aria-live',
  DESCRIBEDBY: 'aria-describedby',
  LABELLEDBY: 'aria-labelledby',
  EXPANDED: 'aria-expanded',
  SELECTED: 'aria-selected',
} as const;
