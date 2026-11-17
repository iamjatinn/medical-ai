// src/pages/Login.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const errorText = (err) => {
  const detail = err.response?.data?.detail;

  if (typeof detail === "string") return detail;

  // Validation errors from the server arrive as a list.
  if (Array.isArray(detail) && detail.length > 0) {
    return detail[0].msg.replace(/^Value error, /, "");
  }

  if (err.message === "Network Error") {
    return "Cannot reach the server. Please check that the backend is running.";
  }

  return "Something went wrong. Please try again.";
};

export const Login = () => {
  const navigate = useNavigate();
  const { login, register } = useAuth();

  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const isRegister = mode === "register";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setBusy(true);

    try {
      if (isRegister) {
        await register(email, password);
      } else {
        await login(email, password);
      }
      navigate("/");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const switchMode = () => {
    setMode(isRegister ? "login" : "register");
    setError(null);
  };

  return (
    <div className="min-h-[calc(100vh-4rem-4rem)] flex items-center justify-center py-12 px-4">
      <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-sm p-8">
        <div className="flex items-center space-x-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white">
            <Activity className="w-5 h-5 stroke-[2.5]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              {isRegister ? "Create your account" : "Welcome back"}
            </h1>
            <p className="text-xs text-slate-500">
              Your reports are private and visible only to you.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-xs font-semibold text-slate-700 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-xs font-semibold text-slate-700 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={isRegister ? 8 : undefined}
              autoComplete={isRegister ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {isRegister && (
              <p className="text-[11px] text-slate-500 mt-1">At least 8 characters.</p>
            )}
          </div>

          {error && (
            <div
              role="alert"
              className="rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs px-3 py-2"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full inline-flex items-center justify-center space-x-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold py-2.5 transition-colors"
          >
            {busy && <Loader2 className="w-4 h-4 animate-spin" />}
            <span>{isRegister ? "Create account" : "Log in"}</span>
          </button>
        </form>

        <p className="text-xs text-slate-600 text-center mt-5">
          {isRegister ? "Already have an account?" : "New here?"}{" "}
          <button
            type="button"
            onClick={switchMode}
            className="text-blue-700 font-semibold hover:underline"
          >
            {isRegister ? "Log in" : "Create an account"}
          </button>
        </p>
      </div>
    </div>
  );
};
