"""Turn AI roadmaps into trackable plans and aggregate them for the dashboard."""

from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import ActivityEvent, LearningPlan, PlanMilestone, PlanStep, SkillProgress


def _text(value, fallback=''):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    return fallback


def _string_list(value):
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def step_topics(step):
    """Topics of a step, falling back to its title so every step feeds a skill."""
    topics = _string_list(step.topics if isinstance(step, PlanStep) else step.get('topics'))
    if topics:
        return topics
    title = step.title if isinstance(step, PlanStep) else _text(step.get('title'))
    return [title] if title else []


def _study_material_for_step(raw_step):
    """Normalise the two shapes the chat service emits into one dict."""
    material = {}
    if isinstance(raw_step.get('study_material'), dict):
        material['default'] = raw_step['study_material']
    topic_materials = raw_step.get('topic_materials')
    if isinstance(topic_materials, list):
        by_topic = {}
        for item in topic_materials:
            if isinstance(item, dict) and isinstance(item.get('topic'), str):
                by_topic[item['topic']] = item.get('study_material')
        if by_topic:
            material['by_topic'] = by_topic
    return material


def _plan_goal(roadmap):
    return _text(roadmap.get('goal'), 'Learning goal')[:255] or 'Learning goal'


def _step_title(raw_step, index):
    fallback = f'Step {index + 1}'
    return _text(raw_step.get('title'), fallback)[:255] or fallback


def _roadmap_step_titles(roadmap):
    steps = roadmap.get('steps') if isinstance(roadmap.get('steps'), list) else []
    return [_step_title(step, index) for index, step in enumerate(steps) if isinstance(step, dict)]


def find_duplicate_plan(user, roadmap, conversation=None):
    """The learner's existing plan for this roadmap, if they already track it.

    Two roadmaps count as the same when they share a goal and the same ordered
    stage titles. A later turn that genuinely revises the plan therefore stays
    trackable, while pressing the button twice on one roadmap does not.
    """
    if not isinstance(roadmap, dict):
        return None

    titles = _roadmap_step_titles(roadmap)
    candidates = LearningPlan.objects.filter(user=user, goal=_plan_goal(roadmap)).prefetch_related('steps')
    if conversation is not None:
        candidates = candidates.filter(conversation=conversation)

    return next(
        (plan for plan in candidates if [step.title for step in plan.steps.all()] == titles),
        None,
    )


@transaction.atomic
def create_plan_from_roadmap(user, roadmap, conversation=None):
    """Persist an AI roadmap as a LearningPlan with steps and milestones."""
    if not isinstance(roadmap, dict):
        raise ValueError('A roadmap object is required.')

    raw_steps = roadmap.get('steps') if isinstance(roadmap.get('steps'), list) else []
    raw_steps = [step for step in raw_steps if isinstance(step, dict)]
    if not raw_steps:
        raise ValueError('This roadmap has no steps to track.')

    plan = LearningPlan.objects.create(
        user=user,
        conversation=conversation,
        goal=_plan_goal(roadmap),
        duration=_text(roadmap.get('duration'))[:120],
        starting_level=_text(roadmap.get('starting_level'))[:120],
        next_action=_text(roadmap.get('next_action')),
        projects=_string_list(roadmap.get('projects')),
    )

    PlanStep.objects.bulk_create([
        PlanStep(
            plan=plan,
            order=index,
            title=_step_title(raw, index),
            duration=_text(raw.get('duration'))[:120],
            description=_text(raw.get('description')),
            topics=_string_list(raw.get('topics')),
            study_material=_study_material_for_step(raw),
        )
        for index, raw in enumerate(raw_steps)
    ])

    PlanMilestone.objects.bulk_create([
        PlanMilestone(plan=plan, order=index, title=title[:255])
        for index, title in enumerate(_string_list(roadmap.get('milestones')))
    ])

    recompute_skills(user)
    ActivityEvent.objects.create(
        user=user,
        plan=plan,
        event_type='plan_created',
        label=f'Started tracking "{plan.goal}"'[:255],
    )
    return plan


