// Conduit — tab views (part 2): Compose, Compare, Templates, Cost, Plan, Settings
const { useState: useStateV2, useEffect: useEffectV2, useMemo: useMemoV2 } = React;

// ─── COMPOSE ──────────────────────────────────────────────────────────────
function ComposeView() {
  const [prompt, setPrompt] = useStateV2('Write a single-paragraph release note for Conduit v0.4 highlighting the new compare mode.');
  const [adapter, setAdapter] = useStateV2('claude');
  const [policy, setPolicy] = useStateV2('sticky');
  const [streaming, setStreaming] = useStateV2(false);
  const [response, setResponse] = useStateV2(null);

  function send() {
    setResponse({ status: 'pending' });
    setTimeout(() => {
      const text = "Conduit v0.4 lands compare mode — fan a single prompt out to multiple adapters and review responses side-by-side, with token + latency deltas inline. Routing policies now include cost-aware selection, and a new daily budget banner warns before you blow past your soft limit. Streaming is on by default for Claude.ai and ChatGPT.";
      const tokIn = Math.ceil(prompt.length / 3.6);
      const tokOut = Math.ceil(text.length / 3.6);
      setResponse({
        status: 'ok', text,
        tokensIn: tokIn, tokensOut: tokOut,
        latency: 4.21,
        cost: (tokIn * 3 + tokOut * 15) / 1_000_000,
      });
    }, streaming ? 600 : 1100);
  }

  return (
    <div>
      <TopBar title="Compose" subtitle="Send a one-off prompt — same path your API clients take" />
      <div style={{ padding: '20px 28px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
        <div>
          <Section label="prompt">
            <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={10}
              style={{
                width: '100%', padding: 12, background: C.panelLo,
                border: `1px solid ${C.border}`, borderRadius: 4, color: C.text,
                fontFamily: 'JetBrains Mono, monospace', fontSize: 12.5, lineHeight: 1.6, resize: 'vertical',
              }}
            />
          </Section>
          <Section label="routing">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <Field label="Target adapter">
                <Select value={adapter} onChange={setAdapter}
                  options={[
                    { v: 'auto', l: '— auto (policy)' },
                    ...window.ADAPTERS.filter(a => a.status !== 'offline').map(a => ({ v: a.id, l: a.name })),
                  ]} />
              </Field>
              <Field label="Policy when auto">
                <Select value={policy} onChange={setPolicy}
                  options={[
                    { v: 'cheapest', l: 'cheapest' },
                    { v: 'fastest', l: 'fastest (p50)' },
                    { v: 'sticky', l: 'sticky session' },
                    { v: 'roundrobin', l: 'round-robin' },
                  ]} />
              </Field>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, fontSize: 12.5, color: C.textDim, cursor: 'pointer' }}>
              <input type="checkbox" checked={streaming} onChange={e => setStreaming(e.target.checked)} />
              Stream response (SSE)
            </label>
          </Section>
          <div style={{ display: 'flex', gap: 10 }}>
            <Btn primary onClick={send}>▶ Send</Btn>
            <Btn ghost>Save as template</Btn>
            <Btn ghost>Copy as cURL</Btn>
          </div>
        </div>

        <div>
          <Section label="response">
            <div style={{
              minHeight: 280, padding: 14, background: C.panelLo,
              border: `1px solid ${C.border}`, borderRadius: 4,
              fontFamily: 'JetBrains Mono, monospace', fontSize: 12.5, lineHeight: 1.6,
              color: C.text, whiteSpace: 'pre-wrap',
            }}>
              {!response && <span style={{ color: C.textMute }}>// response will appear here…</span>}
              {response?.status === 'pending' && <span style={{ color: C.accent, animation: 'blink 1s infinite' }}>⠋ generating…</span>}
              {response?.status === 'ok' && (
                <>
                  {response.text}
                  <span style={{ display: 'inline-block', width: 6, height: 12, background: C.accent, marginLeft: 2, verticalAlign: 'text-bottom' }} />
                </>
              )}
            </div>
          </Section>
          {response?.status === 'ok' && (
            <Section label="this run">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                <Metric label="latency" value={`${response.latency}s`} />
                <Metric label="↓ in" value={fmtNum(response.tokensIn)} />
                <Metric label="↑ out" value={fmtNum(response.tokensOut)} />
                <Metric label="cost" value={fmtCost(response.cost)} />
              </div>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label style={{ display: 'block' }}>
      <div style={{ fontSize: 10, color: C.textMute, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 5 }}>{label}</div>
      {children}
    </label>
  );
}

// ─── COMPARE ──────────────────────────────────────────────────────────────
function CompareView() {
  const [prompt, setPrompt] = useStateV2('In one sentence: when should I prefer SQLite over Postgres?');
  const [picked, setPicked] = useStateV2(['claude', 'chatgpt', 'deepseek']);
  const [results, setResults] = useStateV2(null);

  function fanOut() {
    setResults(picked.map(id => ({ id, status: 'pending' })));
    picked.forEach((id, i) => {
      setTimeout(() => {
        const a = window.ADAPTERS.find(x => x.id === id);
        const responses = {
          claude:   'Prefer SQLite when your write traffic comes from a single process and your data fits on one disk — its simplicity, zero ops, and strong defaults are hard to beat at that scale.',
          chatgpt:  'Choose SQLite for embedded, single-writer workloads where operational simplicity and a file-on-disk deployment beat the network overhead of a server-based DB.',
          deepseek: 'Use SQLite when there is a single writer, low-to-moderate concurrency, and you want zero operational overhead.',
          grok:     'SQLite wins for embedded, single-process apps; Postgres wins anywhere you need network access, replication, or many concurrent writers.',
        };
        const tokIn = 14, tokOut = 30 + Math.floor(Math.random() * 12);
        const lat = (1.4 + Math.random() * 4).toFixed(2);
        setResults(prev => prev.map(r => r.id !== id ? r : {
          ...r, status: 'ok',
          text: responses[id] || 'Synthesized response.',
          tokensIn: tokIn, tokensOut: tokOut,
          latency: parseFloat(lat),
          cost: (tokIn * (window.PROVIDER_PRICING[a.model]?.in || 0) +
                 tokOut * (window.PROVIDER_PRICING[a.model]?.out || 0)) / 1_000_000,
        }));
      }, 700 + i * 500);
    });
  }

  return (
    <div>
      <TopBar title="Compare" subtitle="Fan one prompt to N adapters · weigh quality vs. cost vs. latency" />
      <div style={{ padding: '20px 28px' }}>
        <Section label="prompt">
          <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={3}
            style={{
              width: '100%', padding: 12, background: C.panelLo,
              border: `1px solid ${C.border}`, borderRadius: 4, color: C.text,
              fontFamily: 'JetBrains Mono, monospace', fontSize: 12.5, lineHeight: 1.6, resize: 'vertical',
            }}
          />
        </Section>
        <Section label="adapters to compare">
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {window.ADAPTERS.filter(a => a.status !== 'offline').map(a => {
              const on = picked.includes(a.id);
              return (
                <button key={a.id} onClick={() => setPicked(p => on ? p.filter(x => x !== a.id) : [...p, a.id])}
                  style={{
                    padding: '6px 12px', borderRadius: 4, cursor: 'pointer',
                    background: on ? `${a.color}22` : C.panelLo,
                    border: `1px solid ${on ? a.color + '80' : C.border}`,
                    color: on ? a.color : C.textDim,
                    fontFamily: 'inherit', fontSize: 12,
                  }}>
                  {on ? '✓ ' : ''}{a.name}
                </button>
              );
            })}
          </div>
        </Section>
        <Btn primary onClick={fanOut}>▶ Run on {picked.length} adapters</Btn>

        {results && (
          <div style={{ marginTop: 22, display: 'grid', gridTemplateColumns: `repeat(${results.length}, 1fr)`, gap: 12 }}>
            {results.map(r => {
              const a = window.ADAPTERS.find(x => x.id === r.id);
              return (
                <div key={r.id} style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 6, overflow: 'hidden' }}>
                  <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: `2px solid ${a.color}` }}>
                    <AdapterPill id={r.id} size="md" />
                    {r.status === 'ok' && <span style={{ fontSize: 11, color: C.textDim, fontFamily: 'JetBrains Mono, monospace' }}>{r.latency}s · {fmtCost(r.cost)}</span>}
                  </div>
                  <div style={{ padding: 14, fontFamily: 'JetBrains Mono, monospace', fontSize: 12, lineHeight: 1.6, color: C.text, minHeight: 120 }}>
                    {r.status === 'pending' ? <span style={{ color: C.accent, animation: 'blink 1s infinite' }}>⠋ generating…</span> : r.text}
                  </div>
                  {r.status === 'ok' && (
                    <div style={{ padding: '8px 14px', borderTop: `1px solid ${C.border}`, fontSize: 10.5, color: C.textMute, fontFamily: 'JetBrains Mono, monospace', display: 'flex', justifyContent: 'space-between' }}>
                      <span>↓{r.tokensIn} ↑{r.tokensOut}</span>
                      <span>{a.model}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── TEMPLATES ────────────────────────────────────────────────────────────
function TemplatesView() {
  const [picked, setPicked] = useStateV2(window.TEMPLATES[0]);
  return (
    <div>
      <TopBar title="Templates" subtitle="Reusable prompts with {{variables}}" right={<Btn primary>+ New</Btn>} />
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', minHeight: 'calc(100vh - 78px)' }}>
        <div style={{ borderRight: `1px solid ${C.border}`, padding: '12px 0' }}>
          {window.TEMPLATES.map(t => (
            <button key={t.id} onClick={() => setPicked(t)} style={{
              display: 'block', width: '100%', textAlign: 'left',
              padding: '10px 18px',
              background: picked.id === t.id ? `${C.accent}10` : 'transparent',
              borderLeft: `2px solid ${picked.id === t.id ? C.accent : 'transparent'}`,
              border: 'none', cursor: 'pointer',
            }}>
              <div style={{ fontSize: 13, color: C.text }}>{t.name}</div>
              <div style={{ fontSize: 10.5, color: C.textMute, marginTop: 2, fontFamily: 'JetBrains Mono, monospace' }}>
                {t.tags.map(x => '#' + x).join(' ')} · {t.uses} uses
              </div>
            </button>
          ))}
        </div>
        <div style={{ padding: '20px 28px' }}>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 500 }}>{picked.name}</h2>
          <div style={{ marginTop: 16, padding: 14, background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4, fontFamily: 'JetBrains Mono, monospace', fontSize: 12.5, lineHeight: 1.6, color: C.text, whiteSpace: 'pre-wrap' }}>
            {picked.body.split(/(\{\{\w+\}\})/g).map((part, i) =>
              part.match(/^\{\{\w+\}\}$/)
                ? <span key={i} style={{ background: `${C.accent}20`, color: C.accent, padding: '1px 4px', borderRadius: 2 }}>{part}</span>
                : <span key={i}>{part}</span>
            )}
          </div>
          <div style={{ marginTop: 14, display: 'flex', gap: 8 }}>
            <Btn primary>Use template</Btn>
            <Btn ghost>Edit</Btn>
            <Btn ghost>Duplicate</Btn>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── COST ─────────────────────────────────────────────────────────────────
function CostView() {
  const totals = useMemoV2(() => {
    const t = { req: 0, in: 0, out: 0, cost: 0 };
    window.REQUESTS.forEach(r => { t.req++; t.in += r.tokensIn; t.out += r.tokensOut; t.cost += r.cost; });
    t.month = t.cost * 30;
    return t;
  }, []);
  const byAdapter = useMemoV2(() => {
    const m = {};
    window.REQUESTS.forEach(r => {
      m[r.adapter] = m[r.adapter] || { in: 0, out: 0, cost: 0, count: 0 };
      m[r.adapter].in += r.tokensIn;
      m[r.adapter].out += r.tokensOut;
      m[r.adapter].cost += r.cost;
      m[r.adapter].count++;
    });
    return m;
  }, []);
  const budget = 50; // $/month soft limit
  const pct = Math.min(100, (totals.month / budget) * 100);

  return (
    <div>
      <TopBar title="Cost projection" subtitle="What today's traffic would cost on the real APIs" />
      <div style={{ padding: '20px 28px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 22 }}>
          <Metric label="today, total" value={fmtCost(totals.cost)} sub={`${totals.req} requests`} />
          <Metric label="↓ input tokens" value={fmtNum(totals.in)} />
          <Metric label="↑ output tokens" value={fmtNum(totals.out)} />
          <Metric label="projected / month" value={fmtCost(totals.month)} sub="at current rate" />
        </div>

        <Section label="monthly budget · soft limit $50">
          <div style={{ background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 6, padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: C.textDim, marginBottom: 8, fontFamily: 'JetBrains Mono, monospace' }}>
              <span>{fmtCost(totals.month)} projected</span>
              <span>{pct.toFixed(0)}% of ${budget}</span>
            </div>
            <div style={{ height: 10, background: C.bg, borderRadius: 2, overflow: 'hidden' }}>
              <div style={{
                width: `${pct}%`, height: '100%',
                background: pct > 90 ? C.err : pct > 70 ? C.warn : C.accent,
                transition: 'width 0.4s',
              }} />
            </div>
          </div>
        </Section>

        <Section label="by adapter">
          <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 6 }}>
            {Object.entries(byAdapter).map(([id, v]) => {
              const a = window.ADAPTERS.find(x => x.id === id);
              const max = Math.max(...Object.values(byAdapter).map(x => x.cost));
              return (
                <div key={id} style={{ padding: '14px 18px', borderBottom: `1px solid ${C.border}`, display: 'grid', gridTemplateColumns: '160px 1fr 100px 90px', alignItems: 'center', gap: 14 }}>
                  <AdapterPill id={id} size="md" />
                  <div style={{ height: 6, background: C.bg, borderRadius: 1 }}>
                    <div style={{ width: `${(v.cost/max)*100}%`, height: '100%', background: a.color, borderRadius: 1 }} />
                  </div>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: C.textDim, textAlign: 'right' }}>
                    ↓{fmtNum(v.in)} ↑{fmtNum(v.out)}
                  </span>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, color: C.accent, textAlign: 'right' }}>{fmtCost(v.cost)}</span>
                </div>
              );
            })}
          </div>
        </Section>

        <Section label="hourly traffic · last 24h">
          <HourlyChart />
        </Section>
      </div>
    </div>
  );
}

function HourlyChart() {
  const data = window.HOURLY;
  const max = Math.max(...data.flatMap(d => window.ADAPTERS.map(a => d[a.id] || 0))) || 1;
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 6, padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 140 }}>
        {data.map((d, i) => (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column-reverse', gap: 1, height: '100%' }}>
            {window.ADAPTERS.filter(a => a.status !== 'offline').map(a => {
              const h = ((d[a.id] || 0) / max) * 100;
              if (h === 0) return null;
              return <div key={a.id} style={{ height: `${h}%`, background: a.color, opacity: 0.85 }} title={`${a.name} · ${d[a.id]}`} />;
            })}
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: C.textMute, fontFamily: 'JetBrains Mono, monospace', marginTop: 8 }}>
        <span>24h ago</span><span>12h</span><span>now</span>
      </div>
      <div style={{ display: 'flex', gap: 14, marginTop: 12, fontSize: 10.5, color: C.textDim, fontFamily: 'JetBrains Mono, monospace' }}>
        {window.ADAPTERS.filter(a => a.status !== 'offline').map(a => (
          <span key={a.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 8, height: 8, background: a.color }} />
            {a.name}
          </span>
        ))}
      </div>
    </div>
  );
}

// ─── PLAN (the build roadmap) ─────────────────────────────────────────────
function PlanView() {
  return (
    <div>
      <TopBar
        title="Roadmap"
        subtitle="9 phases · each phase = one Claude session · each phase ends testable"
        right={
          <div style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: C.textDim }}>
            <StatusDot status="online" pulse /> 2 of 10 phases shipped
          </div>
        }
      />
      <div style={{ padding: '22px 28px 40px', maxWidth: 980 }}>
        <PlanIntro />
        <div style={{ position: 'relative', paddingLeft: 28, marginTop: 28 }}>
          <div style={{ position: 'absolute', left: 9, top: 8, bottom: 8, width: 2, background: C.border }} />
          {window.ROADMAP.map((p, i) => <PhaseCard key={p.id} p={p} idx={i} />)}
        </div>
        <SessionEconomics />
      </div>
    </div>
  );
}

