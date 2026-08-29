import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import BrandMark, { APP_FULL_NAME, APP_NAME } from '../components/BrandMark.jsx';
import Footer from '../components/Footer.jsx';
import { CircleCheckIcon, GoalIcon, PasswordIcon } from '../components/icons.jsx';

export default function Register() {
  const { user, loading, register } = useAuth();
  // Set before the request so the redirect below sends a brand-new account to
  // the profile page rather than straight into an empty chat.
  const [destination, setDestination] = useState('/dashboard');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (loading) return <div className="authShell"><div className="authCard">Checking your session...</div></div>;
  if (user) return <Navigate to={destination} replace />;

  const mismatch = confirm.length > 0 && password !== confirm;

  const submit = async (event) => {
    event.preventDefault();
    if (password !== confirm) {
      setError('The two passwords do not match.');
      return;
    }
    setError('');
    setSubmitting(true);
    // New accounts land on the profile so the profiling engine has something to
    // work with before the first roadmap is generated.
    setDestination('/profile');
    try {
      await register(email.trim(), password, fullName.trim());
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="authShell">
      <div className="authIntro">
        <BrandMark size={64} />
        <h1>{APP_NAME}</h1>
        <p className="authFullName">{APP_FULL_NAME}</p>
        <p>
          Create an account to save your roadmaps, keep every chat, and watch your skills
          build up over time.
        </p>
        <ul className="authPoints">
          <li><CircleCheckIcon size={18} /> Free to use</li>
          <li><PasswordIcon size={18} /> Your chats stay private to your account</li>
          <li><GoalIcon size={18} /> Roadmaps tuned to your experience level</li>
        </ul>
      </div>

      <form className="authCard" onSubmit={submit}>
        <h2>Create your account</h2>
        <p className="authSubtitle">It takes less than a minute.</p>

        {error && <div className="errorBox">{error}</div>}

        <label htmlFor="register-name">Full name <span className="optional">(optional)</span></label>
        <input
          id="register-name"
          type="text"
          autoComplete="name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Your name"
        />

        <label htmlFor="register-email">Email</label>
        <input
          id="register-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />

        <label htmlFor="register-password">Password</label>
        <input
          id="register-password"
          type="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="At least 8 characters"
        />
        <p className="fieldHint">
          Use at least 8 characters. Avoid common passwords and anything close to your email.
        </p>

        <label htmlFor="register-confirm">Confirm password</label>
        <input
          id="register-confirm"
          type="password"
          autoComplete="new-password"
          required
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="Repeat your password"
          aria-invalid={mismatch}
        />
        {mismatch && <p className="fieldError">The two passwords do not match.</p>}

        <button
          className="primaryBtn"
          type="submit"
          disabled={submitting || !email || !password || mismatch}
        >
          {submitting ? 'Creating account...' : 'Create account'}
        </button>

        <p className="authSwitch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
        <p className="authSwitch"><Link to="/">Back to home</Link></p>
      </form>

      <div className="authFooter"><Footer /></div>
    </div>
  );
}
