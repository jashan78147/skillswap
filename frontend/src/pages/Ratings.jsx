/* ==========================================================================
   Ratings.jsx -- feedback you have received, and feedback you have given.
   ========================================================================== */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { Alert, Avatar, Empty, Loading, Stars } from '../components/ui';

export default function Ratings() {
  const { user } = useAuth();
  const [tab, setTab] = useState('received');
  const [received, setReceived] = useState([]);
  const [given, setGiven] = useState([]);
  const [summary, setSummary] = useState({ average_rating: null, rating_count: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      api.get('/api/ratings/me'),
      api.get('/api/ratings/given'),
      api.get(`/api/ratings/user/${user.id}`),
    ])
      .then(([r, g, s]) => { setReceived(r); setGiven(g); setSummary(s); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [user.id]);

  if (loading) return <Loading />;

  const rows = tab === 'received' ? received : given;

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <h1>Ratings</h1>
        <p className="muted">Feedback from the swaps you have completed.</p>
      </div>

      {error && <div className="mb-2"><Alert kind="error">{error}</Alert></div>}

      <div className="card mb-3">
        <div className="between">
          <div>
            <p className="stat-label">Your average</p>
            <div className="row mt-1">
              <Stars value={summary.average_rating || 0} count={summary.rating_count} />
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div className="stat-value">{summary.rating_count}</div>
            <div className="stat-label">reviews</div>
          </div>
        </div>
      </div>

      <div className="tabs">
        <button className={`tab ${tab === 'received' ? 'active' : ''}`}
                onClick={() => setTab('received')}>
          About you ({received.length})
        </button>
        <button className={`tab ${tab === 'given' ? 'active' : ''}`}
                onClick={() => setTab('given')}>
          Written by you ({given.length})
        </button>
      </div>

      {rows.length === 0 ? (
        <Empty
          icon="★"
          title={tab === 'received' ? 'No ratings yet' : 'You have not rated anyone yet'}
          hint="Ratings unlock once a swap is marked complete."
          action={<Link to="/requests" className="btn btn-primary btn-sm">Go to requests</Link>}
        />
      ) : (
        <div className="col" style={{ gap: 12 }}>
          {rows.map((r) => {
            const personName = tab === 'received' ? r.rater_name : r.ratee_name;
            const personId   = tab === 'received' ? r.rater_id : r.ratee_id;
            return (
              <div key={r.id} className="card">
                <div className="between mb-1" style={{ alignItems: 'flex-start' }}>
                  <div className="row">
                    <Avatar name={personName || '?'} size="avatar-sm" />
                    <div>
                      <strong><Link to={`/users/${personId}`}>{personName}</Link></strong>
                      <p className="small faint">
                        {tab === 'received' ? 'rated you' : 'you rated'} ·{' '}
                        {new Date(r.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <Stars value={r.stars} />
                </div>
                {r.comment && <p className="small muted mt-1">“{r.comment}”</p>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
