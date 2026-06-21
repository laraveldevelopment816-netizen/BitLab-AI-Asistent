// Conduit — tab views (part 1)
const { useState: useStateV1, useEffect: useEffectV1, useMemo: useMemoV1, useRef: useRefV1 } = React;

// ─── LIVE ──────────────────────────────────────────────────────────────────
function LiveView({ onPick }) {
  const [reqs, setReqs] = useStateV1(window.REQUESTS.slice(0, 14));
  const [paused, setPaused] = useStateV1(false);
  const [freshIds, setFreshIds] = useStateV1(new Set());

  useEffectV1(() => {
    if (paused) return;
    const tick = setInterval(() => {
      const seed = window.REQUESTS[Math.floor(Math.random() * window.REQUESTS.length)];
      const newReq = { ...seed, id: `req_${Math.random().toString(36).slice(2, 8)}`, ts: Date.now() };
      setReqs(prev => [newReq, ...prev].slice(0, 30));
      setFreshIds(s => new Set([...s, newReq.id]));
      setTimeout(() => setFreshIds(s => { const n = new Set(s); n.delete(newReq.id); return n; }), 1500);
    }, 3500);
    return () => clearInterval(tick);
  }, [paused]);

  const totals = useMemoV1(() => {
    const t = { req: reqs.length, in: 0, out: 0, cost: 0 };
    reqs.forEach(r => { t.in += r.tokensIn; t.out += r.tokensOut; t.cost += r.cost; });
    return t;
  }, [reqs]);

  return (
    <div>
      <TopBar
        title="Live stream"
        subtitle="Real-time feed from /v1/chat/completions and adapter queues"
        right={
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: C.textDim }}>
              <StatusDot status={paused ? 'offline' : 'online'} pulse={!paused} />{' '}
              {paused ? 'paused' : 'streaming'}
            </span>
            <Btn onClick={() => setPaused(p => !p)} ghost>{paused ? '▶ resume' : '⏸ pause'}</Btn>
            <Btn>⤓ export jsonl</Btn>
          </div>
        }
      />

      <div style={{ padding: '16px 28px 0', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
        <Metric label="last 30 visible" value={totals.req} sub="requests" />
        <Metric label="input tokens" value={fmtNum(totals.in)} sub="↓ context" />
        <Metric label="output tokens" value={fmtNum(totals.out)} sub="↑ generated" />
        <Metric label="cost @ real api" value={fmtCost(totals.cost)} sub="if migrated" />
      </div>

      <div style={{ margin: '16px 28px 28px', background: C.panel, border: `1px solid ${C.border}`, borderRadius: 6, overflow: 'hidden' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '76px 110px 110px 1fr 70px 80px 70px 60px',
          gap: 12, padding: '10px 16px',
          background: C.panelLo, borderBottom: `1px solid ${C.border}`,
          fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
          letterSpacing: '0.06em', textTransform: 'uppercase', color: C.textMute,
        }}>
          <span>time</span><span>id</span><span>adapter</span><span>prompt</span>
          <span style={{ textAlign: 'right' }}>tokens</span>
          <span style={{ textAlign: 'right' }}>latency</span>
          <span style={{ textAlign: 'right' }}>cost</span>
          <span style={{ textAlign: 'right' }}>status</span>
        </div>
        {reqs.map(r => <LogRow key={r.id} r={r} onClick={onPick} fresh={freshIds.has(r.id)} />)}
      </div>
    </div>
  );
}

