from django.contrib import admin

from .models import ChatMessage, Conversation


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('role', 'message', 'created_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'created_at', 'updated_at')
    search_fields = ('title', 'user__email')
    inlines = [ChatMessageInline]
