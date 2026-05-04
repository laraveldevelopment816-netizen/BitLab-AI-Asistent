import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { C } from '../tokens'

const NAV = [
  { to: '/live',     label: 'Live',     hint: 'Real-time stream' },
  { to: '/history',  label: 'History',  hint: 'All past requests' },
  { to: '/compare',  label: 'Compare',  hint: 'Haiku ↔ Sonnet' },
  { to: '/stats',    label: 'Stats',    hint: 'Tokens · cost' },
  { to: '/settings', label: 'Settings', hint: 'API key, env' },
]

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: C.bg }}>
      <aside style={{
        width: 232, flexShrink: 0,
        background: C.panelLo,
        borderRight: `1px solid ${C.border}`,
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        <div style={{ padding: '20px 18px 18px', borderBottom: `1px solid ${C.border}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <BitlabMark />
            <div>
              <div style={{
                fontFamily: 'JetBrains Mono, monospace', fontSize: 15, fontWeight: 600,
                letterSpacing: '-0.01em', color: C.text,
              }}>
                bitlab-ai
              </div>
              <div style={{
                fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: C.textMute,
                letterSpacing: '0.05em', marginTop: 1,
              }}>
                v0.8 · dashboard
              </div>
            </div>
          </div>
        </div>

        <nav style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          {NAV.map(({ to, label, hint }) => (
            <NavLink key={to} to={to} style={({ isActive }) => ({
              display: 'block',
              padding: '8px 12px',
              margin: '1px 0',
              textDecoration: 'none',
              background:    isActive ? `${C.bitlab}14` : 'transparent',
              borderLeft:    isActive ? `2px solid ${C.bitlab}` : '2px solid transparent',
              transition: 'background 0.12s ease',
            })}>
              {({ isActive }) => (
                <>
                  <div style={{
                    fontSize: 13, fontWeight: isActive ? 500 : 400,
                    color: isActive ? C.text : C.textDim,
                  }}>
                    {label}
                  </div>
                  <div style={{ fontSize: 10.5, color: C.textMute }}>{hint}</div>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <SidebarFooter />
      </aside>

      <main style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {children}
      </main>
    </div>
  )
}

function BitlabMark() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="6" fill={C.bitlab} />
      <text x="16" y="22" textAnchor="middle"
            fontFamily="JetBrains Mono, monospace" fontSize="14" fontWeight="700"
            fill="#0b0d10">bL</text>
    </svg>
  )
}

function SidebarFooter() {
  return (
    <div style={{
      padding: '12px 16px',
      borderTop: `1px solid ${C.border}`,
      fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5,
      color: C.textMute,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
        <span>api</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%', background: C.ok, display: 'inline-block',
          }} />
          :8000
        </span>
      </div>
      <div style={{
        borderTop: `1px dashed ${C.border}`, paddingTop: 6, marginTop: 4, color: C.textMute,
      }}>
        webshop.bitlab.rs
      </div>
    </div>
  )
}
