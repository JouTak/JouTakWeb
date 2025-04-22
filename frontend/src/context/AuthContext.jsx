import React, { createContext, useState, useEffect } from "react";
import { setAuthToken, setupAxiosInterceptors } from "../services/api";

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  useEffect(() => {
    setupAxiosInterceptors(logout);
  }, []);

  const [authState, setAuthState] = useState(() => {
    const accessToken = localStorage.getItem("accessToken");
    const refreshToken = localStorage.getItem("refreshToken");
    if (accessToken && refreshToken) {
      setAuthToken(accessToken);
      return {
        isAuthenticated: true,
        tokens: { access: accessToken, refresh: refreshToken },
      };
    } else {
      return {
        isAuthenticated: false,
        tokens: null,
      };
    }
  });

  const login = (data) => {
    localStorage.setItem("accessToken", data.access);
    localStorage.setItem("refreshToken", data.refresh);
    setAuthToken(data.access);
    setAuthState({ tokens: data, isAuthenticated: true });
  };

  const logout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    setAuthToken(null);
    setAuthState({ isAuthenticated: false, tokens: null });
  };

  return (
    <AuthContext.Provider value={{ authState, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};