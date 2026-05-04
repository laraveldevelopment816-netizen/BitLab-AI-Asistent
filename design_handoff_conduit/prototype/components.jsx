// Conduit dashboard — UI components
// All components written assuming React + TS-via-Babel; exposed on window at bottom.
const { useState, useEffect, useMemo, useRef } = React;

// ─── design tokens ─────────────────────────────────────────────────────────
const C = {
  bg:        '#0b0d10',
  panel:     '#101317',
  panelHi:   '#14181d',
  panelLo:   '#0d1014',
  border:    '#1f242b',
  borderHi:  '#2a3038',
  text:      '#e4e7ec',
  textDim:   '#8a929c',
  textMute:  '#5a626c',
  accent:    '#7dd3fc',  // electric cyan — Conduit signature
  accentDim: '#0c4a6e',
  ok:        '#4ade80',
  warn:      '#fbbf24',
  err:       '#f87171',
  rate:      '#c084fc',
};

const fmtNum = (n) => n >= 1000 ? (n/1000).toFixed(n >= 10000 ? 0 : 1) + 'k' : String(n);
const fmtCost = (c) => c < 0.01 ? `$${(c*1000).toFixed(2)}m` : `$${c.toFixed(4)}`;
const fmtTime = (ts) => {
  const d = new Date(ts);
  const diff = Date.now() - ts;
  if (diff < 60_000) return `${Math.round(diff/1000)}s ago`;
  if (diff < 3600_000) return `${Math.round(diff/60_000)}m ago`;
  if (diff < 86400_000) return `${Math.round(diff/3600_000)}h ago`;
  return d.toLocaleDateString();
};

// ─── atoms ─────────────────────────────────────────────────────────────────
function StatusDot({ status, pulse }) {
  const color = status === 'online' ? C.ok : status === 'degraded' ? C.warn : status === 'offline' ? C.err : C.textMute;
  return (
    <span style={{ position: 'relative', display: 'inline-block', width: 8, height: 8 }}>
      {pulse && status === 'online' && (
        <span style={{
          position: 'absolute', inset: -2, borderRadius: '50%',
          background: color, opacity: 0.3, animation: 'pulse 2s ease-out infinite',
        }} />
      )}
      <span style={{
        position: 'absolute', inset: 0, borderRadius: '50%',
        background: color, boxShadow: `0 0 6px ${color}80`,
      }} />
    </span>
  );
}

function Tag({ children, color, subtle }) {
  return (
    <span style={{
      fontFamily: 'JetBrains Mono, monospace',
      fontSize: 10,
      letterSpacing: '0.04em',
      textTransform: 'uppercase',
      padding: '2px 6px',
      borderRadius: 3,
      border: `1px solid ${color}40`,
      background: subtle ? `${color}10` : `${color}20`,
      color: color,
      whiteSpace: 'nowrap',
    }}>{children}</span>
  );
}

function StatusBadge({ s }) {
  if (s === 'ok')         return <Tag color={C.ok}>200 OK</Tag>;
  if (s === 'error')      return <Tag color={C.err}>ERR</Tag>;
  if (s === 'rate_limit') return <Tag color={C.rate}>429</Tag>;
  return <Tag color={C.textMute}>{s}</Tag>;
}

function AdapterPill({ id, size = 'sm' }) {
  const a = window.ADAPTERS.find(x => x.id === id);
  if (!a) return null;
  const pad = size === 'sm' ? '2px 6px' : '4px 10px';
  const fs  = size === 'sm' ? 11 : 12;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: pad, borderRadius: 4,
      background: `${a.color}18`,
      border: `1px solid ${a.color}30`,
      color: a.color, fontFamily: 'JetBrains Mono, monospace',
      fontSize: fs, fontWeight: 500,
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: a.color }} />
      {a.name}
    </span>
  );
}

