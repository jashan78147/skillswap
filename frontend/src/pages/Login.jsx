/* ==========================================================================
   Login.jsx -- sign in to an existing account.
   ========================================================================== */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { Alert } from '../components/ui';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await login(form.email, form.password);
      navigate('/dashboard');
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
          <h1 style={{ fontSize: '1.5rem' }}>Welcome back</h1>
          <p className="muted small center">Sign in to keep swapping.</p>
        </div>

        <form onSubmit={handleSubmit}>
          {error && <div className="mb-2"><Alert kind="error">{error}</Alert></div>}

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
              onChange={update('password')} placeholder="Your password"
              required autoComplete="current-password"
            />
          </div>

          <button className="btn btn-primary btn-block" disabled={busy}>
            {busy ? <><span className="spinner" /> Signing in…</> : 'Sign In'}
          </button>
        </form>

        <p className="small muted center mt-3">
          New here? <Link to="/signup">Create an account</Link>
        </p>
      </div>
    </div>
  );
}
