/* ==========================================================================
   Dashboard.jsx -- the signed-in home screen.
   Add and remove your own skills, see your numbers, preview top matches.
   ========================================================================== */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { Alert, Empty, Loading, SkillPill, Stars, Toast } from '../components/ui';

export default function Dashboard() {
  const { user } = useAuth();

  const [skills, setSkills] = useState([]);
  const [swaps, setSwaps] = useState([]);
  const [matches, setMatches] = useState([]);
  const [reputation, setReputation] = useState({ average_rating: null, rating_count: 0 });
  const [broadcasts, setBroadcasts] = useState([]);
  const [loading, setLoading] = useState(true);

  // --- the "add a skill" form ---
  const [name, setName] = useState('');
  const [kind, setKind] = useState('offered');
  const [level, setLevel] = useState('intermediate');
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');

  const flash = (msg) => { setToast(msg); setTimeout(() => setToast(''), 2600); };

  /* Load everything the dashboard needs. Promise.all fires the requests
     together rather than waiting for each one in turn.                   */
  const load = useCallback(async () => {
    try {
      const [s, sw, m, rep, bc] = await Promise.all([
        api.get('/api/skills/me'),
        api.get('/api/swaps'),
        api.get('/api/matches?limit=3').catch(() => []),
        api.get(`/api/ratings/user/${user.id}`).catch(() => ({ average_rating: null, rating_count: 0 })),
        api.get('/api/broadcasts?limit=1').catch(() => []),
      ]);
      setSkills(s); setSwaps(sw); setMatches(m); setReputation(rep); setBroadcasts(bc);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user.id]);

  useEffect(() => { load(); }, [load]);

  async function addSkill(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setError('');
    try {
      await api.post('/api/skills', { name: name.trim(), kind, level });
      setName('');
      flash('Skill added.');
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function removeSkill(id) {
    try {
      await api.del(`/api/skills/${id}`);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <Loading />;

  const offered = skills.filter((s) => s.kind === 'offered');
  const wanted  = skills.filter((s) => s.kind === 'wanted');
  const pending = swaps.filter((s) => s.status === 'pending' && s.to_user_id === user.id);
  const active  = swaps.filter((s) => s.status === 'accepted');

  return (
    <div className="page">
      <Toast message={toast} />

      <div className="page-head">
        <h1>Welcome back, {user.name.split(' ')[0]}</h1>
        <p className="muted">Here is where your swapping stands today.</p>
      </div>

      {broadcasts.length > 0 && (
        <div className="mb-3">
          <Alert kind="info">
            <strong>{broadcasts[0].title}</strong> — {broadcasts[0].body}
          </Alert>
        </div>
      )}

      {/* ---------------- stat tiles ---------------- */}
      <div className="grid grid-4 mb-3">
        <div className="stat">
          <div className="stat-value">{offered.length}</div>
          <div className="stat-label">Skills offered</div>
        </div>
        <div className="stat">
          <div className="stat-value">{wanted.length}</div>
          <div className="stat-label">Skills wanted</div>
        </div>
        <div className="stat">
          <div className="stat-value" style={{ color: pending.length ? 'var(--accent)' : undefined }}>
            {pending.length}
          </div>
          <div className="stat-label">Awaiting your reply</div>
        </div>
        <div className="stat">
          <div className="stat-value">{active.length}</div>
          <div className="stat-label">Active swaps</div>
        </div>
      </div>

      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        {/* ---------------- skills ---------------- */}
        <div className="card">
          <h2 className="mb-1">Your skills</h2>
          <p className="small muted mb-2">
            What you can teach, and what you would like to learn.
          </p>

          {error && <div className="mb-2"><Alert kind="error">{error}</Alert></div>}

          <form onSubmit={addSkill} className="mb-3">
            <div className="field">
              <input
                className="input" value={name} onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Python, Guitar, Public Speaking"
              />
            </div>
            <div className="row-wrap">
              <select className="select grow" value={kind} onChange={(e) => setKind(e.target.value)}>
                <option value="offered">I can teach this</option>
                <option value="wanted">I want to learn this</option>
              </select>
              <select className="select grow" value={level} onChange={(e) => setLevel(e.target.value)}>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="expert">Expert</option>
              </select>
              <button className="btn btn-primary">Add</button>
            </div>
          </form>

          <div className="mb-2">
            <p className="small faint mb-1">Can teach ({offered.length})</p>
            {offered.length === 0
              ? <p className="small muted">Nothing yet.</p>
              : <div className="row-wrap">
                  {offered.map((s) => (
                    <SkillPill key={s.id} skill={s} onRemove={() => removeSkill(s.id)} />
                  ))}
                </div>}
          </div>

          <div>
            <p className="small faint mb-1">Wants to learn ({wanted.length})</p>
            {wanted.length === 0
              ? <p className="small muted">Nothing yet.</p>
              : <div className="row-wrap">
                  {wanted.map((s) => (
                    <SkillPill key={s.id} skill={s} onRemove={() => removeSkill(s.id)} />
                  ))}
                </div>}
          </div>

          {/* Flagged listings are hidden from everyone else, so the owner
              should be told why rather than left confused. */}
          {skills.some((s) => !s.is_approved) && (
            <div className="mt-2">
              <Alert kind="error">
                Some of your listings were hidden by a moderator:{' '}
                {skills.filter((s) => !s.is_approved).map((s) => s.name).join(', ')}.
              </Alert>
            </div>
          )}
        </div>

        {/* ---------------- matches + reputation ---------------- */}
        <div className="col" style={{ gap: 16 }}>
          <div className="card">
            <div className="between mb-2">
              <h2>Top matches</h2>
              <Link to="/matches" className="small">See all →</Link>
            </div>

            {matches.length === 0 ? (
              <Empty
                icon="⇄"
                title="No matches yet"
                hint="Add at least one skill you offer and one you want, and suggestions appear here."
              />
            ) : (
              <div className="col" style={{ gap: 12 }}>
                {matches.map((m) => (
                  <Link
                    key={m.user.id}
                    to={`/users/${m.user.id}`}
                    className="between card card-tight card-hover"
                    style={{ color: 'inherit', background: 'var(--surface-2)' }}
                  >
                    <div>
                      <div className="row">
                        <strong>{m.user.name}</strong>
                        {m.is_mutual && <span className="badge badge-accepted">mutual</span>}
                      </div>
                      <p className="small muted">{m.reason}</p>
                    </div>
                    <div className="match-score">{m.score}<span>/100</span></div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="mb-2">Your reputation</h2>
            <div className="row">
              <Stars value={reputation.average_rating || 0} count={reputation.rating_count} />
            </div>
            <p className="small muted mt-1">
              {reputation.rating_count === 0
                ? 'Complete a swap to start collecting feedback.'
                : `Based on ${reputation.rating_count} completed swap${reputation.rating_count > 1 ? 's' : ''}.`}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
