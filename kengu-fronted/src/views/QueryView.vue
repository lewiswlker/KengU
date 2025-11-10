<template>
  <div class="query-page">
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

    <!-- 主体容器：课程栏 + 问答区 完全分开 -->
    <div class="main-wrapper">
      <!-- 左侧课程容器 -->
      <div class="course-container">
        <h3 class="sidebar-title">Courses</h3>
        <el-scrollbar class="course-list">
          <el-tag 
            v-for="course in userStore.courses" 
            :key="course.id"
            class="course-tag"
            @click="selectCourse(course)"
            :class="{ 'selected-course': selectedCourse?.id === course.id }"
          >
            {{ course.name }}
          </el-tag>
        </el-scrollbar>
      </div>

      <!-- 右侧问答容器 -->
      <div class="qa-container">
        <!-- 回答区域（可滚动） -->
        <div class="answer-container">
          <div v-if="!answer" class="empty-answer">
            <p>Welcome to KengU. How can I help you?</p>
          </div>
          <el-card v-if="answer" class="answer-card">
            <div class="answer-header">
              <h3>回答结果</h3>
              <span class="answer-time">{{ answerTime }}</span>
            </div>
            <div class="answer-content">{{ answer.content }}</div>
            <div v-if="answer.sources.length" class="answer-sources">
              <h4>参考来源：</h4>
              <el-link
                v-for="(source, index) in answer.sources"
                :key="index"
                :href="source.url"
                target="_blank"
                class="source-link"
              >
                <el-icon><Document /></el-icon>
                {{ source.name }}
              </el-link>
            </div>
          </el-card>
        </div>

        <!-- 右下角固定提问区域 -->
        <div class="fixed-input-container">
          <textarea
            v-model="question"
            rows="3"
            placeholder="Please Enter your question(Like: {{ selectedCourse ? selectedCourse.name + '的期末考试范围是什么？' : 'COMP7103的聚类算法有哪些？' }})"
            class="query-input"
          ></textarea>
          <div class="query-actions">
            <el-button 
              type="primary" 
              @click="submitQuestion"
              :loading="isLoading"
              :disabled="!question.trim()"
              class="submit-btn"
            >
              <el-icon><Search /></el-icon>
              提交查询
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { askQuestion } from '../services/api'
import { User, ArrowDown, Search, Document } from '@element-plus/icons-vue'

const userStore = useUserStore()
const router = useRouter()
const question = ref('')
const isLoading = ref(false)
const selectedCourse = ref(null)
const answer = ref(null)
const answerTime = ref('')

const goToQuery = () => {
  router.push('/query')
}

const goToDashboard = () => {
  router.push('/dashboard')
}

const goToProfile = () => {
  router.push('/profile')
}

onMounted(() => {
  if (!userStore.email) {
    router.push('/')
    return
  }
  if (userStore.courses.length === 0) {
    userStore.loadCourses()
  }
})

const selectCourse = (course) => {
  selectedCourse.value = course
}

const submitQuestion = async () => {
  isLoading.value = true
  try {
    const res = await askQuestion(question.value)
    answer.value = res.data
    answerTime.value = new Date().toLocaleString()
    question.value = ''
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (error) {
    console.error('提问失败', error)
    alert('查询失败，请重试')
  } finally {
    isLoading.value = false
  }
}

const handleLogout = () => {
  if (confirm('确定要退出登录吗？')) {
    userStore.logout()
    router.push('/')
  }
}
</script>

<style scoped>
/* 页眉样式 */
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

.kengu-btn {
  font-size: 20px;
  font-weight: bold;
  color: #0a4a1f;
  padding: 0;
  margin: 0;
}
.kengu-btn:hover {
  color: #073416;
  background-color: transparent;
}

.header-nav {
  flex: 1;
  display: flex;
  justify-content: flex-start;
  margin-left: 40px;
}

.dashboard-btn {
  font-size: 17px;
  color: #333;
}
.dashboard-btn:hover {
  color: #0a4a1f;
}

.header-right {
  display: flex;
  align-items: center;
}

.notification-btn {
  position: relative;
  margin-right: 15px;
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


.main-wrapper {
  display: flex;
  margin-top: 10px;
  height: calc(100vh - 70px);
}

.course-container {
  width: 250px;
  background-color: #f5f7fa;
  border-right: 1px solid #eaecef;
  position: sticky;
  top: 70px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar-title {
  padding: 15px;
  margin: 0;
  text-align: center;
  font-size: 18px;
  font-weight: 600;
}

.course-list {
  flex: 1;
  padding: 15px;
  overflow-y: auto;
}

.course-tag {
  display: block;
  width: 100%;
  text-align: left;
  margin-bottom: 8px;
  cursor: pointer;
  padding: 8px 12px;
}
.selected-course {
  background-color: #0a4a1f;
  color: #fff;
}

.qa-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
}


.answer-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background-color: #fff;
}

.empty-answer {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
}

.answer-card {
  width: 100%;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  padding: 20px;
}

.answer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.answer-time {
  font-size: 12px;
  color: #666;
}

.answer-content {
  line-height: 1.8;
  white-space: pre-line;
  margin-bottom: 15px;
}

.answer-sources {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #f0f0f0;
}

.source-link {
  display: block;
  margin-bottom: 8px;
  color: #0a4a1f;
}

.fixed-input-container {
  position: fixed;
  bottom: 0;
  right: 0;
  left: 270px;
  background-color: #fff;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
  z-index: 10;
  padding: 15px 20px;
  border-top: 1px solid #eaecef;
}

.query-input {
  width: 100%;
  border-radius: 12px;
  border: 1px solid #ddd;
  padding: 10px;
  background-color: #fff;
  resize: vertical;
}
.query-input:focus {
  border-color: #0a4a1f;
  box-shadow: 0 0 0 2px rgba(10, 74, 31, 0.1);
  outline: none;
}

.query-actions {
  margin-top: 10px;
  text-align: right;
}

.submit-btn {
  padding: 8px 20px;
  font-size: 14px;
  border-radius: 8px;
}
</style>