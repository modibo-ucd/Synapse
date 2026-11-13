import { useEffect, useRef, type MouseEvent, type ReactNode } from 'react'

interface DrawerProps {
  side: 'left' | 'right'
  open: boolean
  onClose: () => void
  label: string
  children: ReactNode
}

/** Native `<dialog>` slide-over used below `lg`. Esc and scrim-click close it. */
export function Drawer({ side, open, onClose, label, children }: DrawerProps) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) {
      dialog.showModal()
      document.body.style.overflow = 'hidden'
    } else if (!open && dialog.open) {
      dialog.close()
    }
  }, [open])

  const handleClose = () => {
    document.body.style.overflow = ''
    onClose()
  }

  const handleScrimClick = (event: MouseEvent<HTMLDialogElement>) => {
    if (event.target === event.currentTarget) {
      ref.current?.close()
    }
  }

  return (
    <dialog
      ref={ref}
      aria-label={label}
      onClose={handleClose}
      onClick={handleScrimClick}
      className={`drawer-sheet drawer-sheet-${side} scope-dark bg-side text-ink ${
        side === 'left' ? 'animate-sheet-in-left' : 'animate-sheet-in-right'
      }`}
    >
      <div className="sheet-pad h-full overflow-y-auto p-4">{children}</div>
    </dialog>
  )
}
