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
      avatar.classList.add('avatar-bot');
    } else {
      avatar.classList.add('avatar-user');
    }
    const bubble = ce('div', 'max-w-[80%] rounded-xl border px-3 py-2 text-sm break-words');
    if (sender === 'bot') { bubble.classList.add('bubble-bot'); }
    else { bubble.classList.add('bubble-user'); }
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
    const avatar = ce('div', 'w-8 h-8 rounded-full grid place-items-center text-sm font-medium avatar-bot'); avatar.textContent = 'Y';
    const bubble = ce('div', 'max-w-[80%] rounded-xl border px-3 py-2 text-sm bubble-bot');
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
    if (info.risk_detected) { window.UI.showCrisisPopup && window.UI.showCrisisPopup(); }
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
  // Email/password login removed; only OAuth is supported.

  // Supabase OAuth (Google/Apple)
  let supabase = null;
  const initSupabase = () => {
    try {
      // Prefer explicit global config if available
      if (window.SUPABASE?.url && window.SUPABASE?.key && window.supabase) {
        supabase = window.supabase.createClient(window.SUPABASE.url, window.SUPABASE.key);
        return;
      }
      // Fallback: read from meta tags (works with strict CSP)
      const urlEl = document.querySelector('meta[name="supabase-url"]');
      const keyEl = document.querySelector('meta[name="supabase-key"]');
      if (urlEl && keyEl && window.supabase) {
        supabase = window.supabase.createClient(urlEl.content, keyEl.content);
      }
    } catch {}
  };

  // User display helpers
  const cap = (s) => s ? (s[0].toUpperCase() + s.slice(1).toLowerCase()) : '';
  const firstNameFromEmail = (email) => {
    if (!email || !email.includes('@')) return '';
    const local = email.split('@')[0];
    const parts = local.split(/[._\-+]+/).filter(Boolean);
    const raw = parts[0] || '';
    const onlyLetters = raw.replace(/[^A-Za-z]/g, '');
    return cap(onlyLetters || raw);
  };
  const firstNameFromUser = (user) => {
    try {
      const meta = user?.user_metadata || {};
      const gn = meta.given_name || meta.first_name;
      if (gn && typeof gn === 'string') return cap(gn);
      const full = meta.name || meta.full_name;
      if (full && typeof full === 'string') return cap(full.split(/\s+/)[0] || '');
      const email = user?.email;
      const fromEmail = firstNameFromEmail(email);
      return fromEmail || '';
    } catch { return ''; }
  };
  const setUserHeader = (firstName) => {
    const wrap = qs('#userDisplay'); const span = qs('#userFirstName');
    if (!wrap || !span) return;
    if (firstName) { span.textContent = firstName; wrap.classList.remove('hidden'); }
    else { wrap.classList.add('hidden'); span.textContent=''; }
  };
  const loginWithProvider = async (provider) => {
    if (!supabase) { alert('Auth not configured'); return; }
    const redirectTo = window.location.origin + '/';
    const { error } = await supabase.auth.signInWithOAuth({ provider, options: { redirectTo } });
    if (error) alert(error.message || 'Sign-in failed');
  };
  const attachOAuthHandlers = () => {
    const g = qs('#googleLoginBtn'); if (g) g.onclick = () => loginWithProvider('google');
  };
  const restoreSupabaseSession = async () => {
    if (!supabase) return false;
    try {
      const { data } = await supabase.auth.getSession();
      const token = data?.session?.access_token;
      if (token) {
        API.setToken(token);
        qs('#authBtnText').textContent = 'Signed in';
        const so = qs('#signOutBtn'); if (so) so.classList.remove('hidden');
        const user = data?.session?.user;
        const fn = firstNameFromUser(user);
        setUserHeader(fn);
        return true;
      }
      return false;
    } catch { return false; }
  };

  const signOut = async () => {
    try { if (supabase) await supabase.auth.signOut(); } catch {}
    API.setToken('');
    localStorage.removeItem('session_id');
    sessionId = null;
    qs('#authBtnText').textContent = 'Sign in';
    const so = qs('#signOutBtn'); if (so) so.classList.add('hidden');
    setUserHeader('');
    openAuth();
  };

  // Crisis popup controls
  const showCrisisPopup = () => { const m = qs('#crisisPopup'); if (!m) return; m.classList.remove('hidden'); m.style.display='flex'; m.setAttribute('aria-hidden','false'); };
  const hideCrisisPopup = () => { const m = qs('#crisisPopup'); if (!m) return; m.classList.add('hidden'); m.style.display='none'; m.setAttribute('aria-hidden','true'); };
  const confirmContinueChat = () => {
    const ok = confirm('Are you sure you want to continue chatting?');
    if (ok) hideCrisisPopup(); else showCrisisPopup();
  };

  // Public UI helpers
  window.UI = {
    sendMessage,
    sendQuick: (text)=>{ els.input.value = text; sendMessage(); },
    showHelp: ()=>{ const m=qs('#helpModal'); m.classList.remove('hidden'); m.style.display='flex'; m.setAttribute('aria-hidden','false'); },
    hideHelp: ()=>{ const m=qs('#helpModal'); m.classList.add('hidden'); m.style.display='none'; m.setAttribute('aria-hidden','true'); },
    toggleDebugPanel: ()=>{ const p=qs('#debugPanel'); const i=qs('#debugToggleIcon'); p.classList.toggle('collapsed'); i.className=p.classList.contains('collapsed')?'bi bi-chevron-left':'bi bi-chevron-right'; },
    openAuth, closeAuth,
    signOut,
    newChat: async ()=>{ localStorage.removeItem('session_id'); sessionId=null; await ensureSession(); await loadHistory(); },
    openHistory: async ()=>{ const d=qs('#historyDrawer'); if (d){ d.classList.remove('hidden'); await loadSessions(); } },
    closeHistory: ()=>{ const d=qs('#historyDrawer'); if (d){ d.classList.add('hidden'); } },
    showCrisisPopup, confirmContinueChat
  };

  // Init
  document.addEventListener('DOMContentLoaded', async () => {
    try { document.title = 'Yarn Chat — Experimental Frontend'; } catch {}
    els.chat = qs('#chatMessages'); els.input = qs('#messageInput'); els.send = qs('#sendBtn');
    attachOAuthHandlers();
    initSupabase();
    els.send.addEventListener('click', sendMessage);
    els.input.addEventListener('keypress', (e)=>{ if (e.key==='Enter' && !e.shiftKey){ e.preventDefault(); sendMessage(); }});

    // Token/session restore
    let token = localStorage.getItem('token'); if (token) API.setToken(token);
    // Try restore from Supabase session
    const restored = await restoreSupabaseSession();
    if (restored) token = localStorage.getItem('token');
    // If token exists but no Supabase user loaded (legacy token), try to fetch user anyway
    if (token && supabase) {
      try { const { data: u } = await supabase.auth.getUser(); const fn = firstNameFromUser(u?.user); setUserHeader(fn); } catch {}
    }
    sessionId = localStorage.getItem('session_id');

    // Health check and environment chip
    const envEl = qs('#envChip');
    if (envEl) {
      try {
        const h = await API.health(); envEl.textContent = `API: ${API.base} (${h.status||'?'})`;
      } catch { envEl.textContent = `API: ${API.base} (offline)`; }
    }

    // Normalize brand chip text in header if it contains placeholder glyphs
    try {
      const brand = document.querySelector('header .grid.place-items-center.text-neutral-900.font-bold');
      if (brand) brand.textContent = 'Y';
    } catch {}

    if (localStorage.getItem('token')) {
      qs('#authBtnText').textContent = 'Signed in';
      const so = qs('#signOutBtn'); if (so) so.classList.remove('hidden');
      try { if (!sessionId) await ensureSession(); await loadHistory(); } catch {}
    } else {
      openAuth();
    }
  });
})();
