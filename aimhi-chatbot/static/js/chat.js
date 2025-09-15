(function(){
  // State
  let sessionId = null;
  let typingEl = null;
  let currentUser = null;
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

  // Render message (user messages without avatar but with proper styling)
  const renderMessage = (sender, text, isHTML=false) => {
    const container = ce('div', 'mb-6');

    if (sender === 'bot') {
      // Bot message with avatar and bubble
      container.className = 'mb-6 flex gap-3 items-start';

      const avatar = ce('div', 'w-8 h-8 rounded-full bg-gradient-to-br from-green-400 to-emerald-500 text-white grid place-items-center text-sm font-medium flex-shrink-0');
      avatar.textContent = 'Y';

      const bubble = ce('div', 'bg-white border border-neutral-200 rounded-2xl px-4 py-3 shadow-sm max-w-3xl');
      const p = ce('p', 'text-neutral-800 leading-relaxed');

      if (isHTML) {
        p.innerHTML = text;
      } else {
        p.textContent = text;
      }

      bubble.appendChild(p);
      container.appendChild(avatar);
      container.appendChild(bubble);
    } else {
      // User message - no avatar but keep the bubble styling
      container.className = 'mb-6 flex justify-end';
      const bubble = ce('div', 'bg-blue-500 text-white rounded-2xl px-4 py-3 max-w-3xl shadow-sm');
      const p = ce('p', 'leading-relaxed');
      p.textContent = text;
      bubble.appendChild(p);
      container.appendChild(bubble);
    }

    // Add animation class
    container.classList.add('animate-slide-in-left');

    const messagesContainer = qs('#chatMessages .max-w-4xl');
    messagesContainer.appendChild(container);

    // Scroll to bottom
    const chatMessages = qs('#chatMessages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
  };

  const showTyping = () => {
    if (typingEl) return;

    typingEl = ce('div', 'mb-6 flex gap-3 items-start');
    typingEl.id = 'typing';

    const avatar = ce('div', 'w-8 h-8 rounded-full bg-gradient-to-br from-green-400 to-emerald-500 text-white grid place-items-center text-sm font-medium flex-shrink-0');
    avatar.textContent = 'Y';

    const bubble = ce('div', 'bg-white border border-neutral-200 rounded-2xl px-4 py-3 shadow-sm');
    const dotsContainer = ce('div', 'typing-dots');

    for (let i = 0; i < 3; i++) {
      const dot = ce('span', 'typing-dot');
      dotsContainer.appendChild(dot);
    }

    bubble.appendChild(dotsContainer);
    typingEl.appendChild(avatar);
    typingEl.appendChild(bubble);

    const messagesContainer = qs('#chatMessages .max-w-4xl');
    messagesContainer.appendChild(typingEl);

    const chatMessages = qs('#chatMessages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
  };

  const hideTyping = () => {
    if (typingEl && typingEl.parentNode) {
      typingEl.parentNode.removeChild(typingEl);
    }
    typingEl = null;
  };

  const updateDebug = (info={}) => {
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

  // Sidebar functionality
  const toggleSidebar = () => {
    const sidebar = qs('#sidebar');
    const collapsedSidebar = qs('#collapsedSidebar');
    const toggleBtn = qs('#toggleSidebar i');

    if (sidebar.style.display === 'none' || sidebar.classList.contains('hidden')) {
      // Expand
      sidebar.classList.remove('hidden');
      sidebar.style.display = 'flex';
      collapsedSidebar.classList.add('hidden');
      collapsedSidebar.style.display = 'none';

      // Update icon
      if (toggleBtn) {
        toggleBtn.className = 'bi bi-chevron-left text-sm';
      }
    } else {
      // Collapse
      sidebar.classList.add('hidden');
      sidebar.style.display = 'none';
      collapsedSidebar.classList.remove('hidden');
      collapsedSidebar.style.display = 'flex';

      // Update icon
      if (toggleBtn) {
        toggleBtn.className = 'bi bi-chevron-right text-sm';
      }
    }

    // Save preference
    localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('hidden') ? 'true' : 'false');
  };

  // Profile dropdown functionality
  const toggleProfileDropdown = () => {
    const dropdown = qs('#profileDropdown');
    dropdown.classList.toggle('hidden');
  };

  // Close dropdown when clicking outside
  const closeProfileDropdown = (e) => {
    const dropdown = qs('#profileDropdown');
    const profileBtn = qs('#profileBtn');

    if (!dropdown.contains(e.target) && !profileBtn.contains(e.target)) {
      dropdown.classList.add('hidden');
    }
  };

  // Session management
  const renderSessionItem = (s) => {
    const item = ce('div', 'group flex items-center justify-between gap-2 p-3 rounded-lg hover:bg-neutral-50 cursor-pointer mb-2 transition-colors');

    const content = ce('div', 'flex-1 min-w-0');
    content.dataset.sessionId = s.session_id; // Add session ID for deletion
    content.onclick = async () => {
      await loadSession(s.session_id);
    };

    const title = ce('div', 'font-medium text-sm text-neutral-800 truncate');
    title.textContent = s.fsm_state || 'New Chat';

    const time = ce('div', 'text-xs text-neutral-500 mt-1');
    const ts = new Date(s.last_activity || s.created_at || Date.now());
    time.textContent = ts.toLocaleDateString() + ' ' + ts.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

    content.appendChild(title);
    content.appendChild(time);

    const deleteBtn = ce('button', 'opacity-0 group-hover:opacity-100 p-1 rounded text-neutral-400 hover:text-red-500 hover:bg-red-50 transition-all');
    deleteBtn.innerHTML = '<i class="bi bi-trash text-xs"></i>';
    deleteBtn.onclick = async (e) => {
      e.stopPropagation();
      // Show loading state
      deleteBtn.innerHTML = '<i class="bi bi-hourglass-split text-xs animate-spin"></i>';
      deleteBtn.disabled = true;

      await deleteSession(s.session_id);

      // Note: button will be removed with the item on success,
      // but restore if there's an error
      if (deleteBtn.parentNode) {
        deleteBtn.innerHTML = '<i class="bi bi-trash text-xs"></i>';
        deleteBtn.disabled = false;
      }
    };

    item.appendChild(content);
    item.appendChild(deleteBtn);

    return item;
  };

  const loadSessions = async () => {
    try {
      const container = qs('#chatHistory');
      const emptyState = qs('#emptyHistoryState');

      const sessions = await API.listSessions(50);

      // Clear existing sessions but keep empty state
      const existingSessions = container.querySelectorAll('.group');
      existingSessions.forEach(session => session.remove());

      if (sessions && sessions.length > 0) {
        emptyState.style.display = 'none';

        sessions.forEach(session => {
          container.insertBefore(renderSessionItem(session), emptyState);
        });
      } else {
        emptyState.style.display = 'block';
      }
    } catch (e) {
      console.error('Error loading sessions:', e);
    }
  };

  const loadSession = async (sessionIdToLoad) => {
    try {
      sessionId = sessionIdToLoad;
      localStorage.setItem('session_id', sessionId);

      await loadHistory();

      // Update UI to show we're in this session
      const titleEl = qs('#currentChatTitle');
      if (titleEl) {
        titleEl.textContent = `Session ${sessionId.slice(0, 8)}...`;
        titleEl.classList.remove('hidden');
      }
    } catch (e) {
      console.error('Error loading session:', e);
    }
  };

  const deleteSession = async (sessionIdToDelete) => {
    if (!confirm('Delete this chat? This cannot be undone.')) {
      return;
    }

    // Find the session item in the UI
    const sessionItems = document.querySelectorAll('.group');
    let sessionElement = null;

    for (const item of sessionItems) {
      const content = item.querySelector('div');
      if (content && content.dataset && content.dataset.sessionId === sessionIdToDelete) {
        sessionElement = item;
        break;
      }
    }

    // Optimistic update - immediately remove from UI
    if (sessionElement) {
      sessionElement.style.opacity = '0.5';
      sessionElement.style.pointerEvents = 'none';
    }

    try {
      // Make the API call
      await API.deleteSession(sessionIdToDelete);

      // Success - complete the removal
      if (sessionElement) {
        sessionElement.remove();
      }

      // If we deleted the active session, clear the chat
      if (sessionId === sessionIdToDelete) {
        sessionId = null;
        localStorage.removeItem('session_id');
        clearChat();

        const titleEl = qs('#currentChatTitle');
        if (titleEl) {
          titleEl.classList.add('hidden');
        }
      }

      // Check if we need to show empty state
      const remainingSessions = document.querySelectorAll('.group');
      const emptyState = qs('#emptyHistoryState');
      if (remainingSessions.length === 0 && emptyState) {
        emptyState.style.display = 'block';
      }

    } catch (err) {
      console.error('Delete failed', err);

      // Rollback - restore the item
      if (sessionElement) {
        sessionElement.style.opacity = '1';
        sessionElement.style.pointerEvents = 'auto';
      }

      alert('Could not delete chat. Please try again.');
    }
  };

  const createNewSession = async () => {
    try {
      const res = await API.createSession('welcome');
      await loadSession(res.session_id);
      await loadSessions();
    } catch (e) {
      console.error('Error creating session:', e);
    }
  };

  const clearChat = () => {
    const messagesContainer = qs('#chatMessages .max-w-4xl');

    // Clear all messages but keep welcome message
    const existingMessages = messagesContainer.querySelectorAll('.mb-6:not(#welcomeMessage)');
    existingMessages.forEach(msg => msg.remove());

    // Show welcome message and quick actions
    const welcomeMsg = qs('#welcomeMessage');
    const quickActions = qs('#quickActions');

    if (welcomeMsg) welcomeMsg.style.display = 'block';
    if (quickActions) quickActions.style.display = 'flex';
  };

  const loadHistory = async () => {
    if (!sessionId) {
      clearChat();
      return;
    }

    try {
      const msgs = await API.getMessages(sessionId, 50);

      // Clear existing messages
      const messagesContainer = qs('#chatMessages .max-w-4xl');
      const existingMessages = messagesContainer.querySelectorAll('.mb-6:not(#welcomeMessage)');
      existingMessages.forEach(msg => msg.remove());

      if (!msgs || msgs.length === 0) {
        // No messages, show welcome
        const welcomeMsg = qs('#welcomeMessage');
        const quickActions = qs('#quickActions');
        if (welcomeMsg) welcomeMsg.style.display = 'block';
        if (quickActions) quickActions.style.display = 'flex';
        return;
      }

      // Hide welcome message if we have chat history
      const welcomeMsg = qs('#welcomeMessage');
      const quickActions = qs('#quickActions');
      if (welcomeMsg) welcomeMsg.style.display = 'none';
      if (quickActions) quickActions.style.display = 'none';

      // Render messages
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

    // Create session if we don't have one (only on first message)
    if (!sessionId) {
      try {
        const res = await API.createSession('welcome');
        sessionId = res.session_id;
        localStorage.setItem('session_id', sessionId);
        await loadSessions(); // Refresh sidebar
      } catch (e) {
        console.error('Error creating session:', e);
        alert('Failed to start conversation. Please try again.');
        return;
      }
    }

    // Hide welcome message and quick actions on first message
    const welcomeMsg = qs('#welcomeMessage');
    const quickActions = qs('#quickActions');
    if (welcomeMsg) welcomeMsg.style.display = 'none';
    if (quickActions) quickActions.style.display = 'none';

    renderMessage('user', msg);
    els.input.value = '';
    autoResizeTextarea(els.input); // Reset height
    setBusy(true);

    showTyping();

    try {
      const data = await API.sendMessage(sessionId, msg);
      hideTyping();
      renderMessage('bot', data.reply || '...');
      updateDebug(data.debug || {});

      // Update session list
      await loadSessions();
    } catch (e) {
      hideTyping();
      renderMessage('bot', e?.data?.error || e.message || 'Sorry, I encountered an error. Please try again.');
      if (e.status === 401) {
        // Redirect to welcome page on auth error
        window.location.href = '/';
      }
    } finally {
      setBusy(false);
      els.input.focus();
    }
  }

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

  const restoreSupabaseSession = async () => {
    if (!supabase) return false;
    try {
      const { data } = await supabase.auth.getSession();
      const token = data?.session?.access_token;
      if (token) {
        API.setToken(token);
        currentUser = data?.session?.user;

        // Update profile dropdown
        const userEmail = qs('#userEmail');
        if (userEmail && currentUser?.email) {
          userEmail.textContent = currentUser.email;
        }

        return true;
      }
      return false;
    } catch {
      return false;
    }
  };

  const signOut = async () => {
    try {
      if (supabase) await supabase.auth.signOut();
    } catch {}

    API.setToken('');
    localStorage.removeItem('session_id');
    localStorage.removeItem('token');
    sessionId = null;
    currentUser = null;

    // Redirect to welcome page
    window.location.href = '/';
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
    signOut,
    newChat: createNewSession,
    showCrisisPopup,
    confirmContinueChat
  };

  // Init
  document.addEventListener('DOMContentLoaded', async () => {
    els.input = qs('#messageInput');
    els.send = qs('#sendBtn');

    initSupabase();

    // Check authentication
    const restored = await restoreSupabaseSession();
    if (!restored) {
      window.location.href = '/';
      return;
    }

    // Setup event listeners
    els.send.addEventListener('click', sendMessage);

    // Auto-resize textarea
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

    // Sidebar controls
    const toggleBtn = qs('#toggleSidebar');
    const expandBtn = qs('#expandSidebar');
    const newChatBtn = qs('#newChatBtn');
    const newChatBtnCollapsed = qs('#newChatBtnCollapsed');

    if (toggleBtn) toggleBtn.addEventListener('click', toggleSidebar);
    if (expandBtn) expandBtn.addEventListener('click', toggleSidebar);
    if (newChatBtn) newChatBtn.addEventListener('click', createNewSession);
    if (newChatBtnCollapsed) newChatBtnCollapsed.addEventListener('click', createNewSession);

    // Restore sidebar preference
    const sidebarCollapsed = localStorage.getItem('sidebarCollapsed');
    if (sidebarCollapsed === 'true') {
      // Start with sidebar collapsed
      const sidebar = qs('#sidebar');
      const collapsedSidebar = qs('#collapsedSidebar');
      if (sidebar) {
        sidebar.classList.add('hidden');
        sidebar.style.display = 'none';
      }
      if (collapsedSidebar) {
        collapsedSidebar.classList.remove('hidden');
        collapsedSidebar.style.display = 'flex';
      }
    }

    // Profile dropdown
    qs('#profileBtn').addEventListener('click', toggleProfileDropdown);
    qs('#signOutBtn').addEventListener('click', signOut);
    document.addEventListener('click', closeProfileDropdown);

    // Load sessions and restore session if available
    await loadSessions();

    sessionId = localStorage.getItem('session_id');
    if (sessionId) {
      await loadHistory();
      const titleEl = qs('#currentChatTitle');
      if (titleEl) {
        titleEl.textContent = `Session ${sessionId.slice(0, 8)}...`;
        titleEl.classList.remove('hidden');
      }
    }

    // Health check
    try {
      await API.health();
    } catch {
      console.warn('API health check failed');
    }

    els.input.focus();
  });
})();