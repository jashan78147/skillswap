/* ==========================================================================
   Profile.jsx -- edit your own profile.
   ========================================================================== */

import { useEffect, useState } from 'react';
import { api } from '../api';
import { useAuth } from '../auth';
import { Alert, Avatar, Toast } from '../components/ui';

export default function Profile() {
  const { user, refresh } = useAuth();

  const [form, setForm] = useState({
    name: '', location: '', bio: '', availability: '',
    contact_info: '', avatar_url: '', is_public: true,
  });
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [busy, setBusy] = useState(false);

  // Copy the signed-in user's details into the form once they are known.
  useEffect(() => {
    if (!user) return;
    setForm({
      name: user.name || '',
      location: user.location || '',
      bio: user.bio || '',
      availability: user.availability || '',
      contact_info: user.contact_info || '',
      avatar_url: user.avatar_url || '',
      is_public: user.is_public,
    });
  }, [user]);

  const update = (key) => (e) =>
    setForm({ ...form, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.patch('/api/users/me', {
        name: form.name.trim(),
        location: form.location.trim() || null,
        bio: form.bio.trim() || null,
        availability: form.availability.trim() || null,
        contact_info: form.contact_info.trim() || null,
        avatar_url: form.avatar_url.trim() || null,
        is_public: form.is_public,
      });
      await refresh();
      setToast('Profile saved.');
      setTimeout(() => setToast(''), 2600);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page page-narrow">
      <Toast message={toast} />

      <div className="page-head">
        <h1>Your profile</h1>
        <p className="muted">This is what other swappers see.</p>
      </div>

      <form onSubmit={save} className="card">
        <div className="row mb-3">
          <Avatar name={form.name} url={form.avatar_url} size="avatar-lg" />
          <div className="grow">
            <div className="field" style={{ marginBottom: 0 }}>
              <label className="label" htmlFor="avatar">Avatar image URL (optional)</label>
              <input id="avatar" className="input" value={form.avatar_url}
                     onChange={update('avatar_url')} placeholder="https://…" />
            </div>
          </div>
        </div>

        {error && <div className="mb-2"><Alert kind="error">{error}</Alert></div>}

        <div className="field">
          <label className="label" htmlFor="name">Full name</label>
          <input id="name" className="input" value={form.name}
                 onChange={update('name')} required />
        </div>

        <div className="field">
          <label className="label" htmlFor="loc">Location</label>
          <input id="loc" className="input" value={form.location}
                 onChange={update('location')} placeholder="Jalandhar, Punjab" />
        </div>

        <div className="field">
          <label className="label" htmlFor="bio">Bio</label>
          <textarea id="bio" className="textarea" value={form.bio}
                    onChange={update('bio')}
                    placeholder="A sentence or two about what you teach and what you want to learn." />
        </div>

        <div className="field">
          <label className="label" htmlFor="avail">Availability</label>
          <input id="avail" className="input" value={form.availability}
                 onChange={update('availability')} placeholder="Weekends, weekday evenings" />
        </div>

        <div className="field">
          <label className="label" htmlFor="contact">Contact details</label>
          <input id="contact" className="input" value={form.contact_info}
                 onChange={update('contact_info')} placeholder="email or phone" />
          <span className="small faint">
            Private. Only shown to someone after you and they have an accepted swap.
          </span>
        </div>

        <label className="row card card-tight mb-3"
               style={{ background: 'var(--surface-2)', cursor: 'pointer', alignItems: 'flex-start', gap: 10 }}>
          <input type="checkbox" checked={form.is_public} onChange={update('is_public')}
                 style={{ marginTop: 3, accentColor: 'var(--accent)' }} />
          <span>
            <strong style={{ fontSize: '0.9rem' }}>Public profile</strong>
            <p className="small muted">
              When off, you are hidden from the Browse page and from other
              people's match suggestions. You can still send requests yourself.
            </p>
          </span>
        </label>

        <button className="btn btn-primary" disabled={busy}>
          {busy ? <><span className="spinner" /> Saving…</> : 'Save changes'}
        </button>
      </form>
    </div>
  );
}
