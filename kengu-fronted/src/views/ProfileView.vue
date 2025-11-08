<template>
  <div class="profile-page">
    <el-header class="page-header">
      <div class="header-left">
        <el-icon><Book /></el-icon>
        <span class="app-name">KengU 学术助手</span>
      </div>
      <div class="header-right">
        <el-button 
          type="text" 
          @click="goToQuery"
        >
          <el-icon><Message /></el-icon>
          问答主页
        </el-button>
      </div>
    </el-header>

    <el-card class="profile-card">
      <div class="profile-header">
        <el-avatar class="avatar" :size="80">
          <User />
        </el-avatar>
        <div class="user-info">
          <h2>{{ userStore.info?.name || '未获取姓名' }}</h2>
          <p>{{ userStore.email }}</p>
          <p>学号：{{ userStore.info?.studentId || '未获取学号' }}</p>
        </div>
      </div>

      <div class="courses-section">
        <h3>已选课程（{{ userStore.courses.length }}门）</h3>
        <el-divider />
        <div class="courses-grid">
          <el-card 
            v-for="course in userStore.courses" 
            :key="course.id"
            class="course-card"
          >
            <div class="course-name">{{ course.name }}</div>
            <div class="course-fullname">{{ course.fullName }}</div>
          </el-card>
        </div>
      </div>

      <div class="logout-section">
        <el-button 
          type="danger" 
          @click="handleLogout"
        >
          <el-icon><Logout /></el-icon>
          退出登录
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { Book, User, Message, Logout } from '@element-plus/icons-vue'

const userStore = useUserStore()
const router = useRouter()

onMounted(() => {
  if (!userStore.email) {
    router.push('/')
    return
  }
  userStore.loadUserInfo()
  userStore.loadCourses()
})

const goToQuery = () => {
  router.push('/query')
}

const handleLogout = () => {
  if (confirm('确定要退出登录吗？')) {
    userStore.logout()
    router.push('/')
  }
}
</script>

<style scoped>
/* 样式参考TS版本，略 */
</style>