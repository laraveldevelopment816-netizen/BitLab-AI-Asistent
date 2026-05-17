// BitLab Hi-Fi Artboards — chat widget + voice modal in multiple states.
// Each artboard renders raw HTML (innerHTML) using design tokens from widget.css.

const I = window.BLIcons;

// ============================================
// HOST PAGE BACKDROP — to show widget in context
// ============================================
function HostBackdrop({ children, dim = false }) {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: dim
          ? 'linear-gradient(180deg, rgba(26,26,46,0.45) 0%, rgba(26,26,46,0.7) 100%), url("https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=1200") center/cover'
          : 'linear-gradient(180deg, #fafbfc 0%, #f1f3f7 100%)',
        position: 'relative',
        overflow: 'hidden',
        fontFamily: 'Inter, sans-serif',
      }}
    >
      {!dim && (
        <>
          <div
            style={{
              padding: '18px 32px',
              background: '#fff',
              borderBottom: '1px solid #ececf0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <img src="bitlab-logo.png" alt="BitLab" style={{ height: 28 }} />
            <div style={{ display: 'flex', gap: 28, fontSize: 13, color: '#565666', fontWeight: 500 }}>
              <span>Početna</span>
              <span>Računari</span>
              <span>Komponente</span>
              <span style={{ color: '#fb6d3b' }}>Akcije</span>
              <span>Kontakt</span>
            </div>
          </div>
          <div
            style={{
              padding: '40px 32px 0',
              maxWidth: 1100,
              margin: '0 auto',
            }}
          >
            <div style={{ fontSize: 13, color: '#8b8b9a', textTransform: 'uppercase', letterSpacing: '0.12em', fontWeight: 600 }}>
              Banja Luka · 5.278 proizvoda
            </div>
            <div style={{ fontSize: 36, fontWeight: 700, color: '#1a1a2e', marginTop: 12, letterSpacing: '-0.02em' }}>
              Tvoj partner za IT opremu.
            </div>
            <div style={{ fontSize: 16, color: '#565666', marginTop: 12, maxWidth: 520, lineHeight: 1.5 }}>
              Računari, komponente i periferija — sa stručnom podrškom i dostavom širom BiH.
            </div>

            {/* Product grid placeholder */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 16,
                marginTop: 32,
              }}
            >
              {[
                ['Crucial', 'SSD BX500 1TB SATA3', '389 KM', '#fed1bb'],
                ['Samsung', 'Monitor 27" IPS 100Hz', '449 KM', '#ffe8db'],
                ['Kingston', 'DDR4 16GB 3200MHz', '89 KM', '#fff5f0'],
              ].map(([brand, name, price, bg], i) => (
                <div
                  key={i}
                  style={{
                    background: '#fff',
                    border: '1px solid #ececf0',
                    borderRadius: 14,
                    overflow: 'hidden',
                  }}
                >
                  <div style={{ height: 110, background: bg }} />
                  <div style={{ padding: 14 }}>
                    <div style={{ fontSize: 11, color: '#8b8b9a', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>{brand}</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a2e', marginTop: 4 }}>{name}</div>
                    <div style={{ fontSize: 16, color: '#fb6d3b', fontWeight: 700, marginTop: 8 }}>{price}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
      {children}
    </div>
  );
}

// ============================================
// CHAT WINDOW — full hi-fi
// ============================================
function ChatWindow({ state = 'welcome' }) {
  // states: 'welcome' (empty), 'conversation', 'typing'
  return (
    <div className="bl-window">
      {/* Header */}
      <div className="bl-header">
        <div className="bl-header__row">
          <div className="bl-header__avatar" dangerouslySetInnerHTML={{ __html: I.bot }} />
          <div className="bl-header__info">
            <div className="bl-header__title">BitLab Asistent</div>
            <div className="bl-header__sub">
              <span className="bl-dot" />
              Online · Odgovara odmah
            </div>
          </div>
          <div className="bl-header__actions">
            <button className="bl-icon-btn" title="Minimize" dangerouslySetInnerHTML={{ __html: I.minus }} />
            <button className="bl-icon-btn" title="Zatvori" dangerouslySetInnerHTML={{ __html: I.close }} />
          </div>
        </div>
        <div className="bl-header__chips">
          <span className="bl-header__chip">
            <span dangerouslySetInnerHTML={{ __html: I.shield }} /> Sigurno
          </span>
          <span className="bl-header__chip">
            <span dangerouslySetInnerHTML={{ __html: I.spark }} /> AI
          </span>
          <span className="bl-header__chip">5.278 proizvoda</span>
        </div>
      </div>

      {/* Body */}
      {state === 'welcome' && (
        <div className="bl-messages" style={{ paddingTop: 8 }}>
          <div className="bl-welcome">
            <div className="bl-welcome__avatar" dangerouslySetInnerHTML={{ __html: I.spark }} />
            <div>
              <div className="bl-welcome__title">
                Pozdrav<span>.</span>
              </div>
              <div className="bl-welcome__sub">
                Pitaj me bilo šta o našim proizvodima, dostavi ili garanciji.
              </div>
            </div>
            <div className="bl-welcome__suggest">
              {[
                [I.laptop, 'Laptopi i računari', 'Pretraga po cijeni i specifikaciji'],
                [I.game, 'Gaming oprema', 'Mišovi, tastature, slušalice'],
                [I.truck, 'Dostava i plaćanje', 'Cijene, rokovi, MKD rate'],
              ].map(([icon, t, d], i) => (
                <button key={i} className="bl-suggest">
                  <div className="bl-suggest__icon" dangerouslySetInnerHTML={{ __html: icon }} />
                  <div className="bl-suggest__body">
                    <div className="bl-suggest__t">{t}</div>
                    <div className="bl-suggest__d">{d}</div>
                  </div>
                  <div className="bl-suggest__arrow" dangerouslySetInnerHTML={{ __html: I.arrow }} />
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {(state === 'conversation' || state === 'typing') && (
        <div className="bl-messages">
          <div className="bl-day-divider">Danas · 14:32</div>

          {/* Bot greeting */}
          <div className="bl-msg-row bl-msg-row--bot">
            <div className="bl-msg bl-msg--bot">
              Pozdrav! Šta tražiš danas?
            </div>
            <div className="bl-msg-row__time">14:32</div>
          </div>

          {/* User msg */}
          <div className="bl-msg-row bl-msg-row--user">
            <div className="bl-msg bl-msg--user">Imate li SSD 1TB do 400 KM?</div>
            <div className="bl-msg-row__time">14:33</div>
          </div>

          {/* Bot with product cards */}
          <div className="bl-msg-row bl-msg-row--bot">
            <div className="bl-msg bl-msg--bot" style={{ maxWidth: '92%' }}>
              Da, imam tri opcije na lageru:
              <a className="bl-prod" href="#">
                <div className="bl-prod__img">💾</div>
                <div className="bl-prod__body">
                  <div className="bl-prod__brand">Crucial</div>
                  <div className="bl-prod__name">SSD BX500 1TB 2.5" SATA3</div>
                  <div className="bl-prod__row">
                    <div className="bl-prod__price">389 KM</div>
                    <div className="bl-prod__avail">
                      <span dangerouslySetInnerHTML={{ __html: I.check }} style={{ width: 11, height: 11, display: 'inline-flex' }} />
                      Na lageru
                    </div>
                  </div>
                </div>
              </a>
              <a className="bl-prod" href="#">
                <div className="bl-prod__img">💾</div>
                <div className="bl-prod__body">
                  <div className="bl-prod__brand">Kingston</div>
                  <div className="bl-prod__name">A400 1TB SATA3</div>
                  <div className="bl-prod__row">
                    <div className="bl-prod__price">369 KM</div>
                    <div className="bl-prod__avail">
                      <span dangerouslySetInnerHTML={{ __html: I.check }} style={{ width: 11, height: 11, display: 'inline-flex' }} />
                      Na lageru
                    </div>
                  </div>
                </div>
              </a>
            </div>
            <div className="bl-msg-row__time">14:33</div>
          </div>

          {state === 'typing' && (
            <div className="bl-msg-row bl-msg-row--bot">
              <div className="bl-msg bl-msg--bot bl-typing">
                <span /><span /><span />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Quick replies (only when not in welcome) */}
      {state !== 'welcome' && (
        <div className="bl-quick">
          <div className="bl-quick__label">Brza pitanja</div>
          <div className="bl-quick__chips">
            <button className="bl-chip">
              <span dangerouslySetInnerHTML={{ __html: I.truck }} /> Dostava
            </button>
            <button className="bl-chip">
              <span dangerouslySetInnerHTML={{ __html: I.shield }} /> Garancija
            </button>
            <button className="bl-chip">B2B / JIB</button>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="bl-input-area">
        <div className="bl-input-wrap">
          <input className="bl-input" placeholder="Postavi pitanje..." defaultValue={state === 'typing' ? 'Imate li u Mostaru?' : ''} />
          <button className="bl-attach" dangerouslySetInnerHTML={{ __html: I.attach }} />
        </div>
        <button className="bl-action-btn bl-action-btn--voice" dangerouslySetInnerHTML={{ __html: I.mic }} />
        <button className="bl-action-btn bl-action-btn--send" dangerouslySetInnerHTML={{ __html: I.send }} />
      </div>

      <div className="bl-footer">
        Pokreće <strong>BitLab AI</strong> · Šifrovano · webshop.bitlab.rs
      </div>
    </div>
  );
}

// ============================================
// VOICE MODAL
// ============================================
function VoiceModal({ state = 'idle' }) {
  // states: 'idle', 'listening', 'speaking'
  const isListening = state === 'listening';
  return (
    <div className="bl-voice">
      <div className="bl-voice__head">
        <div className="bl-voice__head-avatar" dangerouslySetInnerHTML={{ __html: I.mic }} />
        <div style={{ flex: 1 }}>
          <div className="bl-voice__head-title">Voice Asistent</div>
          <div className="bl-voice__head-state">
            <span style={{
              width: 6, height: 6, borderRadius: 99,
              background: isListening ? '#22c55e' : '#fb6d3b',
              boxShadow: `0 0 0 3px ${isListening ? 'rgba(34,197,94,0.25)' : 'rgba(251,109,59,0.25)'}`
            }} />
            {state === 'idle' && 'Spremno · pritisni mikrofon'}
            {state === 'listening' && 'Slušam...'}
            {state === 'speaking' && 'Gabriela govori...'}
          </div>
        </div>
        <button className="bl-icon-btn" dangerouslySetInnerHTML={{ __html: I.close }} />
      </div>

      <div className="bl-voice__stage">
        <div className={`bl-orb ${isListening ? 'bl-orb--listening' : ''}`}>
          <span className="bl-orb__ring" />
          <span className="bl-orb__ring" />
          <span className="bl-orb__ring" />
          <div className="bl-orb__core" dangerouslySetInnerHTML={{ __html: I.mic }} />
        </div>

        {state === 'idle' && (
          <>
            <div className="bl-voice__transcript-line">
              Postavi pitanje glasom.<br />
              <em>Govori bosanski, srpski ili hrvatski.</em>
            </div>
            <div className="bl-voice__hint">
              <span dangerouslySetInnerHTML={{ __html: I.lock }} />
              Mikrofon se aktivira tek na klik
            </div>
          </>
        )}

        {state === 'listening' && (
          <>
            <div className="bl-voice__transcript-line">
              "Tražim laptop do hiljadu petsto maraka, gaming..."
            </div>
            <div className="bl-wave">
              {[10, 22, 30, 16, 28, 18, 24, 12, 20, 32, 14, 26, 18, 22, 10].map((h, i) => (
                <span key={i} style={{ animationDelay: `${i * 0.08}s`, height: h }} />
              ))}
            </div>
          </>
        )}

        {state === 'speaking' && (
          <>
            <div className="bl-voice__transcript-line">
              <em>"Imam tri opcije u tom budžetu..."</em>
            </div>
            <div className="bl-wave">
              {[16, 28, 22, 32, 14, 24, 30, 18, 26].map((h, i) => (
                <span key={i} style={{ animationDelay: `${i * 0.1}s`, height: h, background: '#2563eb' }} />
              ))}
            </div>
          </>
        )}
      </div>

      {state !== 'idle' && (
        <div className="bl-voice__transcript">
          <div className="bl-msg-row bl-msg-row--user">
            <div className="bl-msg bl-msg--user" style={{ fontSize: 13 }}>
              Tražim laptop do 1500 KM, gaming
            </div>
          </div>
          <div className="bl-msg-row bl-msg-row--bot">
            <div className="bl-msg bl-msg--bot" style={{ fontSize: 13 }}>
              Imam tri opcije: <strong>ASUS TUF A15</strong> — 1.449 KM, <strong>Lenovo IdeaPad Gaming 3</strong> — 1.499 KM...
            </div>
          </div>
        </div>
      )}

      <div className="bl-voice__controls">
        <button className="bl-voice__btn">
          <span dangerouslySetInnerHTML={{ __html: I.pause }} /> Pauziraj
        </button>
        <button className="bl-voice__btn bl-voice__btn--danger">
          <span dangerouslySetInnerHTML={{ __html: I.stop }} /> Zaustavi
        </button>
      </div>
    </div>
  );
}

// ============================================
// FLOATING LAUNCHER (closed state on host page)
// ============================================
function FloatingLauncher() {
  return (
    <button className="bl-launcher" aria-label="Otvori chat">
      <span className="bl-launcher__icon" dangerouslySetInnerHTML={{ __html: I.chat }} />
      <span className="bl-launcher__badge">1</span>
    </button>
  );
}

// ============================================
// EXPORT
// ============================================
Object.assign(window, { HostBackdrop, ChatWindow, VoiceModal, FloatingLauncher });
