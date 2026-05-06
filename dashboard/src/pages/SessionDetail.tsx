import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../api'
import type { ToolCall, RequestDetail } from '../api'
import { C, channelColor, modelColor } from '../tokens'
import { TopBar, SectionLabel, Tag, StatusBadge, Btn, Metric } from '../components/atoms'
import { setLastSelected } from '../lastSelected'

export function SessionDetailPage() {
  const { id } = useParams()
  const nav = useNavigate()

  const { data, isLoading, error } = useQuery({
    queryKey: ['session', id],
    queryFn: () => api.getSession(id!),
    enabled: !!id,
  })

  // Sessions list — koristi se za prev/next navigation arrows.
  // Ne enabled na initial load (nemamo cache); ako korisnik je došao
  // sa /sessions, TanStack ima keširanu listu i ne refetch-uje.
  const { data: sessionsList } = useQuery({
    queryKey: ['sessions', ''],  // moramo da se podudara sa Sessions.tsx queryKey
    queryFn: () => api.listSessions(undefined, 1),
    staleTime: 60_000,
  })

  // Pronađi prev/next session ID u listi
  const sessions = sessionsList?.items ?? []
  const currentIdx = sessions.findIndex(s => s.session_id === id)
  const prevSession = currentIdx > 0 ? sessions[currentIdx - 1] : null
  const nextSession = currentIdx >= 0 && currentIdx < sessions.length - 1
    ? sessions[currentIdx + 1] : null

  // Keyboard arrows ← → za prev/next
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Ignoriši kad korisnik tipka u input/textarea
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (e.key === 'ArrowLeft' && prevSession) {
        setLastSelected('sessions', prevSession.session_id)
        nav(`/sessions/${prevSession.session_id}`)
      } else if (e.key === 'ArrowRight' && nextSession) {
        setLastSelected('sessions', nextSession.session_id)
        nav(`/sessions/${nextSession.session_id}`)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [prevSession, nextSession, nav])

  if (isLoading) return <div style={{ padding: 28, color: C.textMute, fontSize: 13 }}>⠋ učitavam…</div>
  if (error || !data) return <div style={{ padding: 28, color: C.err, fontSize: 13 }}>Razgovor nije pronađen.</div>

  const reqs = data.requests
  const totalTokensIn = reqs.reduce((s, r) => s + (r.tokens_in ?? 0), 0)
  const totalTokensOut = reqs.reduce((s, r) => s + (r.tokens_out ?? 0), 0)
  const totalLatency = reqs.reduce((s, r) => s + (r.latency_ms ?? 0), 0)
  const totalCost = reqs.reduce((s, r) => s + (r.cost_usd ?? 0), 0)
  const errorCount = reqs.filter(r => r.status === 'error').length
  const firstChannel = reqs[0]?.channel ?? '—'
  const firstModel = reqs[0]?.model ?? '—'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <TopBar
        title={`Razgovor ${data.session_id.slice(0, 8)}…`}
        subtitle={
          <span>
            <Link to="/sessions" style={{ color: C.textDim, textDecoration: 'none' }}>Razgovori</Link>
            <span style={{ color: C.textMute, margin: '0 6px' }}>›</span>
            <span style={{ color: C.text }}>{data.session_id.slice(0, 8)}…</span>
            <span style={{ color: C.textMute, margin: '0 8px' }}>·</span>
            <span style={{ color: C.textDim }}>
              {reqs.length} poruka · {new Date(reqs[0].created_at).toLocaleTimeString()} → {new Date(reqs[reqs.length-1].created_at).toLocaleTimeString()}
            </span>
            {currentIdx >= 0 && (
              <>
                <span style={{ color: C.textMute, margin: '0 8px' }}>·</span>
                <span style={{ color: C.textMute, fontFamily: 'JetBrains Mono, monospace' }}>
                  {currentIdx + 1} / {sessions.length}
                </span>
              </>
            )}
          </span>
        }
        right={
          <div style={{ display: 'flex', gap: 6 }}>
            <NavBtn
              disabled={!prevSession}
              title={prevSession ? `← prethodni (${prevSession.session_id.slice(0, 8)}…)` : 'prvi razgovor'}
              onClick={() => {
                if (!prevSession) return
                setLastSelected('sessions', prevSession.session_id)
                nav(`/sessions/${prevSession.session_id}`)
              }}
            >←</NavBtn>
            <NavBtn
              disabled={!nextSession}
              title={nextSession ? `sledeći → (${nextSession.session_id.slice(0, 8)}…)` : 'poslednji razgovor'}
              onClick={() => {
                if (!nextSession) return
                setLastSelected('sessions', nextSession.session_id)
                nav(`/sessions/${nextSession.session_id}`)
              }}
            >→</NavBtn>
            <Btn variant="ghost" onClick={() => nav('/sessions')}>nazad na listu</Btn>
          </div>
        }
      />

      <div className="dash-content" style={{ flex: 1, overflow: 'auto', padding: '20px 28px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div className="dash-grid-4" style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
          <Metric label="poruka" value={String(reqs.length)} accent />
          <Metric label="tokeni" value={`↓${totalTokensIn.toLocaleString()} ↑${totalTokensOut.toLocaleString()}`} />
          <Metric label="trajanje" value={`${(totalLatency / 1000).toFixed(1)}s`} />
          <Metric label="trošak" value={totalCost > 0 ? `$${totalCost.toFixed(4)}` : '—'} />
          <Metric label="greške" value={String(errorCount)} />
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <Tag color={channelColor(firstChannel)}>{firstChannel}</Tag>
          <Tag color={modelColor(_modelKey(firstModel))}>{_modelKey(firstModel)}</Tag>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: C.textMute }}>
            session_id: {data.session_id}
          </span>
        </div>

        <SectionLabel>tok razgovora</SectionLabel>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {reqs.map((r, idx) => <Turn key={r.id} r={r} index={idx + 1} />)}
        </div>
      </div>
    </div>
  )
}

