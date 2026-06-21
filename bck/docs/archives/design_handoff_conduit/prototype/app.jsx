// Conduit — root app
const { useState: useStateApp, useEffect: useEffectApp, useMemo: useMemoApp } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "#7dd3fc",
  "density": "comfortable",
  "showSidebarStats": true
}/*EDITMODE-END*/;

function App() {
  const [tab, setTab] = useStateApp('live');
  const [drawer, setDrawer] = useStateApp(null);
  const [tweaks, setTweak] = window.useTweaks ? window.useTweaks(TWEAK_DEFAULTS) : [TWEAK_DEFAULTS, () => {}];

  const stats = useMemoApp(() => ({
    queue: window.ADAPTERS.reduce((s, a) => s + a.queueDepth, 0),
    rpm: 8,
    spend: window.REQUESTS.reduce((s, r) => s + r.cost, 0),
  }), []);

  useEffectApp(() => {
    document.documentElement.style.setProperty('--cdt-accent', tweaks.accent);
  }, [tweaks.accent]);

  const Views = {
    live:      <LiveView onPick={setDrawer} />,
    history:   <HistoryView onPick={setDrawer} />,
    adapters:  <AdaptersView />,
    compose:   <ComposeView />,
    compare:   <CompareView />,
    templates: <TemplatesView />,
    cost:      <CostView />,
    plan:      <PlanView />,
    settings:  <SettingsView />,
  };

  return (
    <>
      <GlobalStyles />
      <div style={{
        display: 'flex', minHeight: '100vh',
        background: window.C.bg, color: window.C.text,
        fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
      }}>
        <Sidebar tab={tab} setTab={setTab} stats={stats} />
        <main style={{ flex: 1, minWidth: 0, overflow: 'auto', maxHeight: '100vh' }}>
          {Views[tab]}
        </main>
      </div>
      <DetailDrawer req={drawer} onClose={() => setDrawer(null)} />

      {window.TweaksPanel && (
        <window.TweaksPanel title="Tweaks">
          <window.TweakSection title="Visual">
            <window.TweakColor
              label="Accent"
              value={tweaks.accent}
              onChange={v => setTweak('accent', v)}
            />
            <window.TweakRadio
              label="Density"
              value={tweaks.density}
              onChange={v => setTweak('density', v)}
              options={[{ label: 'Compact', value: 'compact' }, { label: 'Comfortable', value: 'comfortable' }]}
            />
            <window.TweakToggle
              label="Show sidebar stats"
              value={tweaks.showSidebarStats}
              onChange={v => setTweak('showSidebarStats', v)}
            />
          </window.TweakSection>
          <window.TweakSection title="Jump to tab">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {['live','history','adapters','compose','compare','templates','cost','plan','settings'].map(t => (
                <button key={t} onClick={() => setTab(t)} style={{
                  padding: '4px 10px', borderRadius: 4,
                  background: tab === t ? '#7dd3fc22' : 'transparent',
                  border: '1px solid ' + (tab === t ? '#7dd3fc80' : '#2a3038'),
                  color: tab === t ? '#7dd3fc' : '#aaa', fontSize: 11, cursor: 'pointer',
                }}>{t}</button>
              ))}
            </div>
          </window.TweakSection>
        </window.TweaksPanel>
      )}
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
