import { useState } from 'react';
import { CollapseIcon, EditIcon, ExpandIcon, PlusIcon, TrashIcon } from './icons.jsx';

function relativeTime(iso) {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const minutes = Math.round((Date.now() - then) / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

export default function ChatSidebar({
  conversations,
  activeId,
  loading,
  busy,
  collapsed,
  onToggleCollapse,
  onSelect,
  onNewChat,
  onDelete,
  onRename,
}) {
  const [editingId, setEditingId] = useState(null);
  const [draftTitle, setDraftTitle] = useState('');

  const startRename = (conversation) => {
    setEditingId(conversation.id);
    setDraftTitle(conversation.title);
  };

  const commitRename = async (id) => {
    const title = draftTitle.trim();
    setEditingId(null);
    if (title) await onRename(id, title);
  };

  if (collapsed) {
    return (
      <aside className="chatSidebar collapsed hide-on-print">
        <button
          className="sidebarToggle"
          onClick={onToggleCollapse}
          aria-label="Show chats"
          aria-expanded="false"
          title="Show chats"
        >
          <ExpandIcon size={18} />
        </button>
        <button
          className="iconOnlyBtn"
          onClick={onNewChat}
          disabled={busy}
          aria-label="New chat"
          title={busy ? 'Wait for the current reply to finish' : 'New chat'}
        >
          <PlusIcon size={18} />
        </button>
        {conversations.length > 0 && (
          <span className="collapsedCount" title={`${conversations.length} saved chats`}>
            {conversations.length}
          </span>
        )}
      </aside>
    );
  }

  return (
    <aside className="chatSidebar hide-on-print">
      <div className="sidebarHead">
        <button className="newChatBtn" onClick={onNewChat} disabled={busy}>
          <PlusIcon size={16} /> <span>New chat</span>
        </button>
        <button
          className="sidebarToggle"
          onClick={onToggleCollapse}
          aria-label="Hide chats"
          aria-expanded="true"
          title="Hide chats"
        >
          <CollapseIcon size={18} />
        </button>
      </div>

      <h3>Your chats</h3>

      {loading && <p className="sidebarNote">Loading...</p>}

      {!loading && conversations.length === 0 && (
        <p className="sidebarNote">No chats yet. Ask for a roadmap and it will show up here.</p>
      )}

      <ul className="conversationList">
        {conversations.map((conversation) => (
          <li key={conversation.id} className={conversation.id === activeId ? 'active' : ''}>
            {editingId === conversation.id ? (
              <input
                className="renameInput"
                type="text"
                value={draftTitle}
                autoFocus
                maxLength={120}
                onChange={(e) => setDraftTitle(e.target.value)}
                onBlur={() => commitRename(conversation.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') commitRename(conversation.id);
                  if (e.key === 'Escape') setEditingId(null);
                }}
              />
            ) : (
              <button
                className="conversationBtn"
                onClick={() => onSelect(conversation.id)}
                disabled={busy}
                title={busy ? 'Wait for the current reply to finish' : conversation.title}
              >
                <span className="conversationTitle">{conversation.title}</span>
                <span className="conversationMeta">
                  {relativeTime(conversation.updated_at)} · {conversation.message_count} messages
                </span>
              </button>
            )}

            <div className="conversationActions">
              <button
                onClick={() => startRename(conversation)}
                aria-label={`Rename ${conversation.title}`}
                title="Rename"
              >
                <EditIcon size={14} />
              </button>
              <button
                onClick={() => onDelete(conversation.id, conversation.title)}
                aria-label={`Delete ${conversation.title}`}
                title="Delete"
              >
                <TrashIcon size={14} />
              </button>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
