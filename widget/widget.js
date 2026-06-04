/* ChatSite AI — Embeddable Chat Widget
 * Vanilla JS, Shadow DOM isolation, SSE streaming, no external deps.
 * Target: < 30KB gzipped.
 */
(function () {
  'use strict';

  if (window.ChatSite) return;

  const DEFAULTS = {
    position: 'bottom-right',
    theme: 'light',
    primaryColor: '#4F46E5',
    welcomeMessage: 'Hi! How can I help?',
    suggestedQuestions: [],
    apiBase: 'https://api.chatsite.ai/api/v1',
  };

  const HISTORY_KEY = 'cs.history';
  const SESSION_KEY = 'cs.session';
  const MAX_HISTORY = 50;

  const state = {
    chatbotId: null,
    config: null,
    open: false,
    sessionId: uuid(),
    messages: [],
    streaming: false,
  };

  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function loadHistory() {
    try {
      const raw = localStorage.getItem(HISTORY_KEY + ':' + state.chatbotId);
      if (!raw) return [];
      const arr = JSON.parse(raw);
      return Array.isArray(arr) ? arr.slice(-MAX_HISTORY) : [];
    } catch (_) {
      return [];
    }
  }

  function saveHistory() {
    try {
      localStorage.setItem(
        HISTORY_KEY + ':' + state.chatbotId,
        JSON.stringify(state.messages.slice(-MAX_HISTORY)),
      );
    } catch (_) {}
  }

  function ensureSession() {
    let s = localStorage.getItem(SESSION_KEY + ':' + state.chatbotId);
    if (!s) {
      s = uuid();
      localStorage.setItem(SESSION_KEY + ':' + state.chatbotId, s);
    }
    state.sessionId = s;
  }

  function getConfig() {
    const script = document.currentScript || document.querySelector('script[data-chatsite-id]');
    return new Promise((resolve) => {
      if (script && script.dataset.apiBase) {
        resolve({ ...DEFAULTS, apiBase: script.dataset.apiBase });
        return;
      }
      resolve(DEFAULTS);
    });
  }

  async function track(eventType, data) {
    try {
      await fetch(state.config.apiBase.replace('/api/v1', '') + '/api/v1/analytics/track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chatbot_id: state.chatbotId,
          session_id: state.sessionId,
          event_type: eventType,
          page_url: location.href,
          referrer: document.referrer,
          data: data || {},
        }),
      });
    } catch (_) {}
  }

  function createHost() {
    const host = document.createElement('div');
    host.setAttribute('data-chatsite', '');
    host.style.cssText = 'all:initial;position:fixed;z-index:2147483646;';
    const pos = state.config.position || 'bottom-right';
    host.style[pos.includes('right') ? 'right' : 'left'] = '20px';
    host.style.bottom = '20px';
    document.body.appendChild(host);
    const shadow = host.attachShadow({ mode: 'open' });
    return { host, shadow };
  }

  function styles(theme, primary) {
    return `
      :host { all: initial; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
      .cs-btn {
        width: 56px; height: 56px; border-radius: 50%;
        background: ${primary}; color: #fff; border: none; cursor: pointer;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;
        transition: transform .15s ease;
      }
      .cs-btn:hover { transform: scale(1.05); }
      .cs-btn svg { width: 24px; height: 24px; }
      .cs-panel {
        position: fixed; ${state.config.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
        bottom: 88px; width: 380px; max-width: calc(100vw - 32px);
        height: 560px; max-height: calc(100vh - 120px);
        background: ${theme === 'dark' ? '#0f172a' : '#fff'};
        color: ${theme === 'dark' ? '#f1f5f9' : '#0f172a'};
        border-radius: 16px; box-shadow: 0 24px 60px rgba(0,0,0,0.25);
        display: flex; flex-direction: column; overflow: hidden;
      }
      .cs-header {
        padding: 14px 16px; background: ${primary}; color: #fff;
        display: flex; align-items: center; justify-content: space-between;
      }
      .cs-title { font-weight: 600; }
      .cs-close { background: transparent; border: none; color: #fff; cursor: pointer; font-size: 18px; }
      .cs-body { flex: 1; overflow-y: auto; padding: 12px 16px; }
      .cs-msg { margin: 6px 0; max-width: 85%; }
      .cs-msg.user { margin-left: auto; }
      .cs-bubble {
        display: inline-block; padding: 8px 12px; border-radius: 12px; line-height: 1.4; font-size: 14px;
        word-wrap: break-word; white-space: pre-wrap;
      }
      .cs-msg.user .cs-bubble { background: ${primary}; color: #fff; border-bottom-right-radius: 2px; }
      .cs-msg.bot .cs-bubble { background: ${theme === 'dark' ? '#1e293b' : '#f1f5f9'}; border-bottom-left-radius: 2px; }
      .cs-sources { font-size: 11px; opacity: 0.7; margin-top: 4px; }
      .cs-sources details summary { cursor: pointer; }
      .cs-sources a { color: inherit; text-decoration: underline; }
      .cs-suggested { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
      .cs-suggested button {
        font-size: 12px; padding: 6px 10px; border-radius: 999px;
        background: ${theme === 'dark' ? '#1e293b' : '#eef2ff'};
        border: 1px solid ${primary}; color: ${primary}; cursor: pointer;
      }
      .cs-typing { display: inline-flex; gap: 4px; padding: 8px 12px; }
      .cs-typing span {
        width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: 0.4;
        animation: csblink 1.2s infinite;
      }
      .cs-typing span:nth-child(2) { animation-delay: 0.2s; }
      .cs-typing span:nth-child(3) { animation-delay: 0.4s; }
      @keyframes csblink { 0%, 80%, 100% { opacity: 0.2; } 40% { opacity: 1; } }
      .cs-footer { padding: 10px; border-top: 1px solid ${theme === 'dark' ? '#1e293b' : '#e2e8f0'}; }
      .cs-input-row { display: flex; gap: 6px; }
      .cs-input {
        flex: 1; padding: 10px 12px; border-radius: 8px; border: 1px solid ${theme === 'dark' ? '#334155' : '#cbd5e1'};
        background: transparent; color: inherit; font: inherit;
      }
      .cs-send {
        padding: 0 14px; border-radius: 8px; background: ${primary}; color: #fff; border: none; cursor: pointer;
      }
      .cs-send:disabled { opacity: 0.5; cursor: wait; }
      .cs-lead {
        padding: 12px; background: ${theme === 'dark' ? '#1e293b' : '#eef2ff'};
        border-radius: 8px; margin: 8px 0;
      }
      .cs-lead input {
        width: 100%; padding: 6px 8px; margin-top: 4px; border-radius: 6px;
        border: 1px solid ${theme === 'dark' ? '#334155' : '#cbd5e1'};
        background: transparent; color: inherit; font: inherit;
      }
      .cs-lead button { margin-top: 8px; padding: 8px 12px; background: ${primary}; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
      .cs-conf { font-size: 11px; opacity: 0.7; padding: 0 12px 8px; }
      @media (max-width: 480px) {
        .cs-panel { left: 0 !important; right: 0 !important; bottom: 0; width: 100%; height: 100%; max-height: 100vh; border-radius: 0; }
      }
    `;
  }

  function render(shadow) {
    const theme = state.config.theme === 'auto'
      ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      : state.config.theme;
    const primary = state.config.primaryColor;
    shadow.innerHTML = `
      <style>${styles(theme, primary)}</style>
      <button class="cs-btn" aria-label="Open chat">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
      </button>
      ${state.open ? panelHTML() : ''}
    `;
    shadow.querySelector('.cs-btn').addEventListener('click', toggleOpen);
    if (state.open) bindPanel(shadow);
  }

  function panelHTML() {
    return `
      <div class="cs-panel" role="dialog" aria-label="Chat">
        <div class="cs-header">
          <span class="cs-title">Chat</span>
          <button class="cs-close" aria-label="Close">×</button>
        </div>
        <div class="cs-body" id="cs-body"></div>
        <div class="cs-footer">
          <div class="cs-input-row">
            <input class="cs-input" placeholder="Ask a question…" aria-label="Message" />
            <button class="cs-send" aria-label="Send">Send</button>
          </div>
        </div>
      </div>
    `;
  }

  function bindPanel(shadow) {
    shadow.querySelector('.cs-close').addEventListener('click', toggleOpen);
    const input = shadow.querySelector('.cs-input');
    const send = shadow.querySelector('.cs-send');
    const submit = () => {
      const v = input.value.trim();
      if (!v || state.streaming) return;
      input.value = '';
      sendMessage(v, shadow);
    };
    send.addEventListener('click', submit);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    });
    renderBody(shadow);
    if (state.config.suggestedQuestions && state.config.suggestedQuestions.length && !state.messages.length) {
      renderSuggested(shadow);
    }
  }

  function renderBody(shadow) {
    const body = shadow.getElementById('cs-body');
    if (!body) return;
    body.innerHTML = '';
    for (const m of state.messages) {
      const wrap = document.createElement('div');
      wrap.className = `cs-msg ${m.role}`;
      const b = document.createElement('div');
      b.className = 'cs-bubble';
      b.textContent = m.content;
      wrap.appendChild(b);
      if (m.sources && m.sources.length) {
        const s = document.createElement('div');
        s.className = 'cs-sources';
        s.innerHTML = `<details><summary>${m.sources.length} source${m.sources.length === 1 ? '' : 's'}</summary>` +
          m.sources.map((x) => `<div><a href="${x.url}" target="_blank" rel="noopener">${x.title || x.url}</a></div>`).join('') +
          `</details>`;
        wrap.appendChild(s);
      }
      body.appendChild(wrap);
    }
    body.scrollTop = body.scrollHeight;
  }

  function renderSuggested(shadow) {
    const body = shadow.getElementById('cs-body');
    if (!body) return;
    const wrap = document.createElement('div');
    wrap.className = 'cs-suggested';
    for (const q of state.config.suggestedQuestions || []) {
      const b = document.createElement('button');
      b.textContent = q;
      b.addEventListener('click', () => {
        wrap.remove();
        sendMessage(q, shadow);
      });
      wrap.appendChild(b);
    }
    body.appendChild(wrap);
  }

  function appendMessage(shadow, m) {
    state.messages.push(m);
    saveHistory();
    renderBody(shadow);
  }

  function toggleOpen() {
    state.open = !state.open;
    if (state.open) track('widget_opened');
    else track('widget_closed');
    const { shadow } = getHost();
    render(shadow);
  }

  let _host = null;
  function getHost() {
    if (_host) return _host;
    _host = createHost();
    return _host;
  }

  async function sendMessage(text, shadow) {
    const userMsg = { role: 'user', content: text };
    state.messages.push(userMsg);
    saveHistory();
    track('message_sent', { role: 'user' });

    const botMsg = { role: 'bot', content: '', sources: [] };
    state.messages.push(botMsg);
    state.streaming = true;
    renderBody(shadow);

    const body = shadow.getElementById('cs-body');
    if (body) {
      const typing = document.createElement('div');
      typing.className = 'cs-msg bot';
      typing.innerHTML = `<span class="cs-typing"><span></span><span></span><span></span></span>`;
      body.appendChild(typing);
      body.scrollTop = body.scrollHeight;
    }

    try {
      const resp = await fetch(state.config.apiBase + '/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chatbot_id: state.chatbotId,
          session_id: state.sessionId,
          message: text,
          page_url: location.href,
          metadata: { user_agent: navigator.userAgent, referrer: document.referrer },
          history: state.messages.slice(0, -2).map((m) => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.content })),
        }),
      });
      if (!resp.body) throw new Error('No stream');
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      const typing = body && body.querySelector('.cs-typing') ? body.querySelector('.cs-typing').parentElement : null;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';
        for (const ev of events) {
          const line = ev.trim();
          if (!line.startsWith('data:')) continue;
          try {
            const data = JSON.parse(line.slice(5));
            if (data.type === 'meta') {
              botMsg.sources = data.sources || [];
            } else if (data.type === 'token') {
              if (typing) typing.remove();
              botMsg.content += data.delta;
              renderBody(shadow);
            } else if (data.type === 'error') {
              botMsg.content += '\n[error]';
              renderBody(shadow);
            }
          } catch (_) {}
        }
      }
      saveHistory();
      track('message_sent', { role: 'assistant' });
      maybeShowLeadForm(shadow);
    } catch (err) {
      botMsg.content = 'Sorry, something went wrong. Please try again.';
      renderBody(shadow);
    } finally {
      state.streaming = false;
      const sendBtn = shadow.querySelector('.cs-send');
      if (sendBtn) sendBtn.disabled = false;
    }
  }

  function maybeShowLeadForm(shadow) {
    const userMsgCount = state.messages.filter((m) => m.role === 'user').length;
    const existing = shadow.querySelector('.cs-lead');
    if (existing) return;
    if (userMsgCount >= 3) {
      const body = shadow.getElementById('cs-body');
      if (!body) return;
      const wrap = document.createElement('div');
      wrap.className = 'cs-lead';
      wrap.innerHTML = `
        <div>Want updates? Drop your email:</div>
        <input class="cs-lead-email" type="email" placeholder="you@example.com" />
        <button class="cs-lead-submit">Notify me</button>
      `;
      body.appendChild(wrap);
      wrap.querySelector('.cs-lead-submit').addEventListener('click', async () => {
        const email = wrap.querySelector('.cs-lead-email').value;
        if (!email) return;
        try {
          await fetch(state.config.apiBase + '/leads', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              chatbot_id: state.chatbotId,
              session_id: state.sessionId,
              email,
              source_page_url: location.href,
            }),
          });
          track('lead_captured', { email });
          wrap.remove();
        } catch (_) {}
      });
    }
  }

  async function init(config) {
    state.config = { ...DEFAULTS, ...(config || {}) };
    if (config && config.chatbotId) state.chatbotId = config.chatbotId;
    if (!state.chatbotId) {
      const script = document.currentScript || document.querySelector('script[data-chatsite-id]');
      if (script && script.dataset.chatsiteId) state.chatbotId = script.dataset.chatsiteId;
    }
    if (!state.chatbotId) {
      console.warn('[ChatSite] chatbotId missing');
      return;
    }
    ensureSession();
    state.messages = loadHistory();
    const { shadow } = getHost();
    render(shadow);
    track('page_view');

    document.addEventListener('mouseleave', (e) => {
      if (e.clientY < 0) maybeShowLeadForm(shadow);
    });
  }

  window.ChatSite = { init };
})();
