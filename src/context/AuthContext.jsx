import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const API_URL = 'https://daryllll-gyufuyf.hf.space';
const TOKEN_KEY = 'aethel_access_token';
const USER_KEY  = 'aethel_user';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]   = useState(() => {
    try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch { return null; }
  });
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState(null);

  // Persist to localStorage whenever they change
  useEffect(() => {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else        localStorage.removeItem(TOKEN_KEY);
  }, [token]);

  useEffect(() => {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    else       localStorage.removeItem(USER_KEY);
  }, [user]);

  // On mount: verify the stored token is still valid
  useEffect(() => {
    if (!token) return;
    fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(u => setUser(u))
      .catch(() => {
        setToken(null);
        setUser(null);
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Register: returns { pending_verification, email } — NO token yet
  // UNLESS backend has SKIP_EMAIL_VERIFY=true, in which case it returns
  // access_token + user directly (like login) and we log in immediately.
  const register = useCallback(async ({ email, password, name, role, org }) => {
    setLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name, role, org }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Registration failed.');

      // SKIP_EMAIL_VERIFY mode: backend returns token immediately
      if (data.access_token && data.user) {
        setToken(data.access_token);
        setUser(data.user);
        return { ok: true, loggedIn: true };
      }

      // Normal OTP flow
      return { ok: true, pendingEmail: data.email };
    } catch (e) {
      setAuthError(e.message);
      return { ok: false };
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Verify OTP: on success, sets user + token (logs them in)
  const verifyOtp = useCallback(async ({ email, otp }) => {
    setLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(`${API_URL}/auth/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, otp }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Invalid code.');
      setToken(data.access_token);
      setUser(data.user);
      return { ok: true };
    } catch (e) {
      setAuthError(e.message);
      return { ok: false };
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Resend OTP
  const resendOtp = useCallback(async (email) => {
    setAuthError(null);
    try {
      const res = await fetch(`${API_URL}/auth/resend-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password: '' }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Could not resend.');
      return { ok: true, message: data.message };
    } catch (e) {
      setAuthError(e.message);
      return { ok: false };
    }
  }, []);

  // ── Login
  const login = useCallback(async ({ email, password }) => {
    setLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Login failed.');
      setToken(data.access_token);
      setUser(data.user);
      return { ok: true };
    } catch (e) {
      setAuthError(e.message);
      return { ok: false };
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Request Recruiter Verification
  const requestRecruiterVerification = useCallback(async ({ company_email, linkedin_url }) => {
    setLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(`${API_URL}/auth/request-recruiter-verification`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ company_email, linkedin_url }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Could not request verification.');
      
      if (data.auto_verified) {
        setToken(data.access_token);
        setUser(data.user);
        return { ok: true, auto_verified: true, message: data.message };
      }
      
      return { ok: true, auto_verified: false, message: data.message };
    } catch (e) {
      setAuthError(e.message);
      return { ok: false };
    } finally {
      setLoading(false);
    }
  }, [token]);

  // ── Verify Recruiter OTP
  const verifyRecruiterOTP = useCallback(async ({ company_email, otp }) => {
    setLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(`${API_URL}/auth/verify-recruiter`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ company_email, otp }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Invalid code.');
      
      // Update token and user since they come back refreshed
      setToken(data.access_token);
      setUser(data.user);
      return { ok: true };
    } catch (e) {
      setAuthError(e.message);
      return { ok: false };
    } finally {
      setLoading(false);
    }
  }, [token]);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setAuthError(null);
  }, []);

  const clearAuthError = useCallback(() => setAuthError(null), []);

  const authHeaders = useCallback(() =>
    token ? { Authorization: `Bearer ${token}` } : {},
  [token]);

  return (
    <AuthContext.Provider value={{
      user, token, loading, authError,
      register, verifyOtp, resendOtp, login, logout,
      requestRecruiterVerification, verifyRecruiterOTP,
      clearAuthError, authHeaders,
      isLoggedIn: !!user,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
