import api from './api'

export const chatService = {
  sendMessage: async (message, metadata = {}) => {
    const payload = {
      message,
      metadata,
      timestamp: new Date().toISOString()
    }

    try {
      const response = await api.post('/chat', payload)
      return response.data
    } catch (error) {
      throw error
    }
  },

  getHistory: async () => {
    try {
      const response = await api.get('/chat/history')
      return response.data
    } catch (error) {
      throw error
    }
  }
}