// ─── HISTORY ───────────────────────────────────────────────────────────────
function HistoryView({ onPick }) {
  const [filterAdapter, setFilterAdapter] = useStateV1('all');
  const [filterStatus, setFilterStatus] = useStateV1('all');
  const [search, setSearch] = useStateV1('');

  const filtered = useMemoV1(() => {
    return window.REQUESTS.filter(r => {
      if (filterAdapter !== 'all' && r.adapter !== filterAdapter) return false;
      if (filterStatus !== 'all' && r.status !== filterStatus) return false;
      if (search && !r.prompt.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [filterAdapter, filterStatus, search]);

  return (
    <div>
      <TopBar title="History" subtitle={`${filtered.length} requests · last 24h`} />
      <div style={{ padding: '12px 28px', display: 'flex', gap: 10, alignItems: 'center', borderBottom: `1px solid ${C.border}` }}>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search prompts…"
          style={{
            flex: 1, padding: '7px 12px', background: C.panel,
            border: `1px solid ${C.border}`, borderRadius: 4, color: C.text,
            fontFamily: 'inherit', fontSize: 12,
          }}
        />
        <Select value={filterAdapter} onChange={setFilterAdapter}
          options={[{ v: 'all', l: 'all adapters' }, ...window.ADAPTERS.map(a => ({ v: a.id, l: a.name }))]}
        />
        <Select value={filterStatus} onChange={setFilterStatus}
          options={[
            { v: 'all', l: 'all statuses' },
            { v: 'ok', l: '200 OK' },
            { v: 'error', l: 'errors' },
            { v: 'rate_limit', l: 'rate limited' },
          ]}
        />
      </div>

      <div style={{ margin: '16px 28px 28px', background: C.panel, border: `1px solid ${C.border}`, borderRadius: 6, overflow: 'hidden' }}>
        {filtered.map(r => <LogRow key={r.id} r={r} onClick={onPick} />)}
        {filtered.length === 0 && (
          <div style={{ padding: 40, textAlign: 'center', color: C.textMute, fontSize: 13 }}>No requests match your filters.</div>
        )}
      </div>
    </div>
  );
}

function Select({ value, onChange, options }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      style={{
        padding: '7px 10px', background: C.panel,
        border: `1px solid ${C.border}`, borderRadius: 4, color: C.text,
        fontFamily: 'inherit', fontSize: 12, cursor: 'pointer',
      }}>
      {options.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
    </select>
  );
}

// ─── ADAPTERS ──────────────────────────────────────────────────────────────
function AdaptersView() {
  return (
    <div>
      <TopBar
        title="Adapters"
        subtitle="Browser sessions, health, and per-provider stats"
        right={<Btn primary>+ Add adapter</Btn>}
      />
      <div style={{ padding: '20px 28px', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 14 }}>
        {window.ADAPTERS.map(a => <AdapterCard key={a.id} a={a} />)}
      </div>
    </div>
  );
}

function AdapterCard({ a }) {
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 6, padding: 16, position: 'relative' }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: a.color, opacity: a.status === 'offline' ? 0.2 : 0.7 }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 500, color: C.text, display: 'flex', alignItems: 'center', gap: 8 }}>
            <StatusDot status={a.status} pulse />
            {a.name}
          </div>
          <div style={{ fontSize: 11, color: C.textDim, fontFamily: 'JetBrains Mono, monospace', marginTop: 4 }}>
            {a.model}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {a.status === 'offline' ? <Tag color={C.err}>offline</Tag>
            : a.status === 'degraded' ? <Tag color={C.warn}>degraded</Tag>
            : <Tag color={C.ok}>online</Tag>}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 12 }}>
        <Mini label="queue" v={a.queueDepth} />
        <Mini label="active" v={a.activeRequests} />
        <Mini label="p95" v={a.p95Latency ? `${a.p95Latency}s` : '—'} />
        <Mini label="success" v={a.successRate ? `${a.successRate}%` : '—'} ok={a.successRate >= 99} warn={a.successRate >= 95 && a.successRate < 99} err={a.successRate > 0 && a.successRate < 95} />
      </div>

      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5, color: C.textDim, lineHeight: 1.7, padding: '10px 0', borderTop: `1px dashed ${C.border}` }}>
        <Row k="auth" v={a.auth === 'authenticated' ? <span style={{ color: C.ok }}>● {a.auth}</span> : <span style={{ color: C.textMute }}>{a.auth}</span>} />
        <Row k="session" v={a.sessionAge} />
        <Row k="today" v={`${a.requestsToday} req · ↓${fmtNum(a.tokensToday.in)} ↑${fmtNum(a.tokensToday.out)}`} />
        {a.lastError && <Row k="last err" v={<span style={{ color: C.err }}>{a.lastError}</span>} />}
      </div>

      <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
        <Btn ghost>Re-login</Btn>
        <Btn ghost>Logs</Btn>
        <Btn ghost>Test ping</Btn>
      </div>
    </div>
  );
}

function Mini({ label, v, ok, warn, err }) {
  const color = ok ? C.ok : warn ? C.warn : err ? C.err : C.text;
  return (
    <div>
      <div style={{ fontSize: 9.5, color: C.textMute, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      <div style={{ fontSize: 16, color, fontFamily: 'JetBrains Mono, monospace', marginTop: 2 }}>{v}</div>
    </div>
  );
}

function Row({ k, v }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
      <span style={{ color: C.textMute }}>{k}</span>
      <span style={{ color: C.text, textAlign: 'right' }}>{v}</span>
    </div>
  );
}

Object.assign(window, { LiveView, HistoryView, AdaptersView, Select });
