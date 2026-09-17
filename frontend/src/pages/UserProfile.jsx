/* ==========================================================================
   UserProfile.jsx -- somebody else's public profile.
   ========================================================================== */

import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import SwapModal from '../components/SwapModal';
import { Alert, Avatar, Loading, SkillPill, Stars, Toast } from '../components/ui';

export default function UserProfile() {
  // useParams reads the :id out of the URL /users/:id
  const { id } = useParams();
  const { user } = useAuth();

  const [person, setPerson] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showSwap, setShowSwap] = useState(false);
  const [toast, setToast] = useState('');

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get(`/api/users/${id}`),
      api.get(`/api/ratings/user/${id}`).catch(() => ({ ratings: [] })),
    ])
      .then(([p, r]) => { setPerson(p); setReviews(r.ratings || []); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Loading />;

  if (error) {
    return (
      <div className="page page-narrow">
        <Alert kind="error">{error}</Alert>
        <div className="mt-2"><Link to="/browse" className="btn btn-ghost btn-sm">← Back to browse</Link></div>
      </div>
    );
  }

  const isMe = person.id === user.id;
  const offered = person.skills_offered || [];
  const wanted  = person.skills_wanted || [];

  return (
    <div className="page page-narrow">
      <Toast message={toast} />

      <Link to="/browse" className="small muted">← Back to browse</Link>

      <div className="card mt-2 mb-3">
        <div className="between" style={{ alignItems: 'flex-start' }}>
          <div className="row">
            <Avatar name={person.name} url={person.avatar_url} size="avatar-lg" />
            <div>
              <h1 style={{ fontSize: '1.4rem' }}>{person.name}</h1>
              <p className="small muted">{person.location || 'Location not set'}</p>
              <div className="mt-1">
                <Stars value={person.average_rating || 0} count={person.rating_count} />
              </div>
            </div>
          </div>

          {!isMe && (
            <button className="btn btn-primary" onClick={() => setShowSwap(true)}>
              Request Swap
            </button>
          )}
        </div>

        {person.bio && <p className="muted mt-3">{person.bio}</p>}

        {person.availability && (
          <p className="small muted mt-2">
            <span className="faint">Available:</span> {person.availability}
          </p>
        )}

        {/* Contact details arrive from the server only when an accepted
            swap exists. If it is null, there is nothing to hide client-side. */}
        <div className="mt-3">
          {person.contact_info ? (
            <Alert kind="success">
              Contact unlocked: <strong>{person.contact_info}</strong>
            </Alert>
          ) : !isMe ? (
            <Alert kind="info">
              Contact details are revealed once one of you accepts a swap request.
            </Alert>
          ) : null}
        </div>
      </div>

      <div className="grid grid-2 mb-3">
        <div className="card">
          <h2 className="mb-2">Can teach</h2>
          {offered.length === 0
            ? <p className="small muted">Nothing listed.</p>
            : <div className="row-wrap">
                {offered.map((s) => <SkillPill key={s.id} skill={s} />)}
              </div>}
        </div>

        <div className="card">
          <h2 className="mb-2">Wants to learn</h2>
          {wanted.length === 0
            ? <p className="small muted">Nothing listed.</p>
            : <div className="row-wrap">
                {wanted.map((s) => <SkillPill key={s.id} skill={s} />)}
              </div>}
        </div>
      </div>

      <div className="card">
        <h2 className="mb-2">Reviews ({reviews.length})</h2>
        {reviews.length === 0 ? (
          <p className="small muted">No reviews yet.</p>
        ) : (
          <div className="col" style={{ gap: 14 }}>
            {reviews.map((r) => (
              <div key={r.id} style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
                <div className="between">
                  <strong className="small">{r.rater_name}</strong>
                  <Stars value={r.stars} />
                </div>
                {r.comment && <p className="small muted mt-1">“{r.comment}”</p>}
              </div>
            ))}
          </div>
        )}
      </div>

      {showSwap && (
        <SwapModal
          target={person}
          onClose={() => setShowSwap(false)}
          onSent={(msg) => { setToast(msg); setTimeout(() => setToast(''), 2800); }}
        />
      )}
    </div>
  );
}
