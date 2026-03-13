// SehatSetu — Shared App Utilities
const API_BASE = window.location.origin;
const SUPABASE_URL = 'https://nlfplwhhqvivootwnulg.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5sZnBsd2hocXZpdm9vdHdudWxnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMzMTQzODYsImV4cCI6MjA4ODg5MDM4Nn0.OlYpZEIXOJRkgsEpCYj4xi1K61hOBkmzs3lEcpSHCDQ';

/** Show a toast notification */
function showToast(message, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

/** Check online status */
function isOnline() {
    return navigator.onLine;
}

/** Format timestamp to readable date */
function formatTime(timestamp) {
    const d = new Date(timestamp);
    const now = new Date();
    const diffMs = now - d;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

/** Get stored auth token */
function getAuthToken() {
    return localStorage.getItem('sehatsetu_token');
}

/** Store auth session */
function setAuthSession(session) {
    localStorage.setItem('sehatsetu_token', session.access_token);
    localStorage.setItem('sehatsetu_user', JSON.stringify(session.user));
}

/** Clear auth session */
function clearAuthSession() {
    localStorage.removeItem('sehatsetu_token');
    localStorage.removeItem('sehatsetu_user');
    localStorage.removeItem('sehatsetu_role');
    localStorage.removeItem('sehatsetu_name');
}

/** Get current user */
function getCurrentUser() {
    const user = localStorage.getItem('sehatsetu_user');
    return user ? JSON.parse(user) : null;
}

/** API fetch with optional auth */
async function apiFetch(endpoint, options = {}) {
    const token = getAuthToken();
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ error: 'Request failed' }));
        throw new Error(err.error || 'Request failed');
    }
    return response.json();
}

/** Supabase Auth — sign in with email/password */
async function supabaseSignIn(email, password) {
    const res = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'apikey': SUPABASE_ANON_KEY
        },
        body: JSON.stringify({ email, password })
    });

    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error_description || err.msg || 'Login failed');
    }

    const data = await res.json();
    setAuthSession(data);
    return data;
}

/** Supabase Auth — sign in with Google (OAuth redirect) */
function supabaseSignInWithGoogle(redirectTo) {
    // Redirect back to login.html so handleAuthCallback() can process the token
    const loginUrl = redirectTo || window.location.href.split('?')[0].split('#')[0];
    const params = new URLSearchParams({
        provider: 'google',
        redirect_to: loginUrl
    });
    window.location.href = `${SUPABASE_URL}/auth/v1/authorize?${params.toString()}`;
}

/** Handle OAuth callback — extract tokens from URL hash, check role */
function handleAuthCallback(requiredRole) {
    const hash = window.location.hash;
    if (!hash || !hash.includes('access_token')) return false;

    const params = new URLSearchParams(hash.substring(1));
    const accessToken = params.get('access_token');

    if (accessToken) {
        fetch(`${SUPABASE_URL}/auth/v1/user`, {
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'apikey': SUPABASE_ANON_KEY
            }
        })
        .then(res => res.json())
        .then(async (user) => {
            setAuthSession({ access_token: accessToken, user });
            window.history.replaceState(null, '', window.location.pathname);

            // Check role whitelist
            if (requiredRole) {
                const profile = await checkUserRole(user.email);
                if (!profile || profile.role !== requiredRole) {
                    clearAuthSession();
                    document.body.innerHTML = `
                        <div style="display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;font-family:Inter,sans-serif;background:#1a1a2e;color:#fff;">
                            <h1 style="font-size:3rem;margin-bottom:0.5rem;">🚫 403</h1>
                            <h2 style="color:#e74c3c;">Unauthorized: Medical License Verification Failed</h2>
                            <p style="color:#aaa;margin-top:0.5rem;">Your email (${user.email}) is not registered as a ${requiredRole}.</p>
                            <a href="../index.html" style="margin-top:1.5rem;color:#4ecdc4;text-decoration:underline;">← Back to Home</a>
                        </div>`;
                    return;
                }
                localStorage.setItem('sehatsetu_role', profile.role);
                localStorage.setItem('sehatsetu_name', profile.name || '');
            }
            window.location.href = 'dashboard.html';
        })
        .catch(() => {
            setAuthSession({ access_token: accessToken, user: { email: 'Google User' } });
            window.history.replaceState(null, '', window.location.pathname);
            window.location.href = 'dashboard.html';
        });
        return true;
    }
    return false;
}

/** Supabase Auth — sign out */
async function supabaseSignOut() {
    const token = getAuthToken();
    if (token) {
        await fetch(`${SUPABASE_URL}/auth/v1/logout`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'apikey': SUPABASE_ANON_KEY
            }
        }).catch(() => {});
    }
    clearAuthSession();
}

/** Check user role against profiles whitelist in Supabase */
async function checkUserRole(email) {
    try {
        const res = await fetch(
            `${SUPABASE_URL}/rest/v1/profiles?email=eq.${encodeURIComponent(email)}&select=role,name`,
            { headers: { 'apikey': SUPABASE_ANON_KEY, 'Accept': 'application/json' } }
        );
        if (!res.ok) return null;
        const data = await res.json();
        if (data.length === 0) return null;
        return data[0];
    } catch {
        return null;
    }
}

/** Verify role after login — kick out unauthorized users */
async function enforceRole(requiredRole) {
    const user = getCurrentUser();
    if (!user || !user.email) {
        clearAuthSession();
        return false;
    }

    if (!navigator.onLine) {
        return localStorage.getItem('sehatsetu_role') === requiredRole;
    }

    const profile = await checkUserRole(user.email);
    if (!profile || profile.role !== requiredRole) {
        clearAuthSession();
        return false;
    }
    localStorage.setItem('sehatsetu_role', profile.role);
    localStorage.setItem('sehatsetu_name', profile.name || '');
    return true;
}

/** ASHA Worker — static PIN auth (works offline) */
const ASHA_CREDENTIALS = { phone: '9067038936', pin: '2026', name: 'Utkarsha' };

function ashaLogin(phone, pin) {
    if (phone === ASHA_CREDENTIALS.phone && pin === ASHA_CREDENTIALS.pin) {
        localStorage.setItem('sehatsetu_asha_auth', JSON.stringify({
            phone: phone, name: 'ASHA Worker', authenticated: true, ts: Date.now()
        }));
        return true;
    }
    return false;
}

function isAshaAuthenticated() {
    const auth = localStorage.getItem('sehatsetu_asha_auth');
    return auth ? JSON.parse(auth).authenticated === true : false;
}

function ashaLogout() {
    localStorage.removeItem('sehatsetu_asha_auth');
}