// ─── header / sidebar ──────────────────────────────────────────────────────
function Sidebar({ tab, setTab, stats }) {
  const items = [
    { id: 'live',      label: 'Live',       hint: 'Real-time stream' },
    { id: 'history',   label: 'History',    hint: 'All requests' },
    { id: 'adapters',  label: 'Adapters',   hint: 'Health & sessions' },
    { id: 'compose',   label: 'Compose',    hint: 'Send a prompt' },
    { id: 'compare',   label: 'Compare',    hint: 'Side-by-side' },
    { id: 'templates', label: 'Templates',  hint: 'Prompt library' },
    { id: 'cost',      label: 'Cost',       hint: 'Token & spend' },
    { id: 'plan',      label: 'Roadmap',    hint: 'Build phases' },
    { id: 'settings',  label: 'Settings',   hint: 'API keys, routing' },
  ];
  return (
    <nav style={{
      width: 232, flexShrink: 0,
      background: C.panelLo, borderRight: `1px solid ${C.border}`,
      display: 'flex', flexDirection: 'column',
      height: '100vh', position: 'sticky', top: 0,
    }}>
      <div style={{
        padding: '20px 18px 18px',
        borderBottom: `1px solid ${C.border}`,
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <ConduitMark size={28} />
        <div>
          <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 15, fontWeight: 600, letterSpacing: '-0.01em' }}>
            conduit
          </div>
          <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: C.textMute, letterSpacing: '0.05em' }}>
            v0.3.2 · local
          </div>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 8px' }}>
        {items.map(it => (
          <button key={it.id} onClick={() => setTab(it.id)}
            style={{
              display: 'block', width: '100%', textAlign: 'left',
              padding: '8px 12px', margin: '1px 0',
              background: tab === it.id ? `${C.accent}14` : 'transparent',
              border: 'none', borderLeft: `2px solid ${tab === it.id ? C.accent : 'transparent'}`,
              color: tab === it.id ? C.text : C.textDim,
              fontSize: 13, fontFamily: 'inherit', cursor: 'pointer',
              borderRadius: '0 4px 4px 0', transition: 'background 0.12s',
            }}>
            <div style={{ fontWeight: tab === it.id ? 500 : 400 }}>{it.label}</div>
            <div style={{ fontSize: 10.5, color: C.textMute, marginTop: 1 }}>{it.hint}</div>
          </button>
        ))}
      </div>

      <div style={{
        padding: '12px 16px',
        borderTop: `1px solid ${C.border}`,
        fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5,
        color: C.textDim, lineHeight: 1.7,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>queue</span><span style={{ color: C.text }}>{stats.queue}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>req/min</span><span style={{ color: C.text }}>{stats.rpm}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>spend/d</span><span style={{ color: C.accent }}>{fmtCost(stats.spend)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, paddingTop: 6, borderTop: `1px dashed ${C.border}` }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <StatusDot status="online" pulse />
            <span>API</span>
          </span>
          <span style={{ color: C.textDim }}>:8000</span>
        </div>
      </div>
    </nav>
  );
}

function ConduitMark({ size = 24 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect x="1" y="1" width="30" height="30" rx="6" fill={C.panel} stroke={C.accent} strokeOpacity="0.4" />
      <path d="M8 11 Q16 11 16 16 Q16 21 24 21" stroke={C.accent} strokeWidth="2" fill="none" strokeLinecap="round" />
      <circle cx="8"  cy="11" r="2" fill={C.accent} />
      <circle cx="24" cy="21" r="2" fill={C.accent} />
      <circle cx="16" cy="16" r="1.5" fill={C.text} />
    </svg>
  );
}

function TopBar({ title, subtitle, right }) {
  return (
    <div style={{
      padding: '20px 28px 18px',
      borderBottom: `1px solid ${C.border}`,
      display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
      gap: 24, background: C.bg,
    }}>
      <div>
        <h1 style={{
          margin: 0, fontSize: 22, fontWeight: 500, letterSpacing: '-0.02em',
        }}>{title}</h1>
        {subtitle && <div style={{ color: C.textDim, fontSize: 13, marginTop: 4 }}>{subtitle}</div>}
      </div>
      {right && <div>{right}</div>}
    </div>
  );
}

