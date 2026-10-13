import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
  apiFetch,
  clearToken,
  getStoredToken,
  setUnauthorizedHandler,
  storeToken,
} from './doctorApi.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [doctor, setDoctor] = useState(null);
  const [loading, setLoading] = useState(Boolean(getStoredToken()));

  const logout = useCallback(() => {
    clearToken();
    setDoctor(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (!getStoredToken()) return;
    apiFetch('/doctor/me')
      .then(setDoctor)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [logout]);

  const login = async (email, password) => {
    const data = await apiFetch('/auth/login', {
      method: 'POST',
      body: { email, password },
      auth: false,
    });
    storeToken(data.access_token);
    setDoctor(data.doctor);
  };

  return (
    <AuthContext.Provider value={{ doctor, setDoctor, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);