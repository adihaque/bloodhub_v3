"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type User = { id: string; full_name?: string; phone?: string; role?: string };
type Auth = { access_token: string; refresh_token: string; user: User };
type Metrics = Record<string, number | string>;
type RequestRow = { id: string; patient_name: string; blood_group: string; hospital_name: string; status: string; current_wave?: number; total_offers_sent?: number; created_at?: string; has_accepted_donor?: boolean };
type Inspection = { request: Record<string, unknown>; waves: Array<{ wave_number: number; radius_km: number; timeout_seconds: number; status: string; offers: Array<Record<string, unknown>> }>; assignment?: Record<string, unknown> | null };

const API_ROOT = `${(process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "")}/api/v1`;
const AUTH_KEY = "bloodhub.admin.auth";
const metricLabels: Record<string, string> = { total_donors: "Total donors", available_donors: "Available now", active_requests: "Active requests", active_waves: "Active waves", fulfilled_requests: "Fulfilled requests", acceptance_rate: "Acceptance rate" };
const algorithmFields = ["compatibility_exact_pts", "compatibility_compatible_pts", "proximity_weight_pts", "reliability_weight_pts", "interval_weight_pts", "intent_regular_bonus", "intent_when_needed_bonus", "cooldown_days", "wave1_radius_km", "wave1_timeout_sec", "wave1_candidates", "wave2_radius_km", "wave2_timeout_sec", "wave2_candidates", "wave3_radius_km", "wave3_timeout_sec", "wave3_candidates", "wave4_radius_km", "wave4_timeout_sec", "wave4_candidates", "auto_dispatch_whatsapp", "auto_dispatch_in_app", "auto_dispatch_sms"];

function pretty(value: unknown) { return value === null || value === undefined || value === "" ? "—" : String(value); }
function date(value: unknown) { if (!value) return "—"; const parsed = new Date(String(value)); return Number.isNaN(parsed.valueOf()) ? String(value) : parsed.toLocaleString(); }

