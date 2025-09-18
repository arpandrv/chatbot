(function(){
  // Supabase client
  let supabase = null;
  let lastPhone = '';

  const initSupabase = () => {
    try {
      if (window.SUPABASE?.url && window.SUPABASE?.key && window.supabase) {
        supabase = window.supabase.createClient(window.SUPABASE.url, window.SUPABASE.key);
        return;
      }
      const urlEl = document.querySelector('meta[name="supabase-url"]');
      const keyEl = document.querySelector('meta[name="supabase-key"]');
      if (urlEl && keyEl && window.supabase) {
        supabase = window.supabase.createClient(urlEl.content, keyEl.content);
      }
    } catch (error) {
      console.error('Failed to initialize Supabase:', error);
    }
  };

  const showLoading = () => {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
      overlay.classList.remove('hidden');
    }
  };

  const hideLoading = () => {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
      overlay.classList.add('hidden');
    }
  };

  const setPhoneStatus = (msg, type='info') => {
    const el = document.getElementById('phoneStatus');
    if (!el) return;
    el.textContent = msg || '';
    el.classList.remove('text-red-600','text-emerald-600','text-neutral-500');
    if (type === 'error') el.classList.add('text-red-600');
    else if (type === 'success') el.classList.add('text-emerald-600');
    else el.classList.add('text-neutral-500');
  };

  const isLikelyE164 = (s) => {
    if (!s) return false;
    const v = s.replace(/\s+/g,'');
    return /^\+\d{7,15}$/.test(v);
  };

  const loginWithGoogle = async () => {
    if (!supabase) {
      alert('Authentication not configured');
      return;
    }

    try {
      showLoading();

      const redirectTo = window.location.origin + '/chat';
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo }
      });

      if (error) {
        throw error;
      }
    } catch (error) {
      hideLoading();
      console.error('Sign-in error:', error);
      alert(error.message || 'Sign-in failed');
    }
  };

  const sendPhoneCode = async () => {
    if (!supabase) {
      alert('Authentication not configured');
      return;
    }
    const phoneInput = document.getElementById('phoneInput');
    const sendBtn = document.getElementById('sendCodeBtn');
    const codeSection = document.getElementById('codeSection');
    if (!phoneInput || !sendBtn) return;

    const raw = phoneInput.value.trim();
    const phone = raw.replace(/\s+/g, '');
    if (!isLikelyE164(phone)) {
      setPhoneStatus('Please enter a valid phone in international format, e.g. +61...', 'error');
      phoneInput.focus();
      return;
    }

    try {
      setPhoneStatus('Sending code...');
      sendBtn.disabled = true;
      showLoading();
      const { error } = await supabase.auth.signInWithOtp({ phone });
      if (error) throw error;
      lastPhone = phone;
      if (codeSection) codeSection.classList.remove('hidden');
      setPhoneStatus('Code sent. Check your SMS and enter the 6-digit code.', 'success');
      const codeInput = document.getElementById('codeInput');
      if (codeInput) codeInput.focus();
    } catch (e) {
      console.error('OTP send error:', e);
      setPhoneStatus(e?.message || 'Could not send code. Please try again.', 'error');
    } finally {
      hideLoading();
      sendBtn.disabled = false;
    }
  };

  const verifyPhoneCode = async () => {
    if (!supabase) return;
    const codeInput = document.getElementById('codeInput');
    const verifyBtn = document.getElementById('verifyCodeBtn');
    if (!codeInput || !verifyBtn) return;

    const token = (codeInput.value || '').trim();
    if (!/^[0-9]{4,8}$/.test(token)) {
      setPhoneStatus('Enter the code sent to your phone.', 'error');
      codeInput.focus();
      return;
    }

    try {
      setPhoneStatus('Verifying code...');
      verifyBtn.disabled = true;
      showLoading();
      const { data, error } = await supabase.auth.verifyOtp({
        phone: lastPhone,
        token,
        type: 'sms',
      });
      if (error) throw error;

      // On success, onAuthStateChange will fire (SIGNED_IN) and redirect.
      setPhoneStatus('Code verified. Signing you in...', 'success');
    } catch (e) {
      console.error('OTP verify error:', e);
      setPhoneStatus(e?.message || 'Verification failed. Please try again.', 'error');
    } finally {
      hideLoading();
      verifyBtn.disabled = false;
    }
  };

  const checkExistingSession = async () => {
    if (!supabase) return;

    try {
      const { data } = await supabase.auth.getSession();
      const token = data?.session?.access_token;

      if (token) {
        // User is already signed in, redirect to chat
        window.location.href = '/chat';
      }
    } catch (error) {
      console.error('Session check error:', error);
    }
  };

  // Initialize when DOM is ready
  document.addEventListener('DOMContentLoaded', async () => {
    initSupabase();

    // Check if user is already signed in
    await checkExistingSession();

    // Attach Google login handler
    const googleBtn = document.getElementById('googleLoginBtn');
    if (googleBtn) {
      googleBtn.onclick = loginWithGoogle;
    }

    // Attach phone OTP handlers
    const sendBtn = document.getElementById('sendCodeBtn');
    const verifyBtn = document.getElementById('verifyCodeBtn');
    if (sendBtn) sendBtn.addEventListener('click', sendPhoneCode);
    if (verifyBtn) verifyBtn.addEventListener('click', verifyPhoneCode);

    // Handle OAuth callback
    if (supabase) {
      supabase.auth.onAuthStateChange(async (event, session) => {
        if (event === 'SIGNED_IN' && session) {
          // Store token and redirect to chat
          if (window.API) {
            window.API.setToken(session.access_token);
          }
          window.location.href = '/chat';
        }
      });
    }
  });
})();
