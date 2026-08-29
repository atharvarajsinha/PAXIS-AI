import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header.jsx';
import Footer from '../components/Footer.jsx';
import ProgressRing from '../components/ProgressRing.jsx';
import ActivityChart from '../components/ActivityChart.jsx';
import PlanTracker from '../components/PlanTracker.jsx';
import { useChat } from '../context/ChatContext.jsx';
import {
  ArchiveIcon,
  ChatIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  DashboardIcon,
  MilestoneIcon,
  PlayIcon,
  ProfileIcon,
  ProjectIcon,
  RoadmapIcon,
  ReopenIcon,
  SkillIcon,
  StarIcon,
  StreakIcon,
  CheckIcon,
  CirclePendingIcon,
  GoalIcon,
  TrashIcon,
  UnarchiveIcon,
} from '../components/icons.jsx';
import {
  deletePlan,
  getDashboard,
  getPlan,
  setMilestoneCompletion,
  setPlanActive,
  setStepCompletion,
} from '../services/learningApi.js';

const ACTION_ICONS = {
  step: PlayIcon,
  plan_next_action: GoalIcon,
  project: ProjectIcon,
  profile: ProfileIcon,
  chat: ChatIcon,
};

const EVENT_ICONS = {
  plan_created: RoadmapIcon,
  step_completed: CheckIcon,
  step_reopened: ReopenIcon,
  milestone_completed: MilestoneIcon,
  milestone_reopened: ReopenIcon,
  profile_updated: ProfileIcon,
};

function StatCard({ icon: Icon, value, label, tone = '' }) {
  return (
    <div className={`statCard ${tone}`}>
      <span className="statCardIcon">
        <Icon size={20} />
      </span>
      <div>
        <strong>{value}</strong>
        <p>{label}</p>
      </div>
    </div>
  );
}

