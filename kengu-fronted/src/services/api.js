import axios from 'axios'
import router from '../router'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  timeout: 600000,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use(
  (config) => {
    const userEmail = localStorage.getItem('userEmail')
    const userId = localStorage.getItem('userId')
    
    if (userEmail) {
      config.headers['X-User-Email'] = userEmail
    }
    if (userId) {
      config.headers['X-User-ID'] = userId
    }
    
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (!error.response) {
      ElMessage.error('Network error: Please check backend service or network connection')
      return Promise.reject(error)
    }

    if (error.response?.status === 401) {
      localStorage.removeItem('userEmail')
      localStorage.removeItem('userId')
      router.push('/')
      ElMessage.error('Login expired: Please log in again')
      return Promise.reject(error)
    }

    if (error.response?.status === 400) {
      const errMsg = error.response.data?.message || 'Invalid request: Please check input'
      ElMessage.warning(errMsg)
      return Promise.reject(error)
    }

    if (error.response?.status === 404) {
      const errMsg = error.response.data?.message || 'Resource not found'
      ElMessage.error(errMsg)
      return Promise.reject(error)
    }

    if (error.response?.status >= 500) {
      const errMsg = error.response.data?.message || 'Server error: Please try again later'
      ElMessage.error(errMsg)
      return Promise.reject(error)
    }

    ElMessage.error(`Request failed: ${error.message}`)
    return Promise.reject(error)
  }
)

export const verifyHkuAuth = (email, password) => {
  return api.post('/hku-auth', { email, password })
}

export const checkAndCreateUser = (email) => {
  return api.post('/user/check-and-create', { email })
}

export const updateKnowledgeBase = (email, password, id) => {
  return api.post('/update-data', { email, password, id })
}

export const getUserCourses = (email) => {
  return api.post('/user/courses', { email })
}

export const askQuestion = (user_request, user_id, email, messages) => {
  return fetch('http://localhost:5000/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
      'X-User-Email': email,
      'X-User-ID': user_id ? String(user_id) : ''
    },
    body: JSON.stringify({
      user_request,
      user_id: user_id ? Number(user_id) : null,
      user_email: email,
      messages
    })
  });
};

export const getUserInfo = () => {
  return api.get('/user/info')
}

export const logout = () => {
  localStorage.removeItem('userEmail')
  localStorage.removeItem('userId')
  router.push('/')
  ElMessage.success('Logged out successfully')
}

export default api