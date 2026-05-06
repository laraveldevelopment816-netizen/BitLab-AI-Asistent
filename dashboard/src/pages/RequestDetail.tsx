import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, useNavigate, Link } from 'react-router-dom'
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
    return <div style={{ padding: 28, color: C.textMute, fontSize: 13 }}>⠋ učitavam…</div>
  }
  if (error || !r) {
    return <div style={{ padding: 28, color: C.err, fontSize: 13 }}>Poruka #{id} nije pronađena.</div>
  }

  const ch = channelColor(r.channel)
  const md = modelColor(_modelKey(r.model))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <TopBar
        title={`Poruka #${r.id}`}
        subtitle={
          <span>
            <Link to="/live" style={{ color: C.textDim, textDecoration: 'none' }}>Uživo</Link>
            <span style={{ color: C.textMute, margin: '0 6px' }}>›</span>
            <span style={{ color: C.text }}>#{r.id}</span>
            <span style={{ color: C.textMute, margin: '0 8px' }}>·</span>
            <span style={{ color: C.textDim }}>{new Date(r.created_at).toLocaleString()} · {r.adapter}</span>
            {r.compare_group_id && (
              <>
                <span style={{ color: C.textMute, margin: '0 8px' }}>·</span>
                <span style={{ color: C.warn }}>poređenje {r.compare_group_id.slice(0, 8)}</span>
              </>
            )}
          </span>
        }
        right={<Btn variant="ghost" onClick={() => nav(-1)}>← nazad</Btn>}
      />

      <div className="dash-content" style={{ flex: 1, overflow: 'auto', padding: '20px 28px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Top metrics */}
        <div className="dash-grid-4" style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
          <Metric label="status" value={r.status} accent={r.status === 'ok'} />
          <Metric label="iteracije" value={String(r.iterations ?? '—')} />
          <Metric label="tokeni" value={`↓${r.tokens_in ?? '—'} ↑${r.tokens_out ?? '—'}`} />
          <Metric label="trajanje" value={r.latency_ms ? `${r.latency_ms}ms` : '—'} />
          <Metric label="trošak" value={r.cost_usd != null ? `$${r.cost_usd.toFixed(4)}` : '—'} />
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <Tag color={ch}>{r.channel}</Tag>
          <Tag color={md}>{_modelKey(r.model)}</Tag>
          <StatusBadge status={r.status} />
          {r.compare_group_id && (
            <Tag color={C.warn}>poređenje {r.compare_group_id.slice(0, 8)}</Tag>
          )}
        </div>

        <div>
          <SectionLabel>pitanje korisnika</SectionLabel>
          <pre style={{
            background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4,
            padding: 12, color: C.text, fontFamily: 'JetBrains Mono, monospace',
            fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
          }}>{r.prompt}</pre>
        </div>

        {r.error && (
          <div>
            <SectionLabel>greška</SectionLabel>
            <pre style={{
              background: `${C.err}10`, border: `1px solid ${C.err}40`, borderRadius: 4,
              padding: 12, color: C.err, fontFamily: 'JetBrains Mono, monospace',
              fontSize: 13, whiteSpace: 'pre-wrap', margin: 0,
            }}>{r.error}</pre>
          </div>
        )}

        <div>
          <SectionLabel>pozivi alata, hronološki ({r.tool_calls.length})</SectionLabel>
          {r.tool_calls.length === 0 && (
            <div style={{ color: C.textMute, fontSize: 13 }}>Bez poziva alata.</div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {r.tool_calls.map((tc, i) => <ToolCallRow key={i} tc={tc} />)}
          </div>
        </div>

        <div>
          <SectionLabel>odgovor asistenta</SectionLabel>
          <pre style={{
            background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4,
            padding: 12, color: C.text, fontFamily: 'JetBrains Mono, monospace',
            fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
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
          fontFamily: 'JetBrains Mono, monospace', fontSize: 13,
        }}
      >
        <span style={{ color: C.textMute, width: 28 }}>{open ? '▼' : '▶'}</span>
        <span style={{ color: C.textMute, width: 64 }}>korak #{tc.iteration}</span>
        <span style={{ color: C.accent, fontWeight: 500, minWidth: 160 }}>{tc.tool_name}</span>
        <span style={{ color: C.textDim, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {typeof parsedInput === 'object' ? JSON.stringify(parsedInput).slice(0, 80) : String(parsedInput).slice(0, 80)}
        </span>
        <span style={{ color: C.textMute, fontSize: 11.5 }}>{tc.latency_ms}ms</span>
      </div>
      {open && (
        <div style={{ padding: '0 12px 12px 48px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div>
            <SectionLabel>parametri (ulaz)</SectionLabel>
            <pre style={{
              background: C.bg, border: `1px solid ${C.border}`, borderRadius: 3, padding: 8,
              color: C.text, fontFamily: 'JetBrains Mono, monospace', fontSize: 12.5,
              whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
            }}>{typeof parsedInput === 'object' ? JSON.stringify(parsedInput, null, 2) : String(parsedInput)}</pre>
          </div>
          <div>
            <SectionLabel>rezultat (izlaz)</SectionLabel>
            <pre style={{
              background: C.bg, border: `1px solid ${C.border}`, borderRadius: 3, padding: 8,
              color: C.textDim, fontFamily: 'JetBrains Mono, monospace', fontSize: 12.5,
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
