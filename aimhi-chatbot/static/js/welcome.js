(function(){
  // Supabase client
  let supabase = null;

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