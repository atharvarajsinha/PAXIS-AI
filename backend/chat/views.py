import json
import logging
import time

from django.db import DatabaseError
from django.db.models import Count
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatMessage, Conversation
from .serializers import (
    ChatRequestSerializer,
    ConversationDetailSerializer,
    ConversationListSerializer,
    ConversationRenameSerializer,
)
from .services import AI_UNAVAILABLE_MESSAGE, generate_learning_response


logger = logging.getLogger(__name__)


def _profile_context(user):
    """The learner's profiling record rendered for the system prompt."""
    profile = getattr(user, 'learner_profile', None)
    return profile.as_prompt_context() if profile else ''


def _sse(payload):
    return f'data: {json.dumps(payload)}\n\n'

# Handles learner messages and streams the AI response back to the frontend.
class ChatAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_message = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id')

        if conversation_id is None:
            conversation = Conversation.objects.create(user=request.user, title=user_message[:60])
        else:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=request.user)
            except Conversation.DoesNotExist:
                return Response({'error': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        previous_messages = list(conversation.messages.order_by('created_at', 'id'))
        ChatMessage.objects.create(conversation=conversation, role='user', message=user_message)
        if not conversation.title:
            conversation.title = user_message[:60]
            conversation.save(update_fields=['title', 'updated_at'])
        else:
            conversation.save(update_fields=['updated_at'])

        generator = generate_learning_response(
            user_message,
            previous_messages,
            profile_context=_profile_context(request.user),
        )

        def stream_response():
            started = time.monotonic()
            final_response = None
            final_roadmap = None
            persisted = False

            def persist():
                """Write the assistant turn once, and only when there is one."""
                nonlocal persisted
                if persisted or not final_response:
                    return
                persisted = True
                try:
                    ChatMessage.objects.create(
                        conversation=conversation,
                        role='assistant',
                        message=final_response,
                        roadmap=final_roadmap,
                    )
                    conversation.save(update_fields=['updated_at'])
                except DatabaseError:
                    logger.exception('[chat] conversation=%s outcome=persist-failed', conversation.id)

            logger.info('[chat] conversation=%s outcome=started', conversation.id)

            yield _sse({'conversation_id': conversation.id})

            try:
                try:
                    for chunk in generator:
                        if 'response' in chunk:
                            final_response = chunk['response']
                        if 'roadmap' in chunk:
                            final_roadmap = chunk['roadmap']
                        yield _sse(chunk)
                except Exception:
                    logger.exception('[chat] conversation=%s outcome=failed', conversation.id)
                    yield _sse({'error': AI_UNAVAILABLE_MESSAGE})
                else:
                    persist()
                    logger.info(
                        '[chat] conversation=%s outcome=completed has_roadmap=%s duration=%.2fs',
                        conversation.id, bool(final_roadmap), time.monotonic() - started,
                    )
                yield 'event: end\ndata: {}\n\n'
            finally:
                closer = getattr(generator, 'close', None)
                if callable(closer):
                    closer()
                if not persisted and final_response:
                    logger.info('[chat] conversation=%s outcome=client-disconnected', conversation.id)
                    persist()

        response = StreamingHttpResponse(stream_response(), content_type='text/event-stream')
        response['X-Accel-Buffering'] = 'no'
        response['Cache-Control'] = 'no-cache'
        return response


class ConversationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = (
            Conversation.objects.filter(user=request.user)
            .annotate(message_count=Count('messages'))
            .prefetch_related('messages')
            .order_by('-updated_at')
        )
        return Response(ConversationListSerializer(conversations, many=True).data)


class ConversationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, conversation_id):
        return get_object_or_404(Conversation, id=conversation_id, user=request.user)

    def get(self, request, conversation_id):
        conversation = self.get_object(request, conversation_id)
        return Response(ConversationDetailSerializer(conversation).data)

    def patch(self, request, conversation_id):
        conversation = self.get_object(request, conversation_id)
        serializer = ConversationRenameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation.title = serializer.validated_data['title']
        conversation.save(update_fields=['title', 'updated_at'])
        return Response(ConversationDetailSerializer(conversation).data)

    def delete(self, request, conversation_id):
        conversation = self.get_object(request, conversation_id)
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
