from django.conf import settings
from django.db import models


class LearnerProfile(models.Model):
    """Profiling engine record: what the learner knows, wants, and has finished.

    The stored values are fed into the assistant prompt so every roadmap is
    grounded in the learner's real starting point instead of a generic one.
    """

    EXPERIENCE_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learner_profile',
    )
    full_name = models.CharField(max_length=120, blank=True)
    headline = models.CharField(max_length=160, blank=True)
    experience_level = models.CharField(
        max_length=20,
        choices=EXPERIENCE_CHOICES,
        default='beginner',
    )
    weekly_hours = models.PositiveIntegerField(default=5)
    # Each of these is a plain list of strings, kept as JSON so the profiling
    # engine can grow new fields without another migration per field.
    # Stores the learner's interests, goals, experience, and completed courses.
    interests = models.JSONField(default=list, blank=True)
    objectives = models.JSONField(default=list, blank=True)
    completed_courses = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile for {self.user.email or self.user.username}'

    @property
    def is_complete(self):
        return bool(self.interests and self.objectives)

    def completeness(self):
        """Percentage of the profiling questionnaire the learner has answered."""
        filled = [
            bool(self.full_name),
            bool(self.interests),
            bool(self.objectives),
            bool(self.completed_courses),
            bool(self.experience_level),
            bool(self.weekly_hours),
        ]
        return round(100 * sum(filled) / len(filled))

    def as_prompt_context(self):
        """Compact, human-readable summary handed to the AI provider."""
        lines = []
        if self.full_name:
            lines.append(f'Name: {self.full_name}')
        lines.append(f'Experience level: {self.get_experience_level_display()}')
        lines.append(f'Study time available: about {self.weekly_hours} hours per week')
        if self.interests:
            lines.append('Interests: ' + ', '.join(str(i) for i in self.interests))
        if self.objectives:
            lines.append('Objectives: ' + ', '.join(str(o) for o in self.objectives))
        if self.completed_courses:
            lines.append('Already completed: ' + ', '.join(str(c) for c in self.completed_courses))
        return '\n'.join(lines)
