import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import type { RequestRow } from '../api'
import { C, channelColor, modelColor } from '../tokens'
import { TopBar, SectionLabel, Tag, StatusBadge } from '../components/atoms'

export function Live() {
  const nav = useNavigate()
  const [pause, setPause] = useState(false)
  const lastSeen = useRef<number>(0)
  const [freshIds, setFreshIds] = useState<Set<number>>(new Set())

  const { data, isLoading } = useQuery({
    queryKey: ['requests', 'live'],
    queryFn: () => api.listRequests({ page: 1 }),
    refetchInterval: pause ? false : 5_000,
  })

  // Fresh-row highlight 1.5s
  useEffect(() => {
    if (!data?.items) return
    const newIds = new Set<number>()
    for (const r of data.items) {
      if (r.id > lastSeen.current) newIds.add(r.id)
    }
    if (newIds.size && lastSeen.current > 0) {
      setFreshIds(newIds)
      const t = setTimeout(() => setFreshIds(new Set()), 1500)
      return () => clearTimeout(t)
    }
    if (data.items.length) {
      lastSeen.current = Math.max(...data.items.map(r => r.id))
    }
  }, [data])

  const items = data?.items ?? []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <TopBar
        title="Live"
        subtitle="Real-time stream sa svih kanala (chat · voice · email · compare)"
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
          >
            {pause ? '▶ resume' : '⏸ pause'} (5s polling)
          </button>
        }
      />
      <div style={{ flex: 1, overflow: 'auto', padding: '20px 28px' }}>
        <SectionLabel>last 50 requests</SectionLabel>
        {isLoading && (
          <div style={{ color: C.textMute, fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
            ⠋ loading…
          </div>
        )}
        {!isLoading && items.length === 0 && (
          <div style={{ color: C.textMute, fontSize: 12 }}>
            Nema zalogovanih request-a još. Pokreni jedan curl ili otvori chat widget.
          </div>
        )}
        {items.length > 0 && (
          <table style={{
            width: '100%', borderCollapse: 'collapse',
            fontFamily: 'JetBrains Mono, monospace', fontSize: 12,
          }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${C.border}`, color: C.textMute, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                <Th>id</Th>
                <Th>channel</Th>
                <Th>model</Th>
                <Th>status</Th>
                <Th right>tokens ↓ ↑</Th>
                <Th right>latency</Th>
                <Th right>cost</Th>
                <Th>prompt</Th>
              </tr>
            </thead>
            <tbody>
              {items.map(r => (
                <Row key={r.id} r={r} fresh={freshIds.has(r.id)} onClick={() => nav(`/requests/${r.id}`)} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function Th({ children, right }: { children: React.ReactNode; right?: boolean }) {
  return (
    <th style={{ textAlign: right ? 'right' : 'left', padding: '8px 10px', fontWeight: 500 }}>
      {children}
    </th>
  )
}

function Row({ r, fresh, onClick }: { r: RequestRow; fresh: boolean; onClick: () => void }) {
  const ch = channelColor(r.channel)
  const md = modelColor(_modelKey(r.model))
  return (
    <tr
      onClick={onClick}
      style={{
        cursor: 'pointer',
        background: fresh ? `${C.bitlab}18` : 'transparent',
        borderBottom: `1px solid ${C.border}`,
        transition: 'background 0.6s ease',
      }}
    >
      <Td color={C.textDim}>#{r.id}</Td>
      <Td><Tag color={ch}>{r.channel}</Tag></Td>
      <Td><Tag color={md}>{_modelKey(r.model)}</Tag></Td>
      <Td><StatusBadge status={r.status} /></Td>
      <Td right>{r.tokens_in ?? '—'} / {r.tokens_out ?? '—'}</Td>
      <Td right>{r.latency_ms ? `${r.latency_ms}ms` : '—'}</Td>
      <Td right>{r.cost_usd != null ? `$${r.cost_usd.toFixed(4)}` : '—'}</Td>
      <Td color={C.text}>
        <span style={{ display: 'inline-block', maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', verticalAlign: 'bottom' }}>
          {r.prompt_preview}
        </span>
      </Td>
    </tr>
  )
}

function Td({ children, color, right }: { children: React.ReactNode; color?: string; right?: boolean }) {
  return (
    <td style={{ padding: '8px 10px', textAlign: right ? 'right' : 'left', color: color ?? C.textDim }}>
      {children}
    </td>
  )
}

function _modelKey(model: string): string {
  const m = model.toLowerCase()
  if (m.includes('haiku')) return 'haiku'
  if (m.includes('sonnet')) return 'sonnet'
  if (m.includes('opus')) return 'opus'
  return model.slice(0, 12)
}
