import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import type { ToolCall } from '../api'
import { C, channelColor, modelColor } from '../tokens'
import { TopBar, SectionLabel, Tag, StatusBadge, Metric, Btn } from '../components/atoms'

export function RequestDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const requestId = Number(id)

  const { data: r, isLoading, error } = useQuery({
    queryKey: ['request', requestId],
    queryFn: () => api.getRequest(requestId),
    enabled: !!requestId,
  })

  if (isLoading) {
    return <div style={{ padding: 28, color: C.textMute, fontSize: 12 }}>⠋ loading…</div>
  }
  if (error || !r) {
    return <div style={{ padding: 28, color: C.err, fontSize: 12 }}>Request #{id} nije pronađen.</div>
  }

  const ch = channelColor(r.channel)
  const md = modelColor(_modelKey(r.model))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <TopBar
        title={`Request #${r.id}`}
        subtitle={`${new Date(r.created_at).toLocaleString()} · ${r.adapter}`}
        right={<Btn variant="ghost" onClick={() => nav(-1)}>← back</Btn>}
      />

      <div style={{ flex: 1, overflow: 'auto', padding: '20px 28px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Top metrics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
          <Metric label="status" value={r.status} accent={r.status === 'ok'} />
          <Metric label="iterations" value={String(r.iterations ?? '—')} />
          <Metric label="tokens" value={`↓${r.tokens_in ?? '—'} ↑${r.tokens_out ?? '—'}`} />
          <Metric label="latency" value={r.latency_ms ? `${r.latency_ms}ms` : '—'} />
          <Metric label="cost" value={r.cost_usd != null ? `$${r.cost_usd.toFixed(4)}` : '—'} />
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <Tag color={ch}>{r.channel}</Tag>
          <Tag color={md}>{_modelKey(r.model)}</Tag>
          <StatusBadge status={r.status} />
          {r.compare_group_id && (
            <Tag color={C.warn}>compare {r.compare_group_id.slice(0, 8)}</Tag>
          )}
        </div>

        <div>
          <SectionLabel>prompt</SectionLabel>
          <pre style={{
            background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4,
            padding: 12, color: C.text, fontFamily: 'JetBrains Mono, monospace',
            fontSize: 12, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
          }}>{r.prompt}</pre>
        </div>

        {r.error && (
          <div>
            <SectionLabel>error</SectionLabel>
            <pre style={{
              background: `${C.err}10`, border: `1px solid ${C.err}40`, borderRadius: 4,
              padding: 12, color: C.err, fontFamily: 'JetBrains Mono, monospace',
              fontSize: 12, whiteSpace: 'pre-wrap', margin: 0,
            }}>{r.error}</pre>
          </div>
        )}

        <div>
          <SectionLabel>tool calls timeline ({r.tool_calls.length})</SectionLabel>
          {r.tool_calls.length === 0 && (
            <div style={{ color: C.textMute, fontSize: 12 }}>Bez tool poziva.</div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {r.tool_calls.map((tc, i) => <ToolCallRow key={i} tc={tc} />)}
          </div>
        </div>

        <div>
          <SectionLabel>response</SectionLabel>
          <pre style={{
            background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4,
            padding: 12, color: C.text, fontFamily: 'JetBrains Mono, monospace',
            fontSize: 12, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
          }}>{r.response || '—'}</pre>
        </div>
      </div>
    </div>
  )
}

function ToolCallRow({ tc }: { tc: ToolCall }) {
  const [open, setOpen] = useState(false)
  let parsedInput: any = tc.input_json
  try { parsedInput = JSON.parse(tc.input_json) } catch { /* keep raw */ }

  return (
    <div style={{
      background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4,
      overflow: 'hidden',
    }}>
      <div
        onClick={() => setOpen(!open)}
        style={{
          padding: '8px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12,
          fontFamily: 'JetBrains Mono, monospace', fontSize: 12,
        }}
      >
        <span style={{ color: C.textMute, width: 28 }}>{open ? '▼' : '▶'}</span>
        <span style={{ color: C.textMute, width: 60 }}>iter #{tc.iteration}</span>
        <span style={{ color: C.accent, fontWeight: 500, minWidth: 160 }}>{tc.tool_name}</span>
        <span style={{ color: C.textDim, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {typeof parsedInput === 'object' ? JSON.stringify(parsedInput).slice(0, 80) : String(parsedInput).slice(0, 80)}
        </span>
        <span style={{ color: C.textMute, fontSize: 10.5 }}>{tc.latency_ms}ms</span>
      </div>
      {open && (
        <div style={{ padding: '0 12px 12px 48px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div>
            <SectionLabel>input</SectionLabel>
            <pre style={{
              background: C.bg, border: `1px solid ${C.border}`, borderRadius: 3, padding: 8,
              color: C.text, fontFamily: 'JetBrains Mono, monospace', fontSize: 11.5,
              whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
            }}>{typeof parsedInput === 'object' ? JSON.stringify(parsedInput, null, 2) : String(parsedInput)}</pre>
          </div>
          <div>
            <SectionLabel>output</SectionLabel>
            <pre style={{
              background: C.bg, border: `1px solid ${C.border}`, borderRadius: 3, padding: 8,
              color: C.textDim, fontFamily: 'JetBrains Mono, monospace', fontSize: 11.5,
              whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
              maxHeight: 300, overflow: 'auto',
            }}>{tc.output_text}</pre>
          </div>
        </div>
      )}
    </div>
  )
}

function _modelKey(model: string): string {
  const m = model.toLowerCase()
  if (m.includes('haiku')) return 'haiku'
  if (m.includes('sonnet')) return 'sonnet'
  if (m.includes('opus')) return 'opus'
  return model.slice(0, 12)
}
