import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import type { RequestRow } from '../api'
import { C, channelColor, modelColor } from '../tokens'
import { TopBar, SectionLabel, Tag, StatusBadge } from '../components/atoms'
import { useHoverPreview } from '../components/HoverPreview'
import { isSelected, setLastSelected } from '../lastSelected'

const CHANNELS = ['', 'chat', 'voice', 'email', 'compare']
const STATUSES = ['', 'ok', 'error']

export function History() {
  const nav = useNavigate()
  const [channel, setChannel] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['requests', 'history', channel, status, page],
    queryFn: () => api.listRequests({
      channel: channel || undefined, status: status || undefined, page,
    }),
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const pageSize = data?.page_size ?? 50
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <TopBar title="Istorija" subtitle={`${total.toLocaleString()} poruka ukupno`} />
      <div style={{ flex: 1, overflow: 'auto', padding: '20px 28px' }}>
        <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
          <Filter label="kanal"  value={channel} options={CHANNELS} onChange={(v) => { setChannel(v); setPage(1) }} />
          <Filter label="status" value={status}  options={STATUSES}  onChange={(v) => { setStatus(v); setPage(1) }} />
        </div>

        <SectionLabel>stranica {page} / {totalPages}</SectionLabel>
        {isLoading && (
          <div style={{ color: C.textMute, fontSize: 13 }}>⠋ učitavam…</div>
        )}
        {!isLoading && items.length === 0 && (
          <div style={{ color: C.textMute, fontSize: 13 }}>Nema rezultata za ove filtere.</div>
        )}
        {items.length > 0 && (
          <table style={{
            width: '100%', borderCollapse: 'collapse',
            fontFamily: 'JetBrains Mono, monospace', fontSize: 13,
          }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${C.border}`, color: C.textMute, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                <Th>id</Th><Th>vrijeme</Th><Th>kanal</Th><Th>model</Th><Th>status</Th>
                <Th right>tokeni</Th><Th right>trajanje</Th><Th right>trošak</Th><Th>poruka</Th>
              </tr>
            </thead>
            <tbody>
              {items.map(r => <Row key={r.id} r={r} onClick={() => {
                setLastSelected('requests', r.id)
                nav(`/requests/${r.id}`)
              }} />)}
            </tbody>
          </table>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <PageBtn disabled={page <= 1} onClick={() => setPage(page - 1)}>← prethodna</PageBtn>
          <PageBtn disabled={page >= totalPages} onClick={() => setPage(page + 1)}>sledeća →</PageBtn>
        </div>
      </div>
    </div>
  )
}

function Filter({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void
}) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
      <span style={{ color: C.textMute, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
      <select value={value} onChange={e => onChange(e.target.value)} style={{
        background: C.panelLo, color: C.text, border: `1px solid ${C.border}`,
        borderRadius: 3, padding: '4px 8px', fontFamily: 'inherit', fontSize: 13,
      }}>
        {options.map(o => <option key={o} value={o}>{o || '— svi —'}</option>)}
      </select>
    </label>
  )
}

function Th({ children, right }: { children: React.ReactNode; right?: boolean }) {
  return <th style={{ textAlign: right ? 'right' : 'left', padding: '8px 10px', fontWeight: 500 }}>{children}</th>
}

function Td({ children, color, right }: { children: React.ReactNode; color?: string; right?: boolean }) {
  return <td style={{ padding: '8px 10px', textAlign: right ? 'right' : 'left', color: color ?? C.textDim }}>{children}</td>
}

function Row({ r, onClick }: { r: RequestRow; onClick: () => void }) {
  const ch = channelColor(r.channel)
  const md = modelColor(_modelKey(r.model))
  const time = new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  const selected = isSelected('requests', r.id)
  const hover = useHoverPreview()
  return (<>
    <tr
      className="dash-row"
      data-selected={selected || undefined}
      onClick={onClick}
      {...hover.handlers}
      style={{ borderBottom: `1px solid ${C.border}` }}
    >
      <Td color={C.textDim}>#{r.id}</Td>
      <Td>{time}</Td>
      <Td><Tag color={ch}>{r.channel}</Tag></Td>
      <Td><Tag color={md}>{_modelKey(r.model)}</Tag></Td>
      <Td><StatusBadge status={r.status} /></Td>
      <Td right>{r.tokens_in ?? '—'} / {r.tokens_out ?? '—'}</Td>
      <Td right>{r.latency_ms ? `${r.latency_ms}ms` : '—'}</Td>
      <Td right>{r.cost_usd != null ? `$${r.cost_usd.toFixed(4)}` : '—'}</Td>
      <Td color={C.text}>
        <span style={{ display: 'inline-block', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', verticalAlign: 'bottom' }}>
          {r.prompt_preview}
        </span>
      </Td>
    </tr>
    {hover.render(
      <div>
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: C.textMute, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 6, display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ color: ch }}>● {r.channel}</span>
          <span>·</span>
          <span style={{ color: md }}>{_modelKey(r.model)}</span>
          <span>·</span>
          <span>#{r.id}</span>
          <span>·</span>
          <span style={{ color: r.status === 'ok' ? C.ok : C.err }}>{r.status}</span>
        </div>
        <div style={{ color: C.text, fontWeight: 500, marginBottom: 8 }}>
          {r.prompt_preview || <em style={{ color: C.textMute }}>(prazno)</em>}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: C.textDim }}>
          <div><span style={{ color: C.textMute }}>tokeni:</span> <strong style={{ color: C.text }}>↓{r.tokens_in ?? '—'} ↑{r.tokens_out ?? '—'}</strong></div>
          <div><span style={{ color: C.textMute }}>iter:</span> <strong style={{ color: C.text }}>{r.iterations ?? '—'}</strong></div>
          <div><span style={{ color: C.textMute }}>trajanje:</span> <strong style={{ color: C.text }}>{r.latency_ms != null ? `${r.latency_ms}ms` : '—'}</strong></div>
          <div><span style={{ color: C.textMute }}>trošak:</span> <strong style={{ color: C.text }}>{r.cost_usd != null ? `$${r.cost_usd.toFixed(4)}` : '—'}</strong></div>
        </div>
        <div style={{ marginTop: 10, paddingTop: 8, borderTop: `1px solid ${C.border}`, fontSize: 11.5, color: C.textMute }}>
          klikni za cijelu poruku + pozive alata →
        </div>
      </div>
    )}
  </>)
}

function PageBtn({ children, disabled, onClick }: { children: React.ReactNode; disabled?: boolean; onClick: () => void }) {
  return (
    <button disabled={disabled} onClick={onClick} style={{
      padding: '6px 12px', borderRadius: 4, fontSize: 13, fontFamily: 'JetBrains Mono, monospace',
      background: C.panelHi, color: disabled ? C.textMute : C.text,
      border: `1px solid ${C.border}`, cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
    }}>{children}</button>
  )
}

function _modelKey(model: string): string {
  const m = model.toLowerCase()
  if (m.includes('haiku')) return 'haiku'
  if (m.includes('sonnet')) return 'sonnet'
  if (m.includes('opus')) return 'opus'
  return model.slice(0, 12)
}
