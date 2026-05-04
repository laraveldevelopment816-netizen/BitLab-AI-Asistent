import { useEffect, useState, type ReactNode } from 'react'
import { NavLink, Link, useLocation } from 'react-router-dom'
import { C } from '../tokens'

const NAV = [
  { to: '/overview', label: 'Pregled',        hint: 'Brojevi · grafikoni · status' },
  { to: '/sessions', label: 'Razgovori',      hint: 'Sesije korisnik + AI' },
  { to: '/live',     label: 'Uživo',          hint: 'Pojedinačne poruke' },
  { to: '/history',  label: 'Istorija',       hint: 'Sve prošle poruke' },
  { to: '/compare',  label: 'Uporedi',        hint: 'Haiku ↔ Sonet' },
  { to: '/stats',    label: 'Statistika',     hint: 'Tokeni · trošak' },
  { to: '/settings', label: 'Podešavanja',    hint: 'API ključ, okruženje' },
]

export function Layout({ children }: { children: ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const location = useLocation()

  // Zatvori drawer kad se promijeni ruta (mobilni — klik na nav link)
  useEffect(() => { setDrawerOpen(false) }, [location.pathname])

  // Escape key zatvara drawer
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape' && drawerOpen) setDrawerOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [drawerOpen])

  return (
    <div className="dash-shell">
      {/* Hamburger — vidljiv samo na mobilnom (CSS controlled) */}
      <button
        className="dash-hamburger"
        aria-label="Otvori meni"
        onClick={() => setDrawerOpen(o => !o)}
      >
        {drawerOpen ? '✕' : '☰'}
      </button>

      {/* Overlay — zatamnjenje pozadine na mobilnom kad je drawer otvoren */}
      <div
        className={drawerOpen ? 'dash-overlay open' : 'dash-overlay'}
        onClick={() => setDrawerOpen(false)}
      />

      <aside className={drawerOpen ? 'dash-sidebar open' : 'dash-sidebar'}>
        <div style={{ padding: '20px 18px 18px', borderBottom: `1px solid ${C.border}` }}>
          <Link to="/overview" style={{
            display: 'flex', alignItems: 'center', gap: 10,
            textDecoration: 'none', color: 'inherit',
          }}
            title="Idi na Pregled"
          >
            <BitlabMark />
            <div>
              <div style={{
                fontFamily: 'JetBrains Mono, monospace', fontSize: 15, fontWeight: 600,
                letterSpacing: '-0.01em', color: C.text,
              }}>
                bitlab-ai
              </div>
              <div style={{
                fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: C.textMute,
                letterSpacing: '0.05em', marginTop: 1,
              }}>
                v0.8 · pregled rada
              </div>
            </div>
          </Link>
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
                    fontSize: 14, fontWeight: isActive ? 500 : 400,
                    color: isActive ? C.text : C.textDim,
                  }}>
                    {label}
                  </div>
                  <div style={{ fontSize: 11.5, color: C.textMute }}>{hint}</div>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <SidebarFooter />
      </aside>

      <main className="dash-main">
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
      fontFamily: 'JetBrains Mono, monospace', fontSize: 11.5,
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
