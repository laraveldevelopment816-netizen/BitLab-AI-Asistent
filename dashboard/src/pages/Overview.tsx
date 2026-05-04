import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api'
import type { DailyCount, ChannelBreakdown, ModelBreakdown, RecentSession } from '../api'
import { C, channelColor, modelColor } from '../tokens'
import { TopBar, SectionLabel, Tag } from '../components/atoms'

export function Overview() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['overview'],
    queryFn: () => api.getOverview(),
    refetchInterval: 10_000,
    retry: false,  // ne retry-uj 401/404 — odmah pokaži pravi razlog
  })

  if (isLoading) return <div style={{ padding: 28, color: C.textMute, fontSize: 12 }}>⠋ učitavam…</div>
  if (error || !data) return <ErrorPanel error={error} />

  return (
    <OverviewContent data={data} />
  )
}

function ErrorPanel({ error }: { error: unknown }) {
  // axios greške imaju response sa status / data
  const err = error as any
  const status = err?.response?.status
  const detail = err?.response?.data?.detail
  const isAuth = status === 401 || status === 503
  const isNotFound = status === 404
  const isNetwork = !err?.response && (err?.code === 'ERR_NETWORK' || err?.message === 'Network Error')

  let title = 'Pregled nije dostupan'
  let body: React.ReactNode = (
    <span>Greška: {detail || err?.message || 'nepoznat razlog'}</span>
  )
  let hint: React.ReactNode = null

  if (isAuth) {
    title = 'Nedostaje API ključ'
    body = <span>Server zahtijeva autorizaciju ({status}). {detail || ''}</span>
    hint = <span>Idi u <Link to="/settings" style={{ color: C.accent }}>Podešavanja</Link> i unesi <code style={codeStyle}>DASHBOARD_API_KEY</code> iz <code style={codeStyle}>.env</code> fajla.</span>
  } else if (isNotFound) {
    title = 'Endpoint /overview nije nađen'
    body = <span>Backend možda nije pokrenut sa najnovijim kodom.</span>
    hint = <span>Restartuj <code style={codeStyle}>uvicorn app.main:app --reload</code> ili pokreni novi build poslije <code style={codeStyle}>git pull</code>.</span>
  } else if (isNetwork) {
    title = 'Nema konekcije sa serverom'
    body = <span>Backend nije dostupan na <code style={codeStyle}>/api/dashboard</code>.</span>
    hint = <span>Provjeri da li <code style={codeStyle}>uvicorn</code> radi na portu 8000.</span>
  }

  return (
    <div style={{ padding: 28, maxWidth: 640 }}>
      <div style={{
        background: C.panel, border: `1px solid ${C.border}`,
        borderLeft: `3px solid ${C.err}`,
        borderRadius: 6, padding: '16px 18px',
      }}>
        <div style={{ color: C.err, fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
          {title}
        </div>
        <div style={{ color: C.text, fontSize: 13, lineHeight: 1.5, marginBottom: hint ? 10 : 0 }}>
          {body}
        </div>
        {hint && (
          <div style={{ color: C.textDim, fontSize: 12.5, lineHeight: 1.5, paddingTop: 10, borderTop: `1px solid ${C.border}` }}>
            {hint}
          </div>
        )}
      </div>
    </div>
  )
}

const codeStyle: React.CSSProperties = {
  background: C.panelLo, padding: '1px 6px', borderRadius: 3,
  fontFamily: 'JetBrains Mono, monospace', fontSize: 12,
}

function OverviewContent({ data }: { data: import('../api').OverviewResponse }) {

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <TopBar
        title="Pregled"
        subtitle={
          <span style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <SystemStatusDot />
            <span>AI sistem online · {data.total_sessions.toLocaleString()} razgovora ukupno</span>
          </span>
        }
      />

      <div style={{ flex: 1, overflow: 'auto', padding: '20px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* HERO METRICS */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          <HeroCard
            label="Razgovori"
            value={data.total_sessions.toLocaleString()}
            sub={`+${data.today_sessions} danas`}
            accent={C.bitlab}
          />
          <HeroCard
            label="Poruke"
            value={data.total_requests.toLocaleString()}
            sub={`+${data.today_requests} danas`}
            accent={C.accent}
          />
          <HeroCard
            label="Tokeni"
            value={`${(data.total_tokens_in / 1000).toFixed(1)}k ↓ / ${(data.total_tokens_out / 1000).toFixed(1)}k ↑`}
            sub={`p50 ${data.p50_latency_ms ?? '—'}ms · p95 ${data.p95_latency_ms ?? '—'}ms`}
            accent={C.text}
          />
          <HeroCard
            label="Trošak"
            value={`$${data.total_cost_usd.toFixed(4)}`}
            sub={`+$${data.today_cost_usd.toFixed(4)} danas`}
            accent={data.error_count > 0 ? C.warn : C.ok}
          />
        </div>

        {/* GRAFIK 14 DANA */}
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 12 }}>
            <SectionLabel>aktivnost — poslednjih 14 dana</SectionLabel>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5, color: C.textMute }}>
              poruke · razgovori · greške
            </span>
          </div>
          <DailyBarChart data={data.daily_last_14} />
        </Card>

        {/* DVA STUPCA — channel + model */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Card>
            <SectionLabel>distribucija po kanalu</SectionLabel>
            <div style={{ marginTop: 10 }}>
              <ChannelBars data={data.by_channel} total={data.total_requests} />
            </div>
          </Card>

          <Card>
            <SectionLabel>distribucija po modelu</SectionLabel>
            <div style={{ marginTop: 10 }}>
              <ModelBars data={data.by_model} total={data.total_requests} />
            </div>
          </Card>
        </div>

        {/* RECENT ACTIVITY */}
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 }}>
            <SectionLabel>posljednji razgovori</SectionLabel>
            <Link to="/sessions" style={{ fontSize: 11, color: C.textDim, textDecoration: 'none', fontFamily: 'JetBrains Mono, monospace' }}>
              vidi sve →
            </Link>
          </div>
          {data.recent_sessions.length === 0 ? (
            <div style={{ color: C.textMute, fontSize: 12, padding: '12px 0' }}>Nema razgovora još. Pošalji poruku kroz widget.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {data.recent_sessions.map(s => <RecentSessionRow key={s.session_id} s={s} />)}
            </div>
          )}
        </Card>

        {data.error_count > 0 && (
          <Card style={{ borderLeft: `3px solid ${C.err}` }}>
            <SectionLabel>greške ({data.error_count})</SectionLabel>
            <div style={{ marginTop: 8, fontSize: 12.5, color: C.textDim }}>
              Ima zabilježenih grešaka u sistemu. Pogledaj{' '}
              <Link to="/history?status=error" style={{ color: C.accent }}>
                Istoriju sa filterom 'error'
              </Link>
              {' '}da pogledaš detalje.
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}

// ── Komponente ───────────────────────────────────────────────────────

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: C.panel,
      border: `1px solid ${C.border}`,
      borderRadius: 6,
      padding: '14px 16px',
      ...style,
    }}>{children}</div>
  )
}