// ─── log row & detail drawer ──────────────────────────────────────────────
function LogRow({ r, onClick, fresh }) {
  return (
    <div onClick={() => onClick(r)} style={{
      display: 'grid',
      gridTemplateColumns: '76px 110px 110px 1fr 70px 80px 70px 60px',
      alignItems: 'center', gap: 12,
      padding: '8px 16px',
      borderBottom: `1px solid ${C.border}`,
      cursor: 'pointer',
      fontFamily: 'JetBrains Mono, monospace', fontSize: 12,
      background: fresh ? `${C.accent}08` : 'transparent',
      transition: 'background 0.6s',
    }}
    onMouseEnter={e => e.currentTarget.style.background = `${C.accent}10`}
    onMouseLeave={e => e.currentTarget.style.background = fresh ? `${C.accent}08` : 'transparent'}
    >
      <span style={{ color: C.textMute }}>{fmtTime(r.ts)}</span>
      <span style={{ color: C.textDim }}>{r.id}</span>
      <AdapterPill id={r.adapter} />
      <span style={{ color: C.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {r.prompt}
      </span>
      <span style={{ color: C.textDim, textAlign: 'right' }}>
        <span style={{ color: '#7fb069' }}>↓{fmtNum(r.tokensIn)}</span>{' '}
        <span style={{ color: '#e8c468' }}>↑{fmtNum(r.tokensOut)}</span>
      </span>
      <span style={{ color: C.textDim, textAlign: 'right' }}>{r.latency.toFixed(2)}s</span>
      <span style={{ color: C.accent, textAlign: 'right' }}>{fmtCost(r.cost)}</span>
      <span style={{ textAlign: 'right' }}><StatusBadge s={r.status} /></span>
    </div>
  );
}

function DetailDrawer({ req, onClose }) {
  if (!req) return null;
  const a = window.ADAPTERS.find(x => x.id === req.adapter);
  return (
    <>
      <div onClick={onClose} style={{
        position: 'fixed', inset: 0, background: '#000a', zIndex: 50,
        animation: 'fadeIn 0.18s',
      }} />
      <aside style={{
        position: 'fixed', top: 0, right: 0, bottom: 0,
        width: 540, background: C.panel,
        borderLeft: `1px solid ${C.border}`, zIndex: 51,
        display: 'flex', flexDirection: 'column',
        animation: 'slideIn 0.22s cubic-bezier(.2,.8,.3,1)',
      }}>
        <div style={{ padding: '18px 22px 14px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
          <div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: C.textMute }}>request</div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 16, color: C.text, marginTop: 2 }}>{req.id}</div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8, alignItems: 'center' }}>
              <AdapterPill id={req.adapter} />
              <Tag color={C.textDim} subtle>{req.client}</Tag>
              <StatusBadge s={req.status} />
            </div>
          </div>
          <button onClick={onClose} style={{
            background: 'transparent', border: `1px solid ${C.border}`, color: C.textDim,
            width: 28, height: 28, borderRadius: 4, cursor: 'pointer', fontSize: 14,
          }}>×</button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '18px 22px' }}>
          <Section label="prompt">
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: C.text, lineHeight: 1.6, padding: 12, background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4 }}>
              {req.prompt}
            </div>
          </Section>

          <Section label="response">
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: C.text, lineHeight: 1.6, padding: 12, background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4, whiteSpace: 'pre-wrap' }}>
              {req.response}
              {req.status === 'ok' && <span style={{ display: 'inline-block', width: 6, height: 12, background: C.accent, marginLeft: 2, verticalAlign: 'text-bottom' }} />}
            </div>
          </Section>

          <Section label="timing">
            <TimingBars req={req} />
          </Section>

          <Section label="tokens & cost">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
              <Metric label="input" value={fmtNum(req.tokensIn)} sub="tokens" />
              <Metric label="output" value={fmtNum(req.tokensOut)} sub="tokens" />
              <Metric label="cost @ api" value={fmtCost(req.cost)} sub={a?.model} />
            </div>
          </Section>

          <Section label="actions">
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Btn>Replay</Btn>
              <Btn>Replay on…</Btn>
              <Btn>Copy as cURL</Btn>
              <Btn>Save as template</Btn>
              <Btn ghost>View raw</Btn>
            </div>
          </Section>
        </div>
      </aside>
    </>
  );
}

