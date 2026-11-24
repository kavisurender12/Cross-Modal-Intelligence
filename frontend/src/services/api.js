import axios from 'axios'
import toast from 'react-hot-toast'

const rawApiUrl = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '')
const baseURL = rawApiUrl
  ? (rawApiUrl.endsWith('/api') ? rawApiUrl : `${rawApiUrl}/api`)
  : '/api'

const api = axios.create({
  baseURL,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' }
})

// Attach JWT token to every request
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Global response error handling
api.interceptors.response.use(
  response => response,
  error => {
    if (error.code === 'ERR_NETWORK' || error.code === 'ECONNREFUSED') {
      // Backend not running
      toast.error('Cannot reach the server. Make sure the backend is running on port 5000.', { id: 'network-error', duration: 6000 })
    } else if (error.response?.status === 401) {
      // Token expired — clear and redirect
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    } else if (error.response?.status === 503) {
      toast.error('Database connection failed. Make sure MongoDB is running.', { id: 'db-error', duration: 6000 })
    }
    return Promise.reject(error)
  }
)

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  profile: () => api.get('/auth/profile')
}

// ─── Detection ────────────────────────────────────────────────────────────────
export const detectAPI = {
  fakeNews: (data) => api.post('/detect/fake-news', data),
  phishing: (data) => api.post('/detect/phishing', data),
  digitalFraud: (data) => api.post('/detect/digital-fraud', data),
  crossModal: (data) => api.post('/detect/cross-modal', data),
  image: (formData) => api.post('/detect/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000  // OCR can be slow on first run (model download)
  })
}

// ─── History ──────────────────────────────────────────────────────────────────
export const historyAPI = {
  getAll: (params) => api.get('/history', { params }),  // no trailing slash
  getOne: (id) => api.get(`/history/${id}`),
  delete: (id) => api.delete(`/history/${id}`)
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
export const dashboardAPI = {
  stats: () => api.get('/dashboard/stats')
}

// ─── Reports ─────────────────────────────────────────────────────────────────
export const reportAPI = {
  getPdf: (id) => api.get(`/reports/${id}/pdf`, {
    responseType: 'blob',
    timeout: 30000
  })
}

export default api
