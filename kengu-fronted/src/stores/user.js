import { defineStore } from 'pinia'
import { getUserCourses } from '../services/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    email: localStorage.getItem('userEmail') || '',
    info: null,
    courses: []
  }),
  actions: {
    setLogin(email) {
      this.email = email
      localStorage.setItem('userEmail', email)
    },
    logout() {
      this.email = ''
      this.info = null
      this.courses = []
      localStorage.removeItem('userEmail')
    },
    async loadCourses() {
      try {
        const res = await getUserCourses(this.email)
        this.courses = res.data
      } catch (error) {
        console.error('获取课程失败', error)
      }
    }
  }
})