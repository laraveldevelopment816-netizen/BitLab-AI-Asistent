import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import type { CompareResultItem } from '../api'
import { C, modelColor, channelColor } from '../tokens'
import { TopBar, SectionLabel, Btn, Tag } from '../components/atoms'

const ALL_MODELS = ['haiku', 'sonnet']
const CHANNELS = ['chat', 'voice', 'email']

export function Compare() {
  const [prompt, setPrompt] = useState('')
  const [channel, setChannel] = useState('chat')
  const [picked, setPicked] = useState(new Set(['haiku', 'sonnet']))
  const [results, setResults] = useState<CompareResultItem[]>([])
  const [running, setRunning] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  function toggleModel(m: string) {
    setPicked(prev => {
      const next = new Set(prev)
      if (next.has(m)) { if (next.size > 1) next.delete(m) }
      else next.add(m)
      return next
    })
  }

  async function runCompare() {
    if (!prompt.trim() || running) return
    setRunning(true); setErr(null); setResults([])
    try {
      const data = await api.compare(prompt, channel, [...picked])
      setResults(data.results)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e?.message || 'Greška u compare-u')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <TopBar title="Compare" subtitle="Isti upit kroz N modela paralelno · poredi quality vs cost vs latency" />

      <div style={{ flex: 1, overflow: 'auto', padding: '20px 28px' }}>
        <div style={{ marginBottom: 16 }}>
          <SectionLabel>prompt</SectionLabel>
          <textarea
            rows={3}
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder='npr. "imate li gaming mis", "trebam laptop do 1500 KM"…'
            style={{
              width: '100%', resize: 'vertical',
              fontFamily: 'JetBrains Mono, monospace', fontSize: 12.5, lineHeight: 1.6,
              background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4,
              padding: 12, color: C.text,
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: 24, marginBottom: 16, flexWrap: 'wrap' }}>
          <div>
            <SectionLabel>channel</SectionLabel>
            <div style={{ display: 'flex', gap: 6 }}>
              {CHANNELS.map(c => {
                const on = c === channel
                const col = channelColor(c)
                return (
                  <button key={c} onClick={() => setChannel(c)}
                    style={{
                      padding: '5px 12px', borderRadius: 4, cursor: 'pointer',
                      fontFamily: 'JetBrains Mono, monospace', fontSize: 12,
                      background: on ? col + '22' : C.panelLo,
                      border: `1px solid ${on ? col + '80' : C.border}`,
                      color: on ? col : C.textDim,
                    }}>{on ? '✓ ' : ''}{c}</button>
                )
              })}
            </div>
          </div>
          <div>
            <SectionLabel>models to compare</SectionLabel>
            <div style={{ display: 'flex', gap: 6 }}>
              {ALL_MODELS.map(m => {
                const on = picked.has(m)
                const col = modelColor(m)
                return (
                  <button key={m} onClick={() => toggleModel(m)}
                    style={{
                      padding: '5px 12px', borderRadius: 4, cursor: 'pointer',
                      fontFamily: 'JetBrains Mono, monospace', fontSize: 12,
                      background: on ? col + '22' : C.panelLo,
                      border: `1px solid ${on ? col + '80' : C.border}`,
                      color: on ? col : C.textDim,
                    }}>{on ? '✓ ' : ''}{m}</button>
                )
              })}
            </div>
          </div>
        </div>

        <Btn variant="primary" onClick={runCompare} disabled={running || !prompt.trim()}>
          {running ? '⠋ running…' : `▶ Run on ${picked.size} model${picked.size > 1 ? 's' : ''}`}
        </Btn>

        {err && (
          <div style={{ marginTop: 16, padding: 12, background: `${C.err}10`, border: `1px solid ${C.err}40`, borderRadius: 4, color: C.err, fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
            {err}
          </div>
        )}

        {results.length > 0 && (
          <div style={{
            display: 'grid', gridTemplateColumns: `repeat(${results.length}, 1fr)`,
            gap: 12, marginTop: 20,
          }}>
            {results.map(r => <ResultCard key={r.model_key} r={r} />)}
          </div>
        )}
      </div>
    </div>
  )
}

function ResultCard({ r }: { r: CompareResultItem }) {
  const col = modelColor(r.model_key)
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 6, overflow: 'hidden' }}>
      <div style={{ height: 2, background: col }} />
      <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Tag color={col}>{r.model_key}</Tag>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5, color: C.textMute }}>
          {r.latency_ms ? `${r.latency_ms}ms` : '—'} · {r.cost_usd != null ? `$${r.cost_usd.toFixed(4)}` : '—'}
        </span>
      </div>
      <div style={{ padding: 14, minHeight: 120, fontFamily: 'JetBrains Mono, monospace', fontSize: 12, lineHeight: 1.6, color: C.text, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
        {r.status === 'error' ? (
          <span style={{ color: C.err }}>{r.error || 'Request failed'}</span>
        ) : (
          r.reply
        )}
      </div>
      {r.tool_calls.length > 0 && (
        <div style={{ padding: '8px 14px', borderTop: `1px solid ${C.border}`, fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5, color: C.textMute }}>
          {r.tool_calls.length} tool call{r.tool_calls.length > 1 ? 's' : ''}: {' '}
          {r.tool_calls.map((tc, i) => (
            <span key={i}>{i > 0 && ' · '}{tc.tool_name} ({tc.latency_ms}ms)</span>
          ))}
        </div>
      )}
      <div style={{ padding: '8px 14px', borderTop: `1px solid ${C.border}`, display: 'flex', justifyContent: 'space-between', fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5, color: C.textMute }}>
        <span>{r.tokens_in != null ? `↓${r.tokens_in} ↑${r.tokens_out}` : ''}</span>
        {r.request_id && (
          <Link to={`/requests/${r.request_id}`} style={{ color: C.textDim, textDecoration: 'none' }}>
            #{r.request_id} →
          </Link>
        )}
      </div>
    </div>
  )
}
