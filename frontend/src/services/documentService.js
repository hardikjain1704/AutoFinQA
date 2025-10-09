import api from './api'

export const documentService = {
  uploadDocument: async (file) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await api.post('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      return response.data
    } catch (error) {
      throw error
    }
  },

  checkHealth: async () => {
    try {
      const response = await api.get('/health')
      return response.data
    } catch (error) {
      throw error
    }
  }
}
