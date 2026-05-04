import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { C, channelColor, modelColor } from '../tokens'
import { TopBar, SectionLabel, Tag, Metric } from '../components/atoms'

export function Stats() {
  const { data, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.getStats(),
    refetchInterval: 10_000,
  })

  if (isLoading) {
    return <div style={{ padding: 28, color: C.textMute, fontSize: 12 }}>⠋ loading…</div>
  }
  if (!data) {
    return <div style={{ padding: 28, color: C.err, fontSize: 12 }}>Stats nedostupne (provjeri API key u Settings).</div>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <TopBar title="Stats" subtitle="Tokens · cost · latency po kanalu i modelu" />

      <div style={{ flex: 1, overflow: 'auto', padding: '20px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
          <Metric label="total requests" value={data.total_requests.toLocaleString()} accent />
          <Metric label="tokens in"      value={data.total_tokens_in.toLocaleString()} />
          <Metric label="tokens out"     value={data.total_tokens_out.toLocaleString()} />
          <Metric label="total cost"     value={`$${data.total_cost_usd.toFixed(4)}`} />
        </div>

        <div>
          <SectionLabel>by adapter (channel × model)</SectionLabel>
          {data.by_adapter.length === 0 ? (
            <div style={{ color: C.textMute, fontSize: 12 }}>Nema podataka.</div>
          ) : (
            <table style={{
              width: '100%', borderCollapse: 'collapse',
              fontFamily: 'JetBrains Mono, monospace', fontSize: 12,
            }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}`, color: C.textMute, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  <Th>channel</Th><Th>model</Th>
                  <Th right>requests</Th><Th right>ok</Th><Th right>err</Th>
                  <Th right>tokens ↓</Th><Th right>tokens ↑</Th>
                  <Th right>avg latency</Th><Th right>cost</Th>
                </tr>
              </thead>
              <tbody>
                {data.by_adapter.map(a => (
                  <tr key={a.adapter} style={{ borderBottom: `1px solid ${C.border}` }}>
                    <Td><Tag color={channelColor(a.channel)}>{a.channel}</Tag></Td>
                    <Td><Tag color={modelColor(_modelKey(a.model))}>{_modelKey(a.model)}</Tag></Td>
                    <Td right color={C.text}>{a.total_requests}</Td>
                    <Td right color={C.ok}>{a.ok_requests}</Td>
                    <Td right color={a.error_requests > 0 ? C.err : C.textMute}>{a.error_requests}</Td>
                    <Td right>{a.total_tokens_in.toLocaleString()}</Td>
                    <Td right>{a.total_tokens_out.toLocaleString()}</Td>
                    <Td right>{a.avg_latency_ms ? `${Math.round(a.avg_latency_ms)}ms` : '—'}</Td>
                    <Td right color={C.text}>${a.estimated_cost_usd.toFixed(4)}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

function Th({ children, right }: { children: React.ReactNode; right?: boolean }) {
  return <th style={{ textAlign: right ? 'right' : 'left', padding: '8px 10px', fontWeight: 500 }}>{children}</th>
}

function Td({ children, color, right }: { children: React.ReactNode; color?: string; right?: boolean }) {
  return <td style={{ padding: '8px 10px', textAlign: right ? 'right' : 'left', color: color ?? C.textDim }}>{children}</td>
}

function _modelKey(model: string): string {
  const m = model.toLowerCase()
  if (m.includes('haiku')) return 'haiku'
  if (m.includes('sonnet')) return 'sonnet'
  if (m.includes('opus')) return 'opus'
  return model.slice(0, 12)
}
