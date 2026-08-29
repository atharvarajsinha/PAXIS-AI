import { useEffect, useRef, useState } from 'react';
import Header from '../components/Header.jsx';
import Footer from '../components/Footer.jsx';
import ChatPanel from '../components/ChatPanel.jsx';
import ChatSidebar from '../components/ChatSidebar.jsx';
import RoadmapModal from '../components/RoadmapModal.jsx';
import { RoadmapIcon } from '../components/icons.jsx';
import { useChat } from '../context/ChatContext.jsx';
import { isSidebarCollapsed, setSidebarCollapsed } from '../services/preferences.js';

export default function Chat() {
  const {
    messages,
    roadmap,
    conversationId,
    conversations,
    conversationsLoading,
    loading,
    statusText,
    error,
    saveState,
    sendMessage,
    startNewChat,
    openConversation,
    removeConversation,
    renameConversation,
    trackRoadmap,
  } = useChat();

  const [collapsed, setCollapsed] = useState(isSidebarCollapsed);
  const [roadmapOpen, setRoadmapOpen] = useState(false);
  const seenRoadmapRef = useRef(null);

  useEffect(() => {
    setSidebarCollapsed(collapsed);
  }, [collapsed]);

  // Pop the roadmap open the first time a given conversation produces one, so a
  // new plan is not hidden behind a button the learner has not noticed yet.
  useEffect(() => {
    if (!roadmap || loading) return;
    const key = `${conversationId}:${roadmap.goal || ''}`;
    if (seenRoadmapRef.current === key) return;
    seenRoadmapRef.current = key;
    setRoadmapOpen(true);
  }, [roadmap, loading, conversationId]);

  const confirmDelete = (id, title) => {
    if (window.confirm(`Delete "${title}"? This cannot be undone.`)) removeConversation(id);
  };

  const stageCount = Array.isArray(roadmap?.steps) ? roadmap.steps.length : 0;

  return (
    <>
      <Header />
      <main className={`chatLayout ${collapsed ? 'sidebarCollapsed' : ''}`}>
        <ChatSidebar
          conversations={conversations}
          activeId={conversationId}
          loading={conversationsLoading}
          busy={loading}
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed((value) => !value)}
          onSelect={openConversation}
          onNewChat={startNewChat}
          onDelete={confirmDelete}
          onRename={renameConversation}
        />

        <div className="chatMain">
          <ChatPanel
            messages={messages}
            onSend={sendMessage}
            onClear={startNewChat}
            loading={loading}
            statusText={statusText}
            error={error}
          />

          {roadmap && (
            <button
              className="roadmapFab"
              onClick={() => setRoadmapOpen(true)}
              title="Open your roadmap"
            >
              <RoadmapIcon size={18} />
              <span>View roadmap</span>
              {stageCount > 0 && <span className="roadmapFabCount">{stageCount}</span>}
            </button>
          )}
        </div>
      </main>

      <RoadmapModal
        open={roadmapOpen && Boolean(roadmap)}
        onClose={() => setRoadmapOpen(false)}
        roadmap={roadmap}
        loading={loading}
        statusText={statusText}
        onTrack={trackRoadmap}
        saveState={saveState}
      />

      <Footer />
    </>
  );
}
