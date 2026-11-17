// src/context/AuthContext.jsx
import React, { createContext, useContext, useEffect, useState } from "react";
import {
  TOKEN_KEY,
  USER_KEY,
  clearBrowserSession,
  fetchMeApi,
  loginApi,
  registerApi,
} from "../services/api";

const AuthContext = createContext(null);

const readStoredUser = () => {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY));
  } catch (e) {
    return null;
  }
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(readStoredUser);
  // While a stored token is being checked with the server, show nothing.
  const [checking, setChecking] = useState(() => !!localStorage.getItem(TOKEN_KEY));

  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) return;

    fetchMeApi()
      .then((me) => {
        localStorage.setItem(USER_KEY, JSON.stringify(me));
        setUser(me);
      })
      .catch(() => {
        clearBrowserSession();
        setUser(null);
      })
      .finally(() => setChecking(false));
  }, []);

  const startSession = (data) => {
    // A new login must never inherit the previous user's report or chat.
    clearBrowserSession();
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    setUser(data.user);
  };

  const login = async (email, password) => startSession(await loginApi(email, password));

  const register = async (email, password) => startSession(await registerApi(email, password));

  const logout = () => {
    clearBrowserSession();
    // A full reload also clears everything held in memory.
    window.location.assign("/login");
  };

  return (
    <AuthContext.Provider value={{ user, checking, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
