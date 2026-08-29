import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { useChat } from '../context/ChatContext.jsx';
import BrandMark, { APP_NAME, APP_TAGLINE } from './BrandMark.jsx';
import InstallButton from './InstallButton.jsx';
import { applyTheme, isDarkTheme, setDarkTheme } from '../services/preferences.js';
import {
  ChatIcon,
  CloseIcon,
  DashboardIcon,
  LogOutIcon,
  MenuIcon,
  MoonIcon,
  ProfileIcon,
  SunIcon,
} from './icons.jsx';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', Icon: DashboardIcon },
  { to: '/chat', label: 'Chat', Icon: ChatIcon },
  { to: '/profile', label: 'Profile', Icon: ProfileIcon },
];

function initialsFor(user) {
  const name = user?.profile?.full_name?.trim();
  if (name) {
    return name
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0].toUpperCase())
      .join('');
  }
  return (user?.email?.[0] || 'S').toUpperCase();
}

export default function Header() {
  const { user, logout } = useAuth();
  const { loading: assistantBusy } = useChat();
  const navigate = useNavigate();
  const location = useLocation();
  const [isDark, setIsDark] = useState(isDarkTheme);
  const [menuOpen, setMenuOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const close = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [menuOpen]);

  // Close the mobile nav whenever the route changes.
  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    applyTheme(next);
    setDarkTheme(next);
  };

  const handleLogout = async () => {
    setMenuOpen(false);
    await logout();
    navigate('/login', { replace: true });
  };

  const onChatPage = location.pathname === '/chat';

  return (
    <header className="topbar hide-on-print">
      <Link className="brand" to="/dashboard">
        <BrandMark size={42} />
        <div className="brandText">
          <h1>{APP_NAME}</h1>
          <p>{APP_TAGLINE}</p>
        </div>
      </Link>

      <nav className={`mainNav ${navOpen ? 'open' : ''}`}>
        {NAV_ITEMS.map(({ to, label, Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => (isActive ? 'active' : '')}>
            <Icon size={16} />
            <span>{label}</span>
            {to === '/chat' && assistantBusy && (
              <span className="navBusyDot" aria-label={`${APP_NAME} is replying`} title={`${APP_NAME} is replying`} />
            )}
          </NavLink>
        ))}
      </nav>

      <div className="topbarActions">
        {/* The chat keeps streaming while the learner is on another page, so say so. */}
        {assistantBusy && !onChatPage && (
          <button
            className="assistantBadge"
            onClick={() => navigate('/chat')}
            title={`${APP_NAME} is still replying - tap to watch`}
          >
            <span className="typingDots" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            <span className="assistantBadgeText">{APP_NAME} is replying</span>
          </button>
        )}

        <InstallButton />

        <button
          className="ghostBtn iconBtn"
          onClick={toggleTheme}
          aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {isDark ? <SunIcon size={18} /> : <MoonIcon size={18} />}
        </button>

        <div className="profile" ref={menuRef}>
          <button
            className="avatar"
            onClick={() => setMenuOpen((open) => !open)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            title={user?.email || 'Account'}
          >
            {initialsFor(user)}
          </button>

          {menuOpen && (
            <div className="accountMenu" role="menu">
              <div className="accountMenuHead">
                <strong>{user?.profile?.full_name || 'Learner'}</strong>
                <small>{user?.email}</small>
              </div>
              <button
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  navigate('/dashboard');
                }}
              >
                <DashboardIcon size={16} /> My progress
              </button>
              <button
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  navigate('/profile');
                }}
              >
                <ProfileIcon size={16} /> Edit profile
              </button>
              <button role="menuitem" className="danger" onClick={handleLogout}>
                <LogOutIcon size={16} /> Sign out
              </button>
            </div>
          )}
        </div>

        <button
          className="ghostBtn iconBtn navToggle"
          onClick={() => setNavOpen((open) => !open)}
          aria-label={navOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={navOpen}
        >
          {navOpen ? <CloseIcon size={18} /> : <MenuIcon size={18} />}
        </button>
      </div>
    </header>
  );
}
