// SPEACE Anemos — Client JS per UI chat

const API = '';  // path relativo
let ws = null;

// ── API wrapper ──────────────────────────────────────────────────────
async function api(path, opts = {}) {
  try {
    const res = await fetch(`${API}${path}`, {
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      ...opts,
    });
    if (!res.ok) {
      const err = await res.text();
      return { error: `HTTP ${res.status}: ${err}` };
    }
    return await res.json();
  } catch (e) {
    console.error('API error:', e);
    return { error: e.message };
  }
}

// ── Helpers ──────────────────────────────────────────────────────────
function escapeHtml(text) {
  if (text == null) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatSize(bytes) {
  if (bytes === 0) return '';
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}K`;
  return `${(bytes / 1024 / 1024).toFixed(1)}M`;
}

function formatDate(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

// Markdown minimo (solo **bold**, `code`, e ```blocchi```)
function renderMarkdown(text) {
  if (!text) return '';
  let html = escapeHtml(text);
  // Code blocks ```...```
  html = html.replace(/```([\s\S]*?)```/g, '<pre>$1</pre>');
  // Inline code `...`
  html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
  // Bold **...**
  html = html.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
  return html;
}

// ── Status ───────────────────────────────────────────────────────────
async function loadStatus() {
  const data = await api('/api/anemos/status');
  if (data.error) {
    document.getElementById('systemStatus').textContent = 'Offline';
    document.getElementById('systemStatus').className = 'stat-value status-error';
    return;
  }
  const cfg = data.agent?.config || {};
  document.getElementById('modelName').textContent = cfg.model || 'N/A';
  document.getElementById('msgCount').textContent = data.agent?.history?.in_memory_messages || 0;
}

// ── History ──────────────────────────────────────────────────────────
async function loadHistory() {
  const container = document.getElementById('chatMessages');
  const data = await api('/api/anemos/history?n=100');
  if (data.error) {
    container.innerHTML = `<div class="chat-placeholder">Errore: ${escapeHtml(data.error)}</div>`;
    return;
  }
  if (!data.entries || data.entries.length === 0) {
    container.innerHTML = `<div class="chat-placeholder">
      <p>👋 Ciao Roberto! Sono <strong>SPEACE Anemos</strong>, il principio vitale dell'organismo SPEACE.</p>
      <p style="margin-top:12px;font-size:0.9em;">Modello: <strong>Kimi-K2.7-Code:cloud</strong></p>
      <p style="margin-top:8px;font-size:0.85em;color:var(--text-dim);">
        Posso leggere e analizzare il codice, modificare file con la tua conferma,
        e dialogare con te per far evolvere SPEACE. Cosa vuoi che faccia?
      </p>
    </div>`;
    return;
  }
  container.innerHTML = '';
  for (const entry of data.entries) {
    appendMessage(entry.role, entry.content, entry.ts, false);
  }
  scrollChatToBottom();
}

function appendMessage(role, content, ts, scroll = true) {
  const container = document.getElementById('chatMessages');
  // Rimuovi placeholder se presente
  const ph = container.querySelector('.chat-placeholder');
  if (ph) ph.remove();

  const div = document.createElement('div');
  const isError = content.startsWith('ERRORE') || content.includes('❌');
  div.className = `message ${role === 'user' ? 'user' : (isError ? 'error' : 'anemos')}`;

  const time = formatDate(ts) || new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
  const badgeText = role === 'user' ? 'Roberto' : 'Anemos';
  const badgeClass = role === 'user' ? 'user-badge' : 'anemos-badge';

  div.innerHTML = `
    <div class="meta">
      <span class="badge ${badgeClass}">${badgeText}</span>
      <span>${time}</span>
    </div>
    <div class="content">${renderMarkdown(content)}</div>
  `;
  container.appendChild(div);
  if (scroll) scrollChatToBottom();
}

function scrollChatToBottom() {
  const container = document.getElementById('chatMessages');
  container.scrollTop = container.scrollHeight;
}

// ── Chat send ────────────────────────────────────────────────────────
async function sendMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  if (!message) return;

  // Mostra subito il messaggio utente
  const ts = new Date().toISOString();
  appendMessage('user', message, ts);
  input.value = '';

  // Indicatore typing
  const typing = document.getElementById('typingIndicator');
  typing.classList.add('active');

  // Invia al backend
  const data = await api('/api/anemos/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  });

  typing.classList.remove('active');

  if (data.error) {
    appendMessage('assistant', `❌ Errore: ${data.error}`, null, true);
    document.getElementById('systemStatus').textContent = 'Errore';
    document.getElementById('systemStatus').className = 'stat-value status-error';
    return;
  }

  // Mostra risposta
  let html = renderMarkdown(data.answer || '');
  if (data.actions_executed && data.actions_executed.length > 0) {
    html += `<div class="action-executed">✅ ${data.actions_executed.length} azione/i eseguita/e:`;
    html += '<ul style="margin:4px 0 0 16px;padding:0;">';
    for (const a of data.actions_executed) {
      html += `<li><code>${escapeHtml(a.type)}</code> su <code>${escapeHtml(a.path)}</code></li>`;
    }
    html += '</ul></div>';
  }
  if (data.actions_failed && data.actions_failed.length > 0) {
    html += `<div class="action-failed">⚠️ ${data.actions_failed.length} azione/i fallita/e:`;
    html += '<ul style="margin:4px 0 0 16px;padding:0;">';
    for (const a of data.actions_failed) {
      html += `<li><code>${escapeHtml(a.type)}</code> su <code>${escapeHtml(a.path)}</code>: ${escapeHtml(a.error || '')}</li>`;
    }
    html += '</ul></div>';
  }
  html += `<div class="meta" style="margin-top:6px;font-size:0.7em;color:var(--text-dim);">${data.model} • ${data.duration_sec}s</div>`;

  const container = document.getElementById('chatMessages');
  const ph = container.querySelector('.chat-placeholder');
  if (ph) ph.remove();
  const div = document.createElement('div');
  div.className = 'message anemos';
  div.innerHTML = `
    <div class="meta">
      <span class="badge anemos-badge">Anemos</span>
      <span>${new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}</span>
    </div>
    <div>${html}</div>
  `;
  container.appendChild(div);
  scrollChatToBottom();
  loadStatus();  // aggiorna contatore
}

// ── Filesystem browser ──────────────────────────────────────────────
async function listFiles(path, recursive = false, pattern = null) {
  const params = new URLSearchParams({ path });
  if (recursive) params.set('recursive', 'true');
  if (pattern) params.set('pattern', pattern);
  const data = await api(`/api/anemos/files?${params}`);
  const container = document.getElementById('fsResults');
  if (data.error) {
    container.innerHTML = `<div class="fs-placeholder">Errore: ${escapeHtml(data.error)}</div>`;
    return;
  }
  if (!data.items || data.items.length === 0) {
    container.innerHTML = `<div class="fs-placeholder">Directory vuota</div>`;
    return;
  }
  container.innerHTML = '';
  for (const item of data.items.slice(0, 200)) {
    const div = document.createElement('div');
    div.className = `fs-item ${item.blocked ? 'blocked' : ''}`;
    const icon = item.is_dir ? '📁' : '📄';
    const name = item.path.split('/').pop() || item.path;
    div.innerHTML = `
      <span class="icon">${icon}</span>
      <span class="name" title="${escapeHtml(item.path)}">${escapeHtml(name)}${item.blocked ? ' 🔒' : ''}</span>
      <span class="size">${item.is_dir ? '' : formatSize(item.size)}</span>
    `;
    if (!item.blocked) {
      div.addEventListener('click', () => {
        if (item.is_dir) {
          document.getElementById('fsPath').value = item.path;
          listFiles(item.path);
        } else {
          readFile(item.path);
        }
      });
    }
    container.appendChild(div);
  }
  if (data.items.length > 200) {
    const more = document.createElement('div');
    more.className = 'fs-placeholder';
    more.textContent = `... e altri ${data.items.length - 200} elementi`;
    container.appendChild(more);
  }
}

async function readFile(path) {
  const data = await api(`/api/anemos/files/read?path=${encodeURIComponent(path)}`);
  if (data.error) {
    alert(`Errore: ${data.error}`);
    return;
  }
  document.getElementById('fileModalTitle').textContent = `📄 ${path}`;
  document.getElementById('fileModalContent').textContent = data.content;
  document.getElementById('fileModal').dataset.path = path;
  document.getElementById('fileModal').classList.add('active');
}

// ── Audit log ────────────────────────────────────────────────────────
async function showAudit() {
  const data = await api('/api/anemos/audit?n=50');
  if (data.error) {
    alert(`Errore: ${data.error}`);
    return;
  }
  const text = (data.entries || []).map(e =>
    `[${e.ts}] ${e.operation.toUpperCase()} ${e.path} → ${e.success ? 'OK' : 'FAIL'} ${e.details?.error ? '(' + e.details.error + ')' : ''}`
  ).join('\n');
  document.getElementById('auditModalContent').textContent = text || '(nessuna entry)';
  document.getElementById('auditModal').classList.add('active');
}

// ── Clear history ────────────────────────────────────────────────────
async function clearHistory() {
  if (!confirm('Cancellare TUTTA la cronologia chat con Anemos? Questa azione è irreversibile.')) {
    return;
  }
  const data = await api('/api/anemos/history?confirm=yes', { method: 'DELETE' });
  if (data.error) {
    alert(`Errore: ${data.error}`);
    return;
  }
  document.getElementById('chatMessages').innerHTML = '<div class="chat-placeholder">Cronologia cancellata. Inizia un nuovo dialogo con Anemos.</div>';
  loadStatus();
}

// ── WebSocket ────────────────────────────────────────────────────────
function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/anemos`;
  ws = new WebSocket(wsUrl);
  ws.onopen = () => console.log('WS Anemos connesso');
  ws.onclose = () => {
    console.log('WS Anemos disconnesso, riprovo tra 3s');
    setTimeout(connectWebSocket, 3000);
  };
  ws.onerror = (e) => console.error('WS error:', e);
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      console.log('WS msg:', msg);
    } catch (e) {
      console.error('WS parse error:', e);
    }
  };
}

