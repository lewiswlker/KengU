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
      alert('登录已失效，请重新登录')
    }
    else if (error.response?.status >= 500) {
      alert('服务器繁忙，请稍后重试')
    }
    else if (!error.response) {
      alert('网络连接失败，请检查后端服务是否启动')
    }
    return Promise.reject(error)
  }
)

export const verifyHkuAuth = (email, password) => {
  return api.post('/hku-auth', { email, password })
}

export const login = (email, password) => {
  return api.post('/auth/login', { email, password })
}

export const askQuestion = (question) => {
  return api.post('/rag/query', { question })
}

export const getUserCourses = () => {
  return api.get('/user/courses')
}

export const getUserInfo = () => {
  return api.get('/user/info')
}

export default api