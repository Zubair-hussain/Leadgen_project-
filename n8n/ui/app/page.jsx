'use client';

import { useState } from 'react';

const WEBHOOK_URL = process.env.NEXT_PUBLIC_N8N_WEBHOOK_URL || '';

export default function Home() {
  const [category, setCategory] = useState('Dentists');
  const [location, setLocation] = useState('Austin');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [leads, setLeads] = useState([]);
  const [busy, setBusy] = useState(false);

  const run = async (e) => {
    e.preventDefault();
    setError('');
    setLeads([]);
    if (!WEBHOOK_URL) {
      setError('Set NEXT_PUBLIC_N8N_WEBHOOK_URL to your n8n webhook Production URL.');
      return;
    }
    setBusy(true);
    setStatus('Triggering n8n workflow…');
    try {
      const res = await fetch(WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, location }),
      });
      if (!res.ok) throw new Error(`Webhook responded ${res.status}`);
      const data = await res.json();
      const rows = Array.isArray(data.leads) ? data.leads : [];
      setLeads(rows);
      setStatus(`Done — ${data.count ?? rows.length} lead(s).`);
    } catch (err) {
      setError(err.message || 'Request failed');
      setStatus('');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="wrap">
      <div className="brand">
        <span className="dot" />
        <h1>LeadGen · n8n Control</h1>
      </div>
      <p className="sub">
        Trigger the <code>leadgen-webhook</code> workflow on demand and preview the leads it returns.
      </p>

      <form className="card" onSubmit={run}>
        <div className="grid">
          <div>
            <label htmlFor="category">Niche / Category</label>
            <input id="category" value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. Dentists" />
          </div>
          <div>
            <label htmlFor="location">Location</label>
            <input id="location" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. Austin" />
          </div>
        </div>
        <button className="btn" type="submit" disabled={busy}>
          {busy ? 'Running…' : 'Generate leads'}
        </button>
        {status && <p className="status">{status}</p>}
        {error && <p className="status error">{error}</p>}
      </form>

      {leads.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Email</th>
              <th>Source</th>
              <th>Location</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((l, i) => (
              <tr key={l.id ?? i}>
                <td>{l.email || '—'}</td>
                <td>{l.source || '—'}</td>
                <td>{l.location || '—'}</td>
                <td>
                  <span className={`pill ${l.is_verified ? 'ok' : 'no'}`}>
                    {l.is_verified ? 'verified' : 'pending'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p className="foot">
        Configure the webhook URL in <code>.env.local</code> — see this folder's README.
      </p>
    </main>
  );
}
