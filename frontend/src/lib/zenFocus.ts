// Focus handoff for zen mode: remembers the toggle button that opened the
// reader so closing it can return focus to that control.

let zenTrigger: HTMLElement | null = null

export function setZenTrigger(element: HTMLElement | null): void {
  zenTrigger = element
}

export function restoreZenFocus(): void {
  zenTrigger?.focus()
  zenTrigger = null
}
