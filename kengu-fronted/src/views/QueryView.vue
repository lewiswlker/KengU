<template>
  <div class="query-page">
    <!-- 顶部导航 -->
    <el-header class="page-header">
      <div class="header-left">
        <el-icon><Book /></el-icon>
        <span class="app-name">KengU 学术助手</span>
      </div>
      <div class="header-right">
        <el-button 
          type="text" 
          @click="goToProfile"
          class="profile-btn"
        >
          <el-icon><User /></el-icon>
          {{ userStore.info?.name || userStore.email }}
        </el-button>
        <el-button 
          type="text" 
          @click="handleLogout"
        >
          <el-icon><Logout /></el-icon>
          退出登录
        </el-button>
      </div>
    </el-header>

    <!-- 主内容区 -->
    <el-container class="main-container">
      <!-- 左侧课程列表 -->
      <el-aside width="250px" class="course-sidebar">
        <h3 class="sidebar-title">我的课程</h3>
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
      </el-aside>

      <!-- 右侧问答区 -->
      <el-main class="query-content">
        <el-card class="query-input-card">
          <el-input
            v-model="question"
            type="textarea"
            :rows="4"
            placeholder="请输入您的问题（例如：{{ selectedCourse ? selectedCourse.name + '的期末考试范围是什么？' : 'COMP7103的聚类算法有哪些？' }}）"
            resize="none"
          />
          <div class="query-actions">
            <el-button 
              type="primary" 
              @click="submitQuestion"
              :loading="isLoading"
              :disabled="!question.trim()"
            >
              <el-icon><Search /></el-icon>
              提交查询
            </el-button>
          </div>
        </el-card>

        <!-- 回答展示 -->
        <div v-if="answer" class="answer-container">
          <el-card class="answer-card">
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
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { askQuestion } from '../services/api'
import { Book, User, Logout, Search, Document } from '@element-plus/icons-vue'

// 状态定义
const userStore = useUserStore()
const router = useRouter()
const question = ref('')
const isLoading = ref(false)
const selectedCourse = ref(null)
const answer = ref(null)
const answerTime = ref('')

// 页面加载时初始化
onMounted(() => {
  if (!userStore.email) {
    router.push('/')
    return
  }
  if (userStore.courses.length === 0) {
    userStore.loadCourses()
  }
})

// 选择课程
const selectCourse = (course) => {
  selectedCourse.value = course
}

// 提交问题
const submitQuestion = async () => {
  isLoading.value = true
  try {
    const res = await askQuestion(question.value)
    answer.value = res.data
    answerTime.value = new Date().toLocaleString()
    question.value = ''
  } catch (error) {
    console.error('提问失败', error)
    alert('查询失败，请重试')
  } finally {
    isLoading.value = false
  }
}

// 跳转到个人中心
const goToProfile = () => {
  router.push('/profile')
}

// 退出登录
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