function HeroCard({ label, value, sub, accent }: {
  label: string; value: string; sub?: string; accent: string
}) {
  return (
    <div style={{
      background: C.panel,
      border: `1px solid ${C.border}`,
      borderTop: `2px solid ${accent}`,
      borderRadius: 6,
      padding: '14px 16px',
      display: 'flex', flexDirection: 'column', gap: 6,
    }}>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
        textTransform: 'uppercase', letterSpacing: '0.08em', color: C.textMute,
      }}>{label}</div>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: 22, lineHeight: 1.1,
        color: accent, fontWeight: 500, letterSpacing: '-0.02em',
      }}>{value}</div>
      {sub && (
        <div style={{
          fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5, color: C.textDim,
        }}>{sub}</div>
      )}
    </div>
  )
}

function SystemStatusDot() {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <span style={{ position: 'relative', width: 8, height: 8 }}>
        <span style={{
          width: 8, height: 8, borderRadius: '50%', background: C.ok, display: 'block',
          boxShadow: `0 0 0 3px ${C.ok}30`,
        }} />
        <span style={{
          position: 'absolute', top: 0, left: 0, width: 8, height: 8,
          borderRadius: '50%', background: C.ok, opacity: 0.6,
          animation: 'pulse-ring 2s ease-out infinite',
        }} />
      </span>
    </span>
  )
}

const MONTHS_SR = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 'Jul', 'Avg', 'Sep', 'Okt', 'Nov', 'Dec']

