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
    return <div style={{ padding: 28, color: C.textMute, fontSize: 13 }}>⠋ učitavam…</div>
  }
  if (!data) {
    return <div style={{ padding: 28, color: C.err, fontSize: 13 }}>Statistika nije dostupna (provjeri API ključ u Podešavanjima).</div>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <TopBar title="Statistika" subtitle="Tokeni · trošak · trajanje po kanalu i modelu" />

      <div className="dash-content" style={{ flex: 1, overflow: 'auto', padding: '20px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div className="dash-grid-4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
          <Metric label="ukupno poruka" value={data.total_requests.toLocaleString()} accent />
          <Metric label="tokeni unos"   value={data.total_tokens_in.toLocaleString()} />
          <Metric label="tokeni izlaz"  value={data.total_tokens_out.toLocaleString()} />
          <Metric label="ukupan trošak" value={`$${data.total_cost_usd.toFixed(4)}`} />
        </div>

        <div>
          <SectionLabel>po kanalu × modelu</SectionLabel>
          {data.by_adapter.length === 0 ? (
            <div style={{ color: C.textMute, fontSize: 13 }}>Nema podataka.</div>
          ) : (
            <div className="dash-table-wrap">
            <table style={{
              width: '100%', borderCollapse: 'collapse',
              fontFamily: 'JetBrains Mono, monospace', fontSize: 13,
            }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}`, color: C.textMute, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  <Th>kanal</Th><Th>model</Th>
                  <Th right>poruka</Th><Th right>ok</Th><Th right>greške</Th>
                  <Th right>tokeni ↓</Th><Th right>tokeni ↑</Th>
                  <Th right>prosj. trajanje</Th><Th right>trošak</Th>
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
            </div>
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
