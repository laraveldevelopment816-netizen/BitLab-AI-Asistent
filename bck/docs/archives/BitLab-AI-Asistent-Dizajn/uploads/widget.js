/**
 * BitLab AI Chat Widget v2 — embeddable
 * Integracija: <script src="http://localhost:8000/public/widget.js"></script>
 *
 * Opciono: window.BITLAB_API = 'https://moj-server.ngrok.io' (default: isto origin)
 */
(function () {
  'use strict';

  const API_BASE = (window.BITLAB_API || '').replace(/\/$/, '') || '';
  const CHAT_URL = API_BASE + '/api/chat';
  const STT_URL  = API_BASE + '/api/stt';
  const TTS_URL  = API_BASE + '/api/tts';

  const QUICK_REPLIES = [
    { label: 'Laptopi i računari',  q: 'Koji laptopi su trenutno na lageru?' },
    { label: 'Gaming oprema',       q: 'Šta imate od gaming opreme?' },
    { label: 'Dostava i plaćanje',  q: 'Kakve su opcije dostave i načini plaćanja?' },
    { label: 'Garancija i servis',  q: 'Kakva je politika garancije i povraćaja robe?' },
  ];

  // ── Voice VAD constants ──────────────────────────────────────────
  const SPEECH_THRESHOLD    = 0.038;
  const SPEECH_ONSET_MS     = 400;
  const ONSET_GAP_MS        = 75;
  const SILENCE_MS          = 1100;
  const MIN_SPEECH_MS       = 500;
  const INTERRUPT_THRESHOLD = 0.10;   // visoko — samo jak glas prekida, ne zvučnik
  const TTS_COOLDOWN_MS     = 750;    // pauza nakon TTS da reverb utihne
  const VS = {
    IDLE:'idle', LISTENING:'listening', RECORDING:'recording',
    PROCESSING:'processing', SPEAKING:'speaking',
  };

  // ── CSS ─────────────────────────────────────────────────────────
  const css = `
#bl-launcher {
  position:fixed; bottom:24px; right:24px;
  width:62px; height:62px; border-radius:50%;
  background:linear-gradient(135deg,#fb6d3b,#eA5c2a);
  color:white; border:none; font-size:28px;
  cursor:pointer; z-index:9999;
  box-shadow:0 6px 20px rgba(251,109,59,.45);
  transition:transform .2s;
}
#bl-launcher:hover { transform:scale(1.08); }

#bl-window {
  position:fixed; bottom:100px; right:24px;
  width:400px; max-height:640px;
  background:#fff; border-radius:18px;
  box-shadow:0 20px 60px rgba(0,0,0,.18);
  display:none; flex-direction:column; overflow:hidden;
  z-index:9999; font-family:-apple-system,"Segoe UI",Roboto,sans-serif;
}
#bl-window.open { display:flex; }

#bl-header {
  background:linear-gradient(135deg,#1a1a2e,#2a2a3e);
  color:#fff; padding:14px 18px;
  display:flex; justify-content:space-between; align-items:center;
  flex-shrink:0;
}
.bl-header-left { display:flex; align-items:center; gap:10px; }
.bl-avatar {
  width:38px; height:38px; border-radius:50%;
  background:linear-gradient(135deg,#fb6d3b,#eA5c2a);
  display:flex; align-items:center; justify-content:center;
  font-size:19px; flex-shrink:0;
}
.bl-hinfo .bl-title { font-weight:700; font-size:15px; }
.bl-hinfo .bl-sub {
  font-size:11px; opacity:.8; margin-top:2px;
  display:flex; align-items:center; gap:5px;
}
.bl-dot {
  width:6px; height:6px; border-radius:50%; background:#4ade80;
  display:inline-block; animation:blBlink 2s infinite;
}
@keyframes blBlink { 0%,100%{opacity:1} 50%{opacity:.35} }
#bl-close {
  background:rgba(255,255,255,.15); border:none; color:#fff;
  width:28px; height:28px; border-radius:50%; cursor:pointer; font-size:16px;
  display:flex; align-items:center; justify-content:center;
}
#bl-close:hover { background:rgba(255,255,255,.25); }

#bl-messages {
  flex:1; overflow-y:auto; padding:14px;
  background:#F9FAFB; font-size:14px;
}
#bl-messages::-webkit-scrollbar { width:5px; }
#bl-messages::-webkit-scrollbar-track { background:#EFF2F5; }
#bl-messages::-webkit-scrollbar-thumb { background:#fed1bb; border-radius:3px; }
#bl-messages::-webkit-scrollbar-thumb:hover { background:#fb6d3b; }
.bl-msg {
  margin-bottom:10px; padding:10px 13px; border-radius:12px;
  max-width:88%; line-height:1.5; word-break:break-word;
}
.bl-msg.user {
  background:#fb6d3b; color:#fff;
  margin-left:auto; border-bottom-right-radius:4px;
}
.bl-msg.bot {
  background:#fff; border:1px solid #E5E7EB;
  color:#1F2937; border-bottom-left-radius:4px;
}
.bl-msg.bot a { color:#fb6d3b; }
.bl-msg.bot img {
  width:64px; height:64px; object-fit:contain;
  border-radius:6px; border:1px solid #E5E7EB;
  background:#F9FAFB; vertical-align:middle; margin-right:8px;
}
.bl-typing { display:flex; gap:4px; align-items:center; padding:8px 0; }
.bl-typing span {
  width:7px; height:7px; border-radius:50%; background:#CBD5E1;
  animation:blDot 1.2s infinite ease-in-out;
}
.bl-typing span:nth-child(2) { animation-delay:.2s; }
.bl-typing span:nth-child(3) { animation-delay:.4s; }
@keyframes blDot {
  0%,80%,100%{ transform:scale(.7); opacity:.5; }
  40%{ transform:scale(1); opacity:1; }
}

#bl-quick-wrap {
  padding:4px 14px 10px; background:#F9FAFB;
  border-bottom:1px solid #EFF2F5; flex-shrink:0;
}
#bl-quick-wrap.hidden { display:none; }
.bl-qr-label { font-size:11px; color:#94A3B8; margin-bottom:6px; padding-top:4px; }
.bl-quick-chips { display:flex; flex-wrap:wrap; gap:6px; }
.bl-chip {
  background:#FFF7ED; border:1px solid #fed1bb;
  color:#eA5c2a; border-radius:16px;
  padding:5px 12px; font-size:12px; cursor:pointer;
  transition:background .15s; white-space:nowrap; line-height:1.3;
}
.bl-chip:hover { background:#FED7AA; }

#bl-input-area {
  padding:10px; border-top:1px solid #E5E7EB;
  background:#fff; display:flex; gap:6px; align-items:center; flex-shrink:0;
}
#bl-input {
  flex:1; padding:9px 13px; border:1px solid #E5E7EB;
  border-radius:20px; outline:none; font-size:14px; font-family:inherit;
}
#bl-input:focus { border-color:#fb6d3b; }
#bl-send {
  background:#fb6d3b; color:#fff; border:none;
  border-radius:50%; width:38px; height:38px;
  cursor:pointer; font-size:16px; flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
}
#bl-send:disabled { opacity:.5; cursor:default; }
#bl-voice-btn {
  background:#F1F5F9; color:#475569; border:1px solid #E2E8F0;
  border-radius:50%; width:38px; height:38px;
  cursor:pointer; font-size:18px; flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
  transition:background .15s;
}
#bl-voice-btn:hover { background:#E2E8F0; }

@media (max-width:440px) {
  #bl-window { right:8px; left:8px; width:auto; bottom:88px; }
}

/* ── Voice overlay — samo tamna pozadina, klik na pozadinu NE zatvara ── */
#bl-voice-overlay {
  position:fixed; inset:0;
  background:rgba(0,0,0,0.55);
  backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px);
  display:none; align-items:center; justify-content:center;
  z-index:10001;
}
#bl-voice-overlay.open { display:flex; }

/* Panel — bijeli, identičan widgetu */
#bl-voice-panel {
  width:min(460px, 96vw); max-height:88vh;
  background:#fff; border-radius:18px;
  display:flex; flex-direction:column; overflow:hidden;
  box-shadow:0 24px 80px rgba(0,0,0,.35); color:#1F2937;
}

/* Header — isti gradijent kao chat */
#bl-vheader {
  background:linear-gradient(135deg,#1a1a2e,#2a2a3e);
  color:#fff; padding:14px 18px;
  display:flex; align-items:center; gap:12px; flex-shrink:0;
}
#bl-voice-orb {
  width:42px; height:42px; border-radius:50%; flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
  font-size:20px; transition:background .35s;
}
#bl-voice-orb.orb-idle       { background:rgba(255,255,255,.15); }
#bl-voice-orb.orb-listening  { background:radial-gradient(circle,#16a34a,#15803d); animation:vOrbG 2s infinite; }
#bl-voice-orb.orb-recording  { background:radial-gradient(circle,#dc2626,#991b1b); animation:vOrbR .65s infinite; }
#bl-voice-orb.orb-processing { background:radial-gradient(circle,#7c3aed,#6d28d9); animation:vSpin 1s linear infinite; }
#bl-voice-orb.orb-speaking   { background:radial-gradient(circle,#fb6d3b,#eA5c2a); animation:vOrbO .9s infinite; }

@keyframes vOrbG {
  0%,100%{ box-shadow:0 0 0 0 rgba(22,163,74,0); }
  50%{ box-shadow:0 0 0 10px rgba(22,163,74,.3); transform:scale(1.06); }
}
@keyframes vOrbR {
  0%,100%{ transform:scale(1); }
  50%{ transform:scale(1.1); box-shadow:0 0 0 8px rgba(220,38,38,.22); }
}
@keyframes vOrbO {
  0%,100%{ box-shadow:0 0 0 0 rgba(251,109,59,0); }
  50%{ box-shadow:0 0 0 9px rgba(251,109,59,.28); transform:scale(1.06); }
}
@keyframes vSpin { to{ transform:rotate(360deg); } }

#bl-vheader-info { flex:1; }
.bl-vtitle { font-weight:700; font-size:15px; }
#bl-vstate { font-size:11px; opacity:.8; margin-top:2px; min-height:16px; }

#bl-voice-close-btn {
  background:rgba(255,255,255,.15); border:none; color:#fff;
  width:28px; height:28px; border-radius:50%; cursor:pointer; font-size:16px;
  display:flex; align-items:center; justify-content:center;
}
#bl-voice-close-btn:hover { background:rgba(255,255,255,.28); }

/* Level bar — tanki strip ispod headera */
#bl-vlevel-wrap { height:3px; background:#EFF2F5; flex-shrink:0; }
#bl-vlevel-bar  {
  height:100%; width:0%;
  background:linear-gradient(90deg,#4ade80,#fb6d3b);
  transition:width .05s;
}

/* Transcript — isti kao chat messages area */
#bl-vtranscript {
  flex:1; overflow-y:auto; padding:14px;
  background:#F9FAFB; font-size:14px; min-height:260px;
}
#bl-vtranscript::-webkit-scrollbar { width:5px; }
#bl-vtranscript::-webkit-scrollbar-track { background:#EFF2F5; }
#bl-vtranscript::-webkit-scrollbar-thumb { background:#fed1bb; border-radius:3px; }
#bl-vtranscript::-webkit-scrollbar-thumb:hover { background:#fb6d3b; }

/* Veliki centralni orb (vidljiv samo u vp-idle stanju) */
#bl-vorb-center {
  display:flex; flex-direction:column; align-items:center;
  padding:32px 0 22px; flex-shrink:0;
}
#bl-vorb-large {
  width:88px; height:88px; border-radius:50%; flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
  font-size:40px; margin-bottom:12px; transition:background .35s;
}
#bl-vorb-large.orb-idle {
  background:linear-gradient(135deg,#fb6d3b,#eA5c2a);
  box-shadow:0 8px 24px rgba(251,109,59,.5);
}
#bl-vorb-large.orb-listening {
  background:radial-gradient(circle,#16a34a,#15803d);
  animation:vOrbG 2s infinite;
}
#bl-vorb-label {
  font-size:13px; color:#64748B; text-align:center; line-height:1.5;
}

/* Panel stanje — toggle orba između centra i headera */
#bl-voice-panel.vp-idle   #bl-voice-orb   { display:none !important; }
#bl-voice-panel.vp-active #bl-voice-orb   { display:flex; }
#bl-voice-panel.vp-idle   #bl-vorb-center { display:flex; }
#bl-voice-panel.vp-active #bl-vorb-center { display:none; }

/* Stop dugme — donje, crveno, čisto */
#bl-vstop-wrap {
  padding:12px; border-top:1px solid #E5E7EB;
  background:#fff; display:flex; justify-content:center; flex-shrink:0;
}
#bl-vstop {
  background:#FEF2F2; border:1.5px solid #FECACA;
  color:#DC2626; border-radius:8px;
  padding:8px 32px; font-size:14px; font-weight:600;
  cursor:pointer; transition:background .15s, border-color .15s;
}
#bl-vstop:hover { background:#FEE2E2; border-color:#FCA5A5; }
`;

  // ── Inject CSS & HTML ────────────────────────────────────────────
  const styleEl = document.createElement('style');
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  document.body.insertAdjacentHTML('beforeend', `
<button id="bl-launcher" aria-label="Otvori chat">💬</button>

<div id="bl-window" role="dialog" aria-label="BitLab AI Chat">
  <div id="bl-header">
    <div class="bl-header-left">
      <div class="bl-avatar">🤖</div>
      <div class="bl-hinfo">
        <div class="bl-title">BitLab Asistent</div>
        <div class="bl-sub"><span class="bl-dot"></span>Online &middot; Odgovara odmah</div>
      </div>
    </div>
    <button id="bl-close" aria-label="Zatvori">&times;</button>
  </div>
  <div id="bl-messages"></div>
  <div id="bl-quick-wrap">
    <div class="bl-qr-label">Česta pitanja:</div>
    <div class="bl-quick-chips" id="bl-chips"></div>
  </div>
  <div id="bl-input-area">
    <input id="bl-input" type="text" placeholder="Postavi pitanje..." autocomplete="off">
    <button id="bl-voice-btn" title="Voice mode — razgovaraj glasom">🎤</button>
    <button id="bl-send">&#10148;</button>
  </div>
</div>

<div id="bl-voice-overlay" role="dialog" aria-label="Voice Mode">
  <div id="bl-voice-panel" class="vp-idle">
    <div id="bl-vheader">
      <div id="bl-voice-orb" class="orb-idle">🎤</div>
      <div id="bl-vheader-info">
        <div class="bl-vtitle">BitLab Voice Asistent</div>
        <div id="bl-vstate">Inicijalizacija...</div>
      </div>
      <button id="bl-voice-close-btn" aria-label="Zatvori voice mode">&times;</button>
    </div>
    <div id="bl-vorb-center">
      <div id="bl-vorb-large" class="orb-idle">🎤</div>
      <div id="bl-vorb-label">Inicijalizacija mikrofona...</div>
    </div>
    <div id="bl-vlevel-wrap"><div id="bl-vlevel-bar"></div></div>
    <div id="bl-vtranscript"></div>
    <div id="bl-vstop-wrap">
      <button id="bl-vstop">&#9632;&nbsp; Zaustavi</button>
    </div>
  </div>
</div>
`);

  // ── Quick reply chips ────────────────────────────────────────────
  const chipsEl = document.getElementById('bl-chips');
  QUICK_REPLIES.forEach(({ label, q }) => {
    const btn = document.createElement('button');
    btn.className = 'bl-chip';
    btn.textContent = label;
    btn.onclick = () => {
      hideQuickReplies();
      addMsg(label, 'user');
      sendMessage(q);
    };
    chipsEl.appendChild(btn);
  });

  function hideQuickReplies() {
    document.getElementById('bl-quick-wrap').classList.add('hidden');
  }

  // ── Shared history (chat + voice) ────────────────────────────────
  const history = [];
  let chatOpened = false;

  // ── Markdown renderer ────────────────────────────────────────────
  function renderMarkdown(text) {
    return text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/!\[([^\]]*)\]\((https?:\/\/[^)]+)\)/g,
        '<img src="$2" alt="$1" loading="lazy" onerror="this.style.display=\'none\'">')
      .replace(/\[([^\]]+)\]\(((?:https?|mailto):[^)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/\n/g, '<br>');
  }

  function escHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function addMsg(text, role) {
    const div = document.createElement('div');
    div.className = 'bl-msg ' + role;
    div.innerHTML = role === 'bot' ? renderMarkdown(text) : escHtml(text);
    document.getElementById('bl-messages').appendChild(div);
    scrollBottom();
    return div;
  }

  function addTyping() {
    const div = document.createElement('div');
    div.className = 'bl-msg bot bl-typing';
    div.innerHTML = '<span></span><span></span><span></span>';
    document.getElementById('bl-messages').appendChild(div);
    scrollBottom();
    return div;
  }

  function scrollBottom() {
    const m = document.getElementById('bl-messages');
    m.scrollTop = m.scrollHeight;
  }

  // ── Chat API ─────────────────────────────────────────────────────
  async function sendMessage(text) {
    hideQuickReplies();
    history.push({ role: 'user', content: text });
    const typing = addTyping();
    document.getElementById('bl-send').disabled = true;

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
      document.getElementById('bl-send').disabled = false;
      document.getElementById('bl-input').focus();
    }
  }

  // ── Voice state ──────────────────────────────────────────────────
  let vState = VS.IDLE;
  let voiceModeActive = false;
  let conversationStarted = false;
  let audioCtx = null, analyser = null, micStream = null;
  let recorder = null, chunks = [], silenceTimer = null, speechStart = 0;
  let speechOnsetTimer = null;
  let onsetGapTimer = null;
  let vadRafId = null, currentAudio = null;

  const vEls = {
    orb:      document.getElementById('bl-voice-orb'),
    largOrb:  document.getElementById('bl-vorb-large'),
    orbLabel: document.getElementById('bl-vorb-label'),
    panel:    document.getElementById('bl-voice-panel'),
    status:   document.getElementById('bl-vstate'),
    level:    document.getElementById('bl-vlevel-bar'),
    trans:    document.getElementById('bl-vtranscript'),
  };

  function setVoiceState(s) {
    vState = s;

    // Kad počne snimanje → permanentno pređi na mali header orb
    if (s === VS.RECORDING || s === VS.PROCESSING || s === VS.SPEAKING) {
      conversationStarted = true;
    }
    vEls.panel.className = conversationStarted ? 'vp-active' : 'vp-idle';

    const stateClass = 'orb-' + s;
    vEls.orb.className = stateClass;
    vEls.largOrb.className = stateClass;

    const map = {
      [VS.IDLE]:       ['🎤', 'Čeka...', 'Inicijalizacija mikrofona...'],
      [VS.LISTENING]:  ['👂', 'Slušam...', 'Govori — pauzom šalješ poruku'],
      [VS.RECORDING]:  ['⏺',  'Snimam...', ''],
      [VS.PROCESSING]: ['⏳', 'Razmišljam...', ''],
      [VS.SPEAKING]:   ['🔊', 'Govorim...', ''],
    };
    const [icon, statusTxt, labelTxt] = map[s];
    vEls.orb.textContent = icon;
    vEls.largOrb.textContent = icon;
    vEls.status.textContent = statusTxt;
    if (labelTxt !== '') vEls.orbLabel.textContent = labelTxt;
    if (s !== VS.RECORDING && s !== VS.LISTENING) vEls.level.style.width = '0%';
  }

  function addVoiceMsg(role, content) {
    const div = document.createElement('div');
    div.className = 'bl-msg ' + (role === 'user' ? 'user' : 'bot');
    div.innerHTML = role === 'user' ? escHtml(content) : renderMarkdown(content);
    vEls.trans.appendChild(div);
    vEls.trans.scrollTop = vEls.trans.scrollHeight;
  }

  // ── Mic open/close ───────────────────────────────────────────────
  async function openMic() {
    if (!window.isSecureContext || !navigator.mediaDevices) {
      throw new Error(
        'NIJE_SECURE_CONTEXT'
      );
    }
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
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

  // ── VAD loop ─────────────────────────────────────────────────────
  function startVad() {
    function tick() {
      const rms = getRms();
      if (vState === VS.LISTENING || vState === VS.RECORDING)
        vEls.level.style.width = Math.min(rms / 0.08 * 100, 100) + '%';

      if (vState === VS.LISTENING) {
        if (rms > SPEECH_THRESHOLD) {
          // RMS iznad praga — poništi gap timer, pokreni onset ako već ne teče
          clearTimeout(onsetGapTimer); onsetGapTimer = null;
          if (!speechOnsetTimer) {
            speechOnsetTimer = setTimeout(() => {
              speechOnsetTimer = null;
              if (vState === VS.LISTENING) startCapture();
            }, SPEECH_ONSET_MS);
          }
        } else if (speechOnsetTimer) {
          // Kratka pauza unutar onset prozora — dozvoli do ONSET_GAP_MS
          // (inter-fonemski razmaci u govoru su <50ms, tastatura pravi pauze >100ms)
          if (!onsetGapTimer) {
            onsetGapTimer = setTimeout(() => {
              onsetGapTimer = null;
              clearTimeout(speechOnsetTimer); speechOnsetTimer = null;
            }, ONSET_GAP_MS);
          }
        } else {
          clearTimeout(onsetGapTimer); onsetGapTimer = null;
        }
      } else if (vState === VS.RECORDING) {
        if (rms > SPEECH_THRESHOLD) {
          clearTimeout(silenceTimer); silenceTimer = null;
        } else if (!silenceTimer) {
          silenceTimer = setTimeout(() => {
            if (vState === VS.RECORDING) finishCapture();
          }, SILENCE_MS);
        }
      } else if (vState === VS.SPEAKING && rms > INTERRUPT_THRESHOLD) {
        interruptAndListen();
      }
      vadRafId = requestAnimationFrame(tick);
    }
    vadRafId = requestAnimationFrame(tick);
  }

  function interruptAndListen() {
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    clearTimeout(silenceTimer); silenceTimer = null;
    startCapture();
  }

  // ── Recording ────────────────────────────────────────────────────
  function startCapture() {
    const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus' : 'audio/ogg;codecs=opus';
    recorder = new MediaRecorder(micStream, { mimeType: mime });
    chunks = []; speechStart = Date.now();
    recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
    recorder.start(100);
    setVoiceState(VS.RECORDING);
  }

  async function finishCapture() {
    clearTimeout(silenceTimer); silenceTimer = null;
    if (!recorder || recorder.state === 'inactive') return;
    const elapsed = Date.now() - speechStart;

    if (elapsed < MIN_SPEECH_MS) {
      recorder.stop(); chunks = [];
      if (voiceModeActive) setVoiceState(VS.LISTENING);
      return;
    }

    if (voiceModeActive) setVoiceState(VS.PROCESSING);
    await new Promise(resolve => { recorder.onstop = resolve; recorder.stop(); });
    const blob = new Blob(chunks, { type: recorder.mimeType });
    chunks = [];

    if (!voiceModeActive) return;

    try {
      const transcript = await transcribeAudio(blob);
      if (!transcript.trim() || !voiceModeActive) { rearmVoice(); return; }

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
      if (voiceModeActive) vEls.status.textContent = 'Greška: ' + err.message;
    }
    if (voiceModeActive) rearmVoice(true);  // cool-down nakon TTS
  }

  async function rearmVoice(afterTts = false) {
    if (!voiceModeActive) return;
    if (afterTts) {
      // Čekaj da reverb zvučnika utihne prije nego se ponovo sluša
      clearTimeout(speechOnsetTimer); speechOnsetTimer = null;
      clearTimeout(onsetGapTimer);    onsetGapTimer = null;
      await new Promise(r => setTimeout(r, TTS_COOLDOWN_MS));
      if (!voiceModeActive) return;
    }
    setVoiceState(VS.LISTENING);
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
      // Fallback na browser TTS
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
    const overlay = document.getElementById('bl-voice-overlay');
    overlay.classList.add('open');
    conversationStarted = false;
    vEls.panel.className = 'vp-idle';
    vEls.trans.innerHTML = '';
    vEls.status.textContent = 'Zahtijevam pristup mikrofonu...';
    vEls.orb.className = 'orb-idle';
    vEls.orb.textContent = '🎤';
    vEls.largOrb.className = 'orb-idle';
    vEls.largOrb.textContent = '🎤';
    vEls.orbLabel.textContent = 'Inicijalizacija mikrofona...';

    voiceModeActive = true;
    try {
      await openMic();
      setVoiceState(VS.LISTENING);
      startVad();
    } catch (err) {
      vEls.orb.textContent = '⚠';
      vEls.orb.className = 'orb-idle';

      if (err.message === 'NIJE_SECURE_CONTEXT') {
        vEls.status.textContent = 'Browser blokira mikrofon';
        vEls.trans.innerHTML =
          '<div class="bl-vt-msg bl-vt-ai" style="font-size:12px;line-height:1.7">' +
          '<strong>Chrome fix:</strong><br>' +
          'Otvori <code style="background:rgba(255,255,255,.15);padding:1px 5px;border-radius:3px">chrome://flags/#unsafely-treat-insecure-origin-as-secure</code><br>' +
          'Dodaj <code style="background:rgba(255,255,255,.15);padding:1px 5px;border-radius:3px">' + location.origin + '</code> → Relaunch<br><br>' +
          '<strong>Firefox:</strong> localhost radi bez izmjena.<br><br>' +
          'Ili koristi <a href="/public/voice.html" target="_blank" ' +
          'style="color:#fed1bb;font-weight:700">Voice Asistent (novi tab)</a>' +
          '</div>';
      } else if (err.name === 'NotAllowedError') {
        vEls.status.textContent = 'Dozvola odbijena — odobri mikrofon u browseru';
      } else {
        vEls.status.textContent = 'Mikrofon nedostupan: ' + err.message;
      }
    }
  }

  function closeVoiceMode() {
    voiceModeActive = false;
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    clearTimeout(silenceTimer); silenceTimer = null;
    clearTimeout(speechOnsetTimer); speechOnsetTimer = null;
    clearTimeout(onsetGapTimer); onsetGapTimer = null;
    cancelAnimationFrame(vadRafId);
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    closeMic();
    setVoiceState(VS.IDLE);
    document.getElementById('bl-voice-overlay').classList.remove('open');
  }

  // ── Widget events ────────────────────────────────────────────────
  document.getElementById('bl-launcher').addEventListener('click', function () {
    const win = document.getElementById('bl-window');
    const isOpen = win.classList.toggle('open');
    this.textContent = isOpen ? '✕' : '💬';
    if (isOpen && !chatOpened) {
      chatOpened = true;
      addMsg('Pozdrav! Ja sam BitLab AI Asistent. Tu sam za bilo koju temu vezanu za naš webshop — proizvodi, dostava, garancija ili kontakt.', 'bot');
    }
    if (isOpen) document.getElementById('bl-input').focus();
  });

  document.getElementById('bl-close').addEventListener('click', function () {
    document.getElementById('bl-window').classList.remove('open');
    document.getElementById('bl-launcher').textContent = '💬';
  });

  document.getElementById('bl-send').addEventListener('click', function () {
    const inp = document.getElementById('bl-input');
    const text = inp.value.trim();
    if (!text) return;
    inp.value = '';
    addMsg(text, 'user');
    sendMessage(text);
  });

  document.getElementById('bl-input').addEventListener('keypress', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      document.getElementById('bl-send').click();
    }
  });

  document.getElementById('bl-voice-btn').addEventListener('click', () => openVoiceMode());

  document.getElementById('bl-voice-close-btn').addEventListener('click', () => closeVoiceMode());
  document.getElementById('bl-vstop').addEventListener('click', () => closeVoiceMode());

})();