// ── Init ─────────────────────────────────────────────────────────────
async function init() {
  await loadStatus();
  await loadHistory();
  connectWebSocket();

  // Chat input
  const input = document.getElementById('chatInput');
  document.getElementById('chatSendBtn').addEventListener('click', sendMessage);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // FS sidebar
  document.getElementById('fsListBtn').addEventListener('click', () => {
    listFiles(document.getElementById('fsPath').value);
  });
  document.getElementById('fsRootBtn').addEventListener('click', () => {
    document.getElementById('fsPath').value = '.';
    listFiles('.');
  });
  document.getElementById('fsPath').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') listFiles(e.target.value);
  });

  // Top actions
  document.getElementById('reloadHistoryBtn').addEventListener('click', loadHistory);
  document.getElementById('auditBtn').addEventListener('click', showAudit);
  document.getElementById('clearHistoryBtn').addEventListener('click', clearHistory);

  // Modal close
  document.querySelectorAll('.modal-close').forEach(el => {
    el.addEventListener('click', () => {
      const modalId = el.dataset.modal;
      if (modalId) document.getElementById(modalId).classList.remove('active');
    });
  });
  document.getElementById('fileModalCopyBtn').addEventListener('click', () => {
    const text = document.getElementById('fileModalContent').textContent;
    navigator.clipboard.writeText(text).then(() => {
      const btn = document.getElementById('fileModalCopyBtn');
      btn.textContent = '✅ Copiato';
      setTimeout(() => { btn.textContent = 'Copia'; }, 1500);
    });
  });
}

init();
