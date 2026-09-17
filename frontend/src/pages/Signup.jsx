/* ==========================================================================
   Signup.jsx -- create an account.
   Layout follows the reference design: centred card, logo, three fields,
   agreement checkbox, full-width primary button.
   ========================================================================== */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { Alert } from '../components/ui';

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();

  // useState gives a component memory. `form` holds what is typed;
  // setForm updates it and tells React to redraw.
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function handleSubmit(e) {
    // Without this the browser reloads the whole page on submit,
    // which would wipe the React app and lose the typed values.
    e.preventDefault();
    setError('');

    if (!agreed) {
      setError('Please accept the community guidelines to continue.');
      return;
    }

    setBusy(true);
    try {
      await signup(form.name, form.email, form.password);
      // New accounts go straight to profile setup, as in the reference flow.
      navigate('/profile-setup');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card card">
        <div className="auth-logo">
          <span className="brand-mark" style={{ width: 42, height: 42, fontSize: 21 }}>⇄</span>
          <h1 style={{ fontSize: '1.5rem' }}>Join the network</h1>
          <p className="muted small center">
            Trade what you know for what you want to learn.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          {error && <div className="mb-2"><Alert kind="error">{error}</Alert></div>}

          <div className="field">
            <label className="label" htmlFor="name">Full Name</label>
            <input
              id="name" className="input" value={form.name} onChange={update('name')}
              placeholder="Jashanpreet Singh" required autoComplete="name"
            />
          </div>

          <div className="field">
            <label className="label" htmlFor="email">Email Address</label>
            <input
              id="email" className="input" type="email" value={form.email}
              onChange={update('email')} placeholder="you@example.com"
              required autoComplete="email"
            />
          </div>

          <div className="field">
            <label className="label" htmlFor="password">Password</label>
            <input
              id="password" className="input" type="password" value={form.password}
              onChange={update('password')} placeholder="At least 6 characters"
              required minLength={6} autoComplete="new-password"
            />
          </div>

          <label className="row mb-2" style={{ alignItems: 'flex-start', gap: 9, cursor: 'pointer' }}>
            <input
              type="checkbox" checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              style={{ marginTop: 3, accentColor: 'var(--accent)' }}
            />
            <span className="small muted">
              I agree to the SkillSwap community guidelines and to exchanging
              skills respectfully.
            </span>
          </label>

          <button className="btn btn-primary btn-block" disabled={busy}>
            {busy ? <><span className="spinner" /> Creating account…</> : 'Create Account'}
          </button>
        </form>

        <p className="small muted center mt-3">
          Already swapping? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