@transaction.atomic
def recompute_skills(user):
    """Rebuild SkillProgress rows from every step across the learner's plans.

    Recomputing wholesale keeps the counters correct when steps are reopened or
    plans deleted, which incremental updates get wrong.
    """
    counts = {}
    completed = {}
    labels = {}
    steps = PlanStep.objects.filter(plan__user=user).only('title', 'topics', 'is_completed')
    for step in steps:
        for topic in step_topics(step):
            key = topic.lower()
            counts[key] = counts.get(key, 0) + 1
            if step.is_completed:
                completed[key] = completed.get(key, 0) + 1
            labels.setdefault(key, topic[:160])

    SkillProgress.objects.filter(user=user).exclude(name__in=labels.values()).delete()
    existing = {skill.name: skill for skill in SkillProgress.objects.filter(user=user)}

    to_create, to_update = [], []
    for key, count in counts.items():
        name = labels[key]
        done = completed.get(key, 0)
        skill = existing.get(name)
        if skill is None:
            to_create.append(SkillProgress(user=user, name=name, times_covered=count, times_completed=done))
        elif skill.times_covered != count or skill.times_completed != done:
            skill.times_covered = count
            skill.times_completed = done
            to_update.append(skill)

    if to_create:
        SkillProgress.objects.bulk_create(to_create, ignore_conflicts=True)
    if to_update:
        SkillProgress.objects.bulk_update(to_update, ['times_covered', 'times_completed'])


def _auto_complete_milestones(plan):
    """Tick milestones as their share of the plan's steps is finished.

    Milestones are spread evenly across the roadmap, so milestone i of n counts
    as reached once the learner has finished (i+1)/n of the steps.
    """
    milestones = list(plan.milestones.all())
    total_steps = plan.total_steps
    if not milestones or not total_steps:
        return []

    done_steps = plan.completed_steps
    changed = []
    for index, milestone in enumerate(milestones):
        threshold = (index + 1) / len(milestones)
        reached = done_steps / total_steps >= threshold - 1e-9
        if reached and not milestone.is_completed:
            milestone.set_completed(True)
            changed.append((milestone, True))
        elif not reached and milestone.is_completed:
            milestone.set_completed(False)
            changed.append((milestone, False))
    return changed


def set_step_completion(user, step, completed):
    if step.is_completed == completed:
        return step
    step.set_completed(completed)
    ActivityEvent.objects.create(
        user=user,
        plan=step.plan,
        event_type='step_completed' if completed else 'step_reopened',
        label=step.title[:255],
    )
    for milestone, reached in _auto_complete_milestones(step.plan):
        ActivityEvent.objects.create(
            user=user,
            plan=step.plan,
            event_type='milestone_completed' if reached else 'milestone_reopened',
            label=milestone.title[:255],
        )
    step.plan.save(update_fields=['updated_at'])
    recompute_skills(user)
    return step


def set_milestone_completion(user, milestone, completed):
    if milestone.is_completed == completed:
        return milestone
    milestone.set_completed(completed)
    ActivityEvent.objects.create(
        user=user,
        plan=milestone.plan,
        event_type='milestone_completed' if completed else 'milestone_reopened',
        label=milestone.title[:255],
    )
    milestone.plan.save(update_fields=['updated_at'])
    return milestone


def _weekly_activity(user, weeks=8):
    """Completed-step counts for the last `weeks` weeks, oldest bucket first."""
    now = timezone.now()
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    buckets = []
    for offset in range(weeks - 1, -1, -1):
        end = start_of_today - timedelta(days=7 * offset) + timedelta(days=1)
        start = end - timedelta(days=7)
        count = ActivityEvent.objects.filter(
            user=user,
            event_type='step_completed',
            created_at__gte=start,
            created_at__lt=end,
        ).count()
        buckets.append({'week_start': start.date().isoformat(), 'completed': count})
    return buckets


