import { apiRequest } from './api.js';

export const getDashboard = () => apiRequest('/api/dashboard/');

export const listPlans = () => apiRequest('/api/plans/');

export const getPlan = (id) => apiRequest(`/api/plans/${id}/`);

export const savePlan = (roadmap, conversationId = null) =>
  apiRequest('/api/plans/', {
    method: 'POST',
    body: { roadmap, conversation_id: conversationId },
  });

export const setPlanActive = (id, isActive) =>
  apiRequest(`/api/plans/${id}/`, { method: 'PATCH', body: { is_active: isActive } });

export const deletePlan = (id) => apiRequest(`/api/plans/${id}/`, { method: 'DELETE' });

export const setStepCompletion = (stepId, isCompleted) =>
  apiRequest(`/api/steps/${stepId}/`, { method: 'PATCH', body: { is_completed: isCompleted } });

export const setMilestoneCompletion = (milestoneId, isCompleted) =>
  apiRequest(`/api/milestones/${milestoneId}/`, {
    method: 'PATCH',
    body: { is_completed: isCompleted },
  });