function formatWhen(iso) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function Dashboard() {
  const { refreshTracked } = useChat();
  const [data, setData] = useState(null);
  const [openPlan, setOpenPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyIds, setBusyIds] = useState([]);

  const load = useCallback(async () => {
    try {
      setData(await getDashboard());
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openPlanDetail = async (planId) => {
    if (openPlan?.id === planId) {
      setOpenPlan(null);
      return;
    }
    try {
      setOpenPlan(await getPlan(planId));
    } catch (err) {
      setError(err.message);
    }
  };

  const withBusy = async (key, work) => {
    setBusyIds((prev) => [...prev, key]);
    try {
      await work();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyIds((prev) => prev.filter((entry) => entry !== key));
    }
  };

  // Step and milestone toggles both return the whole updated plan, so the open
  // tracker and the aggregate cards refresh from one round trip.
  const toggle = (kind, id, isCompleted) =>
    withBusy(`${kind}-${id}`, async () => {
      const updated =
        kind === 'step'
          ? await setStepCompletion(id, isCompleted)
          : await setMilestoneCompletion(id, isCompleted);
      setOpenPlan(updated);
      await load();
    });

  const toggleArchive = (plan) =>
    withBusy(`plan-${plan.id}`, async () => {
      const updated = await setPlanActive(plan.id, !plan.is_active);
      if (openPlan?.id === plan.id) setOpenPlan(updated);
      await load();
    });

  const removePlan = (plan) => {
    if (
      !window.confirm(
        `Delete "${plan.goal}"? Its stages, milestones and the progress you have made on them will be removed. This cannot be undone.`,
      )
    ) {
      return;
    }
    return withBusy(`plan-${plan.id}`, async () => {
      await deletePlan(plan.id);
      if (openPlan?.id === plan.id) setOpenPlan(null);
      await load();
      // The chat's "Track this roadmap" button must become available again.
      await refreshTracked();
    });
  };

  if (loading) {
    return (
      <>
        <Header />
        <main className="pageShell">
          <div className="panelCard">Loading your dashboard...</div>
        </main>
        <Footer />
      </>
    );
  }

  if (error && !data) {
    return (
      <>
        <Header />
        <main className="pageShell">
          <div className="errorBox">{error}</div>
        </main>
        <Footer />
      </>
    );
  }

  const {
    summary,
    plans,
    skills,
    milestones,
    weekly_activity: weekly,
    recent_activity: recent,
    next_actions: nextActions,
  } = data;
  const hasPlans = plans.length > 0;
  const activePlans = plans.filter((plan) => plan.is_active);
  const archivedPlans = plans.filter((plan) => !plan.is_active);

  const planRow = (plan) => (
    <li key={plan.id} className={plan.is_active ? '' : 'archived'}>
      <div className="planRowWrap">
        <button className="planRow" onClick={() => openPlanDetail(plan.id)}>
          <div className="planRowMain">
            <strong>{plan.goal}</strong>
            <small>
              {plan.duration || 'Flexible timeline'}
              {plan.starting_level ? ` · ${plan.starting_level}` : ''}
              {plan.is_active ? '' : ' · archived'}
            </small>
          </div>
          <div className="planRowProgress">
            <div className="skillBar">
              <div className="skillBarFill" style={{ width: `${plan.percent_complete}%` }} />
            </div>
            <span>
              {plan.completed_steps}/{plan.total_steps}
            </span>
          </div>
          <span className="planChevron">
            {openPlan?.id === plan.id ? <ChevronUpIcon size={16} /> : <ChevronDownIcon size={16} />}
          </span>
        </button>

        <div className="planRowActions">
          <button
            onClick={() => toggleArchive(plan)}
            disabled={busyIds.includes(`plan-${plan.id}`)}
            aria-label={plan.is_active ? `Archive ${plan.goal}` : `Reactivate ${plan.goal}`}
            title={
              plan.is_active
                ? 'Archive: keeps the progress but stops suggesting next actions'
                : 'Reactivate this path'
            }
          >
            {plan.is_active ? <ArchiveIcon size={15} /> : <UnarchiveIcon size={15} />}
          </button>
          <button
            className="danger"
            onClick={() => removePlan(plan)}
            disabled={busyIds.includes(`plan-${plan.id}`)}
            aria-label={`Delete ${plan.goal}`}
            title="Delete this path and its progress"
          >
            <TrashIcon size={15} />
          </button>
        </div>
      </div>

      {openPlan?.id === plan.id && (
        <PlanTracker plan={openPlan} busyIds={busyIds} onToggle={toggle} />
      )}
    </li>
  );

  return (
    <>
      <Header />
      <main className="pageShell">
        <div className="pageHeading">
          <div>
            <h1>Your progress</h1>
            <p>Everything you are learning, how far along you are, and what to do next.</p>
          </div>
          <Link className="primaryBtn" to="/chat">
            <ChatIcon size={16} /> <span>Plan something new</span>
          </Link>
        </div>

        {error && <div className="errorBox">{error}</div>}

        {!hasPlans ? (
          <div className="panelCard emptyState">
            <div className="emptyIcon">
              <DashboardIcon size={34} />
            </div>
            <h2>Nothing to track yet</h2>
            <p>
              Ask the assistant for a roadmap, then hit <strong>Track this roadmap</strong> on the
              roadmap panel. Your progress, skills and milestones will appear here.
            </p>
            <Link className="primaryBtn" to="/chat">
              Start a chat
            </Link>
          </div>
        ) : (
          <>
            {/* 1. Status cards + weekly activity */}
            <section className="dashboardTop">
              <div className="panelCard overallCard">
                <ProgressRing value={summary.percent_complete} />
                <div>
                  <h2>Overall completion</h2>
                  <p>
                    {summary.completed_steps} of {summary.total_steps} stages finished across{' '}
                    {summary.active_plans} active {summary.active_plans === 1 ? 'path' : 'paths'}.
                  </p>
                </div>
              </div>

              <div className="statGrid">
                <StatCard icon={StreakIcon} value={summary.day_streak} label="day streak" tone="warm" />
                <StatCard
                  icon={MilestoneIcon}
                  value={`${summary.milestones_completed}/${summary.milestones_total}`}
                  label="milestones reached"
                />
                <StatCard icon={SkillIcon} value={summary.skills_tracked} label="skills in progress" />
                <StatCard icon={StarIcon} value={summary.skills_mastered} label="skills mastered" tone="good" />
              </div>

              <div className="panelCard activityCard">
                <h2>Weekly activity</h2>
                <p className="fieldHint">Stages completed over the last 8 weeks.</p>
                <ActivityChart buckets={weekly} />
              </div>
            </section>

            {/* 2. Your learning paths */}
            <section className="panelCard">
              <h2>Your learning paths</h2>
              <p className="fieldHint">
                Open a path to tick off stages. Archive one to keep its progress without it driving
                your next actions.
              </p>
              <ul className="planList">{activePlans.map(planRow)}</ul>

              {archivedPlans.length > 0 && (
                <details className="archivedPlans">
                  <summary>
                    Archived ({archivedPlans.length})
                  </summary>
                  <ul className="planList">{archivedPlans.map(planRow)}</ul>
                </details>
              )}
            </section>

            {/* 3. Next recommended actions */}
            <section className="panelCard">
              <h2>Next recommended actions</h2>
              <p className="fieldHint">Ranked by what will move you forward fastest.</p>
              <ol className="actionList">
                {nextActions.map((action, index) => {
                  const Icon = ACTION_ICONS[action.kind] || GoalIcon;
                  return (
                    <li key={`${action.kind}-${action.step_id ?? index}`}>
                      <span className="actionIcon">
                        <Icon size={17} />
                      </span>
                      <div>
                        <strong>{action.title}</strong>
                        <p>{action.detail}</p>
                        {action.plan_goal && <span className="actionTag">{action.plan_goal}</span>}
                      </div>
                      {action.kind === 'step' && action.step_id && (
                        <button
                          className="ghostBtn"
                          disabled={busyIds.includes(`step-${action.step_id}`)}
                          onClick={() => toggle('step', action.step_id, true)}
                        >
                          Mark done
                        </button>
                      )}
                      {action.kind === 'profile' && (
                        <Link className="ghostBtn" to="/profile">
                          Open
                        </Link>
                      )}
                      {action.kind === 'chat' && (
                        <Link className="ghostBtn" to="/chat">
                          Open
                        </Link>
                      )}
                    </li>
                  );
                })}
              </ol>
            </section>

            {/* 4. Skill development, 5. Milestones, 6. Recent activity */}
            <section className="dashboardGrid">
              <div className="panelCard">
                <h2>Skill development</h2>
                <p className="fieldHint">
                  Mastery grows as you finish the stages covering each topic.
                </p>
                {skills.length === 0 ? (
                  <p className="sidebarNote">Track a roadmap to start building skills.</p>
                ) : (
                  <ul className="skillList">
                    {skills.map((skill) => (
                      <li key={skill.name}>
                        <div className="skillHead">
                          <span>{skill.name}</span>
                          <strong>{skill.mastery}%</strong>
                        </div>
                        <div className="skillBar">
                          <div
                            className={`skillBarFill ${skill.mastery >= 100 ? 'complete' : ''}`}
                            style={{ width: `${skill.mastery}%` }}
                          />
                        </div>
                        <small>
                          {skill.times_completed} of {skill.times_covered} stages covering this topic
                        </small>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="panelCard">
                <h2>Milestones</h2>
                <p className="fieldHint">These tick automatically as you work through a path.</p>
                {milestones.length === 0 ? (
                  <p className="sidebarNote">No milestones yet.</p>
                ) : (
                  <ul className="milestoneList">
                    {milestones.map((milestone) => (
                      <li key={milestone.id} className={milestone.is_completed ? 'done' : ''}>
                        <span className="milestoneIcon">
                          {milestone.is_completed ? (
                            <MilestoneIcon size={17} />
                          ) : (
                            <CirclePendingIcon size={17} />
                          )}
                        </span>
                        <div>
                          <strong>{milestone.title}</strong>
                          <small>
                            {milestone.plan_goal}
                            {milestone.completed_at
                              ? ` · reached ${formatWhen(milestone.completed_at)}`
                              : ''}
                          </small>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="panelCard">
                <h2>Recent activity</h2>
                {recent.length === 0 ? (
                  <p className="sidebarNote">Nothing yet.</p>
                ) : (
                  <ul className="activityList">
                    {recent.map((event, index) => {
                      const Icon = EVENT_ICONS[event.event_type] || CheckIcon;
                      return (
                        <li key={`${event.created_at}-${index}`}>
                          <span>
                            <Icon size={16} />
                          </span>
                          <div>
                            <strong>{event.label}</strong>
                            <small>{formatWhen(event.created_at)}</small>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </section>
          </>
        )}
      </main>
      <Footer />
    </>
  );
}
