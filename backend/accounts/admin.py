from django.contrib import admin

from .models import LearnerProfile


@admin.register(LearnerProfile)
class LearnerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'experience_level', 'weekly_hours', 'updated_at')
    search_fields = ('user__email', 'user__username', 'full_name')
    list_filter = ('experience_level',)
