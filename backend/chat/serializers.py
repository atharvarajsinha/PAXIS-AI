from rest_framework import serializers

from .models import ChatMessage, Conversation


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(trim_whitespace=True, allow_blank=False, max_length=4000)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'message', 'roadmap', 'created_at']
        read_only_fields = fields


class ConversationListSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='display_title', read_only=True)
    message_count = serializers.IntegerField(read_only=True)
    preview = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'title', 'preview', 'message_count', 'created_at', 'updated_at']
        read_only_fields = fields

    def get_preview(self, obj):
        last = obj.messages.order_by('-created_at', '-id').first()
        return last.message[:100] if last else ''


class ConversationDetailSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='display_title', read_only=True)
    messages = ChatMessageSerializer(many=True, read_only=True)
    roadmap = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'title', 'messages', 'roadmap', 'created_at', 'updated_at']
        read_only_fields = fields

    def get_roadmap(self, obj):
        """The most recent roadmap in the thread, so the panel reopens as it was."""
        latest = (
            obj.messages.filter(role='assistant', roadmap__isnull=False)
            .order_by('-created_at', '-id')
            .first()
        )
        return latest.roadmap if latest else None


class ConversationRenameSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120, allow_blank=True, trim_whitespace=True)
