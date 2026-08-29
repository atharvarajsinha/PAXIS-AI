from django.contrib import admin

from .models import ActivityEvent, LearningPlan, PlanMilestone, PlanStep, SkillProgress


class PlanStepInline(admin.TabularInline):
    model = PlanStep
    extra = 0


class PlanMilestoneInline(admin.TabularInline):
    model = PlanMilestone
    extra = 0


@admin.register(LearningPlan)
class LearningPlanAdmin(admin.ModelAdmin):
    list_display = ('goal', 'user', 'is_active', 'percent_complete', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('goal', 'user__email')
    inlines = [PlanStepInline, PlanMilestoneInline]


@admin.register(SkillProgress)
class SkillProgressAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'times_completed', 'times_covered', 'mastery')
    search_fields = ('name', 'user__email')


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'label', 'user', 'created_at')
    list_filter = ('event_type',)