export default function AdminConsole() {
  const [auth, setAuth] = useState<Auth | null>(null);
  const [booting, setBooting] = useState(true);
  const [login, setLogin] = useState({ phone: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [requests, setRequests] = useState<RequestRow[]>([]);
  const [algorithm, setAlgorithm] = useState<Record<string, unknown> | null>(null);
  const [selected, setSelected] = useState<Inspection | null>(null);

  const api = useCallback(async (path: string, init: RequestInit = {}, retried = false): Promise<any> => {
    if (!auth) throw new Error("Not authenticated");
    const headers = new Headers(init.headers); headers.set("Content-Type", "application/json"); headers.set("Authorization", `Bearer ${auth.access_token}`);
    const response = await fetch(`${API_ROOT}${path}`, { ...init, headers });
    if (response.status === 401 && !retried && auth.refresh_token) {
      const refreshed = await fetch(`${API_ROOT}/auth/refresh`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: auth.refresh_token }) });
      if (refreshed.ok) { const next = await refreshed.json(); const updated = { ...auth, access_token: next.access_token, refresh_token: next.refresh_token || auth.refresh_token, user: next.user || auth.user }; setAuth(updated); localStorage.setItem(AUTH_KEY, JSON.stringify(updated)); const retryHeaders = new Headers(init.headers); retryHeaders.set("Content-Type", "application/json"); retryHeaders.set("Authorization", `Bearer ${updated.access_token}`); const retry = await fetch(`${API_ROOT}${path}`, { ...init, headers: retryHeaders }); if (!retry.ok) throw new Error(`Request failed (${retry.status})`); return retry.status === 204 ? null : retry.json(); }
      setAuth(null); localStorage.removeItem(AUTH_KEY);
    }
    if (!response.ok) { let detail = `Request failed (${response.status})`; try { const body = await response.json(); detail = body.detail || detail; } catch {} throw new Error(detail); }
    if (response.status === 204) return null;
    return response.json();
  }, [auth]);

  const load = useCallback(async () => {
    setBusy(true); setError("");
    try { const [m, r, a] = await Promise.all([api("/admin/metrics"), api("/admin/requests"), api("/admin/algorithm")]); setMetrics(m); setRequests(r); setAlgorithm(a); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to load dashboard"); }
    finally { setBusy(false); }
  }, [api]);

  useEffect(() => { try { const stored = localStorage.getItem(AUTH_KEY); if (stored) setAuth(JSON.parse(stored)); } catch {} setBooting(false); }, []);
  useEffect(() => { if (auth) { if (auth.user.role && auth.user.role !== "ADMIN") setError("This account does not have administrator access."); else load(); } }, [auth, load]);

  async function signIn(event: FormEvent) { event.preventDefault(); setBusy(true); setError(""); try { const response = await fetch(`${API_ROOT}/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(login) }); const body = await response.json(); if (!response.ok) throw new Error(body.detail || "Login failed"); if (body.user?.role !== "ADMIN") throw new Error("Administrator access is required."); const next = { access_token: body.access_token, refresh_token: body.refresh_token, user: body.user }; localStorage.setItem(AUTH_KEY, JSON.stringify(next)); setAuth(next); } catch (e) { setError(e instanceof Error ? e.message : "Login failed"); } finally { setBusy(false); } }
  function signOut() { if (auth?.refresh_token) fetch(`${API_ROOT}/auth/logout`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${auth.access_token}` }, body: JSON.stringify({ refresh_token: auth.refresh_token }) }).catch(() => {}); localStorage.removeItem(AUTH_KEY); setAuth(null); setMetrics(null); }
  async function inspect(id: string) { setBusy(true); setError(""); try { setSelected(await api(`/admin/requests/${id}/inspection`)); } catch (e) { setError(e instanceof Error ? e.message : "Unable to inspect request"); } finally { setBusy(false); } }
  async function triggerWave(id: string) { setBusy(true); setError(""); try { await api(`/admin/requests/${id}/trigger-wave`, { method: "POST" }); await load(); if (selected?.request.id === id) setSelected(await api(`/admin/requests/${id}/inspection`)); } catch (e) { setError(e instanceof Error ? e.message : "Unable to trigger wave"); } finally { setBusy(false); } }
  async function saveAlgorithm(event: FormEvent) { event.preventDefault(); if (!algorithm) return; setBusy(true); setError(""); try { const payload = Object.fromEntries(algorithmFields.filter((key) => algorithm[key] !== undefined).map((key) => [key, Number(algorithm[key])])); setAlgorithm(await api("/admin/algorithm", { method: "PUT", body: JSON.stringify(payload) })); } catch (e) { setError(e instanceof Error ? e.message : "Unable to save algorithm"); } finally { setBusy(false); } }
  async function resetAlgorithm() { if (!confirm("Reset algorithm configuration to clinical defaults?")) return; setBusy(true); try { setAlgorithm(await api("/admin/algorithm/reset", { method: "POST" })); } catch (e) { setError(e instanceof Error ? e.message : "Unable to reset algorithm"); } finally { setBusy(false); } }

  const visibleMetrics = useMemo(() => Object.entries(metricLabels).filter(([key]) => metrics?.[key] !== undefined), [metrics]);
  if (booting) return <div className="login"><div className="login-card">Loading secure console…</div></div>;
  if (!auth) return <main className="login"><form className="login-card" onSubmit={signIn}><div className="brand"><span className="brand-mark">♥</span><span>Blood Hub Operations</span></div><h1>Admin console</h1><p className="muted">Sign in to monitor dispatch and tune matching.</p>{error && <div className="alert">{error}</div>}<div className="field"><label htmlFor="phone">Phone</label><input id="phone" autoComplete="username" value={login.phone} onChange={(e) => setLogin({ ...login, phone: e.target.value })} required /></div><div className="field"><label htmlFor="password">Password</label><input id="password" type="password" autoComplete="current-password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })} required /></div><button className="btn primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button></form></main>;

  return <div className="shell"><header className="topbar"><div className="brand"><span className="brand-mark">♥</span><span>Blood Hub <small>Operations</small></span></div><div className="actions"><small>{auth.user.full_name || auth.user.phone}</small><button className="btn" onClick={signOut}>Sign out</button></div></header><main className="main"><div className="heading"><div><h1>Dispatch overview</h1><div className="muted">Live operational view · {metrics?.active_environment || "environment unavailable"}</div></div><button className="btn" onClick={load} disabled={busy}>{busy ? "Refreshing…" : "Refresh data"}</button></div>{error && <div className="alert">{error}</div>}<section className="cards">{visibleMetrics.map(([key, label]) => <div className="card" key={key}><label>{label}</label><div className="value">{pretty(metrics?.[key])}{key === "acceptance_rate" ? "%" : ""}</div>{key === "available_donors" && <div className="muted">ready to match</div>}</div>)}</section><div className="layout"><section className="panel"><h2>Active and recent requests</h2><div className="table-wrap"><table className="clickable"><thead><tr><th>Patient</th><th>Blood</th><th>Hospital</th><th>Status</th><th>Wave</th><th>Offers</th></tr></thead><tbody>{requests.length === 0 ? <tr><td colSpan={6}>No requests found.</td></tr> : requests.map((row) => <tr key={row.id} onClick={() => inspect(row.id)}><td><strong>{row.patient_name}</strong><br /><span className="muted">{date(row.created_at)}</span></td><td>{row.blood_group}</td><td>{row.hospital_name}</td><td><span className={`status ${row.has_accepted_donor ? "ok" : row.status === "MATCHING" ? "warn" : ""}`}>{row.status}</span></td><td>{pretty(row.current_wave)}</td><td>{pretty(row.total_offers_sent)}</td></tr>)}</tbody></table></div></section><section className="panel"><div className="heading"><h2>Algorithm configuration</h2><div className="actions"><button className="btn" onClick={resetAlgorithm} disabled={busy}>Reset</button></div></div>{algorithm && <form onSubmit={saveAlgorithm}><div className="form-grid">{algorithmFields.map((key) => <div className="field" key={key}><label htmlFor={key}>{key.replaceAll("_", " ")}</label><input id={key} type="number" step="any" value={String(algorithm[key] ?? "")} onChange={(e) => setAlgorithm({ ...algorithm, [key]: e.target.value })} /></div>)}</div><button className="btn primary" style={{ marginTop: 16 }} disabled={busy}>Save configuration</button></form>}</section></div></main>{selected && <><div className="backdrop" onClick={() => setSelected(null)} /><aside className="drawer"><div className="drawer-head"><div><h2>Request inspection</h2><div className="muted">{pretty(selected.request.id)}</div></div><button className="btn" onClick={() => setSelected(null)}>Close</button></div><div className="kv"><b>Patient</b><span>{pretty(selected.request.patient_name)}</span><b>Hospital</b><span>{pretty(selected.request.hospital_name)}</span><b>Blood / component</b><span>{pretty(selected.request.blood_group)} · {pretty(selected.request.component)}</span><b>Status</b><span>{pretty(selected.request.status)} · wave {pretty(selected.request.current_wave)}</span><b>Requester contact</b><span>{pretty(selected.request.contact_phone)}</span></div><div className="actions"><button className="btn primary" onClick={() => triggerWave(String(selected.request.id))} disabled={busy}>Trigger next wave</button></div><h2 style={{ marginTop: 26 }}>Dispatch waves</h2>{selected.waves.map((wave) => <div key={wave.wave_number} className="offer"><strong>Wave {wave.wave_number}</strong> · {wave.radius_km} km · {wave.timeout_seconds}s · <span className="status">{wave.status}</span>{wave.offers.map((offer) => <div className="offer" key={String(offer.offer_id)}><strong>{pretty(offer.donor_name)}</strong> · {pretty(offer.blood_group)} · score {pretty(offer.score)}<div className="muted">{pretty(offer.status)} · {pretty(offer.distance_km)} km · latency {pretty(offer.response_latency_seconds)}s</div><div className="muted">Channels: {pretty(offer.channels)}</div>{Boolean(offer.whatsapp_url) && <a href={String(offer.whatsapp_url)} target="_blank" rel="noreferrer">Open WhatsApp link</a>}</div>)}</div>)}{selected.assignment && <><h2>Assignment</h2><div className="kv"><b>Donor</b><span>{pretty(selected.assignment.donor_name)}</span><b>Phone</b><span>{pretty(selected.assignment.donor_phone)}</span><b>Assigned</b><span>{date(selected.assignment.assigned_at)}</span></div></>}</aside></>}</div>;
}



