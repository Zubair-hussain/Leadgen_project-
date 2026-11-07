'use client';

import React, { useEffect, useState } from "react";
import { Check, AlertTriangle, Clock, Send, Trash2, Ban, ShieldOff } from "lucide-react";
import api from "../../services/api";

const STATUS_BADGE = {
  draft: ["ba2", "Draft"],
  queued: ["bg2", "Approved · queued"],
  sending: ["bg2", "Sending"],
  sent: ["bg2", "Sent"],
  skipped: ["br2", "Skipped"],
  failed: ["br2", "Failed"],
  cancelled: ["br2", "Cancelled"],
};

const FILTERS = [
  { id: "draft", label: "Drafts" },
  { id: "queued", label: "Queued" },
  { id: "sent", label: "Sent" },
  { id: "", label: "All" },
];

const EMPTY_DRAFT = { lead_id: "", to_email: "", subject: "", body: "" };
const icon = { width: 14, height: 14 };

const errorText = (error, fallback) => {
  const data = error?.response?.data;
  if (data?.problems) return data.problems.join(" ");
  if (data?.error) return data.error;
  if (data && typeof data === "object") return Object.values(data).flat().join(" ");
  return error?.message || fallback;
};

export default function OutreachTab({ leads = [] }) {
  const [status, setStatus] = useState(null);
  const [messages, setMessages] = useState([]);
  const [filter, setFilter] = useState("draft");
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [suppressions, setSuppressions] = useState([]);
  const [newSuppression, setNewSuppression] = useState("");
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  const sendable = leads.filter(lead => lead.email && lead.email !== "—" && lead.is_verified === true);

  const loadStatus = async () => {
    const { data } = await api.get("outreach/status/");
    setStatus(data);
  };
  const loadMessages = async (wanted = filter) => {
    const { data } = await api.get(`outreach/messages/?page_size=100${wanted ? `&status=${wanted}` : ""}`);
    setMessages(Array.isArray(data) ? data : data?.results || []);
  };
  const loadSuppressions = async () => {
    const { data } = await api.get("outreach/suppressions/");
    setSuppressions(Array.isArray(data) ? data : data?.results || []);
  };
  const refresh = async (wanted = filter) => {
    try {
      await Promise.all([loadStatus(), loadMessages(wanted), loadSuppressions()]);
    } catch (error) {
      setNotice({ ok: false, text: errorText(error, "Could not load outreach data.") });
    }
  };

  useEffect(() => { refresh(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const pickFilter = id => { setFilter(id); refresh(id); };

  const run = async (action, success) => {
    setBusy(true);
    setNotice(null);
    try {
      await action();
      setNotice({ ok: true, text: success });
      await refresh();
    } catch (error) {
      setNotice({ ok: false, text: errorText(error, "Request failed.") });
    } finally {
      setBusy(false);
    }
  };

  const saveDraft = e => {
    e.preventDefault();
    const payload = { subject: draft.subject, body: draft.body };
    if (draft.lead_id) payload.lead_id = Number(draft.lead_id);
    if (draft.to_email) payload.to_email = draft.to_email;
    run(async () => {
      await api.post("outreach/messages/", payload);
      setDraft(EMPTY_DRAFT);
    }, "Draft saved. Review it below, then approve.");
  };

  const approve = id => run(() => api.post(`outreach/messages/${id}/approve/`), "Approved. It will send within the limits and send window.");
  const cancel = id => run(() => api.post(`outreach/messages/${id}/cancel/`), "Cancelled.");
  const remove = id => run(() => api.delete(`outreach/messages/${id}/`), "Draft deleted.");
  const suppress = e => {
    e.preventDefault();
    if (!newSuppression.trim()) return;
    run(async () => {
      await api.post("outreach/suppressions/", { email: newSuppression.trim(), reason: "manual" });
      setNewSuppression("");
    }, "Added to the do-not-contact list.");
  };
  const unsuppress = id => run(() => api.delete(`outreach/suppressions/${id}/`), "Removed from the do-not-contact list.");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>
      <div className="card sender-card">
        <div className="ch">
          <div>
            <div className="ctitle">Sending status</div>
            <div className="csub">{status?.from_email || "No sender configured yet"}</div>
          </div>
          {status && (status.dry_run
            ? <span className="bdg ba2"><Clock style={icon} />Dry run: nothing is really sent</span>
            : <span className="bdg bg2"><Check style={icon} />Live sending</span>)}
        </div>
        {status && (
          <div>
            <div className="sender-metric"><span>{status.transport === "gmail" ? "Gmail" : "Mailbox"} connected</span><strong>{(status.mail_configured ?? status.gmail_configured) ? "Yes" : "No"}</strong></div>
            <div className="sender-metric"><span>Sent today</span><strong>{status.sent_today} / {status.daily_limit}{status.daily_limit_max > status.daily_limit ? ` (warming up to ${status.daily_limit_max})` : ""}</strong></div>
            {status.threads_sent > 0 && (
              <div className="sender-metric"><span>Replies</span><strong>{status.threads_replied} / {status.threads_sent} ({Math.round((100 * status.threads_replied) / status.threads_sent)}%)</strong></div>
            )}
            <div className="sender-metric"><span>Follow-ups queued</span><strong>{status.queued_followups ?? 0}</strong></div>
            <div className="sender-metric"><span>Sent this hour</span><strong>{status.sent_last_hour} / {status.hourly_limit}</strong></div>
            <div className="sender-metric"><span>Waiting in queue</span><strong>{status.queued}</strong></div>
            <div className="sender-metric"><span>Inside send window</span><strong>{status.in_send_window ? "Yes" : "No (queued until business hours)"}</strong></div>
          </div>
        )}
      </div>

      {notice && (
        <span className={`bdg ${notice.ok ? "bg2" : "br2"}`} role="status" style={{ alignSelf: "flex-start", whiteSpace: "normal" }}>
          {notice.ok ? <Check style={icon} /> : <AlertTriangle style={icon} />}{notice.text}
        </span>
      )}

      <form className="card sender-card" onSubmit={saveDraft}>
        <div>
          <div className="ctitle">New email</div>
          <div className="csub">Short, personal, one clear ask. An opt-out line is added automatically.</div>
        </div>
        <div className="sender-check">
          <div>
            <label className="fl" htmlFor="outreach-lead">Verified lead</label>
            <select id="outreach-lead" className="fi" value={draft.lead_id}
              onChange={e => setDraft(d => ({ ...d, lead_id: e.target.value, to_email: "" }))}>
              <option value="">Choose a lead…</option>
              {sendable.map(lead => <option key={lead.id} value={lead.id}>{lead.email}</option>)}
            </select>
          </div>
          <div>
            <label className="fl" htmlFor="outreach-to">Or type an address</label>
            <input id="outreach-to" className="fi" placeholder="name@business.com" value={draft.to_email}
              onChange={e => setDraft(d => ({ ...d, to_email: e.target.value, lead_id: "" }))} />
          </div>
          <div className="wide">
            <label className="fl" htmlFor="outreach-subject">Subject</label>
            <input id="outreach-subject" className="fi" required maxLength={200} value={draft.subject}
              onChange={e => setDraft(d => ({ ...d, subject: e.target.value }))} />
          </div>
          <div className="wide">
            <label className="fl" htmlFor="outreach-body">Body</label>
            <textarea id="outreach-body" className="ta" required style={{ minHeight: 150 }} value={draft.body}
              onChange={e => setDraft(d => ({ ...d, body: e.target.value }))} />
            <div className="csub">{draft.body.split(/\s+/).filter(Boolean).length} words (aim for 120 or fewer)</div>
          </div>
        </div>
        <button className="bp" style={{ alignSelf: "flex-start" }} disabled={busy}>Save draft</button>
      </form>

      <div className="card sender-card">
        <div className="ch">
          <div><div className="ctitle">Messages</div><div className="csub">Nothing is sent until you approve it.</div></div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {FILTERS.map(f => (
              <button key={f.id || "all"} type="button" className={filter === f.id ? "bp" : "bs"} onClick={() => pickFilter(f.id)}>{f.label}</button>
            ))}
          </div>
        </div>
        {messages.length === 0 && <div className="csub">No messages here.</div>}
        {messages.map(message => {
          const [badge, label] = STATUS_BADGE[message.status] || ["ba2", message.status];
          return (
            <div key={message.id} className="rb" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div className="rr">
                <span className="rk" style={{ overflowWrap: "anywhere" }}>{message.to_email}</span>
                <span className={`bdg ${badge}`}>{label}{message.dry_run ? " (dry run)" : ""}</span>
              </div>
              <strong style={{ overflowWrap: "anywhere" }}>{message.subject}</strong>
              <div style={{ whiteSpace: "pre-wrap", fontSize: 13, color: "var(--t2)", overflowWrap: "anywhere" }}>{message.body}</div>
              {message.status === "draft" && (message.notified_at
                ? <span className="csub">Review email sent to you</span>
                : message.notify_error && <span className="bdg br2" style={{ whiteSpace: "normal" }}>Review email failed: {message.notify_error}</span>)}
              {message.warnings?.map(w => <span key={w} className="bdg ba2" style={{ whiteSpace: "normal" }}><AlertTriangle style={icon} />{w}</span>)}
              {message.skip_reason && <span className="bdg br2" style={{ whiteSpace: "normal" }}>{message.skip_reason}</span>}
              {message.error && <span className="bdg br2" style={{ whiteSpace: "normal" }}>{message.error}</span>}
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {message.status === "draft" && <button type="button" className="bp" disabled={busy} onClick={() => approve(message.id)}><Send style={icon} />Approve</button>}
                {["draft", "queued"].includes(message.status) && <button type="button" className="bs" disabled={busy} onClick={() => cancel(message.id)}><Ban style={icon} />Cancel</button>}
                {message.status === "draft" && <button type="button" className="bd" disabled={busy} aria-label="Delete draft" onClick={() => remove(message.id)}><Trash2 style={icon} /></button>}
              </div>
            </div>
          );
        })}
      </div>

      <form className="card sender-card" onSubmit={suppress}>
        <div>
          <div className="ctitle">Do-not-contact list</div>
          <div className="csub">Anyone here is never emailed. Pending emails to them are cancelled.</div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input className="fi" style={{ flex: "1 1 200px" }} placeholder="email@business.com" aria-label="Email to block"
            value={newSuppression} onChange={e => setNewSuppression(e.target.value)} />
          <button className="bs" disabled={busy}><ShieldOff style={icon} />Block</button>
        </div>
        {suppressions.map(item => (
          <div className="rr" key={item.id}>
            <span className="rk" style={{ overflowWrap: "anywhere" }}>{item.email} · {item.reason}</span>
            <button type="button" className="bd" disabled={busy} aria-label={`Unblock ${item.email}`} onClick={() => unsuppress(item.id)}><Trash2 style={icon} /></button>
          </div>
        ))}
      </form>
    </div>
  );
}
