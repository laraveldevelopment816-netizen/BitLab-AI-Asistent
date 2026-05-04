import { useEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { C } from '../tokens'

/**
 * Hover preview hook + popover komponenta.
 *
 * Usage:
 *   const hover = useHoverPreview()
 *   <tr {...hover.handlers}>...</tr>
 *   {hover.render(<div>...sadržaj...</div>)}
 *
 * Pojavi se sa delay-om (default 600ms) kad korisnik zadrži miš na elementu.
 * Pozicija se računa relativno na viewport iz mouse coords pri enter-u.
 * Auto-hide na mouse leave + clearTimeout ako leave prije delay-a.
 */
export function useHoverPreview(delayMs = 600) {
  const [visible, setVisible] = useState(false)
  const [pos, setPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 })
  const timerRef = useRef<number | null>(null)

  function clearTimer() {
    if (timerRef.current != null) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }

  function onMouseEnter(e: React.MouseEvent) {
    clearTimer()
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    // Pozicioniraj desno od reda, vertikalno na sredini
    setPos({ x: e.clientX + 16, y: rect.top + rect.height / 2 })
    timerRef.current = window.setTimeout(() => setVisible(true), delayMs)
  }

  function onMouseMove(e: React.MouseEvent) {
    if (visible) {
      // Update position dok se kreće (smooth follow)
      const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
      setPos({ x: e.clientX + 16, y: rect.top + rect.height / 2 })
    }
  }

  function onMouseLeave() {
    clearTimer()
    setVisible(false)
  }

  useEffect(() => () => clearTimer(), [])

  function render(content: ReactNode) {
    if (!visible) return null
    return createPortal(
      <HoverPopover x={pos.x} y={pos.y}>{content}</HoverPopover>,
      document.body
    )
  }

  return {
    handlers: { onMouseEnter, onMouseMove, onMouseLeave },
    render,
    visible,
  }
}


function HoverPopover({ x, y, children }: { x: number; y: number; children: ReactNode }) {
  // Provjera da popover ne izlazi iz viewport-a desno; ako da, prikaži lijevo.
  // Compute poslije render-a kroz ref + getBoundingClientRect.
  const ref = useRef<HTMLDivElement | null>(null)
  const [adjusted, setAdjusted] = useState<{ left: number; top: number } | null>(null)

  useEffect(() => {
    if (!ref.current) return
    const rect = ref.current.getBoundingClientRect()
    let left = x
    let top = y - rect.height / 2
    if (left + rect.width > window.innerWidth - 8) {
      left = x - rect.width - 32  // postavi lijevo od kursora
    }
    if (top < 8) top = 8
    if (top + rect.height > window.innerHeight - 8) {
      top = window.innerHeight - rect.height - 8
    }
    setAdjusted({ left, top })
  }, [x, y])

  const baseStyle: React.CSSProperties = {
    position: 'fixed',
    pointerEvents: 'none',  // ne ometa hover na red ispod
    zIndex: 1000,
    maxWidth: 480, minWidth: 320,
    background: C.panel,
    border: `1px solid ${C.borderHi}`,
    borderRadius: 6,
    boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
    padding: '12px 14px',
    fontSize: 12.5, lineHeight: 1.5,
    color: C.text,
    opacity: adjusted ? 1 : 0,  // sakrij dok ne računamo poziciju (sprečava flicker)
    transition: 'opacity 0.12s ease',
  }

  return (
    <div
      ref={ref}
      style={{
        ...baseStyle,
        left: adjusted ? adjusted.left : x,
        top: adjusted ? adjusted.top : y,
      }}
    >
      {children}
    </div>
  )
}