function PlanIntro() {
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 6, padding: 20 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
        <Metric label="phases" value="10" sub="phase 0 → phase 9" />
        <Metric label="sessions est." value="~10" sub="1 phase per session" />
        <Metric label="opus sessions" value="3" sub="adapter, streaming, routing" />
        <Metric label="sonnet sessions" value="7" sub="everything else" />
      </div>
      <div style={{ marginTop: 18, fontSize: 13, color: C.textDim, lineHeight: 1.7 }}>
        <strong style={{ color: C.text }}>Working principle:</strong> every phase ends with something you can run, test, and verify. Nothing
        rolls over. <strong style={{ color: C.accent }}>Opus is reserved</strong> for high-leverage architecture moments — the
        first adapter (sets the pattern), streaming (locks the protocol), and smart routing (the brain). Everything else is Sonnet, where it pays for itself.
      </div>
    </div>
  );
}

function PhaseCard({ p, idx }) {
  const statusColor = p.status === 'done' ? C.ok : p.status === 'in_progress' ? C.accent : C.textMute;
  const statusLabel = p.status === 'done' ? '● shipped' : p.status === 'in_progress' ? '◐ in progress' : '○ todo';
  return (
    <div style={{ position: 'relative', marginBottom: 14 }}>
      <div style={{
        position: 'absolute', left: -28, top: 14,
        width: 18, height: 18, borderRadius: '50%',
        background: C.bg, border: `2px solid ${statusColor}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 9, fontFamily: 'JetBrains Mono, monospace', color: statusColor,
      }}>
        {idx}
      </div>
      <div style={{
        background: C.panel, border: `1px solid ${p.status === 'in_progress' ? C.accent + '60' : C.border}`,
        borderRadius: 6, padding: 16,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 12 }}>
          <div>
            <div style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: C.textMute, letterSpacing: '0.06em', textTransform: 'uppercase' }}>phase {p.id}</div>
            <h3 style={{ margin: '2px 0 0', fontSize: 16, fontWeight: 500 }}>{p.name}</h3>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <Tag color={statusColor} subtle>{statusLabel}</Tag>
            <Tag color={p.model.startsWith('Opus') ? '#c084fc' : '#7dd3fc'} subtle>{p.model}</Tag>
            <Tag color={C.textDim} subtle>{p.effort}</Tag>
            <Tag color={C.textDim} subtle>~{p.estMessages} msg</Tag>
          </div>
        </div>
        <ul style={{ margin: '6px 0 12px', padding: '0 0 0 18px', color: C.textDim, fontSize: 12.5, lineHeight: 1.7 }}>
          {p.deliverables.map((d, i) => (
            <li key={i} style={{ marginBottom: 1 }}>{d}</li>
          ))}
        </ul>
        <div style={{
          fontSize: 11.5, fontFamily: 'JetBrains Mono, monospace',
          padding: '8px 10px', background: C.panelLo, borderRadius: 3,
          color: C.textDim, borderLeft: `2px solid ${statusColor}`,
        }}>
          <span style={{ color: C.textMute }}>$ test:</span> {p.testable}
        </div>
      </div>
    </div>
  );
}

function SessionEconomics() {
  return (
    <div style={{ marginTop: 30, padding: 18, background: C.panel, border: `1px solid ${C.border}`, borderRadius: 6 }}>
      <div style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: C.textMute, letterSpacing: '0.08em', textTransform: 'uppercase' }}>session economics on €20 Pro plan</div>
      <h3 style={{ margin: '4px 0 12px', fontSize: 15, fontWeight: 500 }}>How tokens get spent</h3>
      <div style={{ fontSize: 12.5, color: C.textDim, lineHeight: 1.75 }}>
        <p style={{ margin: '0 0 10px' }}>
          Pro plan ≈ <strong style={{ color: C.text }}>40–45 Sonnet messages</strong> per 5h window, or roughly{' '}
          <strong style={{ color: C.text }}>10–12 Opus messages</strong>. Each phase here is sized to fit in one window
          with headroom — if a phase looks tight, we cut scope at the bottom and push it to the next phase rather than
          rushing.
        </p>
        <p style={{ margin: '0 0 10px' }}>
          <strong style={{ color: '#c084fc' }}>Opus phases (2, 5, 7)</strong> are the only ones where I'd burn the bigger
          model. Adapter pattern, streaming protocol, and routing logic are the decisions that ripple through everything
          else — getting them right once is cheaper than re-doing them three times on Sonnet.
        </p>
        <p style={{ margin: 0 }}>
          <strong style={{ color: C.accent }}>Token-saving tactics built into the plan:</strong> seed scripts mean we don't paste
          mock data into chat; recorded HAR fixtures mean we don't re-debug auth flows; a strict "one phase, one PR"
          rhythm means I'm not re-reading the whole repo every session.
        </p>
      </div>
    </div>
  );
}

// ─── SETTINGS ─────────────────────────────────────────────────────────────
function SettingsView() {
  return (
    <div>
      <TopBar title="Settings" subtitle="API keys, routing defaults, alerts" />
      <div style={{ padding: '20px 28px', maxWidth: 720 }}>
        <SettingBlock title="Conduit API key" desc="Used by clients pointing at this router. Hashed at rest in OS keychain.">
          <div style={{ display: 'flex', gap: 8 }}>
            <input readOnly value="sk-cdt-7f4a••••••••••••••••3e21"
              style={{ flex: 1, padding: '8px 12px', background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4, color: C.text, fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }} />
            <Btn>Reveal</Btn>
            <Btn>Rotate</Btn>
          </div>
        </SettingBlock>
        <SettingBlock title="Default routing policy" desc="Used when a client doesn't pin a specific adapter.">
          <Select value="cheapest" onChange={() => {}} options={[
            { v: 'cheapest', l: 'cheapest' }, { v: 'fastest', l: 'fastest (p50)' },
            { v: 'sticky', l: 'sticky session' }, { v: 'roundrobin', l: 'round-robin' },
          ]} />
        </SettingBlock>
        <SettingBlock title="Monthly budget" desc="Soft limit. Webhook fires at 80%, banner shows at 90%, requests pause at 100% (configurable).">
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input value="50" style={{ width: 100, padding: '8px 12px', background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4, color: C.text, fontFamily: 'JetBrains Mono, monospace', fontSize: 13 }} readOnly />
            <span style={{ color: C.textDim, fontSize: 13 }}>USD / month</span>
          </div>
        </SettingBlock>
        <SettingBlock title="Webhooks" desc="Fired on completion, error, budget threshold.">
          <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11.5, color: C.textDim, padding: 10, background: C.panelLo, border: `1px solid ${C.border}`, borderRadius: 4 }}>
            POST https://your-server.dev/conduit-events
          </div>
        </SettingBlock>
        <SettingBlock title="Telemetry" desc="Local-only metrics. Never leaves your machine.">
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, color: C.textDim, fontSize: 13 }}>
            <input type="checkbox" defaultChecked /> Keep request/response bodies (off in production by default)
          </label>
        </SettingBlock>
      </div>
    </div>
  );
}

function SettingBlock({ title, desc, children }) {
  return (
    <div style={{ padding: '16px 0', borderBottom: `1px solid ${C.border}` }}>
      <div style={{ fontSize: 14, color: C.text, fontWeight: 500 }}>{title}</div>
      <div style={{ fontSize: 12, color: C.textDim, marginTop: 3, marginBottom: 10 }}>{desc}</div>
      {children}
    </div>
  );
}

Object.assign(window, {
  ComposeView, CompareView, TemplatesView, CostView, PlanView, SettingsView,
});
