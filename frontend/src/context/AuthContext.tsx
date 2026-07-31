import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/apiConfig';

const TOKEN_KEY = 'creditiq_token';
const USER_KEY = 'admin_user';

interface AuthUser {
  email: string;
  name: string;
  role: string;
}

const AuthContext = createContext<any>(null);

/** Attach (or clear) the bearer token on every subsequent API call. */
const setAuthHeader = (token: string | null) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

/** Map the backend /api/auth/me payload onto the shape the UI consumes. */
const toAuthUser = (me: any): AuthUser => ({
  email: me?.email ?? 'admin@gmail.com',
  name: me?.full_name || 'Administrator',
  role: 'admin',
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Restore the session synchronously so a refresh doesn't bounce to /login,
    // then verify the token against the backend and drop it if it's stale.
    const token = localStorage.getItem(TOKEN_KEY);
    const storedUser = localStorage.getItem(USER_KEY);

    if (!token) {
      localStorage.removeItem(USER_KEY);
      setLoading(false);
      return;
    }

    setAuthHeader(token);

    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        localStorage.removeItem(USER_KEY);
      }
    }
    setLoading(false);

    api.get('/api/auth/me')
      .then(res => {
        const fresh = toAuthUser(res.data);
        localStorage.setItem(USER_KEY, JSON.stringify(fresh));
        setUser(fresh);
      })
      .catch(err => {
        // Only a rejected token invalidates the session — a network blip or a
        // 500 must not log the user out mid-session.
        if (err.response?.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
          setAuthHeader(null);
          setUser(null);
        }
      });
  }, []);

  const login = async (email: string, password: string) => {
    // Backend uses OAuth2PasswordRequestForm — form-encoded `username`/`password`.
    const form = new URLSearchParams();
    form.append('username', email);
    form.append('password', password);

    let token: string;
    try {
      const res = await api.post('/api/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      token = res.data.access_token;
    } catch (err: any) {
      if (!err.response) {
        throw new Error('Cannot reach CreditIQ backend. Make sure the server is running on port 8000.');
      }
      if (err.response.status === 401) {
        throw new Error('Invalid credentials. Access denied.');
      }
      throw new Error(err.userMessage || 'Login failed. Please try again.');
    }

    localStorage.setItem(TOKEN_KEY, token);
    setAuthHeader(token);

    // Profile lookup is best-effort — a failure here shouldn't undo a valid login.
    let authUser: AuthUser = { email, name: 'Administrator', role: 'admin' };
    try {
      const me = await api.get('/api/auth/me');
      authUser = toAuthUser(me.data);
    } catch {
      /* fall back to the email the user just signed in with */
    }

    localStorage.setItem(USER_KEY, JSON.stringify(authUser));
    setUser(authUser);
    return authUser;
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setAuthHeader(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
