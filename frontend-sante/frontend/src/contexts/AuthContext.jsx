import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api.js';

/* eslint-disable react-refresh/only-export-components */
const AuthContext = createContext();

export const useAuth = () => {
  return useContext(AuthContext);
};
/* eslint-enable react-refresh/only-export-components */

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
      setLoading(false);
      return;
    }

    authAPI
      .me()
      .then((response) => {
        setUser(response.data);
      })
      .catch(() => {
        localStorage.removeItem('access_token');
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    setLoading(true);
    setError(null);

    try {
      const response = await authAPI.login(email, password);
      const { access_token, role, email: userEmail } = response.data;
      localStorage.setItem('access_token', access_token);
      if (role && userEmail) {
        localStorage.setItem('user_role', role);
        setUser({ role, email: userEmail });
      } else {
        const meResponse = await authAPI.me();
        setUser(meResponse.data);
      }

      return { success: true };
    } catch (err) {
      const message =
        err?.response?.data?.detail || err?.response?.data?.message || 'Impossible de se connecter';
      setError(message);
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    setUser(null);
    setError(null);
  };

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    isAuthenticated: Boolean(user),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};