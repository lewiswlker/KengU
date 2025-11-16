import axios from 'axios'
import router from '../router'
import { ElMessage } from 'element-plus'

const getBaseURL = () => {
  // 如果是通过内网穿透访问（域名包含 natapp），使用内网穿透的后端地址
  if (window.location.hostname.includes('natapp')) {
    return 'http://kengu-api.natapp1.cc/api'  // 替换成你的后端内网穿透地址
  }
  // 本地开发使用 localhost
  return 'http://localhost:8009/api'
}

const api = axios.create({
  baseURL: getBaseURL(),
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

export const getUpdateProgress = (taskId) => {
  return api.post('/update-status', { task_id: taskId })
}

export const getUserCourses = (email) => {
  return api.post('/user/courses', { email })
}

export const getCourses = (course_id) => {
  return api.post('/user/courses_id', { course_id })
}

export const getEventUpdate = (email, password, start_date, end_date, id) => {
  return api.post('/update-events', {
    user_email: email,
    user_password: password,
    start_date: start_date,
    end_date: end_date,
    user_id: id
  });
}

export const get_assignments_by_date_range = (start_date, end_date, user_id) => {
  return api.post('/assignments/date-range', { start_date, end_date, user_id })
}

export const get_assignments_by_type = (start_date, end_date, user_id, assignment_type) => {
  return api.post('/assignments/type', { start_date, end_date, user_id, assignment_type })
}

export const get_assignment_progress_stats = (user_id) => {
  return api.post('/assignments/stats', { user_id })
}

export const get_upcoming_assignments = (user_id, days) => {
  return api.post('/assignments/upcoming', { user_id, days })
}
export const mark_assignment_complete = (assignment_id) => {
  return api.post('/assignments/mark-complete', { assignment_id })
}

export const mark_assignment_pending = (assignment_id) => {
  return api.post('/assignments/mark-pending', { assignment_id })
}


export const askQuestion = (user_request, user_id, email, messages) => {
  return fetch('/chat/stream', {
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
console.log('导出的函数:', {
  mark_assignment_complete: typeof mark_assignment_complete,
  mark_assignment_pending: typeof mark_assignment_pending
});
export default api