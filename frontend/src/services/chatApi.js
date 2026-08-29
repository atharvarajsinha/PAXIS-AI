import { API_BASE_URL, ApiError, apiRequest, authHeaders, readApiError } from './api.js';

/**
 * Send a message and stream the assistant's reply.
 *
 * `onChunk` receives every server-sent event as it arrives (status updates, the
 * conversation id, the response text, and each roadmap revision) so the UI can
 * render progress instead of waiting for the whole answer.
 */
export async function sendChatMessage(message, conversationId = null, onChunk = null) {
  const response = await fetch(`${API_BASE_URL}/api/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(
      readApiError(errorData, 'Unable to reach the learning assistant.'),
      response.status,
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  const finalData = {};
  let streamError = null;

  const handleBlock = (block) => {
    for (const line of block.split('\n')) {
      if (!line.startsWith('data: ')) continue;
      const raw = line.slice(6).trim();
      if (!raw) continue;

      let chunk;
      try {
        chunk = JSON.parse(raw);
      } catch {
        continue; // A partial frame; the next read will complete it.
      }

      if (chunk.error) {
        streamError = chunk.error;
        continue;
      }
      if (chunk.conversation_id !== undefined) finalData.conversation_id = chunk.conversation_id;
      if (chunk.response !== undefined) finalData.response = chunk.response;
      if (chunk.roadmap !== undefined) finalData.roadmap = chunk.roadmap;
      if (onChunk) onChunk(chunk);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop();
    blocks.forEach(handleBlock);
  }
  if (buffer.trim()) handleBlock(buffer);

  if (streamError) throw new Error(streamError);
  return finalData;
}

export const listConversations = () => apiRequest('/api/conversations/');

export const getConversation = (id) => apiRequest(`/api/conversations/${id}/`);

export const renameConversation = (id, title) =>
  apiRequest(`/api/conversations/${id}/`, { method: 'PATCH', body: { title } });

export const deleteConversation = (id) =>
  apiRequest(`/api/conversations/${id}/`, { method: 'DELETE' });
