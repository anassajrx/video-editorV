"use client";
import { useState } from "react";

export default function Login() {
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function go(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr("");
    const r = await fetch("/api/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password: pw }) });
    if (r.ok) location.reload();
    else { setErr("Mot de passe incorrect"); setBusy(false); }
  }
  return (
    <div className="wrap">
      <form className="card login" onSubmit={go}>
        <span className="brand">Video Studio</span>
        <label className="label">Mot de passe</label>
        <input className="input" type="password" autoFocus value={pw} onChange={(e) => setPw(e.target.value)} />
        <button className="btn wide" disabled={busy || !pw}>{busy ? "…" : "Entrer"}</button>
        {err && <div className="err">{err}</div>}
      </form>
    </div>
  );
}
