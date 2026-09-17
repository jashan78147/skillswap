/* ==========================================================================
   ProfileSetup.jsx -- the one-step onboarding screen shown after signup.
   Layout follows the reference design: two columns, progress bar, tag
   inputs for skills offered and wanted.
   ========================================================================== */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { Alert } from '../components/ui';

/** A reusable "type a word, press Enter, it becomes a pill" input. */
function TagInput({ label, placeholder, tags, onAdd, onRemove, tone }) {
  const [draft, setDraft] = useState('');

  function commit(e) {
    // Enter and comma both finish a tag -- people expect both.
    if (e.key !== 'Enter' && e.key !== ',') return;
    e.preventDefault();
    const value = draft.trim().replace(/,$/, '');
    if (!value) return;
    onAdd(value);
    setDraft('');
  }

  return (
    <div className="field">
      <label className="label">{label}</label>
      {tags.length > 0 && (
        <div className="row-wrap mb-1">
          {tags.map((t) => (
            <span key={t} className={`pill ${tone}`}>
              {t}
              <button className="pill-x" onClick={() => onRemove(t)} aria-label={`Remove ${t}`}>
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      <input
        className="input"
        value={draft}
        placeholder={placeholder}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={commit}
      />
    </div>
  );
}

export default function ProfileSetup() {
  const { refresh } = useAuth();
  const navigate = useNavigate();

  const [location, setLocation] = useState('');
  const [bio, setBio] = useState('');
  const [availability, setAvailability] = useState('');
  const [contact, setContact] = useState('');
  const [offered, setOffered] = useState([]);
  const [wanted, setWanted] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [locating, setLocating] = useState(false);

  /* The browser can give exact coordinates, but turning those into a city
     name needs an external service -- a network call that could fail
     during a demo. So we fill in coordinates and let you type over them. */
  function detectLocation() {
    if (!navigator.geolocation) {
      setError('This browser cannot detect location.');
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        setLocation(`${latitude.toFixed(3)}, ${longitude.toFixed(3)}`);
        setLocating(false);
      },
      () => {
        setError('Could not get your location. You can type it instead.');
        setLocating(false);
      }
    );
  }

  async function finish() {
    setBusy(true);
    setError('');
    try {
      await api.patch('/api/users/me', {
        location: location.trim() || null,
        bio: bio.trim() || null,
        availability: availability.trim() || null,
        contact_info: contact.trim() || null,
      });

      // Skills are separate records, so each one is its own request.
      // Promise.allSettled sends them together and does not abort the whole
      // batch if one is a duplicate.
      await Promise.allSettled([
        ...offered.map((name) => api.post('/api/skills', { name, kind: 'offered' })),
        ...wanted.map((name) => api.post('/api/skills', { name, kind: 'wanted' })),
      ]);

      await refresh();
      navigate('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="card" style={{ width: '100%', maxWidth: 860 }}>
        <div className="between mb-1">
          <h1 style={{ fontSize: '1.45rem' }}>Set Up Your Swapper Profile</h1>
          <span className="badge badge-admin">Step 1 of 1</span>
        </div>
        <p className="muted small">Help community members discover your capabilities.</p>

        <div className="match-bar mt-2 mb-3">
          <div className="match-bar-fill" style={{ width: '100%' }} />
        </div>

        {error && <div className="mb-2"><Alert kind="error">{error}</Alert></div>}

        <div className="grid grid-2" style={{ alignItems: 'start' }}>
          {/* ---------------- left column ---------------- */}
          <div>
            <div className="field">
              <label className="label" htmlFor="loc">City &amp; Location</label>
              <input
                id="loc" className="input" value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Jalandhar, Punjab"
              />
            </div>

            <button
              type="button"
              className="card card-tight card-hover mb-2"
              onClick={detectLocation}
              style={{
                width: '100%', background: 'var(--surface-2)', cursor: 'pointer',
                color: 'var(--muted)', font: 'inherit', textAlign: 'center',
              }}
            >
              <div style={{ fontSize: '1.3rem', marginBottom: 4 }}>◎</div>
              {locating ? 'Detecting…' : 'Click to detect GPS location'}
            </button>

            <div className="field">
              <label className="label" htmlFor="bio">Swapper Bio</label>
              <textarea
                id="bio" className="textarea" value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="Full stack engineer looking to swap React tutoring for Spanish speech practice."
              />
            </div>

            <div className="field">
              <label className="label" htmlFor="avail">Availability</label>
              <input
                id="avail" className="input" value={availability}
                onChange={(e) => setAvailability(e.target.value)}
                placeholder="Weekends and weekday evenings"
              />
            </div>
          </div>

          {/* ---------------- right column ---------------- */}
          <div>
            <TagInput
              label="Skills You Can Offer"
              placeholder="+ Type a skill and press Enter"
              tags={offered} tone="pill-offer"
              onAdd={(t) => setOffered([...new Set([...offered, t])])}
              onRemove={(t) => setOffered(offered.filter((x) => x !== t))}
            />

            <TagInput
              label="Skills You Want to Learn"
              placeholder="+ Add a skill you want"
              tags={wanted} tone="pill-want"
              onAdd={(t) => setWanted([...new Set([...wanted, t])])}
              onRemove={(t) => setWanted(wanted.filter((x) => x !== t))}
            />

            <div className="field">
              <label className="label" htmlFor="contact">Contact Details</label>
              <input
                id="contact" className="input" value={contact}
                onChange={(e) => setContact(e.target.value)}
                placeholder="email or phone"
              />
              <span className="small faint">
                Kept private. Only revealed once you accept a swap with someone.
              </span>
            </div>
          </div>
        </div>

        <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '22px 0' }} />

        <div className="between">
          <button className="btn btn-ghost" onClick={() => navigate('/dashboard')}>
            Skip for now
          </button>
          <button className="btn btn-primary" onClick={finish} disabled={busy}>
            {busy ? <><span className="spinner" /> Saving…</> : 'Finish Setup & Enter Dashboard →'}
          </button>
        </div>
      </div>
    </div>
  );
}
