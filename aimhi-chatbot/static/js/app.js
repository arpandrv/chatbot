(function(){
  // State
  let sessionId = null;
  let typingEl = null;
  const els = {};

  const qs = (sel) => document.querySelector(sel);
  const ce = (tag, cls) => { const e = document.createElement(tag); if (cls) e.className = cls; return e; };

  // Textarea auto-resize helper
  const autoResizeTextarea = (el) => {
    try {
      if (!el) return;
      // Reset height to measure correct scrollHeight
      el.style.height = 'auto';
      const computed = getComputedStyle(el);
      const maxHStr = computed.getPropertyValue('max-height');
      const maxH = maxHStr && maxHStr.endsWith('px') ? parseInt(maxHStr, 10) : null;
      const newH = el.scrollHeight;
      if (maxH && newH > maxH) {
        el.style.overflowY = 'auto';
        el.style.height = maxH + 'px';
      } else {
        el.style.overflowY = 'hidden';
        el.style.height = newH + 'px';
      }
    } catch {}
  };

  const renderMessage = (sender, text, isHTML=false) => {
    const container = ce('div', 'message-container');
    if (sender === 'user') container.classList.add('user');
    
    const avatar = ce('div', 'message-avatar');
    avatar.textContent = sender === 'bot' ? 'Y' : 'U';
    
    if (sender === 'bot') {
      avatar.classList.add('avatar-bot');
    } else {
      avatar.classList.add('avatar-user');
    }
    
    const bubble = ce('div', 'message-bubble');
    if (sender === 'bot') { 
      bubble.classList.add('bubble-bot'); 
    } else { 
      bubble.classList.add('bubble-user'); 
    }
    
    const p = ce('p');
    if (isHTML) {
      p.innerHTML = text;
    } else {
      p.textContent = text;
    }
    bubble.appendChild(p);
    
    if (sender === 'bot') {
      container.appendChild(avatar);
      container.appendChild(bubble);
    } else {
      container.appendChild(bubble);
      container.appendChild(avatar);
    }
    
    // Add animation class
    container.classList.add('animate-slide-in-left');
    
    els.chat.appendChild(container);
    els.chat.scrollTop = els.chat.scrollHeight;
  };

  const showTyping = () => {
    if (typingEl) return;
    
    typingEl = ce('div', 'message-container');
    typingEl.id = 'typing';
    
    const avatar = ce('div', 'message-avatar avatar-bot');
    avatar.textContent = 'Y';
    
    const bubble = ce('div', 'message-bubble bubble-bot');
    const dotsContainer = ce('div', 'typing-dots');
    
    for (let i = 0; i < 3; i++) {
      const dot = ce('span', 'typing-dot');
      dotsContainer.appendChild(dot);
    }
    
    bubble.appendChild(dotsContainer);
    typingEl.appendChild(avatar);
    typingEl.appendChild(bubble);
    
    els.chat.appendChild(typingEl);
    els.chat.scrollTop = els.chat.scrollHeight;
  };
  
  const hideTyping = () => { 
    if (typingEl && typingEl.parentNode) {
      typingEl.parentNode.removeChild(typingEl);
    }
    typingEl = null;
  };

  const updateDebug = (info={}) => {
    // Debug functionality removed for cleaner interface
    if (info.risk_detected) { 
      window.UI.showCrisisPopup && window.UI.showCrisisPopup(); 
    }
    try {
      if (info && (info.fsm_state || info.response_source || info.processing_ms !== undefined)) {
        console.debug('debug:', info);
      }
    } catch {}
  };

  const setBusy = (busy) => {
    els.input.disabled = busy; 
    els.send.disabled = busy;
    
    if (busy) {
      els.send.style.opacity = '0.6';
      els.send.style.cursor = 'not-allowed';
    } else {
      els.send.style.opacity = '1';
      els.send.style.cursor = 'pointer';
    }
  };

  const renderSessionItem = (s) => {
    const row = ce('div', 'flex items-center justify-between gap-2 mb-2');
    const btn = ce('button', 'session-item flex-1 text-left');
    const ts = new Date(s.last_activity || s.created_at || Date.now());

    const title = ce('div', 'session-title');
    title.textContent = s.fsm_state || 'New Chat';

    const time = ce('div', 'session-time');
    time.textContent = ts.toLocaleDateString() + ' ' + ts.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

    btn.appendChild(title);
    btn.appendChild(time);

    btn.onclick = async () => {
      sessionId = s.session_id;
      localStorage.setItem('session_id', sessionId);
      await loadHistory();
      window.UI.closeHistory();
    };

    const delBtn = ce('button', 'px-2 py-2 rounded-lg border border-neutral-300 hover:bg-neutral-50 text-neutral-600');
    delBtn.setAttribute('aria-label', 'Delete chat');
    delBtn.innerHTML = '<i class="bi bi-trash"></i>';
    delBtn.onclick = async (e) => {
      e.stopPropagation();
      const ok = confirm('Delete this chat? This cannot be undone.');
      if (!ok) return;
      try {
        await API.deleteSession(s.session_id);
        // If we deleted the active session, start a new one
        if (sessionId === s.session_id) {
          localStorage.removeItem('session_id');
          sessionId = null;
          await ensureSession();
          await loadHistory();
        }
      } catch (err) {
        console.error('Delete failed', err);
        alert('Could not delete chat.');
      } finally {
        await loadSessions();
      }
    };

    row.appendChild(btn);
    row.appendChild(delBtn);
    return row;
  };

  const loadSessions = async () => {
    try {
      const cont = qs('#sessionList');
      if (!cont) return;
      
      const list = await API.listSessions(20);
      cont.innerHTML = '';
      
      if (list && list.length > 0) {
        for (const s of list) {
          cont.appendChild(renderSessionItem(s));
        }
      } else {
        // Show empty state
        const emptyState = ce('div', 'session-empty-state');
        emptyState.innerHTML = `
          <i class="bi bi-clock-history"></i>
          <p>Your chat history will appear here</p>
        `;
        cont.appendChild(emptyState);
      }
    } catch (e) {
      console.error('Error loading sessions:', e);
      const cont = qs('#sessionList');
      if (cont) {
        cont.innerHTML = '<div class="session-empty-state"><p>Unable to load chat history</p></div>';
      }
    }
  };

  const ensureSession = async () => {
    if (sessionId) return sessionId;
    const res = await API.createSession('welcome');
    sessionId = res.session_id; 
    localStorage.setItem('session_id', sessionId);
    await loadSessions();
    return sessionId;
  };

  const loadHistory = async () => {
    if (!sessionId) return;
    
    try {
      const msgs = await API.getMessages(sessionId, 50);
      
      // Clear chat except welcome message if no messages
      if (!msgs || msgs.length === 0) {
        // Keep welcome message, just clear any existing chat messages
        const existingMessages = els.chat.querySelectorAll('.message-container');
        existingMessages.forEach(msg => msg.remove());
        return;
      }
      
      // Clear all and rebuild with messages
      els.chat.innerHTML = '';
      for (const m of msgs) {
        renderMessage(m.role === 'bot' ? 'bot' : 'user', m.message || '');
      }
    } catch (e) {
      console.error('Error loading history:', e);
    }
  };

  async function sendMessage(){
    const msg = els.input.value.trim(); 
    if (!msg) return;
    
    // Hide welcome message area if it exists
    const welcomeArea = els.chat.querySelector('.max-w-2xl.mx-auto.text-center');
    if (welcomeArea) {
      welcomeArea.style.display = 'none';
    }
    
    renderMessage('user', msg); 
    els.input.value = ''; 
    setBusy(true); 
    
    // Hide quick actions after first message
    const quickActions = qs('#quickActions');
    if (quickActions) {
      quickActions.style.display = 'none';
    }
    
    showTyping();
    
    try {
      await ensureSession();
      const data = await API.sendMessage(sessionId, msg);
      hideTyping();
      renderMessage('bot', data.reply || '...');
      updateDebug(data.debug || {});
    } catch (e) {
      hideTyping(); 
      renderMessage('bot', e?.data?.error || e.message || 'Sorry, I encountered an error. Please try again.');
      if (e.status === 401) { 
        localStorage.removeItem('token'); 
        window.UI.openAuth(); 
      }
    } finally { 
      setBusy(false); 
      els.input.focus(); 
    }
  }

  // Auth UI
  const openAuth = () => { 
    const m = qs('#authModal'); 
    m.classList.remove('hidden'); 
    m.style.display = 'flex'; 
    m.setAttribute('aria-hidden','false');
  };
  
  const closeAuth = () => { 
    const m = qs('#authModal'); 
    m.classList.add('hidden'); 
    m.style.display = 'none'; 
    m.setAttribute('aria-hidden','true'); 
  };

  // Supabase OAuth
  let supabase = null;
  const initSupabase = () => {
    try {
      if (window.SUPABASE?.url && window.SUPABASE?.key && window.supabase) {
        supabase = window.supabase.createClient(window.SUPABASE.url, window.SUPABASE.key);
        return;
      }
      const urlEl = qs('meta[name="supabase-url"]');
      const keyEl = qs('meta[name="supabase-key"]');
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
    const wrap = qs('#userDisplay'); 
    const span = qs('#userFirstName');
    if (!wrap || !span) return;
    
    if (firstName) { 
      span.textContent = firstName; 
      wrap.classList.remove('hidden'); 
    } else { 
      wrap.classList.add('hidden'); 
      span.textContent = ''; 
    }
  };
  
  const loginWithProvider = async (provider) => {
    if (!supabase) { alert('Auth not configured'); return; }
    const redirectTo = window.location.origin + '/';
    const { error } = await supabase.auth.signInWithOAuth({ 
      provider, 
      options: { redirectTo } 
    });
    if (error) alert(error.message || 'Sign-in failed');
  };
  
  const attachOAuthHandlers = () => {
    const g = qs('#googleLoginBtn'); 
    if (g) g.onclick = () => loginWithProvider('google');
  };
  
  const restoreSupabaseSession = async () => {
    if (!supabase) return false;
    try {
      const { data } = await supabase.auth.getSession();
      const token = data?.session?.access_token;
      if (token) {
        API.setToken(token);
        qs('#authBtnText').textContent = 'Signed in';
        const so = qs('#signOutBtn'); 
        if (so) so.classList.remove('hidden');
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
    const so = qs('#signOutBtn'); 
    if (so) so.classList.add('hidden');
    setUserHeader('');
    
    // Reset interface
    els.chat.innerHTML = `
      <div id="welcomeMessage" class="max-w-2xl mx-auto text-center animate-fade-in">
        <div class="w-16 h-16 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-yellow-400 to-green-400 grid place-items-center text-2xl shadow-lg">
          🌿
        </div>
        <h2 class="text-3xl font-bold text-neutral-800 mb-4">G'day! I'm Yarn</h2>
        <p class="text-neutral-600 text-lg leading-relaxed mb-3">
          I'm here to have a yarn with you — to listen and help you think about your strengths and what matters to you.
        </p>
        <p class="text-neutral-600 leading-relaxed mb-6">
          This is a safe space where we can talk about whatever's on your mind. No judgment, just support.
        </p>
        
        <div class="mt-8 p-4 rounded-xl border border-orange-200 bg-gradient-to-r from-orange-50 to-amber-50 text-left">
          <div class="flex items-start gap-3">
            <div class="w-5 h-5 rounded-full bg-orange-100 flex items-center justify-center flex-shrink-0 mt-0.5">
              <i class="bi bi-info-fill text-orange-600 text-xs"></i>
            </div>
            <p class="text-sm text-neutral-700 leading-relaxed">
              This is not a crisis service. If you need immediate help, please click the "Get Help" button above for 24/7 support.
            </p>
          </div>
        </div>
      </div>
    `;
    
    const quickActions = qs('#quickActions');
    if (quickActions) {
      quickActions.style.display = 'flex';
    }
    
    openAuth();
  };

  // Crisis popup controls
  const showCrisisPopup = () => { 
    const m = qs('#crisisPopup'); 
    if (!m) return; 
    m.classList.remove('hidden'); 
    m.style.display = 'flex'; 
    m.setAttribute('aria-hidden','false'); 
  };
  
  const hideCrisisPopup = () => { 
    const m = qs('#crisisPopup'); 
    if (!m) return; 
    m.classList.add('hidden'); 
    m.style.display = 'none'; 
    m.setAttribute('aria-hidden','true'); 
  };
  
  const confirmContinueChat = () => {
    const ok = confirm('Are you sure you want to continue chatting?');
    if (ok) hideCrisisPopup(); 
    else showCrisisPopup();
  };

  // Public UI helpers
  window.UI = {
    sendMessage,
    sendQuick: (text) => { 
      els.input.value = text; 
      sendMessage(); 
    },
    showHelp: () => { 
      const m = qs('#helpModal'); 
      m.classList.remove('hidden'); 
      m.style.display = 'flex'; 
      m.setAttribute('aria-hidden','false'); 
    },
    hideHelp: () => { 
      const m = qs('#helpModal'); 
      m.classList.add('hidden'); 
      m.style.display = 'none'; 
      m.setAttribute('aria-hidden','true'); 
    },
    openAuth, 
    closeAuth,
    signOut,
    newChat: async () => { 
      localStorage.removeItem('session_id'); 
      sessionId = null; 
      await ensureSession(); 
      await loadHistory(); 
    },
    openHistory: async () => { 
      const d = qs('#historyDrawer'); 
      if (d) { 
        d.classList.remove('hidden'); 
        await loadSessions(); 
      } 
    },
    closeHistory: () => { 
      const d = qs('#historyDrawer'); 
      if (d) { 
        d.classList.add('hidden'); 
      } 
    },
    deleteSession: async (id) => {
      try { await API.deleteSession(id); await loadSessions(); } catch (e) { console.error(e); }
    },
    showCrisisPopup, 
    confirmContinueChat
  };

  // Init
  document.addEventListener('DOMContentLoaded', async () => {
    try { 
      document.title = 'Yarn Chat — Experimental Frontend'; 
    } catch {}
    
    els.chat = qs('#chatMessages'); 
    els.input = qs('#messageInput'); 
    els.send = qs('#sendBtn');
    
    attachOAuthHandlers();
    initSupabase();
    
    els.send.addEventListener('click', sendMessage);
    
    // Auto-resize textarea as user types
    if (els.input) {
      autoResizeTextarea(els.input);
      els.input.addEventListener('input', () => autoResizeTextarea(els.input));
    }
    
    els.input.addEventListener('keypress', (e) => { 
      if (e.key === 'Enter' && !e.shiftKey) { 
        e.preventDefault(); 
        sendMessage(); 
      }
    });

    // Token/session restore
    let token = localStorage.getItem('token'); 
    if (token) API.setToken(token);
    
    const restored = await restoreSupabaseSession();
    if (restored) token = localStorage.getItem('token');
    
    if (token && supabase) {
      try { 
        const { data: u } = await supabase.auth.getUser(); 
        const fn = firstNameFromUser(u?.user); 
        setUserHeader(fn); 
      } catch {}
    }
    
    sessionId = localStorage.getItem('session_id');

    // Health check (without displaying API info)
    try {
      await API.health();
    } catch {
      console.warn('API health check failed');
    }

    if (localStorage.getItem('token')) {
      qs('#authBtnText').textContent = 'Signed in';
      const so = qs('#signOutBtn'); 
      if (so) so.classList.remove('hidden');
      try { 
        if (!sessionId) await ensureSession(); 
        await loadHistory(); 
      } catch {}
    } else {
      openAuth();
    }
    
    // Add subtle entrance animation to welcome message
    setTimeout(() => {
      const welcomeMsg = els.chat.querySelector('.animate-fade-in');
      if (welcomeMsg) {
        welcomeMsg.style.opacity = '1';
      }
    }, 300);
  });
})();
