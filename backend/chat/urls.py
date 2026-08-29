from django.urls import path

from .views import ChatAPIView, ConversationDetailAPIView, ConversationListAPIView

urlpatterns = [
    path('chat/', ChatAPIView.as_view(), name='chat'),
    path('conversations/', ConversationListAPIView.as_view(), name='conversation-list'),
    path('conversations/<int:conversation_id>/', ConversationDetailAPIView.as_view(), name='conversation-detail'),
]