function Turn({ r, index }: { r: RequestDetail; index: number }) {
  const [open, setOpen] = useState(true)
  const time = new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })

  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 6 }}>
      <div
        onClick={() => setOpen(!open)}
        style={{
          padding: '10px 14px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12,
          borderBottom: open ? `1px solid ${C.border}` : 0,
        }}
      >
        <span style={{ color: C.textMute, fontFamily: 'JetBrains Mono, monospace', fontSize: 12, width: 40 }}>
          #{index}
        </span>
        <span style={{ color: C.textDim, fontFamily: 'JetBrains Mono, monospace', fontSize: 12, width: 80 }}>{time}</span>
        <StatusBadge status={r.status} />
        <span style={{ flex: 1, color: C.text, fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {r.prompt.slice(0, 120)}
        </span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11.5, color: C.textMute, whiteSpace: 'nowrap' }}>
          {r.tool_calls.length > 0 && `${r.tool_calls.length} tools · `}
          {r.latency_ms}ms · {r.cost_usd != null ? `$${r.cost_usd.toFixed(4)}` : '—'}
        </span>
        <span style={{ color: C.textMute, fontFamily: 'JetBrains Mono, monospace' }}>{open ? '▼' : '▶'}</span>
      </div>

      {open && (
        <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* User prompt */}
          <Bubble role="user">
            <pre style={bubblePre}>{r.prompt}</pre>
          </Bubble>

          {/* Tool calls */}
          {r.tool_calls.length > 0 && (
            <div style={{ paddingLeft: 32 }}>
              <SectionLabel>{r.tool_calls.length} {r.tool_calls.length === 1 ? 'poziv alata' : 'poziva alata'}</SectionLabel>
              {r.tool_calls.map((tc, i) => <ToolCallRow key={i} tc={tc} />)}
            </div>
          )}

          {/* Assistant reply */}
          {r.response && (
            <Bubble role="assistant">
              <pre style={bubblePre}>{r.response}</pre>
            </Bubble>
          )}

          {r.error && (
            <Bubble role="error">
              <pre style={{ ...bubblePre, color: C.err }}>{r.error}</pre>
            </Bubble>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Link to={`/requests/${r.id}`} style={{ color: C.textDim, fontSize: 12, textDecoration: 'none', fontFamily: 'JetBrains Mono, monospace' }}>
              cijela poruka #{r.id} →
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

const bubblePre: React.CSSProperties = {
  margin: 0, fontFamily: 'JetBrains Mono, monospace', fontSize: 13, lineHeight: 1.55,
  whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: C.text,
}

function Bubble({ role, children }: { role: 'user' | 'assistant' | 'error'; children: React.ReactNode }) {
  const colors = {
    user:      { bg: `${C.bitlab}10`, border: `${C.bitlab}40`, label: 'KORISNIK' },
    assistant: { bg: C.panelLo,        border: C.border,        label: 'ASISTENT' },
    error:     { bg: `${C.err}10`,     border: `${C.err}40`,    label: 'GREŠKA' },
  }[role]
  return (
    <div style={{
      background: colors.bg, border: `1px solid ${colors.border}`, borderRadius: 4,
      padding: '10px 14px',
      marginLeft: role === 'user' ? 0 : 32,
      marginRight: role === 'user' ? 32 : 0,
    }}>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5, letterSpacing: '0.08em',
        color: C.textMute, marginBottom: 6,
      }}>{colors.label}</div>
      {children}
    </div>
  )
}

function ToolCallRow({ tc }: { tc: ToolCall }) {
  const [open, setOpen] = useState(false)
  let parsed: any = tc.input_json
  try { parsed = JSON.parse(tc.input_json) } catch { /* keep raw */ }
  return (
    <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 4, marginBottom: 4, fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
      <div onClick={() => setOpen(!open)} style={{ padding: '6px 10px', cursor: 'pointer', display: 'flex', gap: 10, alignItems: 'center' }}>
        <span style={{ color: C.textMute, width: 18 }}>{open ? '▼' : '▶'}</span>
        <span style={{ color: C.accent, fontWeight: 500, width: 140 }}>{tc.tool_name}</span>
        <span style={{ color: C.textDim, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {typeof parsed === 'object' ? JSON.stringify(parsed).slice(0, 100) : String(parsed).slice(0, 100)}
        </span>
        <span style={{ color: C.textMute }}>{tc.latency_ms}ms</span>
      </div>
      {open && (
        <div style={{ padding: '6px 10px 10px 36px', borderTop: `1px solid ${C.border}` }}>
          <pre style={{ color: C.textDim, fontSize: 12, margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 240, overflow: 'auto' }}>
            {tc.output_text}
          </pre>
        </div>
      )}
    </div>
  )
}

function NavBtn({ children, disabled, title, onClick }: {
  children: React.ReactNode; disabled?: boolean; title?: string; onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      style={{
        width: 32, height: 28, borderRadius: 4,
        background: disabled ? C.panelLo : C.panelHi,
        color: disabled ? C.textMute : C.text,
        border: `1px solid ${C.border}`,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.4 : 1,
        fontFamily: 'JetBrains Mono, monospace', fontSize: 14,
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      }}
    >{children}</button>
  )
}

function _modelKey(model: string): string {
  const m = model.toLowerCase()
  if (m.includes('haiku')) return 'haiku'
  if (m.includes('sonnet')) return 'sonnet'
  if (m.includes('opus')) return 'opus'
  return model.slice(0, 12)
}
