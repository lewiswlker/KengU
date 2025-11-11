import axios from 'axios'
import router from '../router'

const api = axios.create({
  baseURL: 'http://localhost:5000/api', 
  timeout: 30000, 
  headers: { 'Content-Type': 'application/json' }
})


api.interceptors.request.use(
  (config) => {
    const userEmail = localStorage.getItem('userEmail')
    if (userEmail) {
      config.headers['X-User-Email'] = userEmail
    }
    return config
  },
  (error) => Promise.reject(error)
)


api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('userEmail')
      router.push('/')
      alert('Login Timeout')
    }
    else if (error.response?.status >= 500) {
      alert('Server is busy, please try again later')
    }
    else if (!error.response) {
      alert('Network connection failed. Please check if the backend service is running.')
    }
    return Promise.reject(error)
  }
)

export const verifyHkuAuth = (email, password) => {
  return api.post('/hku-auth', { email, password })
}

export const checkAndCreateUser = (email) => {
  return api.post('/user/check-and-create', { email })
}

export const getUserCourses = (email) => {
  return api.post('/user/courses', { email})
}

export const askQuestion = (question) => {
  return api.post('/rag/query', { question })
}

export const getUserInfo = () => {
  return api.get('/user/info')
}

export default api