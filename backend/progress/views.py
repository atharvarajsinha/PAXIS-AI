from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import LearnerProfile

from .models import LearningPlan, PlanMilestone, PlanStep
from .serializers import (
    CompletionSerializer,
    CreatePlanSerializer,
    LearningPlanDetailSerializer,
    LearningPlanListSerializer,
)
from .services import (
    build_dashboard,
    create_plan_from_roadmap,
    find_duplicate_plan,
    set_milestone_completion,
    set_step_completion,
)


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = LearnerProfile.objects.get_or_create(user=request.user)
        return Response(build_dashboard(request.user, profile))


class LearningPlanListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = LearningPlan.objects.filter(user=request.user).prefetch_related('steps')
        return Response(LearningPlanListSerializer(plans, many=True).data)

    def post(self, request):
        serializer = CreatePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        roadmap = serializer.validated_data['roadmap']
        conversation = None
        conversation_id = serializer.validated_data.get('conversation_id')
        if conversation_id is not None:
            from chat.models import Conversation

            conversation = Conversation.objects.filter(id=conversation_id, user=request.user).first()
            if conversation is None:
                return Response({'detail': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        existing = find_duplicate_plan(request.user, roadmap, conversation)
        if existing is not None:
            return Response(
                {
                    'detail': 'You are already tracking this roadmap.',
                    'plan': LearningPlanDetailSerializer(existing).data,
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            plan = create_plan_from_roadmap(request.user, roadmap, conversation)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(LearningPlanDetailSerializer(plan).data, status=status.HTTP_201_CREATED)


class LearningPlanDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, plan_id):
        return get_object_or_404(LearningPlan, id=plan_id, user=request.user)

    def get(self, request, plan_id):
        plan = self.get_object(request, plan_id)
        return Response(LearningPlanDetailSerializer(plan).data)

    def patch(self, request, plan_id):
        plan = self.get_object(request, plan_id)
        if 'is_active' in request.data:
            plan.is_active = bool(request.data['is_active'])
            plan.save(update_fields=['is_active', 'updated_at'])
        return Response(LearningPlanDetailSerializer(plan).data)

    def delete(self, request, plan_id):
        plan = self.get_object(request, plan_id)
        plan.delete()

        from .services import recompute_skills

        recompute_skills(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlanStepCompletionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, step_id):
        step = get_object_or_404(PlanStep, id=step_id, plan__user=request.user)
        serializer = CompletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        set_step_completion(request.user, step, serializer.validated_data['is_completed'])
        step.refresh_from_db()
        return Response(LearningPlanDetailSerializer(step.plan).data)


class PlanMilestoneCompletionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, milestone_id):
        milestone = get_object_or_404(PlanMilestone, id=milestone_id, plan__user=request.user)
        serializer = CompletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        set_milestone_completion(request.user, milestone, serializer.validated_data['is_completed'])
        milestone.refresh_from_db()
        return Response(LearningPlanDetailSerializer(milestone.plan).data)
