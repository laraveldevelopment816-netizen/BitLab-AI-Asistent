/**
 * BitLab AI Chat Widget v3 — embeddable, hi-fi redesign
 * Integracija: <script src="http://localhost:8000/public/widget.js"></script>
 *
 * Opciono: window.BITLAB_API = 'https://moj-server.ngrok.io' (default: isto origin)
 *
 * Backend (FastAPI /api/chat, /api/stt, /api/tts) NIJE mijenjan u v3 —
 * samo CSS, HTML markup i markdown post-processor za product card-ove.
 */
(function () {
  'use strict';

  const API_BASE = (window.BITLAB_API || '').replace(/\/$/, '') || '';
  const CHAT_URL = API_BASE + '/api/chat';
  const STT_URL  = API_BASE + '/api/stt';
  const TTS_URL  = API_BASE + '/api/tts';

  const QUICK_REPLIES = [
    { label: 'Dostava',   icon: 'truck',  q: 'Kakve su opcije dostave i načini plaćanja?' },
    { label: 'Garancija', icon: 'shield', q: 'Kakva je politika garancije i povraćaja robe?' },
    { label: 'B2B / JIB', icon: '',       q: 'Kako naručujemo kao firma sa JIB-om?' },
  ];

  const SUGGESTIONS = [
    { icon: 'laptop', title: 'Laptopi i računari', desc: 'Pretraga po cijeni i specifikaciji', q: 'Koji laptopi su trenutno na lageru?' },
    { icon: 'game',   title: 'Gaming oprema',      desc: 'Mišovi, tastature, slušalice',       q: 'Šta imate od gaming opreme?' },
    { icon: 'truck',  title: 'Dostava i plaćanje', desc: 'Cijene, rokovi, MKD rate',           q: 'Kakve su opcije dostave i načini plaćanja?' },
  ];

  // ── Voice VAD constants ─────────────────────────────────────────
  // Strategija: kontinuirano snimanje od trenutka otvaranja mikrofona.
  // VAD detektuje samo KRAJ govora (silence) — početak nikad ne propusti.
  const SPEECH_THRESHOLD    = 0.035;  // RMS prag — viši = manje osetljiv na šum
  const SPEECH_ONSET_MS     = 200;    // koliko sustained signal pred markiranje "speech"
                                       // (filtrira pucketanje, kucanje, kratke šumove)
  const SILENCE_MS          = 1500;   // koliko tišine = "korisnik je završio"
                                       // (1.5s daje vremena za "razmišljanje" pauzu
                                       // unutar rečenice prije nego što finaliziramo)
  const MIN_SPEECH_MS       = 500;    // minimalna dužina govora — kraće = drop
  const MAX_RECORDING_MS    = 30000;  // safety cap — auto-finalize posle 30s

  // Interrupt detection (korisnik prekida AI dok govori)
  const INTERRUPT_THRESHOLD = 0.18;   // viši prag — samo jak korisnički glas, ne reverb
  const INTERRUPT_HOLD_MS   = 350;    // mora govoriti 350ms da prekid bude validan
                                       // (filtrira AI glas iz zvučnika koji curi u mic)
  const INTERRUPT_GUARD_MS  = 1000;   // ne dozvoli prekid u prvih 1s TTS-a (settle time)
  const TTS_COOLDOWN_MS     = 750;    // pauza nakon TTS da reverb utihne
  const VS = {
    IDLE:'idle', LISTENING:'listening', RECORDING:'recording',
    PROCESSING:'processing', SPEAKING:'speaking',
  };

  // ── Inline SVG icons ─────────────────────────────────────────────
  const I = {
    chat:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>',
    spark:  '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l1.8 5.4L19 9l-5.2 1.6L12 16l-1.8-5.4L5 9l5.2-1.6z"/><path d="M5 17l.9 2.7L8 20l-2.1.3L5 23l-.9-2.7L2 20l2.1-.3z"/></svg>',
    bot:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="8" width="18" height="12" rx="3"/><path d="M12 2v4M8 14h.01M16 14h.01M9 18h6"/></svg>',
    mic:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v4M8 22h8"/></svg>',
    send:   '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3.4 20.4l17.45-7.48a1 1 0 0 0 0-1.84L3.4 3.6a1 1 0 0 0-1.4.92V9.5L15 12 2 14.5v4.98a1 1 0 0 0 1.4.92z"/></svg>',
    close:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    minus:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M5 12h14"/></svg>',
    attach: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.4 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66L9.41 17.38a2 2 0 0 1-2.83-2.83l8.49-8.49"/></svg>',
    laptop: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="14" rx="2"/><path d="M2 20h20"/></svg>',
    truck:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="6" width="13" height="11" rx="1"/><path d="M14 9h4l3 4v4h-7V9zM6 21a2 2 0 100-4 2 2 0 000 4zM18 21a2 2 0 100-4 2 2 0 000 4z"/></svg>',
    shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l8 4v6c0 5-3.5 9.5-8 10-4.5-.5-8-5-8-10V6z"/></svg>',
    game:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 12h4M8 10v4M15 13h.01M18 11h.01"/><rect x="2" y="6" width="20" height="12" rx="6"/></svg>',
    arrow:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>',
    check:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg>',
    lock:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/></svg>',
    stop:   '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>',
    pause:  '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>',
    play:   '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>',
  };

  // ── CSS ─────────────────────────────────────────────────────────
  const css = `
:root {
  --bl-orange:      #fb6d3b;
  --bl-orange-600:  #ea5c2a;
  --bl-orange-700:  #e0511f;
  --bl-orange-50:   #fff5f0;
  --bl-orange-100:  #ffe8db;
  --bl-orange-200:  #fed1bb;
  --bl-navy:        #1a1a2e;
  --bl-navy-600:    #2a2a3e;
  --bl-bg-soft:     #f7f8fa;
  --bl-bg-softer:   #fafbfc;
  --bl-line:        #ececf0;
  --bl-line-strong: #d9d9e0;
  --bl-text:        #1a1a2e;
  --bl-text-2:      #565666;
  --bl-text-3:      #8b8b9a;
  --bl-success:     #16a34a;
  --bl-success-bg:  #ecfdf3;
  --bl-danger:      #dc2626;
  --bl-danger-bg:   #fef2f2;
  --bl-shadow-1:    0 1px 2px rgba(26,26,46,.04), 0 1px 1px rgba(26,26,46,.03);
  --bl-shadow-2:    0 4px 12px rgba(26,26,46,.06), 0 2px 4px rgba(26,26,46,.04);
  --bl-shadow-3:    0 16px 40px rgba(26,26,46,.12), 0 4px 12px rgba(26,26,46,.06);
  --bl-shadow-orange: 0 8px 24px rgba(251,109,59,.32), 0 2px 6px rgba(251,109,59,.18);
  --bl-font:        "Inter", -apple-system, "Segoe UI", Roboto, sans-serif;
}

/* ───── Launcher ───── */
#bl-launcher {
  position: fixed; bottom: 24px; right: 24px;
  width: 64px; height: 64px; border-radius: 50%;
  border: none; cursor: pointer; z-index: 9999;
  background: linear-gradient(135deg, var(--bl-orange) 0%, var(--bl-orange-600) 100%);
  box-shadow: var(--bl-shadow-orange);
  color: #fff; font-family: var(--bl-font);
  display: flex; align-items: center; justify-content: center;
  transition: transform .2s cubic-bezier(.34,1.56,.64,1), box-shadow .2s;
}
#bl-launcher:hover {
  transform: translateY(-2px) scale(1.04);
  box-shadow: 0 12px 32px rgba(251,109,59,.42), 0 4px 8px rgba(251,109,59,.22);
}
#bl-launcher svg { width: 28px; height: 28px; }
#bl-launcher::before {
  content: ""; position: absolute; inset: -6px;
  border-radius: 50%; border: 2px solid var(--bl-orange);
  opacity: 0; pointer-events: none;
  animation: bl-launcher-ring 2.4s ease-out infinite;
}
@keyframes bl-launcher-ring {
  0%   { transform: scale(.85); opacity: 0; }
  40%  { opacity: .4; }
  100% { transform: scale(1.25); opacity: 0; }
}
#bl-launcher .bl-launcher__badge {
  position: absolute; top: -2px; right: -2px;
  min-width: 20px; height: 20px; padding: 0 6px;
  border-radius: 99px; background: var(--bl-navy);
  color: #fff; font-size: 11px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  border: 2px solid #fff;
}
#bl-launcher.bl-open::before { display: none; }
#bl-launcher.bl-open .bl-launcher__badge { display: none; }

/* ───── Window ───── */
#bl-window {
  position: fixed; bottom: 100px; right: 24px;
  width: 408px; height: 620px; max-height: calc(100vh - 120px);
  background: #fff; border-radius: 24px;
  box-shadow: var(--bl-shadow-3);
  display: none; flex-direction: column; overflow: hidden;
  z-index: 9999; font-family: var(--bl-font);
  color: var(--bl-text); border: 1px solid var(--bl-line);
  overscroll-behavior: contain;
}
#bl-window.open { display: flex; }

/* ───── Header ───── */
#bl-header {
  background: linear-gradient(135deg, var(--bl-navy) 0%, var(--bl-navy-600) 100%);
  color: #fff; padding: 18px 18px 16px;
  position: relative; overflow: hidden; flex-shrink: 0;
}
#bl-header::after {
  content: ""; position: absolute; right: -40px; top: -40px;
  width: 140px; height: 140px;
  background: radial-gradient(circle, rgba(251,109,59,.22) 0%, rgba(251,109,59,0) 70%);
  pointer-events: none;
}
.bl-header__row {
  display: flex; align-items: center; gap: 12px;
  position: relative; z-index: 1;
}
.bl-header__avatar {
  width: 44px; height: 44px; border-radius: 14px;
  background: linear-gradient(135deg, var(--bl-orange) 0%, var(--bl-orange-600) 100%);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(251,109,59,.4), inset 0 1px 0 rgba(255,255,255,.2);
  position: relative; color: #fff;
}
.bl-header__avatar svg { width: 22px; height: 22px; }
.bl-header__avatar::after {
  content: ""; position: absolute; bottom: -2px; right: -2px;
  width: 12px; height: 12px; border-radius: 99px;
  background: var(--bl-success); border: 2px solid var(--bl-navy);
}
.bl-header__info { flex: 1; min-width: 0; }
.bl-header__title {
  font-size: 15px; font-weight: 700; letter-spacing: -.01em; line-height: 1.2;
}
.bl-header__sub {
  margin-top: 2px; font-size: 12px; opacity: .7;
  display: flex; align-items: center; gap: 8px;
}
.bl-dot {
  width: 6px; height: 6px; border-radius: 99px;
  background: var(--bl-success);
  box-shadow: 0 0 0 3px rgba(22,163,74,.18);
  animation: bl-pulse 2.4s ease-in-out infinite;
  display: inline-block;
}
@keyframes bl-pulse {
  0%,100% { opacity: 1; transform: scale(1); }
  50%     { opacity: .6; transform: scale(.85); }
}
.bl-header__actions { display: flex; gap: 6px; }
.bl-icon-btn {
  width: 32px; height: 32px; border-radius: 10px;
  background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.06);
  color: rgba(255,255,255,.85);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background .15s;
  padding: 0;
}
.bl-icon-btn:hover { background: rgba(255,255,255,.18); }
.bl-icon-btn svg { width: 14px; height: 14px; }
.bl-header__chips {
  display: flex; gap: 6px; margin-top: 12px;
  position: relative; z-index: 1;
}
.bl-header__chip {
  font-size: 11px; padding: 5px 10px; border-radius: 99px;
  background: rgba(255,255,255,.08);
  color: rgba(255,255,255,.85);
  border: 1px solid rgba(255,255,255,.08);
  display: flex; align-items: center; gap: 5px;
  font-weight: 500;
}
.bl-header__chip svg { width: 11px; height: 11px; }

/* ───── Messages ───── */
#bl-messages {
  flex: 1; overflow-y: auto; padding: 18px 16px 8px;
  background: var(--bl-bg-softer);
  display: flex; flex-direction: column; gap: 10px;
  font-size: 14px;
  overscroll-behavior: contain;  /* scroll ostaje u widget-u, ne propušta na pozadinsku stranicu */
}
#bl-messages::-webkit-scrollbar { width: 6px; }
#bl-messages::-webkit-scrollbar-thumb {
  background: var(--bl-line-strong); border-radius: 99px;
}
.bl-msg {
  max-width: 86%; padding: 10px 14px; border-radius: 16px;
  font-size: 14px; line-height: 1.5; word-break: break-word;
}
.bl-msg.bot {
  background: #fff; border: 1px solid var(--bl-line);
  color: var(--bl-text); box-shadow: var(--bl-shadow-1);
  border-bottom-left-radius: 6px; align-self: flex-start;
}
.bl-msg.user {
  background: linear-gradient(135deg, var(--bl-orange) 0%, var(--bl-orange-600) 100%);
  color: #fff; align-self: flex-end;
  border-bottom-right-radius: 6px;
  box-shadow: 0 2px 6px rgba(251,109,59,.25);
}
.bl-msg.bot a { color: var(--bl-orange-700); font-weight: 600; }
.bl-msg.bot strong { font-weight: 700; }
.bl-msg.bot img:not(.bl-prod__img-real) {
  width: 64px; height: 64px; object-fit: contain;
  border-radius: 6px; border: 1px solid var(--bl-line);
  background: var(--bl-bg-soft); vertical-align: middle; margin-right: 8px;
}

/* Product card (rendered from markdown) */
.bl-prod {
  display: flex; gap: 12px; padding: 10px;
  background: var(--bl-bg-soft);
  border: 1px solid var(--bl-line);
  border-radius: 12px; margin-top: 8px;
  text-decoration: none; color: inherit;
  transition: border-color .15s, transform .15s;
}
.bl-prod:hover { border-color: var(--bl-orange-200); transform: translateY(-1px); }
.bl-prod__img {
  width: 56px; height: 56px; flex-shrink: 0;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--bl-orange-100), var(--bl-orange-50));
  display: flex; align-items: center; justify-content: center;
  border: 1px solid #fff; overflow: hidden;
  position: relative;
}
.bl-prod__img-real {
  width: 100%; height: 100%; object-fit: contain;
  background: #fff;
}
.bl-prod__body { flex: 1; min-width: 0; }
.bl-prod__name {
  font-size: 13px; font-weight: 600; color: var(--bl-text);
  line-height: 1.3;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}
.bl-prod__row {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 6px; gap: 8px;
}
.bl-prod__price {
  font-size: 14px; font-weight: 700; color: var(--bl-orange);
  font-variant-numeric: tabular-nums;
}
.bl-prod__avail {
  font-size: 10px; color: var(--bl-success);
  display: flex; align-items: center; gap: 3px; font-weight: 600;
}
.bl-prod__avail svg { width: 11px; height: 11px; }
.bl-prod__avail--order {
  color: var(--bl-text-3);
}

/* Typing indicator */
.bl-msg.bot.bl-typing {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 12px 14px;
}
.bl-typing span {
  width: 7px; height: 7px; border-radius: 99px;
  background: var(--bl-orange);
  animation: bl-typing 1.2s infinite ease-in-out;
  opacity: .4;
}
.bl-typing span:nth-child(2) { animation-delay: .15s; }
.bl-typing span:nth-child(3) { animation-delay: .3s; }
@keyframes bl-typing {
  0%,80%,100% { transform: translateY(0); opacity: .4; }
  40%         { transform: translateY(-4px); opacity: 1; }
}

/* ───── Welcome screen ───── */
.bl-welcome {
  padding: 28px 20px 12px;
  display: flex; flex-direction: column; align-items: center; gap: 12px;
  text-align: center;
}
.bl-welcome__avatar {
  width: 64px; height: 64px; border-radius: 18px;
  background: linear-gradient(135deg, var(--bl-orange), var(--bl-orange-600));
  display: flex; align-items: center; justify-content: center;
  box-shadow: var(--bl-shadow-orange); color: #fff;
}
.bl-welcome__avatar svg { width: 30px; height: 30px; }
.bl-welcome__title {
  font-size: 18px; font-weight: 700; color: var(--bl-text);
  letter-spacing: -.015em;
}
.bl-welcome__title span { color: var(--bl-orange); }
.bl-welcome__sub {
  font-size: 13px; color: var(--bl-text-2);
  line-height: 1.45; max-width: 300px;
}
.bl-welcome__suggest {
  width: 100%; display: flex; flex-direction: column;
  gap: 8px; margin-top: 8px;
}
.bl-suggest {
  width: 100%; display: flex; align-items: center; gap: 12px;
  padding: 12px 14px; background: #fff;
  border: 1px solid var(--bl-line); border-radius: 12px;
  cursor: pointer; text-align: left;
  font-family: inherit; transition: all .15s;
}
.bl-suggest:hover {
  border-color: var(--bl-orange-200);
  background: var(--bl-orange-50);
  transform: translateY(-1px);
}
.bl-suggest__icon {
  width: 36px; height: 36px; border-radius: 10px;
  background: var(--bl-orange-50); color: var(--bl-orange);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.bl-suggest__icon svg { width: 18px; height: 18px; }
.bl-suggest__body { flex: 1; min-width: 0; }
.bl-suggest__t { font-size: 13px; font-weight: 600; color: var(--bl-text); line-height: 1.2; }
.bl-suggest__d { font-size: 11px; color: var(--bl-text-3); margin-top: 2px; }
.bl-suggest__arrow { color: var(--bl-text-3); flex-shrink: 0; }
.bl-suggest__arrow svg { width: 14px; height: 14px; }

/* ───── Quick replies ───── */
#bl-quick-wrap {
  padding: 10px 14px 12px; background: var(--bl-bg-softer);
  border-top: 1px solid var(--bl-line); flex-shrink: 0;
}
#bl-quick-wrap.hidden { display: none; }
.bl-qr-label {
  font-size: 10px; text-transform: uppercase; letter-spacing: .1em;
  color: var(--bl-text-3); font-weight: 600; margin-bottom: 8px;
}
.bl-quick-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.bl-chip {
  padding: 7px 12px; border-radius: 99px;
  background: #fff; border: 1px solid var(--bl-line);
  color: var(--bl-text); font-size: 12px; font-weight: 500;
  cursor: pointer; font-family: inherit;
  display: inline-flex; align-items: center; gap: 5px;
  transition: all .15s; line-height: 1.3;
}
.bl-chip:hover {
  border-color: var(--bl-orange);
  color: var(--bl-orange-700);
  background: var(--bl-orange-50);
}
.bl-chip svg { width: 12px; height: 12px; opacity: .7; }

/* ───── Input ───── */
#bl-input-area {
  padding: 12px 14px; background: #fff;
  border-top: 1px solid var(--bl-line);
  display: flex; align-items: center; gap: 8px; flex-shrink: 0;
}
.bl-input-wrap {
  flex: 1; display: flex; align-items: center;
  background: var(--bl-bg-soft);
  border: 1px solid var(--bl-line);
  border-radius: 99px;
  padding: 0 4px 0 14px; height: 42px;
  transition: border-color .15s, background .15s, box-shadow .15s;
}
.bl-input-wrap:focus-within {
  border-color: var(--bl-orange);
  background: #fff;
  box-shadow: 0 0 0 3px var(--bl-orange-50);
}
#bl-input {
  flex: 1; border: none; background: transparent;
  outline: none; font-family: inherit;
  font-size: 14px; color: var(--bl-text);
  height: 100%; min-width: 0;
}
#bl-input::placeholder { color: var(--bl-text-3); }
.bl-attach {
  width: 32px; height: 32px; background: transparent;
  border: none; border-radius: 99px;
  color: var(--bl-text-3); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; padding: 0;
}
.bl-attach:hover { color: var(--bl-text); background: var(--bl-line); }
.bl-attach svg { width: 18px; height: 18px; }
#bl-voice-btn {
  width: 42px; height: 42px; border-radius: 99px;
  background: var(--bl-bg-soft);
  border: 1px solid var(--bl-line);
  color: var(--bl-navy); cursor: pointer;
  flex-shrink: 0; padding: 0;
  display: flex; align-items: center; justify-content: center;
  transition: all .15s; font-family: inherit;
}
#bl-voice-btn:hover {
  background: var(--bl-orange-50);
  border-color: var(--bl-orange-200);
  color: var(--bl-orange-700);
}
#bl-voice-btn svg { width: 18px; height: 18px; }
#bl-send {
  width: 42px; height: 42px; border-radius: 99px;
  border: none; cursor: pointer; flex-shrink: 0; padding: 0;
  background: linear-gradient(135deg, var(--bl-orange), var(--bl-orange-600));
  color: #fff;
  box-shadow: 0 2px 8px rgba(251,109,59,.32);
  display: flex; align-items: center; justify-content: center;
  transition: all .15s; font-family: inherit;
}
#bl-send:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(251,109,59,.44);
}
#bl-send:disabled { opacity: .5; cursor: default; transform: none; }
#bl-send svg { width: 18px; height: 18px; }

/* ───── Footer ───── */
.bl-footer {
  padding: 8px 14px 10px; background: #fff;
  border-top: 1px solid var(--bl-line);
  font-size: 10px; color: var(--bl-text-3);
  text-align: center; font-weight: 500;
  letter-spacing: .04em; flex-shrink: 0;
}
.bl-footer strong { color: var(--bl-orange); font-weight: 700; }

/* ───── Mobile ───── */
@media (max-width: 440px) {
  #bl-window {
    right: 8px; left: 8px; bottom: 88px;
    width: auto; height: auto; max-height: calc(100vh - 100px);
  }
  #bl-launcher { right: 16px; bottom: 16px; }
}

/* ───── Voice modal ───── */
#bl-voice-overlay {
  position: fixed; inset: 0;
  background: rgba(26,26,46,.55);
  backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
  display: none; align-items: center; justify-content: center;
  z-index: 10001; padding: 16px;
}
#bl-voice-overlay.open { display: flex; }
/* Zaključaj scroll pozadinske stranice dok je modal otvoren */
html.bl-scroll-lock,
html.bl-scroll-lock body {
  overflow: hidden !important;
  overscroll-behavior: contain;
}
#bl-voice-panel {
  width: 460px; max-width: 100%;
  height: 80vh; max-height: 720px; min-height: 520px;
  background: #fff; border-radius: 24px;
  box-shadow: var(--bl-shadow-3);
  display: flex; flex-direction: column; overflow: hidden;
  font-family: var(--bl-font); color: var(--bl-text);
  border: 1px solid var(--bl-line);
  overscroll-behavior: contain;
}

#bl-vheader {
  background: linear-gradient(135deg, var(--bl-navy) 0%, var(--bl-navy-600) 100%);
  color: #fff; padding: 16px 18px;
  display: flex; align-items: center; gap: 12px; flex-shrink: 0;
}
#bl-vheader-avatar {
  width: 36px; height: 36px; border-radius: 12px;
  background: rgba(251,109,59,.18);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; color: var(--bl-orange);
}
#bl-vheader-avatar svg { width: 18px; height: 18px; }
#bl-vheader-info { flex: 1; min-width: 0; }
.bl-vtitle { font-size: 14px; font-weight: 700; }
#bl-vstate {
  font-size: 11px; opacity: .75; margin-top: 2px;
  display: flex; align-items: center; gap: 6px; min-height: 14px;
}
#bl-vstate-dot {
  width: 6px; height: 6px; border-radius: 99px;
  background: var(--bl-orange);
  box-shadow: 0 0 0 3px rgba(251,109,59,.25);
}
#bl-voice-panel.vp-listening #bl-vstate-dot,
#bl-voice-panel.vp-recording #bl-vstate-dot {
  background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34,197,94,.25);
}

/* Compact stage with orb — header section ~25% panela */
#bl-vstage {
  padding: 14px 18px 14px;
  display: flex; flex-direction: row; align-items: center; gap: 14px;
  background: linear-gradient(180deg, #fff 0%, var(--bl-bg-softer) 100%);
  border-bottom: 1px solid var(--bl-line);
  flex-shrink: 0;
}
.bl-orb {
  position: relative; width: 64px; height: 64px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.bl-orb__ring {
  position: absolute; inset: 0; border-radius: 50%;
  border: 1.5px solid var(--bl-orange-200);
  opacity: 0;
}
.bl-orb__ring:nth-child(1) { animation: bl-orb-ring 3s ease-out infinite; }
.bl-orb__ring:nth-child(2) { animation: bl-orb-ring 3s ease-out infinite 1s; }
.bl-orb__ring:nth-child(3) { animation: bl-orb-ring 3s ease-out infinite 2s; }
@keyframes bl-orb-ring {
  0%   { transform: scale(.7); opacity: 0; }
  20%  { opacity: .55; }
  100% { transform: scale(1.3); opacity: 0; }
}
.bl-orb__core {
  width: 48px; height: 48px; border-radius: 50%;
  background: linear-gradient(135deg, var(--bl-orange) 0%, var(--bl-orange-600) 100%);
  box-shadow:
    0 6px 16px rgba(251,109,59,.4),
    inset 0 2px 4px rgba(255,255,255,.3),
    inset 0 -3px 8px rgba(224,81,31,.4);
  display: flex; align-items: center; justify-content: center;
  color: #fff; position: relative; z-index: 1;
  cursor: pointer;
  transition: background .3s, box-shadow .3s;
}
.bl-orb__core svg { width: 22px; height: 22px; }
.bl-orb--listening .bl-orb__core,
.bl-orb--recording .bl-orb__core {
  background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
  box-shadow: 0 12px 32px rgba(22,163,74,.42), inset 0 2px 4px rgba(255,255,255,.3);
}
.bl-orb--listening .bl-orb__ring,
.bl-orb--recording .bl-orb__ring { border-color: rgba(22,163,74,.4); }
.bl-orb--processing .bl-orb__core {
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  box-shadow: 0 12px 32px rgba(37,99,235,.5), inset 0 2px 4px rgba(255,255,255,.3);
  animation: bl-orb-throb 1.6s ease-in-out infinite;
}
.bl-orb--processing .bl-orb__ring { border-color: rgba(37,99,235,.45); }
@keyframes bl-orb-throb {
  0%, 100% { transform: scale(1); }
  50%      { transform: scale(1.05); }
}
/* 3-dot loader inside orb during PROCESSING (zamjenjuje mic ikonu) */
.bl-orb__loader {
  display: flex; gap: 4px; align-items: center; justify-content: center;
}
.bl-orb__loader span {
  width: 6px; height: 6px; border-radius: 50%;
  background: #fff;
  animation: bl-orb-loader-dot 1.3s infinite ease-in-out;
}
.bl-orb__loader span:nth-child(2) { animation-delay: 0.2s; }
.bl-orb__loader span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bl-orb-loader-dot {
  0%, 80%, 100% { opacity: 0.35; transform: scale(0.65); }
  40%           { opacity: 1; transform: scale(1); }
}
.bl-orb--paused .bl-orb__core {
  background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
  box-shadow: 0 8px 20px rgba(100,116,139,.3);
}
.bl-orb--paused .bl-orb__ring { animation: none; opacity: 0; }

/* Stage tekst — kompaktan, lijevo poravnat (orb je lijevo) */
#bl-vstage-info {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 6px;
}
#bl-vtline {
  font-size: 13px; font-weight: 600;
  color: var(--bl-text); line-height: 1.35;
  letter-spacing: -.01em;
}
#bl-vtline em { color: var(--bl-text-3); font-style: normal; font-weight: 400; }

.bl-wave {
  display: flex; align-items: center; gap: 2px;
  height: 18px; min-height: 18px;
}
.bl-wave span {
  width: 2px; border-radius: 2px;
  background: var(--bl-orange); opacity: .85;
  animation: bl-wave 1.2s ease-in-out infinite;
}
#bl-voice-panel.vp-speaking .bl-wave span { background: #2563eb; }
@keyframes bl-wave {
  0%,100% { height: 4px; }
  50%     { height: 16px; }
}
#bl-vwave.bl-hidden, #bl-vhint.bl-hidden, #bl-vtranscript.bl-hidden,
.bl-orb__ring.bl-hidden { display: none !important; }

#bl-vhint {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 11px; color: var(--bl-text-3);
  padding: 0;
}
#bl-vhint svg { width: 11px; height: 11px; flex-shrink: 0; }

/* Transcript / rezultati — glavna body sekcija (~75% panela) */
#bl-vtranscript {
  padding: 14px 18px 14px;
  display: flex; flex-direction: column; gap: 10px;
  flex: 1; min-height: 0; overflow-y: auto;
  background: var(--bl-bg-softer);
}
#bl-vtranscript.bl-hidden {
  /* Kad je prazan u idle stanju: zauzima isti prostor, ali bez sadržaja */
  display: flex !important;
  align-items: center; justify-content: center;
}
#bl-vtranscript.bl-hidden::before {
  content: 'Pričaj sa asistentom — rezultati će se prikazati ovdje';
  color: var(--bl-text-3); font-size: 12px; text-align: center;
  padding: 0 24px;
}
#bl-vtranscript::-webkit-scrollbar { width: 5px; }
#bl-vtranscript::-webkit-scrollbar-thumb {
  background: var(--bl-line-strong); border-radius: 99px;
}
#bl-vtranscript .bl-msg { font-size: 13px; }

#bl-vcontrols {
  padding: 14px 18px; background: #fff;
  border-top: 1px solid var(--bl-line);
  display: flex; gap: 8px; flex-shrink: 0;
}
.bl-vbtn {
  flex: 1; height: 44px; border-radius: 12px;
  border: 1px solid var(--bl-line);
  background: #fff; color: var(--bl-text);
  font-family: inherit; font-size: 13px; font-weight: 600;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: all .15s; padding: 0 16px;
}
.bl-vbtn:hover { background: var(--bl-bg-soft); }
.bl-vbtn--danger {
  background: var(--bl-danger-bg);
  color: var(--bl-danger);
  border-color: #fecaca;
}
.bl-vbtn--danger:hover { background: #fee2e2; }
.bl-vbtn svg { width: 14px; height: 14px; }

@media (max-width: 480px) {
  #bl-voice-overlay { padding: 0; align-items: stretch; }
  #bl-voice-panel {
    width: 100%; max-height: 100vh; height: 100vh;
    border-radius: 0;
  }
  /* Mobilno: header nešto kompaktniji da ostane ~20% */
  #bl-vstage { padding: 10px 14px; gap: 12px; }
  .bl-orb { width: 56px; height: 56px; }
  .bl-orb__core { width: 44px; height: 44px; }
  .bl-orb__core svg { width: 20px; height: 20px; }
  #bl-vtline { font-size: 12.5px; }
}
`;

  // ── Inject CSS & HTML ────────────────────────────────────────────
  const styleEl = document.createElement('style');
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  document.body.insertAdjacentHTML('beforeend', `
<button id="bl-launcher" aria-label="Otvori chat">
  ${I.chat}
  <span class="bl-launcher__badge">1</span>
</button>

<div id="bl-window" role="dialog" aria-label="BitLab AI Chat">
  <div id="bl-header">
    <div class="bl-header__row">
      <div class="bl-header__avatar">${I.bot}</div>
      <div class="bl-header__info">
        <div class="bl-header__title">BitLab Asistent</div>
        <div class="bl-header__sub">
          <span class="bl-dot"></span>Online · Odgovara odmah
        </div>
      </div>
      <div class="bl-header__actions">
        <button class="bl-icon-btn" id="bl-min" title="Minimize" aria-label="Minimize">${I.minus}</button>
        <button class="bl-icon-btn" id="bl-close" title="Zatvori" aria-label="Zatvori">${I.close}</button>
      </div>
    </div>
    <div class="bl-header__chips">
      <span class="bl-header__chip">${I.shield} Sigurno</span>
      <span class="bl-header__chip">${I.spark} AI</span>
      <span class="bl-header__chip">5.278 proizvoda</span>
    </div>
  </div>

  <div id="bl-messages"></div>

  <div id="bl-quick-wrap" class="hidden">
    <div class="bl-qr-label">Brza pitanja</div>
    <div class="bl-quick-chips" id="bl-chips"></div>
  </div>

  <div id="bl-input-area">
    <div class="bl-input-wrap">
      <input id="bl-input" type="text" placeholder="Postavi pitanje..." autocomplete="off">
      <button class="bl-attach" title="Priloži" aria-label="Priloži">${I.attach}</button>
    </div>
    <button id="bl-voice-btn" title="Voice mode" aria-label="Voice mode">${I.mic}</button>
    <button id="bl-send" aria-label="Pošalji">${I.send}</button>
  </div>

  <div class="bl-footer">
    Pokreće <strong>BitLab AI</strong> · Šifrovano · webshop.bitlab.rs
  </div>
</div>

<div id="bl-voice-overlay" role="dialog" aria-label="Voice Mode">
  <div id="bl-voice-panel" class="vp-idle">
    <div id="bl-vheader">
      <div id="bl-vheader-avatar">${I.mic}</div>
      <div id="bl-vheader-info">
        <div class="bl-vtitle">Voice Asistent</div>
        <div id="bl-vstate"><span id="bl-vstate-dot"></span><span id="bl-vstate-text">Inicijalizacija...</span></div>
      </div>
      <button id="bl-voice-close-btn" class="bl-icon-btn" aria-label="Zatvori">${I.close}</button>
    </div>

    <div id="bl-vstage">
      <div id="bl-voice-orb" class="bl-orb">
        <span class="bl-orb__ring"></span>
        <span class="bl-orb__ring"></span>
        <span class="bl-orb__ring"></span>
        <div id="bl-vorb-large" class="bl-orb__core">${I.mic}</div>
      </div>
      <div id="bl-vstage-info">
        <div id="bl-vtline"><em>Spremno za razgovor...</em></div>
        <div id="bl-vwave" class="bl-wave bl-hidden">
          ${Array.from({ length: 12 }, (_, i) =>
            `<span style="animation-delay:${(i * 0.08).toFixed(2)}s"></span>`
          ).join('')}
        </div>
        <div id="bl-vhint">${I.lock} Mikrofon se aktivira tek na klik</div>
      </div>
    </div>

    <div id="bl-vtranscript" class="bl-hidden"></div>

    <div id="bl-vcontrols">
      <button class="bl-vbtn" id="bl-vpause">${I.pause}<span id="bl-vpause-label">Pauziraj</span></button>
      <button class="bl-vbtn bl-vbtn--danger" id="bl-vstop">${I.stop} Zaustavi</button>
    </div>

    <!-- Hidden legacy element for VAD level (kept to avoid null refs) -->
    <div id="bl-vlevel-bar" style="display:none"></div>
  </div>
</div>
`);

  // ── Element refs ─────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);
  const messagesEl = $('bl-messages');
  const chipsEl    = $('bl-chips');
  const quickWrap  = $('bl-quick-wrap');

  // ── Quick reply chips ────────────────────────────────────────────
  QUICK_REPLIES.forEach(({ label, icon, q }) => {
    const btn = document.createElement('button');
    btn.className = 'bl-chip';
    btn.innerHTML = (icon ? I[icon] + ' ' : '') + label;
    btn.onclick = () => {
      addMsg(label, 'user');
      sendMessage(q);
    };
    chipsEl.appendChild(btn);
  });

  // ── Welcome screen ───────────────────────────────────────────────
  function renderWelcome() {
    const wrap = document.createElement('div');
    wrap.className = 'bl-welcome';
    wrap.id = 'bl-welcome';
    wrap.innerHTML = `
      <div class="bl-welcome__avatar">${I.spark}</div>
      <div>
        <div class="bl-welcome__title">Pozdrav<span>.</span></div>
        <div class="bl-welcome__sub">Pitaj me bilo šta o našim proizvodima, dostavi ili garanciji.</div>
      </div>
      <div class="bl-welcome__suggest"></div>
    `;
    const suggestWrap = wrap.querySelector('.bl-welcome__suggest');
    SUGGESTIONS.forEach(({ icon, title, desc, q }) => {
      const btn = document.createElement('button');
      btn.className = 'bl-suggest';
      btn.innerHTML = `
        <div class="bl-suggest__icon">${I[icon]}</div>
        <div class="bl-suggest__body">
          <div class="bl-suggest__t">${title}</div>
          <div class="bl-suggest__d">${desc}</div>
        </div>
        <div class="bl-suggest__arrow">${I.arrow}</div>
      `;
      btn.onclick = () => {
        addMsg(title, 'user');
        sendMessage(q);
      };
      suggestWrap.appendChild(btn);
    });
    messagesEl.appendChild(wrap);
  }

  function clearWelcome() {
    const w = $('bl-welcome');
    if (w) w.remove();
  }

  function showQuickReplies() {
    quickWrap.classList.remove('hidden');
  }

  // ── Shared history (chat + voice) ────────────────────────────────
  const history = [];
  let chatOpened = false;

  // ── Markdown + product card post-processor ───────────────────────
  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // Strip "X kom" / "X komada" / "(X kom.)" — defensive
  function stripQty(s) {
    return String(s)
      .replace(/\s*\(\s*\d+\s*kom(?:ada)?\.?\s*\)/gi, '')
      .replace(/\s*[—–-]\s*\d+\s*kom(?:ada)?\.?(?=\s|$)/gi, '')
      .replace(/\s*\b\d+\s*kom(?:ada)?\.?(?=\s|$)/gi, '')
      .trim();
  }

  // Sklopi multi-line product card u single-line. Defensive parser jer
  // Claude (Sonnet 4.6) povremeno razbije format propisan promptom.
  // Pattern koji tražimo (sa praznim redovima ili bez):
  //   ![](image_url)        ← optional
  //   **Name**
  //   929 KM                ← cijena bilo gdje, "X[.,]Y KM"
  //   Na lageru / Dobavljivo ← optional
  //   [Pogledaj](url)        ← optional
  function collapseMultiLineProducts(src) {
    const lines = src.split('\n');
    const out = [];
    let i = 0;
    const RE_IMG  = /^\s*!\[[^\]]*\]\((https?:\/\/[^)]+)\)\s*$/;
    const RE_BOLD = /^\s*\*\*([^*]+?)\*\*\s*$/;
    const RE_PRICE = /^\s*([0-9][\d.,]*)\s*KM\s*$/i;
    const RE_AVAIL = /^\s*(na\s+lager[a-z]*|dobavljiv[a-z]*|na\s+stanju|po\s+narud(?:ž|z)bi)\s*$/i;
    const RE_LINK  = /^\s*\[([^\]]+)\]\((https?:\/\/[^)]+)\)\s*$/;

    while (i < lines.length) {
      // Skip leading blanks before potential block
      let j = i;
      while (j < lines.length && lines[j].trim() === '') j++;

      // Try parse block starting at j
      let img = null, name = null, price = null, avail = null, href = null;
      let k = j;
      const skipBlanks = () => { while (k < lines.length && lines[k].trim() === '') k++; };

      // Optional image line
      const mImg = k < lines.length && lines[k].match(RE_IMG);
      if (mImg) { img = mImg[1]; k++; skipBlanks(); }

      // Required: bold name
      const mBold = k < lines.length && lines[k].match(RE_BOLD);
      if (!mBold) { out.push(lines[i]); i++; continue; }
      name = mBold[1]; k++; skipBlanks();

      // Required: price
      const mPrice = k < lines.length && lines[k].match(RE_PRICE);
      if (!mPrice) { out.push(lines[i]); i++; continue; }
      price = mPrice[1]; k++; skipBlanks();

      // Optional: availability
      const mAvail = k < lines.length && lines[k].match(RE_AVAIL);
      if (mAvail) { avail = mAvail[1]; k++; skipBlanks(); }

      // Optional: link
      const mLink = k < lines.length && lines[k].match(RE_LINK);
      if (mLink) { href = { label: mLink[1], url: mLink[2] }; k++; }

      // Sklopi single-line ekvivalent koji PROD_RE hvata
      let line = '';
      if (img) line += `![](${img}) `;
      line += `**${name}** — ${price} KM`;
      if (avail) line += ` — ${avail}`;
      if (href) line += ` — [${href.label}](${href.url})`;
      // Push leading blanks i sklopljenu liniju
      for (let b = i; b < j; b++) out.push(lines[b]);
      out.push(line);
      i = k;
    }
    return out.join('\n');
  }

  // Match a product line in markdown:
  //   - ![](image_url) **Name** — 389 KM — Na lageru — [Pogledaj](url)
  //   1. ![](image_url) **Name** — 389 KM — Na lageru — [Pogledaj](url)
  // Leading bullet ("- ", "* ", or "1. "), image, availability, link → svi optional.
  const PROD_RE = new RegExp(
    '^\\s*(?:[-*]\\s+|\\d+\\.\\s+)?' +                        // optional list bullet (- * 1.)
    '(?:!\\[[^\\]]*\\]\\((https?:\\/\\/[^)]+)\\)\\s+)?' +     // 1: image url (optional)
    '\\*\\*([^*]+?)\\*\\*' +                                  // 2: name
    '\\s*[—–-]\\s*' +
    '([0-9][\\d.,]*)\\s*KM' +                                 // 3: price
    '(?:\\s*[—–-]\\s*([^\\n[]+?))?' +                         // 4: availability (optional, greedy)
    '(?:\\s*[—–-]\\s*\\[([^\\]]+)\\]\\((https?:\\/\\/[^)]+)\\))?' + // 5,6: link
    '\\s*$',
    'i'
  );

  function renderProductCard({ img, name, price, avail, href }) {
    const isAvail = /lager|stanj|dostup/i.test(avail || '');
    const availClass = isAvail ? 'bl-prod__avail' : 'bl-prod__avail bl-prod__avail--order';
    const availIcon  = isAvail ? I.check : '';
    const availText  = stripQty(avail || (isAvail ? 'Na lageru' : ''));
    const tag        = href ? 'a' : 'div';
    const hrefAttr   = href ? ` href="${escHtml(href)}" target="_blank" rel="noopener"` : '';
    const imgInner   = img
      ? `<img class="bl-prod__img-real" src="${escHtml(img)}" alt="" loading="lazy" onerror="this.remove()">`
      : I.laptop;
    return (
      `<${tag} class="bl-prod"${hrefAttr}>` +
        `<div class="bl-prod__img">${imgInner}</div>` +
        `<div class="bl-prod__body">` +
          `<div class="bl-prod__name">${escHtml(name.trim())}</div>` +
          `<div class="bl-prod__row">` +
            `<div class="bl-prod__price">${escHtml(price)} KM</div>` +
            (availText ? `<div class="${availClass}">${availIcon}${escHtml(availText)}</div>` : '') +
          `</div>` +
        `</div>` +
      `</${tag}>`
    );
  }

  function renderMarkdown(text) {
    text = String(text);

    // 0a) DEFENSIVE: ukloni curajuće XML tagove iz voice channel-a
    // (<voice>, <text>) koji su dizajnirani za TTS ekstrakciju u
    // backend-u, ali ako parser pukne ne smiju doći u UI. Sesija 8 bug:
    // Claude pošalje samo <voice> blok bez <text>, parser fallback-uje
    // na cijeli text uključujući raw tagove. Belt-and-suspenders fix.
    // Ako postoji <voice>...</voice>, ukloni cijeli blok (sadržaj
    // ide u TTS, ne u UI). Ako postoji samo <text>...</text>, izvuci
    // sadržaj.
    const textMatch = text.match(/<text>([\s\S]*?)<\/text>/i);
    if (textMatch) {
      text = textMatch[1];
    } else {
      text = text.replace(/<voice>[\s\S]*?<\/voice>/gi, '');
    }
    // Ostaci nepar tagova (otvoreni bez zatvorenog ili obrnuto)
    text = text.replace(/<\/?(?:voice|text)>/gi, '').trim();

    // 0b) Globally strip "(N kom)" / "(N komada)" anywhere — defensive
    text = text.replace(/\s*\(\s*\d+\s*kom(?:ada)?\.?\s*\)/gi, '');

    // 0c) DEFENSIVE: Sonnet ponekad razbije product card u 4-5 odvojenih
    // redova umjesto jednog (image, **name**, price KM, "Na lageru",
    // [Pogledaj](url)). Sklopimo te blokove u single-line ekvivalent
    // koji PROD_RE hvata. Ovo je hotfix za production demo bug
    // (Sesija 8) gdje su slike izlazile iznad imena, layout razbijen.
    text = collapseMultiLineProducts(text);

    // 1) Extract product card lines first → placeholder tokens
    const cards = [];
    const TOKEN = (i) => `BLPRODCARD-${i}-BLEND`;
    const lines = text.split('\n');
    const processed = lines.map((line) => {
      const m = line.match(PROD_RE);
      if (m) {
        cards.push({ img: m[1], name: m[2], price: m[3], avail: m[4], href: m[6] });
        return TOKEN(cards.length - 1);
      }
      return line;
    });
    let html = processed.join('\n');

    // 2) Standard markdown
    html = html
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/!\[([^\]]*)\]\((https?:\/\/[^)]+)\)/g,
        '<img src="$2" alt="$1" loading="lazy" onerror="this.style.display=\'none\'">')
      .replace(/\[([^\]]+)\]\(((?:https?|mailto):[^)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/\n/g, '<br>');

    // 3) Restore cards (HTML-encoded tokens preserved through escaping)
    html = html.replace(/BLPRODCARD-(\d+)-BLEND/g, (_, i) => renderProductCard(cards[+i]));
    return html;
  }

  function addMsg(text, role) {
    clearWelcome();
    showQuickReplies();
    const div = document.createElement('div');
    div.className = 'bl-msg ' + role;
    div.innerHTML = role === 'bot' ? renderMarkdown(text) : escHtml(text);
    messagesEl.appendChild(div);
    scrollBottom();
    return div;
  }

  function addTyping() {
    const div = document.createElement('div');
    div.className = 'bl-msg bot bl-typing';
    div.innerHTML = '<span></span><span></span><span></span>';
    messagesEl.appendChild(div);
    scrollBottom();
    return div;
  }

  function scrollBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // ── Chat API ─────────────────────────────────────────────────────
  async function sendMessage(text) {
    history.push({ role: 'user', content: text });
    const typing = addTyping();
    $('bl-send').disabled = true;

    try {
      const resp = await fetch(CHAT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: history.slice(0, -1), channel: 'chat' }),
      });
      typing.remove();
      if (!resp.ok) { addMsg('Greška servera. Pokušaj ponovo.', 'bot'); return; }
      const data = await resp.json();
      const reply = data.reply || '(bez odgovora)';
      history.push({ role: 'assistant', content: reply });
      addMsg(reply, 'bot');
    } catch (err) {
      typing.remove();
      addMsg('Greška mreže: ' + err.message, 'bot');
    } finally {
      $('bl-send').disabled = false;
      $('bl-input').focus();
    }
  }

  // ── Voice state ──────────────────────────────────────────────────
  let vState = VS.IDLE;
  let voiceModeActive = false;
  let voicePaused = false;
  let audioCtx = null, analyser = null, micStream = null;
  let recorder = null, chunks = [], silenceTimer = null;
  let recorderStartTs = 0, speechDetected = false, speechStartTs = 0;
  let maxRecordingTimer = null, speechOnsetTimer = null;
  let interruptTimer = null, speakingStartTs = 0;
  let vadRafId = null, currentAudio = null;

  const vEls = {
    panel:    $('bl-voice-panel'),
    orb:      $('bl-voice-orb'),
    core:     $('bl-vorb-large'),
    statusTxt:$('bl-vstate-text'),
    tline:    $('bl-vtline'),
    wave:     $('bl-vwave'),
    hint:     $('bl-vhint'),
    trans:    $('bl-vtranscript'),
    pauseBtn: $('bl-vpause'),
    pauseLbl: $('bl-vpause-label'),
  };

  const ORB_LOADER_HTML = '<span class="bl-orb__loader"><span></span><span></span><span></span></span>';

  const STATE_MAP = {
    [VS.IDLE]:       { mod: '',           status: 'Spremno · pritisni mikrofon', tline: '<em>Postavi pitanje glasom.</em><br><em>Govori bosanski, srpski ili hrvatski.</em>', wave: false, hint: true },
    [VS.LISTENING]:  { mod: 'listening',  status: 'Slušam...',                   tline: '<em>Govori — pauzom šalješ poruku</em>',                                            wave: false, hint: true },
    [VS.RECORDING]:  { mod: 'recording',  status: 'Snimam...',                   tline: '<em>Govori...</em>',                                                                wave: true,  hint: false },
    [VS.PROCESSING]: { mod: 'processing', status: 'Razmišljam...',               tline: '<em>Tražim odgovor...</em>',                                                        wave: false, hint: false },
    [VS.SPEAKING]:   { mod: '',           status: 'Govorim...',                  tline: '<em>Asistent govori...</em>',                                                       wave: true,  hint: false },
  };

  function setVoiceState(s) {
    const prev = vState;
    vState = s;
    if (s === VS.SPEAKING && prev !== VS.SPEAKING) {
      speakingStartTs = Date.now();
    }
    if (s !== VS.SPEAKING) {
      clearTimeout(interruptTimer); interruptTimer = null;
    }
    const cfg = STATE_MAP[s];
    vEls.orb.className = 'bl-orb' + (cfg.mod ? ' bl-orb--' + cfg.mod : '');
    vEls.panel.className = 'vp-' + s;
    vEls.statusTxt.textContent = cfg.status;
    vEls.tline.innerHTML = cfg.tline;
    vEls.wave.classList.toggle('bl-hidden', !cfg.wave);
    vEls.hint.classList.toggle('bl-hidden', !cfg.hint);
    setOrbCoreContent(s === VS.PROCESSING ? 'loader' : 'mic');
  }

  function setOrbCoreContent(kind) {
    if (vEls.core.dataset.kind === kind) return;
    vEls.core.innerHTML = (kind === 'loader') ? ORB_LOADER_HTML : I.mic;
    vEls.core.dataset.kind = kind;
  }

  function setPausedState() {
    vEls.orb.className = 'bl-orb bl-orb--paused';
    vEls.panel.className = 'vp-paused';
    vEls.statusTxt.textContent = 'Pauzirano';
    vEls.tline.innerHTML = '<em>Pauzirano — klikni "Nastavi" da nastaviš razgovor.</em>';
    vEls.wave.classList.add('bl-hidden');
    vEls.hint.classList.add('bl-hidden');
    setOrbCoreContent('mic');
  }

  function addVoiceMsg(role, content) {
    vEls.trans.classList.remove('bl-hidden');
    const div = document.createElement('div');
    div.className = 'bl-msg ' + (role === 'user' ? 'user' : 'bot');
    div.innerHTML = role === 'user' ? escHtml(content) : renderMarkdown(content);
    vEls.trans.appendChild(div);
    vEls.trans.scrollTop = vEls.trans.scrollHeight;
  }

  // ── Mic open/close ───────────────────────────────────────────────
  async function openMic() {
    if (!window.isSecureContext || !navigator.mediaDevices) {
      throw new Error('NIJE_SECURE_CONTEXT');
    }
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,    // gasi TTS reverb iz zvučnika
        noiseSuppression: true,    // gasi pozadinski šum
        autoGainControl: true,     // izjednačava jačinu glasa
        channelCount: 1,
      },
    });
    audioCtx  = new (window.AudioContext || window.webkitAudioContext)();
    analyser  = audioCtx.createAnalyser();
    analyser.fftSize = 512;
    audioCtx.createMediaStreamSource(micStream).connect(analyser);
  }

  function closeMic() {
    cancelAnimationFrame(vadRafId);
    if (micStream) { micStream.getTracks().forEach(t => t.stop()); micStream = null; }
    if (audioCtx)  { audioCtx.close(); audioCtx = null; }
    analyser = null;
  }

  function getRms() {
    if (!analyser) return 0;
    const buf = new Float32Array(analyser.fftSize);
    analyser.getFloatTimeDomainData(buf);
    let sum = 0; for (const v of buf) sum += v * v;
    return Math.sqrt(sum / buf.length);
  }

  // ── Continuous recording: start ASAP, capture from frame 0 ──────
  // Recorder se pokreće odmah kad smo u LISTENING stanju. Sve što
  // korisnik kaže (uključujući "Dobar dan", prve slogove, itd.) ide
  // u recording. VAD samo detektuje KRAJ govora (silence) i tada
  // šalje cijeli buffer na STT.
  function startListeningRecorder() {
    if (!micStream || !voiceModeActive) return;
    // Stop bilo kakav postojeći recorder (bez triggera onstop logike)
    if (recorder && recorder.state !== 'inactive') {
      recorder.onstop = null;
      try { recorder.stop(); } catch (e) {}
    }
    clearTimeout(silenceTimer); silenceTimer = null;
    clearTimeout(maxRecordingTimer); maxRecordingTimer = null;
    clearTimeout(speechOnsetTimer); speechOnsetTimer = null;
    chunks = [];
    speechDetected = false;
    speechStartTs = 0;
    recorderStartTs = Date.now();

    const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus' : 'audio/ogg;codecs=opus';
    recorder = new MediaRecorder(micStream, { mimeType: mime });
    recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
    recorder.start(100);
    setVoiceState(VS.LISTENING);

    // Safety cap — ako korisnik priča duže od 30s bez pauze, prisilno finalize
    maxRecordingTimer = setTimeout(() => {
      if (voiceModeActive && speechDetected) finalizeAndSend();
    }, MAX_RECORDING_MS);
  }

  // ── VAD loop ─────────────────────────────────────────────────────
  function startVad() {
    function tick() {
      if (voicePaused) { vadRafId = requestAnimationFrame(tick); return; }
      const rms = getRms();
      const now = Date.now();

      if (vState === VS.LISTENING || vState === VS.RECORDING) {
        if (rms > SPEECH_THRESHOLD) {
          if (speechDetected) {
            // Već detektovan govor — samo poništi silence timer
            clearTimeout(silenceTimer); silenceTimer = null;
          } else if (!speechOnsetTimer) {
            // Sustained-onset filter: signal mora trajati SPEECH_ONSET_MS
            // pre nego što potvrdimo da je stvarni govor (filtrira tranzijente)
            speechOnsetTimer = setTimeout(() => {
              speechOnsetTimer = null;
              if ((vState === VS.LISTENING || vState === VS.RECORDING) && voiceModeActive) {
                speechDetected = true;
                speechStartTs = Date.now();
                if (vState === VS.LISTENING) setVoiceState(VS.RECORDING);
              }
            }, SPEECH_ONSET_MS);
          }
        } else {
          // RMS pao ispod praga
          if (speechOnsetTimer && !speechDetected) {
            // Onset nije potvrđen — bio je samo tranzijent, otkaži
            clearTimeout(speechOnsetTimer); speechOnsetTimer = null;
          }
          if (speechDetected && !silenceTimer) {
            silenceTimer = setTimeout(() => {
              if ((vState === VS.LISTENING || vState === VS.RECORDING) && voiceModeActive) {
                finalizeAndSend();
              }
            }, SILENCE_MS);
          }
        }
      } else if (vState === VS.SPEAKING) {
        // Interrupt detection — viši prag + sustained hold + guard window
        const sinceSpeaking = now - speakingStartTs;
        if (sinceSpeaking < INTERRUPT_GUARD_MS) {
          // Settle period — ignoriši mic dok TTS audio ne stigne do steady state
          clearTimeout(interruptTimer); interruptTimer = null;
        } else if (rms > INTERRUPT_THRESHOLD) {
          if (!interruptTimer) {
            interruptTimer = setTimeout(() => {
              interruptTimer = null;
              if (vState === VS.SPEAKING) interruptAndListen();
            }, INTERRUPT_HOLD_MS);
          }
        } else {
          clearTimeout(interruptTimer); interruptTimer = null;
        }
      }
      vadRafId = requestAnimationFrame(tick);
    }
    vadRafId = requestAnimationFrame(tick);
  }

  function interruptAndListen() {
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    startListeningRecorder();
  }

  async function finalizeAndSend() {
    clearTimeout(silenceTimer); silenceTimer = null;
    clearTimeout(maxRecordingTimer); maxRecordingTimer = null;
    clearTimeout(speechOnsetTimer); speechOnsetTimer = null;
    if (!recorder || recorder.state === 'inactive') return;

    const speechElapsed = speechDetected ? (Date.now() - speechStartTs) : 0;
    if (!speechDetected || speechElapsed < MIN_SPEECH_MS) {
      // Nema validnog govora — restart fresh
      if (voiceModeActive) startListeningRecorder();
      return;
    }

    if (voiceModeActive) setVoiceState(VS.PROCESSING);
    await new Promise(resolve => { recorder.onstop = resolve; recorder.stop(); });
    const blob = new Blob(chunks, { type: recorder.mimeType });
    chunks = [];

    if (!voiceModeActive) return;

    try {
      const transcript = await transcribeAudio(blob);
      if (!transcript.trim() || !voiceModeActive) {
        if (voiceModeActive) startListeningRecorder();
        return;
      }

      addVoiceMsg('user', transcript);
      addMsg(transcript, 'user');
      history.push({ role: 'user', content: transcript });

      const { replyText, replyVoice } = await chatVoiceApi(transcript);
      if (!voiceModeActive) return;

      addVoiceMsg('ai', replyText);
      addMsg(replyText, 'bot');
      history.push({ role: 'assistant', content: replyText });

      if (!voiceModeActive) return;
      setVoiceState(VS.SPEAKING);
      await speakText(replyVoice || replyText);
    } catch (err) {
      if (voiceModeActive) vEls.statusTxt.textContent = 'Greška: ' + err.message;
    }

    // Cooldown nakon TTS-a (anti-reverb), pa ponovo slušaj
    if (voiceModeActive) {
      await new Promise(r => setTimeout(r, TTS_COOLDOWN_MS));
      if (voiceModeActive) startListeningRecorder();
    }
  }

  // ── Voice API calls ──────────────────────────────────────────────
  async function transcribeAudio(blob) {
    const form = new FormData();
    form.append('audio', blob, 'rec.webm');
    const resp = await fetch(STT_URL, { method: 'POST', body: form });
    if (!resp.ok) throw new Error('STT greška ' + resp.status);
    return (await resp.json()).text || '';
  }

  async function chatVoiceApi(message) {
    const resp = await fetch(CHAT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history: history.slice(0, -1), channel: 'voice' }),
    });
    if (!resp.ok) throw new Error('Chat greška ' + resp.status);
    const data = await resp.json();
    return { replyText: data.reply || '', replyVoice: data.reply_voice || '' };
  }

  async function speakText(text) {
    try {
      const resp = await fetch(TTS_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!resp.ok) throw new Error();
      const url = URL.createObjectURL(await resp.blob());
      currentAudio = new Audio(url);
      await new Promise((res, rej) => {
        currentAudio.onended = () => { URL.revokeObjectURL(url); currentAudio = null; res(); };
        currentAudio.onerror = () => { URL.revokeObjectURL(url); currentAudio = null; rej(new Error()); };
        currentAudio.play().catch(rej);
      });
    } catch {
      if (!window.speechSynthesis) return;
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      const v = window.speechSynthesis.getVoices().find(x => /hr|bs|sr/i.test(x.lang));
      if (v) u.voice = v; u.lang = 'hr-HR'; u.rate = 0.95;
      await new Promise(r => { u.onend = r; u.onerror = r; window.speechSynthesis.speak(u); });
    }
  }

  // ── Voice overlay open / close ───────────────────────────────────
  async function openVoiceMode() {
    const overlay = $('bl-voice-overlay');
    overlay.classList.add('open');
    // Zaključaj scroll pozadinske stranice — modal preuzima ekran
    document.documentElement.classList.add('bl-scroll-lock');
    voicePaused = false;
    vEls.pauseLbl.textContent = 'Pauziraj';
    vEls.pauseBtn.querySelector('svg')?.replaceWith(
      Object.assign(document.createElement('span'), { innerHTML: I.pause }).firstChild
    );

    setVoiceState(VS.IDLE);
    vEls.statusTxt.textContent = 'Zahtijevam pristup mikrofonu...';
    voiceModeActive = true;

    try {
      await openMic();
      startListeningRecorder();
      startVad();
    } catch (err) {
      vEls.orb.className = 'bl-orb bl-orb--paused';
      if (err.message === 'NIJE_SECURE_CONTEXT') {
        vEls.statusTxt.textContent = 'Browser blokira mikrofon';
        vEls.tline.innerHTML =
          '<div style="font-size:12px;line-height:1.7;text-align:left">' +
          '<strong>Chrome fix:</strong><br>' +
          'Otvori <code style="background:rgba(0,0,0,.06);padding:1px 5px;border-radius:3px">chrome://flags/#unsafely-treat-insecure-origin-as-secure</code><br>' +
          'Dodaj <code style="background:rgba(0,0,0,.06);padding:1px 5px;border-radius:3px">' + escHtml(location.origin) + '</code> → Relaunch<br><br>' +
          '<strong>Firefox:</strong> localhost radi bez izmjena.<br><br>' +
          'Ili koristi <a href="/public/voice.html" target="_blank" style="color:var(--bl-orange);font-weight:700">Voice Asistent (novi tab)</a>' +
          '</div>';
      } else if (err.name === 'NotAllowedError') {
        vEls.statusTxt.textContent = 'Dozvola odbijena — odobri mikrofon u browseru';
      } else {
        vEls.statusTxt.textContent = 'Mikrofon nedostupan: ' + err.message;
      }
    }
  }

  function closeVoiceMode() {
    voiceModeActive = false;
    voicePaused = false;
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    clearTimeout(silenceTimer); silenceTimer = null;
    clearTimeout(maxRecordingTimer); maxRecordingTimer = null;
    clearTimeout(speechOnsetTimer); speechOnsetTimer = null;
    clearTimeout(interruptTimer); interruptTimer = null;
    cancelAnimationFrame(vadRafId);
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    closeMic();
    setVoiceState(VS.IDLE);
    $('bl-voice-overlay').classList.remove('open');
    document.documentElement.classList.remove('bl-scroll-lock');
    vEls.trans.innerHTML = '';
    vEls.trans.classList.add('bl-hidden');
  }

  function togglePause() {
    if (!voiceModeActive) return;
    voicePaused = !voicePaused;
    if (voicePaused) {
      // Halt all active recording / playback but keep mic stream open
      if (currentAudio) { currentAudio.pause(); currentAudio = null; }
      if (window.speechSynthesis) window.speechSynthesis.cancel();
      clearTimeout(silenceTimer); silenceTimer = null;
      clearTimeout(maxRecordingTimer); maxRecordingTimer = null;
      clearTimeout(speechOnsetTimer); speechOnsetTimer = null;
      clearTimeout(interruptTimer); interruptTimer = null;
      if (recorder && recorder.state !== 'inactive') {
        recorder.onstop = null;
        try { recorder.stop(); } catch (e) {}
      }
      setPausedState();
      vEls.pauseLbl.textContent = 'Nastavi';
      vEls.pauseBtn.querySelector('svg')?.replaceWith(
        Object.assign(document.createElement('span'), { innerHTML: I.play }).firstChild
      );
    } else {
      vEls.pauseLbl.textContent = 'Pauziraj';
      vEls.pauseBtn.querySelector('svg')?.replaceWith(
        Object.assign(document.createElement('span'), { innerHTML: I.pause }).firstChild
      );
      startListeningRecorder();
    }
  }

  // ── Widget events ────────────────────────────────────────────────
  $('bl-launcher').addEventListener('click', function () {
    const win = $('bl-window');
    const isOpen = win.classList.toggle('open');
    this.classList.toggle('bl-open', isOpen);
    if (isOpen && !chatOpened) {
      chatOpened = true;
      renderWelcome();
    }
    if (isOpen) $('bl-input').focus();
  });

  $('bl-close').addEventListener('click', () => {
    $('bl-window').classList.remove('open');
    $('bl-launcher').classList.remove('bl-open');
  });

  $('bl-min').addEventListener('click', () => {
    $('bl-window').classList.remove('open');
    $('bl-launcher').classList.remove('bl-open');
  });

  $('bl-send').addEventListener('click', () => {
    const inp = $('bl-input');
    const text = inp.value.trim();
    if (!text) return;
    inp.value = '';
    addMsg(text, 'user');
    sendMessage(text);
  });

  $('bl-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      $('bl-send').click();
    }
  });

  $('bl-voice-btn').addEventListener('click', () => openVoiceMode());
  $('bl-voice-close-btn').addEventListener('click', () => closeVoiceMode());
  $('bl-vstop').addEventListener('click', () => closeVoiceMode());
  $('bl-vpause').addEventListener('click', () => togglePause());

})();