function Section({ label, children }) {
  return (
    <div style={{ marginBottom: 22 }}>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        color: C.textMute, marginBottom: 8,
      }}>{label}</div>
      {children}
    </div>
  );
}

function Metric({ label, value, sub }) {
  return (
    <div style={{ background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4, padding: '10px 12px' }}>
      <div style={{ fontSize: 10, color: C.textMute, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      <div style={{ fontSize: 18, color: C.text, fontFamily: 'JetBrains Mono, monospace', marginTop: 2 }}>{value}</div>
      {sub && <div style={{ fontSize: 10.5, color: C.textDim, marginTop: 2, fontFamily: 'JetBrains Mono, monospace' }}>{sub}</div>}
    </div>
  );
}

function TimingBars({ req }) {
  // synthesize a timing breakdown
  const total = req.latency * 1000;
  const phases = [
    { name: 'queue',     ms: total * 0.04, color: C.textMute },
    { name: 'navigate',  ms: total * 0.08, color: '#5a8aae' },
    { name: 'send',      ms: total * 0.06, color: '#7fb069' },
    { name: 'gen',       ms: total * 0.78, color: C.accent },
    { name: 'extract',   ms: total * 0.04, color: '#c084fc' },
  ];
  return (
    <div>
      <div style={{ display: 'flex', height: 8, borderRadius: 2, overflow: 'hidden', background: C.panelLo, border: `1px solid ${C.border}` }}>
        {phases.map(p => (
          <div key={p.name} style={{ width: `${(p.ms/total)*100}%`, background: p.color }} />
        ))}
      </div>
      <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6 }}>
        {phases.map(p => (
          <div key={p.name} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: C.textMute }}>
              <span style={{ width: 6, height: 6, background: p.color, borderRadius: 1 }} />
              {p.name}
            </div>
            <div style={{ color: C.text, marginTop: 2 }}>{Math.round(p.ms)}ms</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Btn({ children, onClick, ghost, primary }) {
  const bg = primary ? C.accent : ghost ? 'transparent' : C.panelHi;
  const fg = primary ? C.bg : ghost ? C.textDim : C.text;
  const bd = primary ? C.accent : C.border;
  return (
    <button onClick={onClick} style={{
      padding: '6px 12px', borderRadius: 4,
      background: bg, color: fg, border: `1px solid ${bd}`,
      fontFamily: 'inherit', fontSize: 12, cursor: 'pointer',
      transition: 'all 0.12s',
    }}
    onMouseEnter={e => { if (!primary) e.currentTarget.style.background = C.borderHi; }}
    onMouseLeave={e => { if (!primary) e.currentTarget.style.background = bg; }}
    >
      {children}
    </button>
  );
}

// ─── shared CSS ───────────────────────────────────────────────────────────
function GlobalStyles() {
  return (
    <style>{`
      @keyframes pulse { 0% { transform: scale(1); opacity: 0.5; } 100% { transform: scale(2.4); opacity: 0; } }
      @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
      @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
      @keyframes blink { 50% { opacity: 0.3; } }
      ::-webkit-scrollbar { width: 10px; height: 10px; }
      ::-webkit-scrollbar-track { background: ${C.panelLo}; }
      ::-webkit-scrollbar-thumb { background: ${C.border}; border-radius: 5px; }
      ::-webkit-scrollbar-thumb:hover { background: ${C.borderHi}; }
    `}</style>
  );
}

Object.assign(window, {
  C, fmtNum, fmtCost, fmtTime,
  StatusDot, Tag, StatusBadge, AdapterPill,
  Sidebar, ConduitMark, TopBar,
  LogRow, DetailDrawer, Section, Metric, TimingBars,
  Btn, GlobalStyles,
});
