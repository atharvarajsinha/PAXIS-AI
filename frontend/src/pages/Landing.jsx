import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import BrandMark, { APP_FULL_NAME, APP_NAME } from '../components/BrandMark.jsx';
import Footer from '../components/Footer.jsx';
import InstallButton from '../components/InstallButton.jsx';
import { applyTheme, isDarkTheme, setDarkTheme } from '../services/preferences.js';
import { useAuth } from '../context/AuthContext.jsx';
import {
  ArrowRightIcon,
  ChatIcon,
  CheckIcon,
  CloseIcon,
  DashboardIcon,
  DownloadIcon,
  GoalIcon,
  MenuIcon,
  MilestoneIcon,
  MoonIcon,
  PinIcon,
  ProfileIcon,
  RoadmapIcon,
  SkillIcon,
  SparklesIcon,
  StagesIcon,
  StreakIcon,
  SunIcon,
  VideoIcon,
  WebsiteIcon,
} from '../components/icons.jsx';

/* The landing page is deliberately static: it renders from these constants and
   never calls the API, so it works with the backend down. */

const PILLARS = [
  {
    key: 'P',
    word: 'Personalized',
    body: 'Your interests, experience level, weekly hours and finished courses shape every answer.',
  },
  {
    key: 'A',
    word: 'AI',
    body: 'A capable model turns a one-line goal into a staged plan with projects and milestones.',
  },
  {
    key: 'X',
    word: 'eXploration',
    body: 'Ask, refine, change direction. Every conversation is kept so you can pick a thread back up.',
  },
  {
    key: 'I',
    word: 'Intelligent',
    body: 'Curated study material per topic, chosen from live search results rather than invented.',
  },
  {
    key: 'S',
    word: 'Strategy',
    body: 'A roadmap you can track: tick off stages, watch skills grow, hit milestones.',
  },
];

const FEATURES = [
  {
    Icon: ChatIcon,
    title: 'Conversational planning',
    body: 'Describe a goal in plain English, Hindi or Hinglish. Ask follow-ups and the plan adapts instead of starting over.',
  },
  {
    Icon: ProfileIcon,
    title: 'A profile that does work',
    body: 'Record what you already know and what you are aiming for. Roadmaps skip finished ground and match your pace.',
  },
  {
    Icon: RoadmapIcon,
    title: 'Structured roadmaps',
    body: 'Every plan arrives as ordered stages with durations, topics, practical projects and a clear next action.',
  },
  {
    Icon: WebsiteIcon,
    title: 'Real study material',
    body: 'Each topic is paired with one article and one video picked from current search results, never fabricated links.',
  },
  {
    Icon: DashboardIcon,
    title: 'Progress you can see',
    body: 'Overall completion, per-skill mastery, milestones, an eight-week activity chart and a day streak.',
  },
  {
    Icon: SkillIcon,
    title: 'Skill development tracking',
    body: 'Topics become skills. Mastery rises as you finish the stages that cover them, and rolls back if you reopen one.',
  },
  {
    Icon: MilestoneIcon,
    title: 'Automatic milestones',
    body: 'Milestones sit at even points along a path and tick themselves as you work, so momentum stays visible.',
  },
  {
    Icon: DownloadIcon,
    title: 'Take it with you',
    body: 'Download any roadmap as a PDF, or keep several paths running and archive the ones on hold.',
  },
];

const STEPS = [
  {
    Icon: ProfileIcon,
    title: 'Create your account',
    body: 'Sign up with an email and password, then fill in interests, experience level, objectives and anything you have already completed.',
  },
  {
    Icon: ChatIcon,
    title: 'Describe your goal',
    body: '"I want to become an ML engineer in 6 months." The assistant reads your profile before it answers, so the plan starts where you actually are.',
  },
  {
    Icon: PinIcon,
    title: 'Track the roadmap',
    body: 'Save the plan to your dashboard in one click. It becomes a checklist of stages, milestones and projects.',
  },
  {
    Icon: StreakIcon,
    title: 'Work through it',
    body: 'Tick stages off as you finish them. Skills, milestones, your streak and the next recommended action all update.',
  },
];

