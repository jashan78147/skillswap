/* ==========================================================================
   Requests.jsx -- the swap inbox.
   Which buttons appear depends on who you are in the swap and what state
   it is in, mirroring the rules the backend enforces.
   ========================================================================== */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { Alert, Empty, Loading, StarPicker, StatusBadge, Toast } from '../components/ui';

/* ------------------------------------------------------------ rate box -- */
function RateDialog({ swap, otherName, onClose, onDone }) {
  const [stars, setStars] = useState(5);
  const [comment, setComment] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    setError('');
    try {
      await api.post('/api/ratings', {
        swap_id: swap.id,
        stars,
        comment: comment.trim() || null,
      });
      onDone(`Thanks — your rating of ${otherName} was saved.`);
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
      <div className="card" onClick={(e) => e.stopPropagation()}
           style={{ width: '100%', maxWidth: 420 }}>
        <h2 className="mb-1">Rate {otherName}</h2>
        <p className="small muted mb-2">How did the swap go?</p>

        {error && <div className="mb-2"><Alert kind="error">{error}</Alert></div>}

        <div className="mb-2"><StarPicker value={stars} onChange={setStars} /></div>

        <div className="field">
          <label className="label">Comment (optional)</label>
          <textarea
            className="textarea" value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="What went well? Anything they should know for next time?"
          />
        </div>

        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={submit} disabled={busy}>
            {busy ? <><span className="spinner" /> Saving…</> : 'Submit rating'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* --------------------------------------------------------------- page -- */
export default function Requests() {
  const { user } = useAuth();

  const [tab, setTab] = useState('incoming');
  const [swaps, setSwaps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [rating, setRating] = useState(null);
  const [toast, setToast] = useState('');

  const flash = (msg) => { setToast(msg); setTimeout(() => setToast(''), 2800); };

  const load = useCallback(() => {
    setLoading(true);
    api
      .get(`/api/swaps?box=${tab === 'all' ? 'all' : tab}`)
      .then(setSwaps)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [tab]);

  useEffect(load, [load]);

  async function act(swapId, action, successMsg) {
    setError('');
    try {
      await api.post(`/api/swaps/${swapId}/${action}`);
      flash(successMsg);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  const counts = {
    pending: swaps.filter((s) => s.status === 'pending').length,
  };

  return (
    <div className="page">
      <Toast message={toast} />

      <div className="page-head">
        <h1>Swap requests</h1>
        <p className="muted">Everything you have sent and received.</p>
      </div>

      <div className="tabs">
        {['incoming', 'outgoing', 'all'].map((t) => (
          <button
            key={t}
            className={`tab ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            {t === 'incoming' ? 'Received' : t === 'outgoing' ? 'Sent' : 'All'}
            {t === tab && counts.pending > 0 && (
              <span className="nav-count">{counts.pending}</span>
            )}
          </button>
        ))}
      </div>

      {error && <div className="mb-2"><Alert kind="error">{error}</Alert></div>}

      {loading ? (
        <Loading />
      ) : swaps.length === 0 ? (
        <Empty
          icon="⇄"
          title={tab === 'incoming' ? 'No requests received yet' : 'You have not sent any requests'}
          hint="Find someone on the Browse or Matches page to get started."
          action={<Link to="/matches" className="btn btn-primary btn-sm">See matches</Link>}
        />
      ) : (
        <div className="col" style={{ gap: 14 }}>
          {swaps.map((s) => {
            const iSent = s.from_user_id === user.id;
            const otherName = iSent ? s.to_user_name : s.from_user_name;
            const otherId = iSent ? s.to_user_id : s.from_user_id;

            return (
              <div key={s.id} className="card">
                <div className="between mb-2" style={{ alignItems: 'flex-start' }}>
                  <div>
                    <div className="row-wrap">
                      <strong>
                        {iSent ? 'To' : 'From'}{' '}
                        <Link to={`/users/${otherId}`}>{otherName}</Link>
                      </strong>
                      <StatusBadge status={s.status} />
                      <span className="badge">{iSent ? 'sent' : 'received'}</span>
                    </div>
                    <p className="small faint mt-1">
                      {new Date(s.created_at).toLocaleDateString()} ·{' '}
                      {new Date(s.created_at).toLocaleTimeString([], {
                        hour: '2-digit', minute: '2-digit',
                      })}
                    </p>
                  </div>
                </div>

                {/* --- what is on the table --- */}
                <div className="row-wrap mb-2">
                  {s.offered_skill_name && (
                    <span className="pill pill-offer">
                      {iSent ? 'You teach' : 'They teach'}: {s.offered_skill_name}
                    </span>
                  )}
                  {s.requested_skill_name && (
                    <span className="pill pill-want">
                      {iSent ? 'You learn' : 'They learn'}: {s.requested_skill_name}
                    </span>
                  )}
                </div>

                {s.message && (
                  <p className="small muted mb-2"
                     style={{ borderLeft: '2px solid var(--border-strong)', paddingLeft: 11 }}>
                    “{s.message}”
                  </p>
                )}

                {/* --- contact details, unlocked by acceptance --- */}
                {s.contact_info && (
                  <div className="mb-2">
                    <Alert kind="success">
                      Contact unlocked: <strong>{s.contact_info}</strong>
                    </Alert>
                  </div>
                )}

                {/* --- actions, matching the backend rules exactly --- */}
                <div className="row-wrap">
                  {s.status === 'pending' && !iSent && (
                    <>
                      <button className="btn btn-primary btn-sm"
                              onClick={() => act(s.id, 'accept', `Swap with ${otherName} accepted.`)}>
                        Accept
                      </button>
                      <button className="btn btn-danger btn-sm"
                              onClick={() => act(s.id, 'reject', 'Request rejected.')}>
                        Reject
                      </button>
                    </>
                  )}

                  {s.status === 'pending' && iSent && (
                    <button className="btn btn-ghost btn-sm"
                            onClick={() => act(s.id, 'cancel', 'Request withdrawn.')}>
                      Cancel request
                    </button>
                  )}

                  {s.status === 'accepted' && (
                    <button className="btn btn-primary btn-sm"
                            onClick={() => act(s.id, 'complete', 'Marked complete — you can now leave a rating.')}>
                      Mark as complete
                    </button>
                  )}

                  {s.status === 'completed' && !s.already_rated && (
                    <button className="btn btn-primary btn-sm"
                            onClick={() => setRating({ swap: s, otherName })}>
                      Leave a rating
                    </button>
                  )}

                  {s.status === 'completed' && s.already_rated && (
                    <span className="small muted">You have rated this swap.</span>
                  )}

                  {(s.status === 'rejected' || s.status === 'cancelled') && (
                    <span className="small faint">No further action.</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {rating && (
        <RateDialog
          swap={rating.swap}
          otherName={rating.otherName}
          onClose={() => setRating(null)}
          onDone={(msg) => { flash(msg); load(); }}
        />
      )}
    </div>
  );
}
