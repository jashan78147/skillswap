/* ==========================================================================
   Browse.jsx -- search and filter the directory of swappers.
   ========================================================================== */

import { useEffect, useState } from 'react';
import { api, qs } from '../api';
import SwapModal from '../components/SwapModal';
import UserCard from '../components/UserCard';
import { Alert, Empty, Loading, Toast } from '../components/ui';

export default function Browse() {
  const [query, setQuery] = useState('');
  const [skill, setSkill] = useState('');
  const [level, setLevel] = useState('');
  const [page, setPage] = useState(1);

  const [data, setData] = useState({ results: [], total: 0, has_more: false });
  const [popular, setPopular] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [target, setTarget] = useState(null);   // who the swap modal is for
  const [toast, setToast] = useState('');

  useEffect(() => {
    api.get('/api/skills/popular?limit=10').then(setPopular).catch(() => {});
  }, []);

  /* Debounced search: wait 350ms after the last keystroke before asking
     the server. Typing "python" would otherwise fire six requests.      */
  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => {
      api
        .get('/api/users/browse' + qs({ q: query, skill, level, page, page_size: 12 }))
        .then(setData)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }, 350);

    // React runs this cleanup before the next effect, cancelling the
    // previous timer. That is what makes the debounce work.
    return () => clearTimeout(timer);
  }, [query, skill, level, page]);

  // Any filter change sends you back to page 1.
  useEffect(() => { setPage(1); }, [query, skill, level]);

  const flash = (msg) => { setToast(msg); setTimeout(() => setToast(''), 2600); };

  return (
    <div className="page">
      <Toast message={toast} />

      <div className="page-head">
        <h1>Browse swappers</h1>
        <p className="muted">Find someone who teaches what you want to learn.</p>
      </div>

      {/* ---------------- filters ---------------- */}
      <div className="card card-tight mb-3">
        <div className="row-wrap">
          <input
            className="input grow"
            style={{ minWidth: 220 }}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, skill, city or bio…"
          />
          <select className="select" style={{ width: 170 }} value={level}
                  onChange={(e) => setLevel(e.target.value)}>
            <option value="">Any level</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="expert">Expert</option>
          </select>
          {(query || skill || level) && (
            <button
              className="btn btn-ghost"
              onClick={() => { setQuery(''); setSkill(''); setLevel(''); }}
            >
              Clear
            </button>
          )}
        </div>

        {popular.length > 0 && (
          <div className="row-wrap mt-2">
            <span className="small faint">Popular:</span>
            {popular.map((p) => (
              <button
                key={p.name}
                className={`pill ${skill === p.name ? 'pill-offer' : ''}`}
                style={{ cursor: 'pointer' }}
                onClick={() => setSkill(skill === p.name ? '' : p.name)}
              >
                {p.name} <span className="faint">{p.count}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {error && <div className="mb-2"><Alert kind="error">{error}</Alert></div>}

      {loading ? (
        <Loading />
      ) : data.results.length === 0 ? (
        <Empty
          icon="⌕"
          title="Nobody matched that search"
          hint="Try a broader term, or clear the filters."
        />
      ) : (
        <>
          <p className="small muted mb-2">
            Showing {data.results.length} of {data.total}
          </p>

          <div className="grid grid-2">
            {data.results.map((person) => (
              <UserCard key={person.id} person={person} onSwap={setTarget} />
            ))}
          </div>

          {(page > 1 || data.has_more) && (
            <div className="row mt-3" style={{ justifyContent: 'center' }}>
              <button
                className="btn btn-ghost" disabled={page === 1}
                onClick={() => setPage(page - 1)}
              >
                ← Previous
              </button>
              <span className="small muted">Page {page}</span>
              <button
                className="btn btn-ghost" disabled={!data.has_more}
                onClick={() => setPage(page + 1)}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}

      {target && (
        <SwapModal
          target={target}
          onClose={() => setTarget(null)}
          onSent={flash}
        />
      )}
    </div>
  );
}
