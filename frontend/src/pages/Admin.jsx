/* ==========================================================================
   Admin.jsx -- the moderation dashboard.
   Every request here needs an admin token; the backend rejects anyone else.
   ========================================================================== */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE, api, getToken } from '../api';
import { useAuth } from '../auth';
import { Alert, Avatar, Empty, Loading, Toast } from '../components/ui';

export default function Admin() {
  const { user } = useAuth();

  const [tab, setTab] = useState('overview');
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [skills, setSkills] = useState([]);
  const [broadcasts, setBroadcasts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');

  const [bTitle, setBTitle] = useState('');
  const [bBody, setBBody] = useState('');
  const [userQuery, setUserQuery] = useState('');
  const [flaggedOnly, setFlaggedOnly] = useState(false);

  const flash = (msg) => { setToast(msg); setTimeout(() => setToast(''), 2800); };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [st, us, sk, bc] = await Promise.all([
        api.get('/api/admin/stats'),
        api.get('/api/admin/users'),
        api.get(`/api/admin/skills${flaggedOnly ? '?flagged_only=true' : ''}`),
        api.get('/api/broadcasts?limit=20'),
      ]);
      setStats(st); setUsers(us); setSkills(sk); setBroadcasts(bc);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [flaggedOnly]);

  useEffect(() => { load(); }, [load]);

  async function run(fn, msg) {
    setError('');
    try {
      await fn();
      flash(msg);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  /* CSV endpoints need the Authorization header, and a plain <a href> cannot
     send one. So fetch the file with the token, then trigger a save.      */
  async function downloadCsv(name) {
    try {
      const res = await fetch(`${API_BASE}/api/admin/reports/${name}.csv`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) throw new Error(`Download failed (${res.status}).`);

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `skillswap_${name}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      flash(`${name}.csv downloaded.`);
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <Loading />;

  const visibleUsers = users.filter(
    (u) =>
      !userQuery ||
      u.name.toLowerCase().includes(userQuery.toLowerCase()) ||
      u.email.toLowerCase().includes(userQuery.toLowerCase())
  );

  return (
    <div className="page">
      <Toast message={toast} />

      <div className="page-head">
        <div className="row-wrap">
          <h1>Admin</h1>
          <span className="badge badge-admin">moderator</span>
        </div>
        <p className="muted">Platform health, moderation and reporting.</p>
      </div>

      <div className="tabs">
        {['overview', 'users', 'skills', 'broadcasts', 'reports'].map((t) => (
          <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t[0].toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {error && <div className="mb-2"><Alert kind="error">{error}</Alert></div>}

      {/* ------------------------------------------------- overview ---- */}
      {tab === 'overview' && stats && (
        <div className="grid grid-4">
          {[
            ['Total users', stats.total_users],
            ['Banned users', stats.banned_users],
            ['Total skills', stats.total_skills],
            ['Flagged skills', stats.flagged_skills],
            ['Pending swaps', stats.pending_swaps],
            ['Accepted swaps', stats.accepted_swaps],
            ['Completed swaps', stats.completed_swaps],
            ['Ratings left', stats.total_ratings],
          ].map(([label, value]) => (
            <div className="stat" key={label}>
              <div className="stat-value">{value}</div>
              <div className="stat-label">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* ---------------------------------------------------- users ---- */}
      {tab === 'users' && (
        <>
          <input
            className="input mb-2" style={{ maxWidth: 340 }}
            value={userQuery} onChange={(e) => setUserQuery(e.target.value)}
            placeholder="Filter by name or email…"
          />
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>User</th><th>Email</th><th>Location</th><th>Status</th><th></th>
                </tr>
              </thead>
              <tbody>
                {visibleUsers.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <div className="row">
                        <Avatar name={u.name} url={u.avatar_url} size="avatar-sm" />
                        <Link to={`/users/${u.id}`}>{u.name}</Link>
                      </div>
                    </td>
                    <td className="muted">{u.email}</td>
                    <td className="muted">{u.location || '—'}</td>
                    <td>
                      <div className="row-wrap">
                        {u.is_admin && <span className="badge badge-admin">admin</span>}
                        {u.is_banned && <span className="badge badge-banned">banned</span>}
                        {!u.is_public && <span className="badge">private</span>}
                        {!u.is_admin && !u.is_banned && u.is_public && (
                          <span className="small faint">active</span>
                        )}
                      </div>
                    </td>
                    <td>
                      {u.id === user.id ? (
                        <span className="small faint">you</span>
                      ) : u.is_banned ? (
                        <button className="btn btn-ghost btn-sm"
                                onClick={() => run(() => api.post(`/api/admin/users/${u.id}/unban`),
                                                   `${u.name} reinstated.`)}>
                          Unban
                        </button>
                      ) : (
                        <button className="btn btn-danger btn-sm"
                                onClick={() => run(() => api.post(`/api/admin/users/${u.id}/ban`),
                                                   `${u.name} banned.`)}>
                          Ban
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* --------------------------------------------------- skills ---- */}
      {tab === 'skills' && (
        <>
          <label className="row mb-2" style={{ cursor: 'pointer' }}>
            <input type="checkbox" checked={flaggedOnly}
                   onChange={(e) => setFlaggedOnly(e.target.checked)}
                   style={{ accentColor: 'var(--accent)' }} />
            <span className="small">Show only flagged listings</span>
          </label>

          {skills.length === 0 ? (
            <Empty icon="✓" title="Nothing to moderate" hint="No listings match this filter." />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th>Skill</th><th>Kind</th><th>Level</th><th>Status</th><th></th></tr>
                </thead>
                <tbody>
                  {skills.map((s) => (
                    <tr key={s.id}>
                      <td>
                        <strong>{s.name}</strong>
                        {s.description && <p className="small muted">{s.description}</p>}
                      </td>
                      <td className="muted">{s.kind}</td>
                      <td className="muted">{s.level}</td>
                      <td>
                        {s.is_approved ? (
                          <span className="small faint">visible</span>
                        ) : (
                          <>
                            <span className="badge badge-banned">hidden</span>
                            {s.rejection_reason && (
                              <p className="small faint mt-1">{s.rejection_reason}</p>
                            )}
                          </>
                        )}
                      </td>
                      <td>
                        {s.is_approved ? (
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => {
                              const reason = prompt(
                                'Why is this listing being hidden?',
                                'Spam or misleading listing.'
                              );
                              if (reason === null) return;
                              run(
                                () => api.post(`/api/admin/skills/${s.id}/flag`, { reason }),
                                `"${s.name}" hidden.`
                              );
                            }}
                          >
                            Flag
                          </button>
                        ) : (
                          <button className="btn btn-ghost btn-sm"
                                  onClick={() => run(() => api.post(`/api/admin/skills/${s.id}/approve`),
                                                     `"${s.name}" restored.`)}>
                            Restore
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* ----------------------------------------------- broadcasts ---- */}
      {tab === 'broadcasts' && (
        <div className="grid grid-2" style={{ alignItems: 'start' }}>
          <div className="card">
            <h2 className="mb-2">New announcement</h2>
            <div className="field">
              <label className="label">Title</label>
              <input className="input" value={bTitle} onChange={(e) => setBTitle(e.target.value)}
                     placeholder="Scheduled downtime" />
            </div>
            <div className="field">
              <label className="label">Message</label>
              <textarea className="textarea" value={bBody} onChange={(e) => setBBody(e.target.value)}
                        placeholder="What do users need to know?" />
            </div>
            <button
              className="btn btn-primary"
              disabled={!bTitle.trim() || !bBody.trim()}
              onClick={() =>
                run(async () => {
                  await api.post('/api/admin/broadcasts', { title: bTitle, body: bBody });
                  setBTitle(''); setBBody('');
                }, 'Announcement published.')
              }
            >
              Publish
            </button>
          </div>

          <div className="col" style={{ gap: 12 }}>
            {broadcasts.length === 0 ? (
              <Empty icon="◻" title="No announcements yet" />
            ) : (
              broadcasts.map((b) => (
                <div key={b.id} className="card card-tight">
                  <div className="between">
                    <strong>{b.title}</strong>
                    <button className="pill-x"
                            onClick={() => run(() => api.del(`/api/admin/broadcasts/${b.id}`),
                                               'Announcement removed.')}>
                      ×
                    </button>
                  </div>
                  <p className="small muted mt-1">{b.body}</p>
                  <p className="small faint mt-1">
                    {new Date(b.created_at).toLocaleDateString()}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* -------------------------------------------------- reports ---- */}
      {tab === 'reports' && (
        <div className="card" style={{ maxWidth: 560 }}>
          <h2 className="mb-1">Download reports</h2>
          <p className="small muted mb-3">
            Exported as CSV, which opens directly in Excel or Google Sheets.
          </p>
          <div className="col">
            {[
              ['users', 'Every account, with location, status and join date'],
              ['swaps', 'Every swap request and its current status'],
              ['ratings', 'Every rating left, with comments'],
            ].map(([name, desc]) => (
              <div key={name} className="between card card-tight"
                   style={{ background: 'var(--surface-2)' }}>
                <div>
                  <strong className="small">{name}.csv</strong>
                  <p className="small muted">{desc}</p>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={() => downloadCsv(name)}>
                  Download
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
