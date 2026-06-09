import { Lock, Mail } from "lucide-react";
import { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function AuthModal({ onToken }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    const response = await fetch(`${API_URL}/auth/${mode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    if (!response.ok) {
      setError("Authentication failed");
      return;
    }
    const data = await response.json();
    localStorage.setItem("cliniq_token", data.access_token);
    onToken(data.access_token);
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/35 px-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded border border-slate-200 bg-white p-5 shadow-xl">
        <div className="mb-5">
          <h2 className="text-lg font-semibold text-slate-950">{mode === "login" ? "Sign in" : "Create account"}</h2>
          <p className="mt-1 text-sm text-slate-600">Access ClinIQ clinical retrieval workspace.</p>
        </div>
        <label className="mb-3 block">
          <span className="mb-1 block text-xs font-medium uppercase text-slate-500">Email</span>
          <span className="flex h-10 items-center gap-2 rounded border border-slate-300 px-3">
            <Mail size={16} className="text-slate-500" />
            <input className="min-w-0 flex-1 outline-none" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </span>
        </label>
        <label className="mb-4 block">
          <span className="mb-1 block text-xs font-medium uppercase text-slate-500">Password</span>
          <span className="flex h-10 items-center gap-2 rounded border border-slate-300 px-3">
            <Lock size={16} className="text-slate-500" />
            <input className="min-w-0 flex-1 outline-none" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </span>
        </label>
        {error ? <p className="mb-3 text-sm text-red-600">{error}</p> : null}
        <button className="h-10 w-full rounded bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800" type="submit">
          {mode === "login" ? "Sign in" : "Register"}
        </button>
        <button
          className="mt-3 w-full text-sm text-teal-700 hover:text-teal-900"
          type="button"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "Create an account" : "Use existing account"}
        </button>
      </form>
    </div>
  );
}
