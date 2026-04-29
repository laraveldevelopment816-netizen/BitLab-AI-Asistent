/**
 * BitLab AI Chat Widget — embeddable
 * Integracija: <script src="http://localhost:8000/public/widget.js"></script>
 *
 * Opciono: window.BITLAB_API = 'https://moj-server.ngrok.io' (default: isto origin)
 */
(function () {
  'use strict';

  const API_BASE = (window.BITLAB_API || '').replace(/\/$/, '') || '';
  const CHAT_URL = API_BASE + '/api/chat';

  // ── CSS ────────────────────────────────────────────────────────
  const css = `
#bl-launcher {
  position: fixed; bottom: 24px; right: 24px;
  width: 60px; height: 60px; border-radius: 50%;
  background: linear-gradient(135deg, #FB923C, #C2410C);
  color: white; border: none; font-size: 28px;
  cursor: pointer; z-index: 9999;
  box-shadow: 0 6px 20px rgba(251,146,60,.45);
  transition: transform .2s;
}
#bl-launcher:hover { transform: scale(1.08); }

#bl-window {
  position: fixed; bottom: 96px; right: 24px;
  width: 360px; max-height: 540px;
  background: #fff; border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0,0,0,.18);
  display: none; flex-direction: column; overflow: hidden;
  z-index: 9999; font-family: -apple-system,"Segoe UI",Roboto,sans-serif;
}
#bl-window.open { display: flex; }

#bl-header {
  background: linear-gradient(135deg, #0F2A47, #1a3d6e);
  color: #fff; padding: 14px 18px;
  display: flex; justify-content: space-between; align-items: center;
}
#bl-header .bl-title { font-weight: 700; font-size: 15px; }
#bl-header .bl-sub { font-size: 11px; opacity: .8; margin-top: 2px; }
#bl-close {
  background: rgba(255,255,255,.15); border: none; color: #fff;
  width: 26px; height: 26px; border-radius: 50%; cursor: pointer; font-size: 14px;
}

#bl-messages {
  flex: 1; overflow-y: auto; padding: 14px;
  background: #F9FAFB; font-size: 14px;
}
.bl-msg {
  margin-bottom: 10px; padding: 10px 13px; border-radius: 12px;
  max-width: 88%; line-height: 1.5; word-break: break-word;
}
.bl-msg.user {
  background: #FB923C; color: #fff;
  margin-left: auto; border-bottom-right-radius: 4px;
}
.bl-msg.bot {
  background: #fff; border: 1px solid #E5E7EB;
  color: #1F2937; border-bottom-left-radius: 4px;
}
.bl-msg.bot a { color: #FB923C; }
.bl-typing { display: flex; gap: 4px; align-items: center; padding: 8px 0; }
.bl-typing span {
  width: 7px; height: 7px; border-radius: 50%; background: #CBD5E1;
  animation: blDot 1.2s infinite ease-in-out;
}
.bl-typing span:nth-child(2) { animation-delay: .2s; }
.bl-typing span:nth-child(3) { animation-delay: .4s; }
@keyframes blDot {
  0%,80%,100% { transform: scale(.7); opacity:.5; }
  40% { transform: scale(1); opacity:1; }
}

#bl-input-area {
  padding: 10px; border-top: 1px solid #E5E7EB;
  background: #fff; display: flex; gap: 8px;
}
#bl-input {
  flex: 1; padding: 9px 13px; border: 1px solid #E5E7EB;
  border-radius: 20px; outline: none; font-size: 14px; font-family: inherit;
}
#bl-input:focus { border-color: #FB923C; }
#bl-send {
  background: #FB923C; color: #fff; border: none;
  border-radius: 50%; width: 38px; height: 38px;
  cursor: pointer; font-size: 16px; flex-shrink: 0;
}
#bl-send:disabled { opacity: .5; cursor: default; }

@media (max-width: 420px) {
  #bl-window { right: 8px; left: 8px; width: auto; bottom: 88px; }
}
`;

  // ── DOM setup ─────────────────────────────────────────────────
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  document.body.insertAdjacentHTML('beforeend', `
<button id="bl-launcher" aria-label="Otvori chat">💬</button>
<div id="bl-window" role="dialog" aria-label="BitLab AI Chat">
  <div id="bl-header">
    <div>
      <div class="bl-title">BitLab Asistent</div>
      <div class="bl-sub">AI pomoćnik &middot; Online</div>
    </div>
    <button id="bl-close" aria-label="Zatvori">&times;</button>
  </div>
  <div id="bl-messages"></div>
  <div id="bl-input-area">
    <input id="bl-input" type="text" placeholder="Postavi pitanje..." autocomplete="off">
    <button id="bl-send">&#10148;</button>
  </div>
</div>
`);

  // ── State ──────────────────────────────────────────────────────
  const history = [];

  // ── Helpers ────────────────────────────────────────────────────
  function renderMarkdown(text) {
    return text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/\n/g, '<br>');
  }

  function addMsg(text, role) {
    const div = document.createElement('div');
    div.className = 'bl-msg ' + role;
    div.innerHTML = role === 'bot' ? renderMarkdown(text) : escHtml(text);
    document.getElementById('bl-messages').appendChild(div);
    scrollBottom();
    return div;
  }

  function escHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
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

  // ── API call ───────────────────────────────────────────────────
  async function sendMessage(text) {
    history.push({ role: 'user', content: text });

    const typing = addTyping();
    document.getElementById('bl-send').disabled = true;

    try {
      const resp = await fetch(CHAT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: history.slice(0, -1),
          channel: 'chat',
        }),
      });

      typing.remove();

      if (!resp.ok) {
        addMsg('Greška servera. Pokušaj ponovo.', 'bot');
        return;
      }

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

  // ── Events ─────────────────────────────────────────────────────
  document.getElementById('bl-launcher').addEventListener('click', function () {
    const win = document.getElementById('bl-window');
    const isOpen = win.classList.toggle('open');
    this.textContent = isOpen ? '✕' : '💬';
    if (isOpen && !history.length) {
      addMsg('Pozdrav! Ja sam BitLab AI Asistent. Pitaj me o proizvodima, dostavi, garanciji ili bilo čemu vezanom za naš webshop.', 'bot');
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
})();
