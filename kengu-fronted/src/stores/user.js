import { defineStore } from 'pinia'
import { getUserCourses } from '../services/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    id: localStorage.getItem('userId') || '',
    email: localStorage.getItem('userEmail') || '',
    info: null,
    password: null,
    courses: [],
    updateStatus: 'idle',
    updateMessage: '',
    // 新增：用于进度条的任务ID（关键！）
    eventTaskId: localStorage.getItem('eventTaskId') || null 
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
      this.eventTaskId = null // 退出时清空任务ID
      localStorage.removeItem('userEmail')
      localStorage.removeItem('userId')
      localStorage.removeItem('eventTaskId') // 清除本地存储的任务ID
    },
    setUserId(id) {
      this.id = id
      localStorage.setItem('userId', id)
    },
    // 新增：存储事件更新任务ID（进度条核心）
    setEventTaskId(taskId) {
      this.eventTaskId = taskId
      if (taskId) {
        localStorage.setItem('eventTaskId', taskId) // 持久化到本地存储
      } else {
        localStorage.removeItem('eventTaskId')
      }
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