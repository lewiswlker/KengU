import { defineStore } from 'pinia'
import { getUserCourses } from '../services/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    id: localStorage.getItem('userId') || '', // 新增：用户ID（从本地存储读取）
    email: localStorage.getItem('userEmail') || '',
    info: null,
    password: null,
    courses: [],
    updateStatus: 'idle',
    updateMessage: ''
  }),
  actions: {
    setLogin(email, password, id) {
      this.password = password
      this.email = email
      this.id = id || ''
      localStorage.setItem('userEmail', email)
      localStorage.setItem('userId', id || '')
    },
    logout() {
      this.id = ''
      this.email = ''
      this.info = null
      this.password = null
      this.courses = []
      localStorage.removeItem('userEmail')
      localStorage.removeItem('userId')
    },
    setUserId(id) {
      this.id = id
      localStorage.setItem('userId', id)
    },
    async loadCourses() {
      try {
        const res = await getUserCourses(this.email)
        this.courses = res.data || []
      } catch (error) {
        console.error('获取课程失败', error)
        this.courses = []
      }
    }
  }
})