from django.urls import path

from .views import (
    DashboardAPIView,
    LearningPlanDetailAPIView,
    LearningPlanListAPIView,
    PlanMilestoneCompletionAPIView,
    PlanStepCompletionAPIView,
)

urlpatterns = [
    path('dashboard/', DashboardAPIView.as_view(), name='dashboard'),
    path('plans/', LearningPlanListAPIView.as_view(), name='plan-list'),
    path('plans/<int:plan_id>/', LearningPlanDetailAPIView.as_view(), name='plan-detail'),
    path('steps/<int:step_id>/', PlanStepCompletionAPIView.as_view(), name='plan-step'),
    path('milestones/<int:milestone_id>/', PlanMilestoneCompletionAPIView.as_view(), name='plan-milestone'),
]
