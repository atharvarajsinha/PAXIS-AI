from rest_framework import serializers

from .models import LearningPlan, PlanMilestone, PlanStep


class PlanStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanStep
        fields = [
            'id',
            'order',
            'title',
            'duration',
            'description',
            'topics',
            'study_material',
            'is_completed',
            'completed_at',
        ]
        read_only_fields = ['id', 'order', 'title', 'duration', 'description', 'topics', 'study_material', 'completed_at']


class PlanMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanMilestone
        fields = ['id', 'order', 'title', 'is_completed', 'completed_at']
        read_only_fields = ['id', 'order', 'title', 'completed_at']


class LearningPlanListSerializer(serializers.ModelSerializer):
    total_steps = serializers.IntegerField(read_only=True)
    completed_steps = serializers.IntegerField(read_only=True)
    percent_complete = serializers.IntegerField(read_only=True)
    # Lets the chat UI recognise a roadmap it already tracks without pulling
    # every step of every plan.
    step_titles = serializers.SerializerMethodField()

    class Meta:
        model = LearningPlan
        fields = [
            'id',
            'goal',
            'duration',
            'starting_level',
            'is_active',
            'conversation',
            'total_steps',
            'completed_steps',
            'percent_complete',
            'step_titles',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [f for f in fields if f != 'is_active']

    def get_step_titles(self, obj):
        return [step.title for step in obj.steps.all()]


class LearningPlanDetailSerializer(LearningPlanListSerializer):
    steps = PlanStepSerializer(many=True, read_only=True)
    milestones = PlanMilestoneSerializer(many=True, read_only=True)

    class Meta(LearningPlanListSerializer.Meta):
        fields = LearningPlanListSerializer.Meta.fields + ['next_action', 'projects', 'steps', 'milestones']
        read_only_fields = [f for f in fields if f != 'is_active']


class CreatePlanSerializer(serializers.Serializer):
    roadmap = serializers.JSONField()
    conversation_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_roadmap(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('roadmap must be an object.')
        steps = value.get('steps')
        if not isinstance(steps, list) or not any(isinstance(step, dict) for step in steps):
            raise serializers.ValidationError('roadmap must contain at least one step.')
        return value


class CompletionSerializer(serializers.Serializer):
    is_completed = serializers.BooleanField()
