import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json'
  },
  timeout: 600000,
  withCredentials: false,
})

api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      error.message = 'Request timeout. Please try again.'
    } else if (!error.response) {
      error.message = 'Network error. Please confirm the backend is reachable.'
    } else {
      const { status, data } = error.response
      const defaultMessage = 'Something went wrong. Please try again.'
      if (status >= 500) {
        error.message = data?.message || 'Server error. Please try later.'
      } else if (status === 404) {
        error.message = 'Endpoint not found. Please confirm the backend route exists.'
      } else if (status === 400) {
        error.message = data?.message || 'Invalid request. Please check your input.'
      } else {
        error.message = data?.message || defaultMessage
      }
    }
    return Promise.reject(error)
  }
)

export default api
