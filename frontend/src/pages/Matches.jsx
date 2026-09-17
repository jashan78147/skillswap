/* ==========================================================================
   Matches.jsx -- ranked swap suggestions from the backend algorithm.
   ========================================================================== */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import SwapModal from '../components/SwapModal';
import UserCard from '../components/UserCard';
import { Alert, Empty, Loading, Toast } from '../components/ui';

export default function Matches() {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [target, setTarget] = useState(null);
  const [toast, setToast] = useState('');
  const [showHow, setShowHow] = useState(false);

  function load() {
    setLoading(true);
    api
      .get('/api/matches?limit=20')
      .then(setMatches)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  const flash = (msg) => { setToast(msg); setTimeout(() => setToast(''), 2600); };

  const mutual = matches.filter((m) => m.is_mutual);
  const oneWay = matches.filter((m) => !m.is_mutual);

  return (
    <div className="page">
      <Toast message={toast} />

      <div className="page-head between">
        <div>
          <h1>Smart matches</h1>
          <p className="muted">
            Ranked by how well your skills line up with theirs.
          </p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={() => setShowHow(!showHow)}>
          {showHow ? 'Hide' : 'How does this work?'}
        </button>
      </div>

      {showHow && (
        <div className="card mb-3">
          <h3 className="mb-1">How the score is calculated</h3>
          <p className="small muted mb-2">
            Pure skill-overlap arithmetic, computed on the server. No external
            AI service, so it never fails because of a network problem and
            gives the same answer every time.
          </p>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>Signal</th><th>Points</th></tr>
              </thead>
              <tbody>
                <tr><td>Mutual match — you each want what the other offers</td><td>+40</td></tr>
                <tr><td>Each skill they can teach you</td><td>+12 (max 36)</td></tr>
                <tr><td>Each skill you can teach them</td><td>+8 (max 24)</td></tr>
                <tr><td>Same location</td><td>+6</td></tr>
                <tr><td>Their rating history</td><td>up to +8</td></tr>
              </tbody>
            </table>
          </div>
          <p className="small muted mt-2">
            Skill names are compared word by word, so <code>React</code> still
            matches <code>React / Frontend</code>.
          </p>
        </div>
      )}

      {error && <div className="mb-2"><Alert kind="error">{error}</Alert></div>}

      {loading ? (
        <Loading />
      ) : matches.length === 0 ? (
        <Empty
          icon="⇄"
          title="No matches yet"
          hint="Matching needs at least one skill you offer and one you want. Add them on your dashboard."
          action={<Link to="/dashboard" className="btn btn-primary btn-sm">Go to dashboard</Link>}
        />
      ) : (
        <>
          {mutual.length > 0 && (
            <>
              <h2 className="mb-1">Two-way matches</h2>
              <p className="small muted mb-2">
                You each have something the other wants — the strongest kind of swap.
              </p>
              <div className="grid grid-2 mb-3">
                {mutual.map((m) => (
                  <UserCard key={m.user.id} person={m.user} match={m} onSwap={setTarget} />
                ))}
              </div>
            </>
          )}

          {oneWay.length > 0 && (
            <>
              <h2 className="mb-1">One-way matches</h2>
              <p className="small muted mb-2">
                Overlap in one direction only. Still worth a message.
              </p>
              <div className="grid grid-2">
                {oneWay.map((m) => (
                  <UserCard key={m.user.id} person={m.user} match={m} onSwap={setTarget} />
                ))}
              </div>
            </>
          )}
        </>
      )}

      {target && (
        <SwapModal
          target={target}
          onClose={() => setTarget(null)}
          onSent={(msg) => { flash(msg); load(); }}
        />
      )}
    </div>
  );
}
