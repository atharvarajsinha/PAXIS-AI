import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import {
  deleteConversation as deleteConversationRequest,
  getConversation,
  listConversations,
  renameConversation as renameConversationRequest,
  sendChatMessage,
} from '../services/chatApi.js';
import { listPlans, savePlan } from '../services/learningApi.js';
import { useAuth } from './AuthContext.jsx';

const ChatContext = createContext(null);

const generateId = () => {
  try {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  } catch {
    // Fall through to the timestamp id below.
  }
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
};

const welcomeFor = (user) => {
  const name = user?.profile?.full_name?.split(' ')[0];
  return {
    id: 'welcome',
    role: 'assistant',
    content:
      `Hi${name ? ` ${name}` : ''}! 👋\n\n` +
      'I’m here to help you build personalized learning roadmaps, tackle your questions, and turn your goals into clear, actionable steps.\n\nWhat would you like to learn or solve today?',
  };
};

/** Identity of a roadmap for the "already tracking this" check, mirroring the server. */
const roadmapKey = (roadmap) => {
  if (!roadmap) return null;
  const goal = (typeof roadmap.goal === 'string' ? roadmap.goal.trim() : '') || 'Learning goal';
  const titles = (Array.isArray(roadmap.steps) ? roadmap.steps : [])
    .filter((step) => step && typeof step === 'object')
    .map((step, index) => (typeof step.title === 'string' ? step.title.trim() : '') || `Step ${index + 1}`);
  return JSON.stringify([goal.slice(0, 255), titles]);
};

/**
 * Chat state lives above the router so a request keeps streaming while the
 * learner reads their dashboard or edits their profile. Only the view unmounts.
 */
export function ChatProvider({ children }) {
  const { user } = useAuth();
  const [messages, setMessages] = useState(() => [welcomeFor(user)]);
  const [roadmap, setRoadmap] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [conversationsLoading, setConversationsLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [trackedKeys, setTrackedKeys] = useState([]);

  // Read inside async callbacks that must not capture a stale value.
  const loadingRef = useRef(false);
  const userIdRef = useRef(user?.id ?? null);

  const setLoadingState = useCallback((value) => {
    loadingRef.current = value;
    setLoading(value);
  }, []);

  const refreshConversations = useCallback(async () => {
    try {
      setConversations(await listConversations());
    } catch (err) {
      setError(err.message);
    } finally {
      setConversationsLoading(false);
    }
  }, []);

  const refreshTracked = useCallback(async () => {
    try {
      const plans = await listPlans();
      setTrackedKeys(plans.map((plan) => JSON.stringify([plan.goal, plan.step_titles || []])));
    } catch {
      // Not fatal: the server still rejects a duplicate with 409.
    }
  }, []);

  // Reset everything when the signed-in account changes, so one learner never
  // sees another's threads after a logout/login in the same tab.
  useEffect(() => {
    const nextId = user?.id ?? null;
    if (userIdRef.current === nextId) return;
    userIdRef.current = nextId;

    setMessages([welcomeFor(user)]);
    setRoadmap(null);
    setConversationId(null);
    setConversations([]);
    setError('');
    setLoadingState(false);
    setStatusText('');

    if (nextId === null) {
      setTrackedKeys([]);
      setConversationsLoading(false);
      return;
    }
    setConversationsLoading(true);
    refreshConversations();
    refreshTracked();
  }, [user, refreshConversations, refreshTracked, setLoadingState]);

  const startNewChat = useCallback(() => {
    if (loadingRef.current) return;
    setMessages([welcomeFor(user)]);
    setRoadmap(null);
    setConversationId(null);
    setError('');
  }, [user]);

  const openConversation = useCallback(
    async (id) => {
      if (loadingRef.current || id === conversationId) return;
      setError('');
      try {
        const data = await getConversation(id);
        setConversationId(data.id);
        setRoadmap(data.roadmap || null);
        setMessages(
          data.messages.length
            ? data.messages.map((m) => ({ id: `db-${m.id}`, role: m.role, content: m.message }))
            : [welcomeFor(user)],
        );
      } catch (err) {
        setError(err.message);
      }
    },
    [conversationId, user],
  );

  const removeConversation = useCallback(
    async (id) => {
      try {
        await deleteConversationRequest(id);
        setConversations((prev) => prev.filter((c) => c.id !== id));
        if (id === conversationId) {
          setMessages([welcomeFor(user)]);
          setRoadmap(null);
          setConversationId(null);
        }
      } catch (err) {
        setError(err.message);
      }
    },
    [conversationId, user],
  );

  const renameConversation = useCallback(async (id, title) => {
    try {
      await renameConversationRequest(id, title);
      setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)));
    } catch (err) {
      setError(err.message);
    }
  }, []);

  const sendMessage = useCallback(
    async (content) => {
      if (loadingRef.current) return;

      const startedIn = conversationId;
      setMessages((prev) => [...prev, { id: generateId(), role: 'user', content }]);
      setLoadingState(true);
      setStatusText('Thinking...');
      setError('');

      try {
        const data = await sendChatMessage(content, startedIn, (chunk) => {
          if (chunk.conversation_id) {
            setConversationId(chunk.conversation_id);
            // Surface the new thread in the sidebar immediately instead of
            // leaving "No chats yet" up for the length of the whole answer.
            if (startedIn === null) refreshConversations();
          }
          if (chunk.status) setStatusText(chunk.status);
          if (chunk.roadmap) setRoadmap(chunk.roadmap);
        });

        if (data.conversation_id) setConversationId(data.conversation_id);
        setMessages((prev) => [
          ...prev,
          {
            id: generateId(),
            role: 'assistant',
            content: data.response || 'Roadmap generated successfully.',
          },
        ]);
        if (data.roadmap) setRoadmap(data.roadmap);
      } catch (err) {
        setError(err.message);
        setMessages((prev) => [
          ...prev,
          {
            id: generateId(),
            role: 'assistant',
            content: 'Sorry, I could not generate a roadmap right now. Please try again.',
          },
        ]);
      } finally {
        setLoadingState(false);
        setStatusText('');
        refreshConversations();
      }
    },
    [conversationId, refreshConversations, setLoadingState],
  );

  const currentRoadmapKey = useMemo(() => roadmapKey(roadmap), [roadmap]);
  const isTracked = currentRoadmapKey !== null && trackedKeys.includes(currentRoadmapKey);

  const trackRoadmap = useCallback(async () => {
    if (!roadmap || saving || isTracked) return;
    setSaving(true);
    try {
      await savePlan(roadmap, conversationId);
      if (currentRoadmapKey) setTrackedKeys((prev) => [...prev, currentRoadmapKey]);
    } catch (err) {
      // A 409 means another tab or an earlier session already tracked it, which
      // is the state the button wants anyway.
      if (err.status === 409 && currentRoadmapKey) {
        setTrackedKeys((prev) => [...prev, currentRoadmapKey]);
      } else {
        setError(err.message);
      }
    } finally {
      setSaving(false);
    }
  }, [roadmap, conversationId, saving, isTracked, currentRoadmapKey]);

  const saveState = saving ? 'saving' : isTracked ? 'saved' : 'idle';

  const value = useMemo(
    () => ({
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
      refreshTracked,
      clearError: () => setError(''),
    }),
    [
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
      refreshTracked,
    ],
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) throw new Error('useChat must be used inside a ChatProvider.');
  return context;
}
