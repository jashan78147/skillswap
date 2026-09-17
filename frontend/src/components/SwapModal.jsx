/* ==========================================================================
   SwapModal.jsx -- the "propose a swap" dialog.
   Used from Browse, Matches and a user's profile page, so it lives here
   rather than being written three times.
   ========================================================================== */

import { useEffect, useState } from 'react';
import { api } from '../api';
import { Alert, Avatar } from './ui';

export default function SwapModal({ target, onClose, onSent }) {
  const [mySkills, setMySkills] = useState([]);
  const [offeredId, setOfferedId] = useState('');
  const [requestedId, setRequestedId] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  // Load my offered skills so I can choose what to put on the table.
  useEffect(() => {
    api
      .get('/api/skills/me')
      .then((rows) => setMySkills(rows.filter((s) => s.kind === 'offered')))
      .catch((e) => setError(e.message));
  }, []);

  // Escape closes the dialog -- expected behaviour for any modal.
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const theirOffers = target.skills_offered || [];

  async function send() {
    setBusy(true);
    setError('');
    try {
      await api.post('/api/swaps', {
        to_user_id: target.id,
        offered_skill_id: offeredId ? Number(offeredId) : null,
        requested_skill_id: requestedId ? Number(requestedId) : null,
        message: message.trim() || null,
      });
      onSent?.(`Swap request sent to ${target.name}.`);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 150,
        background: 'rgba(0,0,0,.65)', backdropFilter: 'blur(3px)',
        display: 'grid', placeItems: 'center', padding: 20,
      }}
    >
      {/* stopPropagation stops a click INSIDE the card from closing it */}
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{ width: '100%', maxWidth: 480 }}
      >
        <div className="row mb-3">
          <Avatar name={target.name} url={target.avatar_url} />
          <div>
            <h2 style={{ fontSize: '1.1rem' }}>Propose a swap</h2>
            <p className="small muted">with {target.name}</p>
          </div>
        </div>

        {error && <div className="mb-2"><Alert kind="error">{error}</Alert></div>}

        <div className="field">
          <label className="label">You will teach</label>
          <select className="select" value={offeredId} onChange={(e) => setOfferedId(e.target.value)}>
            <option value="">— choose one of your skills —</option>
            {mySkills.map((s) => (
              <option key={s.id} value={s.id}>{s.name} ({s.level})</option>
            ))}
          </select>
          {mySkills.length === 0 && (
            <span className="small faint">
              You have not added any offered skills yet. You can still send a
              request, but adding one makes it far more likely to be accepted.
            </span>
          )}
        </div>

        <div className="field">
          <label className="label">You want to learn</label>
          <select
            className="select" value={requestedId}
            onChange={(e) => setRequestedId(e.target.value)}
          >
            <option value="">— choose one of their skills —</option>
            {theirOffers.map((s) => (
              <option key={s.id} value={s.id}>{s.name} ({s.level})</option>
            ))}
          </select>
        </div>

        <div className="field">
          <label className="label">Message</label>
          <textarea
            className="textarea" value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={`Hi ${target.name.split(' ')[0]}, I would love to swap — are you free at the weekend?`}
          />
        </div>

        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={send} disabled={busy}>
            {busy ? <><span className="spinner" /> Sending…</> : 'Send Request'}
          </button>
        </div>
      </div>
    </div>
  );
}