const FAQS = [
  {
    q: 'What does PAXIS stand for?',
    a: 'Personalized AI Exploration and Intelligent Strategy. The name describes the loop: explore a goal in conversation, then get a strategy you can actually follow.',
  },
  {
    q: 'Do I need an account?',
    a: 'Yes. Chats, profiles and progress are private to each account, so nothing is shared between users and your roadmaps are waiting for you next time.',
  },
  {
    q: 'What can I ask it?',
    a: 'Anything you want to learn: a career change, a specific framework, exam preparation, a language. You can reply in English, Hindi or Hinglish.',
  },
  {
    q: 'Where do the study links come from?',
    a: 'Live web and video search results. The model selects one suitable article and one specific video per topic from those results, so it cannot invent URLs.',
  },
  {
    q: 'Can I run more than one path at a time?',
    a: 'Yes. Track as many as you like, archive the ones you are pausing, and delete anything you no longer need.',
  },
  {
    q: 'Can the assistant be wrong?',
    a: 'It can. Treat a roadmap as a well-informed starting point and sanity-check anything important before you commit months to it.',
  },
];

function LandingNav() {
  const [isDark, setIsDark] = useState(isDarkTheme);
  const [open, setOpen] = useState(false);

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    applyTheme(next);
    setDarkTheme(next);
  };

  return (
    <header className="landingNav">
      <a className="brand" href="#top">
        <BrandMark size={42} />
        <div className="brandText">
          <h1>{APP_NAME}</h1>
          <p>{APP_FULL_NAME}</p>
        </div>
      </a>

      <nav className={`landingLinks ${open ? 'open' : ''}`}>
        <a href="#features" onClick={() => setOpen(false)}>Features</a>
        <a href="#how" onClick={() => setOpen(false)}>How it works</a>
        <a href="#usage" onClick={() => setOpen(false)}>Usage</a>
        <a href="#faq" onClick={() => setOpen(false)}>FAQ</a>
      </nav>

      <div className="landingActions">
        <InstallButton />

        <button
          className="ghostBtn iconBtn"
          onClick={toggleTheme}
          aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {isDark ? <SunIcon size={18} /> : <MoonIcon size={18} />}
        </button>
        <Link className="ghostBtn" to="/login">Log in</Link>
        <Link className="primaryBtn small" to="/register">Get started</Link>
        <button
          className="ghostBtn iconBtn navToggle"
          onClick={() => setOpen((value) => !value)}
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
        >
          {open ? <CloseIcon size={18} /> : <MenuIcon size={18} />}
        </button>
      </div>
    </header>
  );
}

