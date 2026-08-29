from django.conf import settings
from django.db import models
from django.utils import timezone


class LearningPlan(models.Model):
    """A roadmap the learner saved from a chat, turned into trackable work."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_plans',
    )
    conversation = models.ForeignKey(
        'chat.Conversation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='plans',
    )
    goal = models.CharField(max_length=255)
    duration = models.CharField(max_length=120, blank=True)
    starting_level = models.CharField(max_length=120, blank=True)
    next_action = models.TextField(blank=True)
    projects = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.goal} ({self.user_id})'

    @property
    def total_steps(self):
        return self.steps.count()

    @property
    def completed_steps(self):
        return self.steps.filter(is_completed=True).count()

    @property
    def percent_complete(self):
        total = self.total_steps
        if not total:
            return 0
        return round(100 * self.completed_steps / total)


class PlanStep(models.Model):
    plan = models.ForeignKey(LearningPlan, on_delete=models.CASCADE, related_name='steps')
    order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=255)
    duration = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    topics = models.JSONField(default=list, blank=True)
    # The Serper/Gemini study links belonging to this step, kept verbatim so a
    # saved plan renders the same resources the chat produced.
    study_material = models.JSONField(default=dict, blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.order + 1}. {self.title}'

    def set_completed(self, completed):
        self.is_completed = completed
        self.completed_at = timezone.now() if completed else None
        self.save(update_fields=['is_completed', 'completed_at'])


class PlanMilestone(models.Model):
    plan = models.ForeignKey(LearningPlan, on_delete=models.CASCADE, related_name='milestones')
    order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

    def set_completed(self, completed):
        self.is_completed = completed
        self.completed_at = timezone.now() if completed else None
        self.save(update_fields=['is_completed', 'completed_at'])


class SkillProgress(models.Model):
    """Per-topic mastery, recomputed whenever a step is ticked off."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='skills',
    )
    name = models.CharField(max_length=160)
    times_covered = models.PositiveIntegerField(default=0)
    times_completed = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-times_completed', 'name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_skill_per_user'),
        ]

    def __str__(self):
        return f'{self.name} ({self.mastery}%)'

    @property
    def mastery(self):
        if not self.times_covered:
            return 0
        return round(100 * self.times_completed / self.times_covered)


class ActivityEvent(models.Model):
    """Append-only trail used to draw the dashboard's activity timeline."""

    EVENT_CHOICES = [
        ('plan_created', 'Plan created'),
        ('step_completed', 'Step completed'),
        ('step_reopened', 'Step reopened'),
        ('milestone_completed', 'Milestone completed'),
        ('milestone_reopened', 'Milestone reopened'),
        ('profile_updated', 'Profile updated'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_events',
    )
    plan = models.ForeignKey(
        LearningPlan,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activity_events',
    )
    event_type = models.CharField(max_length=32, choices=EVENT_CHOICES)
    label = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.event_type}: {self.label}'
