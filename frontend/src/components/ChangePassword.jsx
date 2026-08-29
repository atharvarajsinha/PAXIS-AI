import { useState } from 'react';
import { apiRequest, setToken } from '../services/api.js';
import { PasswordIcon } from './icons.jsx';

const EMPTY = { current_password: '', new_password: '', confirm: '' };

export default function ChangePassword() {
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [saving, setSaving] = useState(false);

  const update = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setDone(false);
    setError('');
  };

  const mismatch = form.confirm.length > 0 && form.new_password !== form.confirm;
  const canSubmit = form.current_password && form.new_password && !mismatch && !saving;

  const submit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;
    setSaving(true);
    setError('');
    try {
      const payload = await apiRequest('/api/auth/password/', {
        method: 'POST',
        body: {
          current_password: form.current_password,
          new_password: form.new_password,
        },
      });
      // The server rotates the token on a password change; adopt the new one so
      // this tab stays signed in.
      setToken(payload.token);
      setForm(EMPTY);
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="panelCard">
      <h2>
        <PasswordIcon size={18} /> Change password
      </h2>
      <p className="fieldHint">
        You stay signed in here. Any other device using this account will be signed out.
      </p>

      {error && <div className="errorBox">{error}</div>}
      {done && <div className="successBox">Password updated.</div>}

      <form onSubmit={submit}>
        <div className="formGrid">
          <div>
            <label htmlFor="current-password">Current password</label>
            <input
              id="current-password"
              type="password"
              autoComplete="current-password"
              value={form.current_password}
              onChange={(e) => update('current_password', e.target.value)}
              placeholder="Your current password"
            />
          </div>
          <div>
            <label htmlFor="new-password">New password</label>
            <input
              id="new-password"
              type="password"
              autoComplete="new-password"
              value={form.new_password}
              onChange={(e) => update('new_password', e.target.value)}
              placeholder="At least 8 characters"
            />
          </div>
          <div>
            <label htmlFor="confirm-password">Confirm new password</label>
            <input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              value={form.confirm}
              onChange={(e) => update('confirm', e.target.value)}
              placeholder="Repeat the new password"
              aria-invalid={mismatch}
            />
            {mismatch && <p className="fieldError">The two passwords do not match.</p>}
          </div>
        </div>

        <div className="formActions">
          <button className="primaryBtn" type="submit" disabled={!canSubmit}>
            {saving ? 'Updating...' : 'Update password'}
          </button>
        </div>
      </form>
    </section>
  );
}
