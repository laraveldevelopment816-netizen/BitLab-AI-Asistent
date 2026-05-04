import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import type { SessionRow } from '../api'
import { C, channelColor, modelColor } from '../tokens'
import { TopBar, SectionLabel, Tag } from '../components/atoms'
import { isSelected, setLastSelected } from '../lastSelected'

const CHANNELS = ['', 'chat', 'voice', 'email']

export function Sessions() {
  const nav = useNavigate()
  const [channel, setChannel] = useState('')
  const [pause, setPause] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['sessions', channel],
    queryFn: () => api.listSessions(channel || undefined, 1),
    refetchInterval: pause ? false : 5_000,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <TopBar
        title="Sessions"
        subtitle={`${total.toLocaleString()} razgovora · jedan red = jedna sesija (klijent + AI)`}
        right={
          <button
            onClick={() => setPause(p => !p)}
            style={{
              padding: '6px 12px', borderRadius: 4, fontSize: 12, cursor: 'pointer',
              fontFamily: 'JetBrains Mono, monospace',
              background: pause ? C.warn + '20' : C.panelHi,
              color: pause ? C.warn : C.textDim,
              border: `1px solid ${pause ? C.warn + '40' : C.border}`,
            }}
          >{pause ? '▶ resume' : '⏸ pause'} (5s polling)</button>
        }
      />
      <div style={{ flex: 1, overflow: 'auto', padding: '20px 28px' }}>
        <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
          <Filter label="channel" value={channel} options={CHANNELS} onChange={setChannel} />
        </div>

        <SectionLabel>razgovori (sortirani po posljednjoj poruci)</SectionLabel>

        {isLoading && <div style={{ color: C.textMute, fontSize: 12 }}>⠋ loading…</div>}
        {!isLoading && items.length === 0 && (
          <div style={{ color: C.textMute, fontSize: 12 }}>
            Nema sesija. Pošalji par poruka kroz widget — pojavit će se za 5s.
          </div>
        )}

        {items.length > 0 && (
          <table style={{
            width: '100%', borderCollapse: 'collapse',
            fontFamily: 'JetBrains Mono, monospace', fontSize: 12,
          }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${C.border}`, color: C.textMute, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                <Th>session</Th>
                <Th>channel</Th>
                <Th>model</Th>
                <Th right>msgs</Th>
                <Th right>tokens</Th>
                <Th right>latency</Th>
                <Th right>cost</Th>
                <Th right>err</Th>
                <Th>started</Th>
                <Th>last activity</Th>
                <Th>first prompt</Th>
              </tr>
            </thead>
            <tbody>
              {items.map(s => <Row key={s.session_id} s={s} onClick={() => {
                setLastSelected('sessions', s.session_id)
                nav(`/sessions/${s.session_id}`)
              }} />)}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function Filter({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void
}) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>
      <span style={{ color: C.textMute, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
      <select value={value} onChange={e => onChange(e.target.value)} style={{
        background: C.panelLo, color: C.text, border: `1px solid ${C.border}`,
        borderRadius: 3, padding: '4px 8px', fontFamily: 'inherit', fontSize: 12,
      }}>
        {options.map(o => <option key={o} value={o}>{o || '— any —'}</option>)}
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

function Row({ s, onClick }: { s: SessionRow; onClick: () => void }) {
  const ch = channelColor(s.channel)
  const md = modelColor(_modelKey(s.model))
  const start = new Date(s.first_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const lastDate = new Date(s.last_message_at)
  const last = lastDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  const selected = isSelected('sessions', s.session_id)
  return (
    <tr
      className="dash-row"
      data-selected={selected || undefined}
      onClick={onClick}
      style={{ borderBottom: `1px solid ${C.border}` }}
    >
      <Td color={C.textDim}>{s.session_id.slice(0, 8)}…</Td>
      <Td><Tag color={ch}>{s.channel}</Tag></Td>
      <Td><Tag color={md}>{_modelKey(s.model)}</Tag></Td>
      <Td right color={C.text}>{s.msg_count}</Td>
      <Td right>{s.total_tokens_in.toLocaleString()} / {s.total_tokens_out.toLocaleString()}</Td>
      <Td right>{s.total_latency_ms ? `${(s.total_latency_ms / 1000).toFixed(1)}s` : '—'}</Td>
      <Td right color={C.text}>{s.total_cost_usd != null ? `$${s.total_cost_usd.toFixed(4)}` : '—'}</Td>
      <Td right color={s.error_count > 0 ? C.err : C.textMute}>{s.error_count}</Td>
      <Td>{start}</Td>
      <Td>{last}</Td>
      <Td color={C.text}>
        <span style={{ display: 'inline-block', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', verticalAlign: 'bottom' }}>
          {s.first_prompt_preview}
        </span>
      </Td>
    </tr>
  )
}

function _modelKey(model: string): string {
  const m = model.toLowerCase()
  if (m.includes('haiku')) return 'haiku'
  if (m.includes('sonnet')) return 'sonnet'
  if (m.includes('opus')) return 'opus'
  return model.slice(0, 12)
}