def _current_streak(user):
    """Consecutive days, ending today or yesterday, with a completed step."""
    days = {
        timezone.localtime(dt).date()
        for dt in ActivityEvent.objects.filter(
            user=user, event_type='step_completed'
        ).values_list('created_at', flat=True)
    }
    if not days:
        return 0
    today = timezone.localdate()
    cursor = today if today in days else today - timedelta(days=1)
    if cursor not in days:
        return 0
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def next_recommended_actions(user, plans, profile=None, limit=5):
    """Rank what the learner should do next, most concrete suggestion first."""
    actions = []

    for plan in plans:
        if not plan.is_active:
            continue
        next_step = next((s for s in plan.steps.all() if not s.is_completed), None)
        if next_step is None:
            continue
        actions.append({
            'kind': 'step',
            'priority': 1,
            'title': next_step.title,
            'detail': next_step.description or f'Next stage of "{plan.goal}".',
            'plan_id': plan.id,
            'plan_goal': plan.goal,
            'step_id': next_step.id,
        })

    for plan in plans:
        if plan.is_active and plan.next_action and plan.percent_complete < 100:
            actions.append({
                'kind': 'plan_next_action',
                'priority': 2,
                'title': plan.next_action[:160],
                'detail': f'Suggested by your "{plan.goal}" roadmap.',
                'plan_id': plan.id,
                'plan_goal': plan.goal,
                'step_id': None,
            })

    for plan in plans:
        pending_project = plan.projects[0] if plan.is_active and plan.projects else None
        if pending_project and plan.percent_complete >= 50:
            actions.append({
                'kind': 'project',
                'priority': 3,
                'title': f'Build: {pending_project}',
                'detail': f'You are {plan.percent_complete}% through "{plan.goal}" - time to apply it.',
                'plan_id': plan.id,
                'plan_goal': plan.goal,
                'step_id': None,
            })

    if profile is not None and profile.completeness() < 100:
        actions.append({
            'kind': 'profile',
            'priority': 4,
            'title': 'Finish your learner profile',
            'detail': 'Interests, objectives and completed courses make every roadmap sharper.',
            'plan_id': None,
            'plan_goal': None,
            'step_id': None,
        })

    if not plans:
        actions.append({
            'kind': 'chat',
            'priority': 0,
            'title': 'Describe your learning goal in chat',
            'detail': 'Tell the assistant what you want to learn, then save the roadmap to start tracking it.',
            'plan_id': None,
            'plan_goal': None,
            'step_id': None,
        })

    actions.sort(key=lambda item: item['priority'])
    return actions[:limit]


def build_dashboard(user, profile=None):
    plans = list(
        LearningPlan.objects.filter(user=user)
        .prefetch_related('steps', 'milestones')
        .annotate(
            step_count=Count('steps', distinct=True),
            done_count=Count('steps', filter=Q(steps__is_completed=True), distinct=True),
        )
    )

    total_steps = sum(plan.step_count for plan in plans)
    done_steps = sum(plan.done_count for plan in plans)
    milestones = [m for plan in plans for m in plan.milestones.all()]
    skills = list(SkillProgress.objects.filter(user=user))

    return {
        'summary': {
            'active_plans': sum(1 for plan in plans if plan.is_active),
            'total_plans': len(plans),
            'total_steps': total_steps,
            'completed_steps': done_steps,
            'percent_complete': round(100 * done_steps / total_steps) if total_steps else 0,
            'milestones_total': len(milestones),
            'milestones_completed': sum(1 for m in milestones if m.is_completed),
            'skills_tracked': len(skills),
            'skills_mastered': sum(1 for skill in skills if skill.mastery >= 100),
            'day_streak': _current_streak(user),
            'profile_completeness': profile.completeness() if profile else 0,
        },
        'plans': [
            {
                'id': plan.id,
                'goal': plan.goal,
                'duration': plan.duration,
                'starting_level': plan.starting_level,
                'is_active': plan.is_active,
                'total_steps': plan.step_count,
                'completed_steps': plan.done_count,
                'percent_complete': round(100 * plan.done_count / plan.step_count) if plan.step_count else 0,
                'updated_at': plan.updated_at.isoformat(),
            }
            for plan in plans
        ],
        'skills': [
            {
                'name': skill.name,
                'mastery': skill.mastery,
                'times_covered': skill.times_covered,
                'times_completed': skill.times_completed,
            }
            for skill in sorted(skills, key=lambda s: (-s.mastery, s.name))[:24]
        ],
        'milestones': [
            {
                'id': m.id,
                'title': m.title,
                'is_completed': m.is_completed,
                'completed_at': m.completed_at.isoformat() if m.completed_at else None,
                'plan_id': m.plan_id,
                'plan_goal': m.plan.goal,
            }
            for m in sorted(milestones, key=lambda m: (m.is_completed, m.order))
        ],
        'weekly_activity': _weekly_activity(user),
        'recent_activity': [
            {
                'event_type': event.event_type,
                'label': event.label,
                'created_at': event.created_at.isoformat(),
            }
            for event in ActivityEvent.objects.filter(user=user)[:12]
        ],
        'next_actions': next_recommended_actions(user, plans, profile),
    }