function DailyBarChart({ data }: { data: DailyCount[] }) {
  const maxR = Math.max(1, ...data.map(d => d.requests))
  const width = 760
  const height = 140
  const barW = (width - 40) / data.length
  const padL = 32

  return (
    <div style={{ overflowX: 'auto' }}>
      <svg viewBox={`0 0 ${width} ${height + 28}`} style={{ width: '100%', maxWidth: width }}>
        {/* Y-axis grid linije */}
        {[0.25, 0.5, 0.75, 1].map(p => (
          <g key={p}>
            <line
              x1={padL} y1={height - height * p}
              x2={width - 8} y2={height - height * p}
              stroke={C.border} strokeWidth="1" strokeDasharray="2,3"
            />
            <text x={padL - 6} y={height - height * p + 3}
              fontSize="9" fill={C.textMute} textAnchor="end"
              fontFamily="JetBrains Mono, monospace">
              {Math.round(maxR * p)}
            </text>
          </g>
        ))}
        {data.map((d, i) => {
          const reqH = (d.requests / maxR) * height
          const errH = (d.errors / maxR) * height
          const x = padL + i * barW + 2
          const w = barW - 4
          const dt = new Date(d.date)
          const dayLbl = `${dt.getDate()} ${MONTHS_SR[dt.getMonth()]}`
          return (
            <g key={d.date}>
              {/* glavni bar */}
              <rect
                x={x} y={height - reqH} width={w} height={reqH}
                fill={C.accent} fillOpacity="0.65" rx="2"
              >
                <title>{`${d.date}: ${d.requests} poruka, ${d.sessions} razgovora${d.errors > 0 ? `, ${d.errors} greške` : ''}`}</title>
              </rect>
              {/* greške overlay (crveni dio na vrhu) */}
              {errH > 0 && (
                <rect
                  x={x} y={height - reqH} width={w} height={errH}
                  fill={C.err} fillOpacity="0.85" rx="2"
                />
              )}
              {/* dnevni label */}
              <text x={x + w / 2} y={height + 14}
                fontSize="9" fill={C.textMute} textAnchor="middle"
                fontFamily="JetBrains Mono, monospace">
                {dayLbl}
              </text>
              {/* req number na vrhu (ako bar je dovoljno visok) */}
              {d.requests > 0 && reqH > 14 && (
                <text x={x + w / 2} y={height - reqH - 4}
                  fontSize="9" fill={C.textDim} textAnchor="middle"
                  fontFamily="JetBrains Mono, monospace">
                  {d.requests}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function ChannelBars({ data, total }: { data: ChannelBreakdown[]; total: number }) {
  if (data.length === 0) return <div style={{ color: C.textMute, fontSize: 12 }}>Nema podataka.</div>
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {data.map(c => {
        const pct = total > 0 ? (c.requests / total) * 100 : 0
        return (
          <div key={c.channel} style={{ display: 'flex', alignItems: 'center', gap: 10, fontFamily: 'JetBrains Mono, monospace', fontSize: 11.5 }}>
            <div style={{ width: 70, color: C.textDim }}>
              <Tag color={channelColor(c.channel)}>{c.channel}</Tag>
            </div>
            <div style={{ flex: 1, height: 18, background: C.panelLo, borderRadius: 3, overflow: 'hidden', position: 'relative' }}>
              <div style={{
                width: `${pct}%`, height: '100%',
                background: channelColor(c.channel), opacity: 0.7,
                transition: 'width 0.4s ease',
              }} />
              <div style={{ position: 'absolute', top: 0, left: 8, right: 8, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10.5, color: C.text }}>
                <span>{c.requests.toLocaleString()}</span>
                <span style={{ color: C.textDim }}>{pct.toFixed(0)}%</span>
              </div>
            </div>
            <div style={{ width: 60, textAlign: 'right', color: C.textDim }}>
              ${c.cost_usd.toFixed(3)}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function ModelBars({ data, total }: { data: ModelBreakdown[]; total: number }) {
  if (data.length === 0) return <div style={{ color: C.textMute, fontSize: 12 }}>Nema podataka.</div>
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {data.map(m => {
        const pct = total > 0 ? (m.requests / total) * 100 : 0
        const col = modelColor(m.model_key)
        return (
          <div key={m.model_key} style={{ display: 'flex', alignItems: 'center', gap: 10, fontFamily: 'JetBrains Mono, monospace', fontSize: 11.5 }}>
            <div style={{ width: 70, color: C.textDim }}>
              <Tag color={col}>{m.model_key}</Tag>
            </div>
            <div style={{ flex: 1, height: 18, background: C.panelLo, borderRadius: 3, overflow: 'hidden', position: 'relative' }}>
              <div style={{
                width: `${pct}%`, height: '100%',
                background: col, opacity: 0.7,
                transition: 'width 0.4s ease',
              }} />
              <div style={{ position: 'absolute', top: 0, left: 8, right: 8, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10.5, color: C.text }}>
                <span>{m.requests.toLocaleString()}</span>
                <span style={{ color: C.textDim }}>{pct.toFixed(0)}%</span>
              </div>
            </div>
            <div style={{ width: 60, textAlign: 'right', color: C.textDim }}>
              ${m.cost_usd.toFixed(3)}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function RecentSessionRow({ s }: { s: RecentSession }) {
  const time = new Date(s.last_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  return (
    <Link to={`/sessions/${s.session_id}`} style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '8px 10px', borderRadius: 4,
      textDecoration: 'none',
      background: C.panelLo,
      transition: 'background 0.12s ease',
    }}
      onMouseEnter={e => (e.currentTarget.style.background = C.panelHi)}
      onMouseLeave={e => (e.currentTarget.style.background = C.panelLo)}
    >
      <Tag color={channelColor(s.channel)}>{s.channel}</Tag>
      <Tag color={modelColor(_modelKey(s.model))}>{_modelKey(s.model)}</Tag>
      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5, color: C.textMute, whiteSpace: 'nowrap' }}>
        {s.msg_count} {s.msg_count === 1 ? 'poruka' : 'poruka'} · {time}
      </span>
      <span style={{ flex: 1, color: C.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12.5 }}>
        {s.first_prompt || <em style={{ color: C.textMute }}>(prazno)</em>}
      </span>
      <span style={{ color: C.textMute, fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>→</span>
    </Link>
  )
}

function _modelKey(model: string): string {
  const m = model.toLowerCase()
  if (m.includes('haiku')) return 'haiku'
  if (m.includes('sonnet')) return 'sonnet'
  if (m.includes('opus')) return 'opus'
  return model.slice(0, 12)
}
