import api from './api'

export const chatService = {
  askQuestion: async (query) => {
    try {
      const response = await api.post('/ask', { query })
      return response.data
    } catch (error) {
      throw error
    }
  },
}
