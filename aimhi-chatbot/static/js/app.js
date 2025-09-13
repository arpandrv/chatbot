(function(){
  // State
  let sessionId = null;
  let typingEl = null;
  const els = {};

  const qs = (sel) => document.querySelector(sel);
  const ce = (tag, cls) => { const e = document.createElement(tag); if (cls) e.className = cls; return e; };

  const renderMessage = (sender, text, isHTML=false) => {
    const row = ce('div', 'flex gap-3 items-start');
    if (sender === 'user') row.classList.add('justify-end');
    const avatar = ce('div', 'w-8 h-8 rounded-full grid place-items-center text-sm font-medium');
    avatar.textContent = sender === 'bot' ? 'Y' : 'You';
    if (sender === 'bot') {
      avatar.classList.add('bg-gradient-to-br','from-primary','to-accent','text-white');
    } else {
      avatar.classList.add('bg-neutral-300');
    }
    const bubble = ce('div', 'max-w-[80%] rounded-xl border px-3 py-2 text-sm break-words');
    if (sender === 'bot') { bubble.classList.add('bg-white','border-neutral-200','text-neutral-900'); }
    else { bubble.classList.add('bg-primary/10','border-blue-200','text-neutral-900'); }
    const p = ce('p');
    if (isHTML) p.innerHTML = text; else p.textContent = text;
    bubble.appendChild(p);
    if (sender === 'bot') { row.appendChild(avatar); row.appendChild(bubble); }
    else { row.appendChild(bubble); row.appendChild(avatar); }
    els.chat.appendChild(row);
    els.chat.scrollTop = els.chat.scrollHeight;
  };

  const showTyping = () => {
    if (typingEl) return; typingEl = ce('div', 'flex gap-3 items-start'); typingEl.id='typing';
    const avatar = ce('div', 'w-8 h-8 rounded-full grid place-items-center text-sm font-medium bg-gradient-to-br from-primary to-accent text-white'); avatar.textContent = 'Y';
    const bubble = ce('div', 'max-w-[80%] rounded-xl border px-3 py-2 text-sm bg-white border-neutral-200');
    const dots = ce('div', 'flex gap-1 items-center');
    for (let i=0;i<3;i++){ const d=ce('span','inline-block w-2 h-2 rounded-full bg-neutral-400'); d.style.opacity = String(0.4 + i*0.2); dots.appendChild(d); }
    bubble.appendChild(dots); typingEl.appendChild(avatar); typingEl.appendChild(bubble);
    els.chat.appendChild(typingEl); els.chat.scrollTop = els.chat.scrollHeight;
  };
  const hideTyping = () => { if (typingEl && typingEl.parentNode) typingEl.parentNode.removeChild(typingEl); typingEl = null; };

  const updateDebug = (info={}) => {
    const safe = (v) => v ?? '-';
    const set = (id, val) => { const el = qs('#'+id); if (el){ el.textContent = val; el.classList.add('updated'); setTimeout(()=>el.classList.remove('updated'),500);} };
    set('fsmState', safe(info.fsm_state));
    if (info.intent_classification) {
      const ic = info.intent_classification;
      set('intentInfo', `Intent: ${ic.detected_intent||'unknown'} | Conf: ${ic.confidence? (ic.confidence*100).toFixed(1)+'%':'N/A'}`);
    }
    set('responseSource', safe(info.response_source));
    set('userSentiment', safe(info.user_sentiment));
    set('fallbackInfo', info.fallback_triggered ? `Triggered (Attempt ${info.attempt_count||1})` : 'Not triggered');
    set('riskDetection', info.risk_detected ? 'Risk detected' : 'No risk');
  };

  const setBusy = (busy) => {
    els.input.disabled = busy; els.send.disabled = busy;
  };

  const renderSessionItem = (s) => {
    const btn = ce('button', 'w-full text-left px-3 py-2 rounded-md hover:bg-neutral-100');
    const ts = new Date(s.last_activity || s.created_at || Date.now());
    btn.innerHTML = `<div class="text-sm font-medium">${(s.fsm_state||'welcome')}</div><div class="text-[11px] text-neutral-400">${ts.toLocaleString()}</div>`;
    btn.onclick = async () => { sessionId = s.session_id; localStorage.setItem('session_id', sessionId); await loadHistory(); };
    return btn;
  };

  const loadSessions = async () => {
    try{
      const cont = document.querySelector('#sessionList');
      if (!cont) return; // Sidebar not present in this layout
      const list = await API.listSessions(20);
      cont.innerHTML = '';
      for (const s of list) cont.appendChild(renderSessionItem(s));
    } catch (e){ /* ignore */ }
  };

  const ensureSession = async () => {
    if (sessionId) return sessionId;
    const res = await API.createSession('welcome');
    sessionId = res.session_id; localStorage.setItem('session_id', sessionId);
    await loadSessions();
    return sessionId;
  };

  const loadHistory = async () => {
    if (!sessionId) return;
    const msgs = await API.getMessages(sessionId, 50);
    els.chat.innerHTML = '';
    for (const m of msgs){ renderMessage(m.role === 'bot' ? 'bot' : 'user', m.message || ''); }
  };

  async function sendMessage(){
    const msg = els.input.value.trim(); if (!msg) return;
    renderMessage('user', msg); els.input.value=''; setBusy(true); qs('#quickActions')?.style && (qs('#quickActions').style.display='none');
    showTyping();
    try{
      await ensureSession();
      const data = await API.sendMessage(sessionId, msg);
      hideTyping();
      renderMessage('bot', data.reply || '...');
      updateDebug(data.debug || {});
    } catch (e){
      hideTyping(); renderMessage('bot', e?.data?.error || e.message || 'Error');
      if (e.status === 401){ localStorage.removeItem('token'); window.UI.openAuth(); }
    } finally{ setBusy(false); els.input.focus(); }
  }

  // Auth UI
  const openAuth = () => { const m = qs('#authModal'); m.classList.remove('hidden'); m.style.display = 'flex'; m.setAttribute('aria-hidden','false');
    qs('#apiBaseDisplay').textContent = API.base; };
  const closeAuth = () => { const m = qs('#authModal'); m.classList.add('hidden'); m.style.display = 'none'; m.setAttribute('aria-hidden','true'); };
  const onLogin = async (e) => {
    e.preventDefault();
    const email = qs('#authEmail').value.trim(); const password = qs('#authPassword').value;
    try{
      const res = await API.login(email, password);
      const token = res.access_token; API.setToken(token);
      qs('#authBtnText').textContent = 'Signed in';
      await ensureSession(); await loadHistory(); closeAuth();
    } catch (err){ alert(err?.data?.error || err.message || 'Login failed'); }
  };
  const onRegister = async () => {
    const email = qs('#authEmail').value.trim(); const password = qs('#authPassword').value;
    try{ await API.register(email, password); alert('Registered. You can now sign in.'); }
    catch (err){ alert(err?.data?.error || err.message || 'Registration failed'); }
  };

  // Public UI helpers
  window.UI = {
    sendMessage,
    sendQuick: (text)=>{ els.input.value = text; sendMessage(); },
    showHelp: ()=>{ const m=qs('#helpModal'); m.classList.remove('hidden'); m.style.display='flex'; m.setAttribute('aria-hidden','false'); },
    hideHelp: ()=>{ const m=qs('#helpModal'); m.classList.add('hidden'); m.style.display='none'; m.setAttribute('aria-hidden','true'); },
    toggleDebugPanel: ()=>{ const p=qs('#debugPanel'); const i=qs('#debugToggleIcon'); p.classList.toggle('collapsed'); i.className=p.classList.contains('collapsed')?'bi bi-chevron-left':'bi bi-chevron-right'; },
    openAuth, closeAuth,
    newChat: async ()=>{ localStorage.removeItem('session_id'); sessionId=null; await ensureSession(); await loadHistory(); },
    openHistory: async ()=>{ const d=qs('#historyDrawer'); if (d){ d.classList.remove('hidden'); await loadSessions(); } },
    closeHistory: ()=>{ const d=qs('#historyDrawer'); if (d){ d.classList.add('hidden'); } },
  };

  // Init
  document.addEventListener('DOMContentLoaded', async () => {
    els.chat = qs('#chatMessages'); els.input = qs('#messageInput'); els.send = qs('#sendBtn');
    const authForm = qs('#authForm'); authForm.addEventListener('submit', onLogin); qs('#registerBtn').addEventListener('click', onRegister);
    els.send.addEventListener('click', sendMessage);
    els.input.addEventListener('keypress', (e)=>{ if (e.key==='Enter' && !e.shiftKey){ e.preventDefault(); sendMessage(); }});

    // Token/session restore
    const token = localStorage.getItem('token'); if (token) API.setToken(token);
    sessionId = localStorage.getItem('session_id');

    // Health check and environment chip
    try {
      const h = await API.health(); qs('#envChip').textContent = `API: ${API.base} (${h.status||'?'})`;
    } catch { qs('#envChip').textContent = `API: ${API.base} (offline)`; }

    if (token) {
      qs('#authBtnText').textContent = 'Signed in';
      try { if (!sessionId) await ensureSession(); await loadHistory(); } catch {}
    } else {
      openAuth();
    }
  });
})();
