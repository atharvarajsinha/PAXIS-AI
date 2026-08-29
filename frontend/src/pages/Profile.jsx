import { useEffect, useState } from 'react';
import Header from '../components/Header.jsx';
import Footer from '../components/Footer.jsx';
import TagInput from '../components/TagInput.jsx';
import { apiRequest } from '../services/api.js';
import { useAuth } from '../context/AuthContext.jsx';
import ChangePassword from '../components/ChangePassword.jsx';
import { ProfileIcon } from '../components/icons.jsx';

const EXPERIENCE_LEVELS = [
  { value: 'beginner', label: 'Beginner', hint: 'New to the field, starting from fundamentals.' },
  { value: 'intermediate', label: 'Intermediate', hint: 'Comfortable with basics, building real projects.' },
  { value: 'advanced', label: 'Advanced', hint: 'Working at depth, sharpening specialist skills.' },
];

const INTEREST_SUGGESTIONS = [
  'Web Development', 'Machine Learning', 'Data Science', 'Mobile Apps',
  'Cybersecurity', 'Cloud & DevOps', 'Game Development', 'UI/UX Design',
];

const OBJECTIVE_SUGGESTIONS = [
  'Land my first job', 'Get an internship', 'Switch careers',
  'Build a portfolio project', 'Prepare for interviews', 'Earn a certification',
];

const EMPTY = {
  full_name: '',
  headline: '',
  experience_level: 'beginner',
  weekly_hours: 5,
  interests: [],
  objectives: [],
  completed_courses: [],
};

export default function Profile() {
  const { refreshUser } = useAuth();
  const [form, setForm] = useState(EMPTY);
  const [completeness, setCompleteness] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiRequest('/api/profile/')
      .then((data) => {
        if (cancelled) return;
        setForm({
          full_name: data.full_name || '',
          headline: data.headline || '',
          experience_level: data.experience_level || 'beginner',
          weekly_hours: data.weekly_hours ?? 5,
          interests: data.interests || [],
          objectives: data.objectives || [],
          completed_courses: data.completed_courses || [],
        });
        setCompleteness(data.completeness ?? 0);
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const update = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setSaved(false);
  };

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      const data = await apiRequest('/api/profile/', {
        method: 'PUT',
        body: { ...form, weekly_hours: Number(form.weekly_hours) || 0 },
      });
      setCompleteness(data.completeness ?? 0);
      setSaved(true);
      await refreshUser();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <>
        <Header />
        <main className="pageShell"><div className="panelCard">Loading your profile...</div></main>
        <Footer />
      </>
    );
  }

  return (
    <>
      <Header />
      <main className="pageShell">
        <div className="pageHeading">
          <div>
            <h1><ProfileIcon size={22} /> Your learner profile</h1>
            <p>
              This is the profiling engine behind your roadmaps. Everything here is sent to
              the assistant so it skips what you know and pitches the rest at your level.
            </p>
          </div>
          <div className="completenessRing" style={{ '--value': `${completeness}%` }}>
            <span>{completeness}%</span>
            <small>complete</small>
          </div>
        </div>

        {error && <div className="errorBox">{error}</div>}
        {saved && <div className="successBox">Profile saved. Your next roadmap will use it.</div>}

        <form className="profileForm" onSubmit={submit}>
          <section className="panelCard">
            <h2>About you</h2>
            <div className="formGrid">
              <div>
                <label htmlFor="profile-name">Full name</label>
                <input
                  id="profile-name"
                  type="text"
                  value={form.full_name}
                  onChange={(e) => update('full_name', e.target.value)}
                  placeholder="Your name"
                  maxLength={120}
                />
              </div>
              <div>
                <label htmlFor="profile-headline">Headline</label>
                <input
                  id="profile-headline"
                  type="text"
                  value={form.headline}
                  onChange={(e) => update('headline', e.target.value)}
                  placeholder="e.g. Second-year CS student"
                  maxLength={160}
                />
              </div>
            </div>
          </section>

          <section className="panelCard">
            <h2>Experience level</h2>
            <p className="fieldHint">How deep are you in your main area right now?</p>
            <div className="levelGrid">
              {EXPERIENCE_LEVELS.map((level) => (
                <button
                  type="button"
                  key={level.value}
                  className={`levelCard ${form.experience_level === level.value ? 'selected' : ''}`}
                  onClick={() => update('experience_level', level.value)}
                  aria-pressed={form.experience_level === level.value}
                >
                  <strong>{level.label}</strong>
                  <span>{level.hint}</span>
                </button>
              ))}
            </div>

            <label htmlFor="profile-hours">Study time: <strong>{form.weekly_hours} hours per week</strong></label>
            <input
              id="profile-hours"
              type="range"
              min="1"
              max="60"
              value={form.weekly_hours}
              onChange={(e) => update('weekly_hours', Number(e.target.value))}
              className="rangeInput"
            />
            <p className="fieldHint">Roadmap timelines are paced against this number.</p>
          </section>

          <section className="panelCard">
            <h2>Interests</h2>
            <TagInput
              id="profile-interests"
              label="What do you want to work on?"
              hint="Press Enter after each one."
              placeholder="e.g. Machine Learning"
              suggestions={INTEREST_SUGGESTIONS}
              values={form.interests}
              onChange={(value) => update('interests', value)}
            />
          </section>

          <section className="panelCard">
            <h2>Objectives</h2>
            <TagInput
              id="profile-objectives"
              label="What are you aiming for?"
              hint="Concrete goals work best - the assistant plans backwards from them."
              placeholder="e.g. Land my first backend role"
              suggestions={OBJECTIVE_SUGGESTIONS}
              values={form.objectives}
              onChange={(value) => update('objectives', value)}
            />
          </section>

          <section className="panelCard">
            <h2>Completed courses</h2>
            <TagInput
              id="profile-courses"
              label="What have you already finished?"
              hint="Anything listed here gets skipped in future roadmaps."
              placeholder="e.g. CS50x - Introduction to Computer Science"
              values={form.completed_courses}
              onChange={(value) => update('completed_courses', value)}
            />
          </section>

          <div className="formActions">
            <button className="primaryBtn" type="submit" disabled={saving}>
              {saving ? 'Saving...' : 'Save profile'}
            </button>
          </div>
        </form>

        <ChangePassword />
      </main>
      <Footer />
    </>
  );
}
