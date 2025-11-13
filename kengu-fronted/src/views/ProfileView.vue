<template>
  <div class="profile-page">
    <!-- 与QueryView一致的页面头 -->
    <el-header class="hku-header">
      <div class="header-left">
        <el-button 
          type="text" 
          @click="goToQuery"
          class="kengu-btn"
        >
          KengU
        </el-button>
      </div>
      <div class="header-nav">
        <el-button 
          type="text" 
          @click="goToDashboard"
          class="dashboard-btn"
        >
          Dashboard
        </el-button>
      </div>
      <div class="header-right">
        <el-dropdown trigger="click">
          <div class="user-info">
            <el-icon class="user-icon"><User /></el-icon>
            <span class="user-name">{{ userStore.info?.name || userStore.email }}</span>
            <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="goToProfile">Profile</el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout">Logout</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-card class="profile-card">
      <div class="profile-header">
        <el-avatar class="avatar" :size="80">
          <User />
        </el-avatar>
        <div class="user-info">
          <p>{{ userStore.email }}</p>
        </div>
      </div>

      <div class="courses-section">
        <h3>Courses({{ userStore.courses.length }})</h3>
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
    </el-card>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { User, ArrowDown} from '@element-plus/icons-vue'

const userStore = useUserStore()
const router = useRouter()

onMounted(() => {
  if (!userStore.email) {
    router.push('/')
    return
  }
  userStore.loadCourses()
})

// 导航方法（与QueryView保持一致）
const goToQuery = () => router.push('/query')
const goToDashboard = () => router.push('/dashboard')
const goToProfile = () => router.push('/profile')

const handleLogout = () => {
  if (confirm('确定要退出登录吗？')) {
    userStore.logout()
    router.push('/')
  }
}
</script>

<style scoped>
/* 引入与QueryView一致的头部样式 */
.hku-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background-color: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  height: 60px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
}

.el-button.kengu-btn {
  font-size: 20px;
  font-weight: bold;
  color: #0a4a1f;
  padding: 0;
  margin: 0;
}
.el-button.kengu-btn:hover {
  color: #00300f;
  background-color: transparent;
}

.header-nav {
  flex: 1;
  display: flex;
  justify-content: flex-start;
  margin-left: 40px;
}

.el-button.dashboard-btn {
  font-size: 17px;
  color: #333;
}
.el-button.dashboard-btn:hover {
  color: #1f6937;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.user-icon {
  margin-right: 8px;
  font-size: 18px;
}

.user-name {
  font-size: 14px;
  margin-right: 5px;
}

.dropdown-icon {
  font-size: 16px;
}

/* Profile页面特有样式 */
.profile-card {
  max-width: 800px;
  margin: 30px auto;
  padding: 20px;
}

.profile-header {
  display: flex;
  align-items: center;
  margin-bottom: 30px;
  gap: 20px;
}

.avatar {
  background-color: #0a4a1f;
}

.user-info p {
  font-size: 18px;
  font-weight: 500;
  margin: 0;
}

.courses-section {
  margin: 30px 0;
}

.courses-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
  margin-top: 15px;
}

.course-card {
  cursor: pointer;
  transition: all 0.3s;
}
.course-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.course-name {
  font-weight: 600;
  margin-bottom: 5px;
}

.course-fullname {
  font-size: 13px;
  color: #666;
  word-break: break-all;
}
</style>