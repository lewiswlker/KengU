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
        <img 
          src="../assets/logo.png"
          alt="KengU Logo" 
          class="kengu-logo"
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
import { ElMessageBox } from 'element-plus';

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
  ElMessageBox.confirm(
    'Are you sure to logout?', 
    'Confirmation', 
    {
      confirmButtonText: 'Yes',
      cancelButtonText: 'Cancel',
      type: 'warning',
      customClass: 'custom-logout-box'
    }
  )
  .then(() => {
    userStore.logout();
    router.push('/');
  })
  .catch(() => {
    // 取消退出逻辑
  });
};
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

.kengu-logo {
  width: 40px;           /* 建议稍大于文字高度，视觉更协调 */
  height: 40px;
  object-fit: contain;   /* 保持图片比例，避免变形 */
  border-radius: 4px;    /* 可选：轻微圆角，柔和边缘 */
}

.kengu-btn:hover .kengu-logo {
  opacity: 0.9;          /* 图片hover时稍暗，增强反馈 */
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

@media (max-width: 768px) {
  .kengu-logo {
    width: 40px;
    height: 40px;
  }
  .kengu-btn {
    font-size: 16px;
  }
}
</style>

<style>
/* 移除 scoped 属性，确保样式能穿透到弹窗组件 */

/* 针对 custom-logout-box 类的弹窗样式 */
.custom-logout-box .el-message-box {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

/* 标题颜色 */
.custom-logout-box .el-message-box__title {
  color: #0a4a1f !important; /* 主题绿标题 */
}

/* 内容文字颜色 */
.custom-logout-box .el-message-box__message {
  color: #555 !important; /* 深灰色内容 */
  font-size: 14px !important;
}

/* 确认按钮（Yes） */
.custom-logout-box .el-button--primary {
  background-color: #0a4a1f !important; /* 主题绿背景 */
  border-color: #0a4a1f !important;
  color: white !important;
}

/* 确认按钮 hover */
.custom-logout-box .el-button--primary:hover {
  background-color: #073416 !important; /* 深色绿 */
  border-color: #073416 !important;
}

/* 取消按钮（Cancel） */
.custom-logout-box .el-button--default {
  background-color: #f5f5f5 !important; /* 浅灰背景 */
  border-color: #ddd !important;
  color: #666 !important;
}

/* 取消按钮 hover */
.custom-logout-box .el-button--default:hover {
  background-color: #e6e6e6 !important; /* 深一点的浅灰 */
  border-color: #ccc !important;
  color: #333 !important;
}

</style>