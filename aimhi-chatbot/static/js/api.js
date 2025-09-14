// Lightweight API client inspired by Vercel example patterns
(function(){
  const DEFAULT_BASE = (window.APP_CONFIG && window.APP_CONFIG.apiBase) || localStorage.getItem('apiBase') || window.location.origin;
  let TOKEN = localStorage.getItem('token') || '';

  const withTimeout = (promise, ms) => {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), ms);
    return [promise(ctrl.signal).finally(() => clearTimeout(t)), ctrl];
  };

  const jsonFetch = async (path, { method = 'GET', body, headers = {}, timeout = 15000, retries = 1 } = {}) => {
    const url = (path.startsWith('http') ? path : DEFAULT_BASE + path);
    const doFetch = (signal) => fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(TOKEN ? { 'Authorization': `Bearer ${TOKEN}` } : {}),
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
      signal,
      credentials: 'include',
    });

    let attempt = 0;
    while (true) {
      try {
        const [p] = withTimeout(doFetch, timeout);
        const res = await p;
        const ct = res.headers.get('content-type') || '';
        const data = ct.includes('application/json') ? await res.json() : await res.text();
        if (!res.ok) {
          const err = new Error(data?.error || res.statusText || 'Request failed');
          err.status = res.status; err.data = data; throw err;
        }
        return data;
      } catch (e) {
        attempt++;
        if (attempt > retries || (e.name === 'AbortError')) throw e;
        await new Promise(r => setTimeout(r, Math.min(1000 * attempt, 3000)));
      }
    }
  };

  const setToken = (t) => { TOKEN = t || ''; if (t) localStorage.setItem('token', t); else localStorage.removeItem('token'); };
  const setApiBase = (b) => { if (b) localStorage.setItem('apiBase', b); };

  window.API = {
    get base(){ return DEFAULT_BASE; },
    setToken,
    setApiBase,
    health: () => jsonFetch('/health', {}),
    createSession: (fsm_state) => jsonFetch('/sessions', { method: 'POST', body: { fsm_state } }),
    sendMessage: (sessionId, message) => jsonFetch(`/sessions/${sessionId}/messages`, { method: 'POST', body: { message } }),
    getMessages: (sessionId, limit=50) => jsonFetch(`/sessions/${sessionId}/messages?limit=${limit}`),
    listSessions: (limit=20) => jsonFetch(`/sessions?limit=${limit}`),
  };
})();
