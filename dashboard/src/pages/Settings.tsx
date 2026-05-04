import { useState } from 'react'
import { C } from '../tokens'
import { TopBar, SectionLabel, Btn } from '../components/atoms'

export function Settings() {
  const [key, setKey] = useState(() => localStorage.getItem('bitlab.dashboardKey') || '')
  const [saved, setSaved] = useState(false)

  function save() {
    if (key.trim()) {
      localStorage.setItem('bitlab.dashboardKey', key.trim())
    } else {
      localStorage.removeItem('bitlab.dashboardKey')
    }
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
    // Force reload tako da TanStack Query povuče svježe sa novim ključem
    setTimeout(() => window.location.reload(), 600)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <TopBar title="Podešavanja" subtitle="API ključ i konekcija na backend" />
      <div style={{ flex: 1, overflow: 'auto', padding: '20px 28px', maxWidth: 720 }}>
        <div style={{ marginBottom: 24 }}>
          <SectionLabel>API ključ (Bearer)</SectionLabel>
          <div style={{ fontSize: 12, color: C.textDim, marginBottom: 8, lineHeight: 1.5 }}>
            Unesi <code style={{ background: C.panelLo, padding: '1px 6px', borderRadius: 3, fontFamily: 'JetBrains Mono, monospace' }}>DASHBOARD_API_KEY</code> iz tvog
            <code style={{ background: C.panelLo, padding: '1px 6px', borderRadius: 3, fontFamily: 'JetBrains Mono, monospace', marginLeft: 4 }}>.env</code> fajla.
            Čuva se lokalno u browser-u (localStorage); backend prima kao Bearer header.
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="password"
              value={key}
              onChange={e => setKey(e.target.value)}
              placeholder="zaljepi API ključ…"
              style={{
                flex: 1, padding: '8px 12px', borderRadius: 4, fontSize: 12,
                fontFamily: 'JetBrains Mono, monospace',
                background: C.panelLo, color: C.text, border: `1px solid ${C.border}`,
                outline: 'none',
              }}
            />
            <Btn variant="primary" onClick={save}>{saved ? '✓ sačuvano' : 'sačuvaj'}</Btn>
          </div>
        </div>

        <div style={{ marginBottom: 24 }}>
          <SectionLabel>okruženje</SectionLabel>
          <table style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
            <tbody>
              <Row k="API ruta"             v="/api/dashboard" />
              <Row k="proxy u dev modu"     v="http://localhost:8000" />
              <Row k="autorizacija"         v="Bearer (localStorage)" />
              <Row k="osvježavanje liste"   v="5s (Uživo, Razgovori), 10s (Statistika)" />
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <tr>
      <td style={{ padding: '4px 16px 4px 0', color: C.textMute }}>{k}</td>
      <td style={{ padding: '4px 0', color: C.text }}>{v}</td>
    </tr>
  )
}
