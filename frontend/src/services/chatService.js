import api from './api'

const endpointForWorkflow = (workflow) => {
  if (workflow === 'agent') return '/ask-agent'
  return '/ask' // default simple
}

export const chatService = {
  askQuestion: async (query, { workflow = 'simple', sessionId = 'default_user' } = {}) => {
    try {
      const path = endpointForWorkflow(workflow)
      const response = await api.post(path, { query, session_id: sessionId })
      return response.data
    } catch (error) {
      throw error
    }
  },
}