export default function Landing() {
  const { user, loading } = useAuth();

  // Someone already signed in has no use for the marketing page.
  if (!loading && user) return <Navigate to="/dashboard" replace />;

  return (
    <div className="landing" id="top">
      <LandingNav />

      <main>
        <section className="landingHero">
          <div className="landingHeroText">
            <span className="heroPill">
              <SparklesIcon size={14} /> {APP_FULL_NAME}
            </span>
            <h2>
              Stop guessing what to learn next.
            </h2>
            <p>
              {APP_NAME} turns a one-line goal into a staged learning roadmap built around what
              you already know - then tracks your progress through it, stage by stage.
            </p>
            <div className="heroButtons">
              <Link className="primaryBtn" to="/register">
                Get started free <ArrowRightIcon size={16} />
              </Link>
              <Link className="ghostBtn large" to="/login">
                I already have an account
              </Link>
            </div>
            <ul className="heroPoints">
              <li><CheckIcon size={16} /> Free to use</li>
              <li><CheckIcon size={16} /> Your chats stay private</li>
              <li><CheckIcon size={16} /> No credit card</li>
            </ul>
          </div>

          <div className="landingHeroArt" aria-hidden="true">
            <BrandMark size={260} withGlow />
          </div>
        </section>

        <section className="landingStrip">
          {PILLARS.map((pillar) => (
            <div className="pillar" key={pillar.key}>
              <span className="pillarKey">{pillar.key}</span>
              <strong>{pillar.word}</strong>
              <p>{pillar.body}</p>
            </div>
          ))}
        </section>

        <section className="landingSection" id="features">
          <div className="sectionHead">
            <h2>What you get</h2>
            <p>Everything below is part of the product today - no waitlists, no add-ons.</p>
          </div>
          <div className="featureGrid">
            {FEATURES.map(({ Icon, title, body }) => (
              <article className="featureCard" key={title}>
                <span className="featureIcon"><Icon size={20} /></span>
                <h3>{title}</h3>
                <p>{body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landingSection" id="how">
          <div className="sectionHead">
            <h2>How it works</h2>
            <p>Four steps from a vague ambition to a plan with a checkbox next to every stage.</p>
          </div>
          <ol className="stepFlow">
            {STEPS.map(({ Icon, title, body }, index) => (
              <li key={title}>
                <span className="stepFlowNumber">{index + 1}</span>
                <div>
                  <h3><Icon size={18} /> {title}</h3>
                  <p>{body}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="landingSection" id="usage">
          <div className="sectionHead">
            <h2>What it looks like in use</h2>
            <p>A real exchange, shortened. The reply is shaped by the profile behind it.</p>
          </div>

          <div className="usageGrid">
            <div className="usageChat">
              <div className="usageBubble user">
                I want to become an ML engineer in 6 months. Give me a roadmap.
              </div>
              <div className="usageBubble assistant">
                Since you already know Python and linear algebra, we can fast-track you straight to
                core machine learning and deep learning. With 14 hours a week, start with classical
                ML using scikit-learn. Here is your 6-month roadmap to that internship.
              </div>
              <p className="usageNote">
                <GoalIcon size={14} /> Goal, level and timeline are read from your profile - you do
                not repeat yourself every time.
              </p>
            </div>

            <div className="usageRoadmap">
              <div className="usageRoadmapHead">
                <RoadmapIcon size={18} />
                <div>
                  <strong>Get an ML Engineering internship</strong>
                  <span>6 months &middot; Intermediate</span>
                </div>
              </div>
              <ul>
                <li>
                  <span className="usageStage">1</span>
                  <div>
                    <strong>Core ML &amp; feature engineering</strong>
                    <small>6 weeks &middot; scikit-learn, cross-validation, metrics</small>
                    <span className="usageLinks">
                      <WebsiteIcon size={13} /> Article <VideoIcon size={13} /> Video
                    </span>
                  </div>
                </li>
                <li>
                  <span className="usageStage">2</span>
                  <div>
                    <strong>Deep learning fundamentals</strong>
                    <small>8 weeks &middot; PyTorch, CNNs, transformers</small>
                  </div>
                </li>
                <li>
                  <span className="usageStage">3</span>
                  <div>
                    <strong>MLOps &amp; deployment</strong>
                    <small>6 weeks &middot; FastAPI, Docker, MLflow</small>
                  </div>
                </li>
              </ul>
              <div className="usageTrack">
                <StagesIcon size={15} /> Track this roadmap to tick stages off on your dashboard
              </div>
            </div>
          </div>
        </section>

        <section className="landingSection" id="faq">
          <div className="sectionHead">
            <h2>Questions</h2>
          </div>
          <div className="faqGrid">
            {FAQS.map(({ q, a }) => (
              <details className="faqItem" key={q}>
                <summary>{q}</summary>
                <p>{a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="landingCta">
          <BrandMark size={72} />
          <h2>Ready to plan your next six months?</h2>
          <p>Create an account, fill in your profile, and ask your first question.</p>
          <div className="heroButtons">
            <Link className="primaryBtn" to="/register">
              Create your account <ArrowRightIcon size={16} />
            </Link>
            <Link className="ghostBtn large" to="/login">Log in</Link>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
