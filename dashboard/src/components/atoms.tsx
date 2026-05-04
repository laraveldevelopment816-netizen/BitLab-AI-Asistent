import type { ReactNode, CSSProperties } from 'react'
import { C, providerColor } from '../tokens'

// ── StatusDot ────────────────────────────────────────────────────────────────

type DotStatus = 'ok' | 'warn' | 'err' | 'rate' | 'mute' | 'accent'

const DOT_COLOR: Record<DotStatus, string> = {
  ok:     C.ok,
  warn:   C.warn,
  err:    C.err,
  rate:   C.rate,
  accent: C.accent,
  mute:   C.textMute,
}

export function StatusDot({ status, pulse }: { status: DotStatus; pulse?: boolean }) {
  const color = DOT_COLOR[status] ?? C.textMute
  return (
    <span style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 8, height: 8, flexShrink: 0 }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, boxShadow: `0 0 0 3px ${color}22`, display: 'block' }} />
      {pulse && (
        <span style={{
          position: 'absolute', top: 0, left: 0, width: 8, height: 8,
          borderRadius: '50%', background: color, opacity: 0.5,
          animation: 'pulse-ring 2s ease-out infinite',
        }} />
      )}
    </span>
  )
}

// ── Tag ──────────────────────────────────────────────────────────────────────

export function Tag({ children, color = C.textDim, subtle }: { children: ReactNode; color?: string; subtle?: boolean }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      fontFamily: 'JetBrains Mono, monospace',
      fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.04em',
      padding: '2px 6px', borderRadius: 3,
      background: color + (subtle ? '10' : '20'),
      border: `1px solid ${color}40`,
      color,
      whiteSpace: 'nowrap',
    }}>
      {children}
    </span>
  )
}

// ── StatusBadge ───────────────────────────────────────────────────────────────

export function StatusBadge({ status }: { status: string }) {
  if (status === 'ok' || status === 'done' || status === 'online')
    return <Tag color={C.ok}>200 OK</Tag>
  if (status === 'rate_limit' || status === 'rate_limited')
    return <Tag color={C.rate}>429</Tag>
  if (status === 'in_progress')
    return <Tag color={C.accent}>running</Tag>
  if (status === 'warn' || status === 'degraded')
    return <Tag color={C.warn}>degraded</Tag>
  return <Tag color={C.err}>ERR</Tag>
}

// ── AdapterPill ───────────────────────────────────────────────────────────────

export function AdapterPill({ adapter, size = 'sm' }: { adapter: string; size?: 'sm' | 'md' }) {
  const color = providerColor(adapter)
  const [fs, pad] = size === 'md' ? [12, '4px 10px'] : [11, '2px 6px']
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      fontFamily: 'JetBrains Mono, monospace', fontWeight: 500, fontSize: fs,
      padding: pad, borderRadius: 3,
      background: color + '18', border: `1px solid ${color}30`, color,
      whiteSpace: 'nowrap',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} />
      {adapter}
    </span>
  )
}

// ── Btn ───────────────────────────────────────────────────────────────────────

type BtnVariant = 'default' | 'ghost' | 'primary' | 'danger'

export function Btn({
  children, onClick, variant = 'default', disabled, style, type = 'button',
}: {
  children: ReactNode
  onClick?: () => void
  variant?: BtnVariant
  disabled?: boolean
  style?: CSSProperties
  type?: 'button' | 'submit'
}) {
  const base: CSSProperties = {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    padding: '6px 12px', borderRadius: 4,
    fontSize: 12, fontFamily: 'Inter, sans-serif', cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'background 0.12s ease, color 0.12s ease',
    opacity: disabled ? 0.4 : 1,
    outline: 'none',
  }
  const variants: Record<BtnVariant, CSSProperties> = {
    default: { background: C.panelHi, color: C.text,    border: `1px solid ${C.border}` },
    ghost:   { background: 'transparent', color: C.textDim, border: `1px solid ${C.border}` },
    primary: { background: C.accent, color: C.bg,        border: `1px solid ${C.accent}` },
    danger:  { background: C.err + '20', color: C.err,   border: `1px solid ${C.err}40` },
  }
  return (
    <button type={type} onClick={onClick} disabled={disabled} style={{ ...base, ...variants[variant], ...style }}>
      {children}
    </button>
  )
}

// ── Metric ────────────────────────────────────────────────────────────────────

export function Metric({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: boolean }) {
  return (
    <div style={{ background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4, padding: '10px 12px' }}>
      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: C.textMute, marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 18, color: accent ? C.accent : C.text, lineHeight: 1 }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5, color: C.textDim, marginTop: 3 }}>
          {sub}
        </div>
      )}
    </div>
  )
}

// ── SectionLabel ─────────────────────────────────────────────────────────────

export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <div style={{
      fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
      textTransform: 'uppercase', letterSpacing: '0.08em',
      color: C.textMute, marginBottom: 8,
    }}>
      {children}
    </div>
  )
}

// ── TopBar ────────────────────────────────────────────────────────────────────

export function TopBar({ title, subtitle, right }: { title: string; subtitle?: string; right?: ReactNode }) {
  return (
    <div style={{
      padding: '20px 28px 18px',
      borderBottom: `1px solid ${C.border}`,
      display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
      flexShrink: 0,
    }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 500, letterSpacing: '-0.02em', color: C.text }}>
          {title}
        </h1>
        {subtitle && (
          <div style={{ fontSize: 13, color: C.textDim, marginTop: 4 }}>{subtitle}</div>
        )}
      </div>
      {right && <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>{right}</div>}
    </div>
  )
}
