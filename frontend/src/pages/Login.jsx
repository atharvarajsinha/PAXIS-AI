import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import BrandMark, { APP_FULL_NAME, APP_NAME } from '../components/BrandMark.jsx';
import Footer from '../components/Footer.jsx';
import { ChatIcon, RoadmapIcon, TrendingUpIcon } from '../components/icons.jsx';

export default function Login() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (loading) return <div className="authShell"><div className="authCard">Checking your session...</div></div>;
  if (user) return <Navigate to={location.state?.from || '/dashboard'} replace />;

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate(location.state?.from || '/dashboard', { replace: true });
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
          Sign in to pick up your roadmap where you left off, revisit past chats, and track
          how far you have come.
        </p>
        <ul className="authPoints">
          <li><RoadmapIcon size={18} /> Personalized roadmaps built around your profile</li>
          <li><ChatIcon size={18} /> Every conversation saved to your account</li>
          <li><TrendingUpIcon size={18} /> Progress, skills and milestones on one dashboard</li>
        </ul>
      </div>

      <form className="authCard" onSubmit={submit}>
        <h2>Welcome back</h2>
        <p className="authSubtitle">Sign in to continue learning.</p>

        {error && <div className="errorBox">{error}</div>}

        <label htmlFor="login-email">Email</label>
        <input
          id="login-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />

        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Your password"
        />

        <button className="primaryBtn" type="submit" disabled={submitting || !email || !password}>
          {submitting ? 'Signing in...' : 'Sign in'}
        </button>

        <p className="authSwitch">
          New here? <Link to="/register">Create an account</Link>
        </p>
        <p className="authSwitch"><Link to="/">Back to home</Link></p>
      </form>

      <div className="authFooter"><Footer /></div>
    </div>
  );
}
