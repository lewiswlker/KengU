<template>
  <div class="query-page">
    <!-- 顶部进度条 -->
    <el-progress
      v-if="showProgress"
      :percentage="progressPercent"
      :status="progressStatus"
      stroke-width="4"
      style="position: fixed; top: 60px; left: 0; right: 0; z-index: 100; background: white; padding: 5px 20px;"
    >
      <template #default>
        <span style="margin-right: 15px; font-size: 14px; font-weight: 500;">Loading course resources:</span>
        <span style="margin-left: 10px; font-size: 14px;">{{ progressText }}</span>
      </template>
    </el-progress>

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

    <div class="main-wrapper">
      <!-- 左侧课程容器 -->
      <div class="course-container">
        <h3 class="sidebar-title">Courses</h3>
        <div class="course-action-btn">
          <el-button
            type="primary"
            size="small"
            @click="handleUpdateAllCourses"
            class="update-course-btn"
            :loading="isUpdateLoading"
          >
            <el-icon v-if="isUpdateLoading" class="loading-icon"><Loading /></el-icon>
            <el-icon v-else><Refresh /></el-icon>
            Load/Update all my course
          </el-button>
        </div>
        <el-scrollbar class="course-list">
          <el-tag 
            v-for="course in userStore.courses" 
            :key="course.id"
            class="course-tag"
            @click="addCourseReference(course)"
            :class="{ 'selected-course': isCourseSelected(course.id) }"
            :title="course.name"
          >
            <span class="course-text">{{ course.name }}</span>
          </el-tag>
        </el-scrollbar>
      </div>

      <!-- 右侧问答容器 -->
      <div class="qa-container">
        <!-- 回答区域（可滚动） -->
        <div class="answer-container">
          <el-scrollbar class="chat-scroll">
            <!-- 空状态 -->
            <div v-if="chatHistory.length === 0" class="empty-answer">
              <p>Welcome to KengU. How can I help you?</p>
            </div>
            
            <!-- 聊天消息列表 -->
            <div v-else class="chat-messages">
              <div 
                v-for="(msg, index) in chatHistory" 
                :key="index"
                :class="['chat-message', msg.role === 'user' ? 'user-message' : 'ai-message']"
                ref="messageRefs"
              >
                <div class="message-role">
                  {{ msg.role === 'user' ? 'You' : 'KengU Assistant' }}
                  <span class="message-time">{{ msg.time }}</span>
                </div>
                <div class="message-content" v-html="formatMessage(msg.content)"></div>
                
                <!-- AI 回答的参考来源 -->
                <div v-if="msg.role === 'assistant' && msg.sources?.length" class="message-sources">
                  <h4>参考来源：</h4>
                  <el-link
                    v-for="(source, idx) in msg.sources"
                    :key="idx"
                    :href="source.url"
                    target="_blank"
                    class="source-link"
                  >
                    <el-icon><Document /></el-icon>
                    {{ source.name }}
                  </el-link>
                </div>
              </div>
              
              <!-- AI 正在输入提示 -->
              <div v-if="isGenerating" class="chat-message ai-message generating" ref="typingRef">
                <div class="message-role">
                  KengU Assistant
                  <span class="message-time">{{ new Date().toLocaleString() }}</span>
                </div>
                <div class="message-content">
                  {{ currentAiContent }}<span class="typing-dot">●</span>
                </div>
              </div>
            </div>
          </el-scrollbar>
        </div>

        <!-- 右下角固定提问区域（包含终止按钮） -->
        <div class="fixed-input-container">
          <!-- 课程引用标签区域 -->
          <div class="reference-tags" v-if="selectedCourses.length > 0">
            <el-tag 
              v-for="course in selectedCourses" 
              :key="course.id"
              closable 
              type="info"
              @close="removeCourseReference(course.id)"
              class="course-reference-tag"
            >
              {{ course.name }}
            </el-tag>
          </div>
          
          <textarea
            v-model="question"
            rows="3"
            placeholder="Please Enter your question..."
            class="query-input"
            @keydown.enter.prevent="submitQuestion"
            :disabled="isLoading || isGenerating"
          ></textarea>
          
          <div class="query-actions">
            <!-- 生成中显示终止按钮，否则显示清空按钮 -->
            <el-button 
              v-if="isGenerating"
              type="text" 
              @click="stopGeneration"
              class="stop-btn"
            >
              Stop
            </el-button>
            <el-button 
              v-else
              type="text" 
              @click="clearInput"
              class="clear-btn"
              :disabled="!question.trim() && selectedCourses.length === 0"
            >
              Clear
            </el-button>
            
            <el-button 
              type="primary" 
              @click="submitQuestion"
              :loading="isLoading || isGenerating"
              :disabled="(!question.trim() && selectedCourses.length === 0) || isGenerating"
              class="submit-btn"
            >
              <el-icon><Search /></el-icon>
              Submit
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { updateKnowledgeBase, getUpdateProgress } from '../services/api'  // 新增进度查询接口
import { User, ArrowDown, Search, Document, Refresh, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const router = useRouter()

// 核心状态
const question = ref('')
const isLoading = ref(false)
const isGenerating = ref(false)
const chatHistory = ref([])
const currentAiContent = ref('')
const isUpdateLoading = ref(false)
const abortController = ref(null)
const selectedCourses = ref([])
const updatePollInterval = ref(null)  // 用于存储进度轮询的计时器

// 进度条相关状态
const showProgress = ref(false)
const progressPercent = ref(0)
const progressText = ref('准备更新...')
const progressStatus = computed(() => {
  if (progressText.value.includes('失败')) return 'exception'
  if (progressPercent.value === 100) return 'success'
  return 'active'
})

// 用于获取消息 DOM 元素的 ref
const messageRefs = ref([])
const typingRef = ref(null)

// 滚动到最新消息的方法
const scrollToLatest = async () => {
  await nextTick()
  if (isGenerating.value && typingRef.value) {
    typingRef.value.scrollIntoView({ behavior: 'smooth', block: 'end' })
  } else if (messageRefs.value.length > 0) {
    messageRefs.value[messageRefs.value.length - 1].scrollIntoView({ behavior: 'smooth', block: 'end' })
  }
}

// 添加课程引用
const addCourseReference = (course) => {
  const isAlreadySelected = selectedCourses.value.some(item => item.id === course.id)
  if (!isAlreadySelected) {
    selectedCourses.value.push(course)
  }
}

// 移除课程引用
const removeCourseReference = (courseId) => {
  selectedCourses.value = selectedCourses.value.filter(course => course.id !== courseId)
}

// 检查课程是否被选中
const isCourseSelected = (courseId) => {
  return selectedCourses.value.some(course => course.id === courseId)
}

// 导航方法
const goToQuery = () => router.push('/query')
const goToDashboard = () => router.push('/dashboard')
const goToProfile = () => router.push('/profile')

// 页面加载时初始化
onMounted(async () => {
  if (!userStore.email) {
    router.push('/')
    return
  }
  if (userStore.courses.length === 0) {
    await userStore.loadCourses()
  }
  // 自动触发更新
  handleUpdateAllCourses()
})

// 组件卸载时清理
onUnmounted(() => {
  if (abortController.value) {
    abortController.value.abort()
  }
  if (updatePollInterval.value) {
    clearInterval(updatePollInterval.value)
  }
})

// 清空输入框
const clearInput = () => {
  question.value = ''
  selectedCourses.value = []
}

// 格式化消息内容
const formatMessage = (content) => {
  return content.replace(/\n/g, '<br/>')
}

// 终止AI回答生成
const stopGeneration = () => {
  if (abortController.value) {
    abortController.value.abort()
    console.log('已手动终止回答')
    
    if (currentAiContent.value.trim()) {
      chatHistory.value.push({
        role: 'assistant',
        content: currentAiContent.value,
        time: new Date().toLocaleString(),
        sources: []
      })
    }
    
    isGenerating.value = false
    currentAiContent.value = ''
    scrollToLatest()
    ElMessage.info('已终止回答生成')
  }
}

// 自定义 fetch 版本的 askQuestion
const fetchAskQuestion = (user_request, user_id, email, messages) => {
  return fetch('http://localhost:5000/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream'
    },
    body: JSON.stringify({
      user_request,
      user_id: user_id ? Number(user_id) : null,
      user_email: email,
      messages
    }),
    signal: abortController.value?.signal
  })
}

// 提交问题
const submitQuestion = async () => {
  let finalQuestion = question.value.trim()
  if (selectedCourses.value.length > 0) {
    const courseNames = selectedCourses.value.map(course => course.name).join('、')
    finalQuestion = `[课程: ${courseNames}] ${finalQuestion}`
  }

  if (!finalQuestion) return

  const userMsg = {
    role: 'user',
    content: finalQuestion,
    time: new Date().toLocaleString()
  }
  chatHistory.value.push(userMsg)
  question.value = ''
  selectedCourses.value = []
  isGenerating.value = true
  currentAiContent.value = ''

  const messagesParams = chatHistory.value.map(msg => ({
    role: msg.role,
    content: msg.content
  }))

  try {
    abortController.value = new AbortController()

    const response = await fetchAskQuestion(
      finalQuestion,
      userStore.id,
      userStore.email,
      messagesParams
    )

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    if (!response.body || typeof response.body.getReader !== 'function') {
      throw new Error('后端未返回有效的流式响应')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let isStreaming = true

    while (isStreaming) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      for (const line of lines) {
        if (line.startsWith('data: ') && line.trim() !== 'data: ') {
          try {
            const dataStr = line.slice(6)
            const { chunk } = JSON.parse(dataStr)
            currentAiContent.value += chunk
            await nextTick()
            scrollToLatest()
          } catch (e) {
            console.error('解析流式数据失败：', e)
          }
        }
      }
      buffer = lines[lines.length - 1] || ''
    }

    isGenerating.value = false
    if (currentAiContent.value) {
      chatHistory.value.push({
        role: 'assistant',
        content: currentAiContent.value,
        time: new Date().toLocaleString(),
        sources: []
      })
      currentAiContent.value = ''
      await nextTick()
      scrollToLatest()
    }

  } catch (error) {
    isGenerating.value = false
    if (error.name !== 'AbortError') {
      console.error('提问失败', error)
      ElMessage.error('查询失败，请重试')
      chatHistory.value.pop()
    }
  } finally {
    abortController.value = null
  }
}

// 退出登录
const handleLogout = () => {
  if (confirm('确定要退出登录吗？')) {
    if (abortController.value) {
      abortController.value.abort()
    }
    if (updatePollInterval.value) {
      clearInterval(updatePollInterval.value)
    }
    userStore.logout()
    router.push('/')
  }
}

// 更新课程（带进度条）
const handleUpdateAllCourses = async () => {
  if (!userStore.email || !userStore.password) {
    ElMessage.warning('请先登录')
    router.push('/')
    return
  }

  if (isUpdateLoading.value) return

  // 初始化进度条
  showProgress.value = true
  progressPercent.value = 0
  progressText.value = '正在启动更新任务...'
  isUpdateLoading.value = true

  try {
    // 1. 启动更新任务，获取task_id
    const startRes = await updateKnowledgeBase(
      userStore.email, 
      userStore.password, 
      userStore.id
    )

    if (!startRes.success || !startRes.task_id) {
      throw new Error(startRes.error || '启动更新任务失败')
    }
    const taskId = startRes.task_id

    // 2. 清除可能存在的旧计时器
    if (updatePollInterval.value) {
      clearInterval(updatePollInterval.value)
    }

    // 3. 轮询获取进度（每1秒一次）
    updatePollInterval.value = setInterval(async () => {
      try {
        const progressRes = await getUpdateProgress(taskId)
        
        if (progressRes.completed) {
          // 更新完成
          clearInterval(updatePollInterval.value)
          progressPercent.value = 100
          progressText.value = '更新完成！'
          await userStore.loadCourses()
          
          // 2秒后隐藏进度条
          setTimeout(() => {
            showProgress.value = false
          }, 2000)
        } else if (progressRes.failed) {
          // 更新失败
          clearInterval(updatePollInterval.value)
          progressText.value = `Updating Falied:${progressRes.error || 'Unknown'}`
          ElMessage.error(progressRes.error || '更新过程中发生错误')
          
          // 3秒后隐藏进度条
          setTimeout(() => {
            showProgress.value = false
          }, 3000)
        } else {
          // 更新中
          progressPercent.value = progressRes.percent || 0
          progressText.value = progressRes.status || `正在更新（${progressRes.percent || 0}%）`
        }
      } catch (e) {
        clearInterval(updatePollInterval.value)
        progressText.value = `查询进度失败：${e.message}`
        setTimeout(() => {
          showProgress.value = false
        }, 3000)
      }
    }, 1000)

  } catch (error) {
    console.error('更新课程失败', error)
    progressText.value = `启动失败：${error.message}`
    ElMessage.error(error.message || '网络异常，请重试')
    
    // 3秒后隐藏进度条
    setTimeout(() => {
      showProgress.value = false
    }, 3000)
  } finally {
    isUpdateLoading.value = false
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

.course-action-btn {
  padding: 0 15px 15px;
}
.update-course-btn {
  width: 100%;
  background-color: #0a4a1f;
  border-color: #0a4a1f;
  font-size: 14px;
  padding: 20px 10px;
}
.update-course-btn:hover {
  background-color: #073416;
  border-color: #073416;
}

.loading-icon {
  margin-right: 5px;
  animation: rotate 1.5s linear infinite;
}
@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.course-list {
  flex: 1;
  padding: 0 15px 15px;
  overflow-y: auto;
}

.course-tag {
  display: flex;
  align-items: center;
  width: 100%;
  margin-bottom: 8px;
  cursor: pointer;
  padding: 20px 12px;
  min-height: 60px;
  transition: all 0.3s;
  background-color: #6e9c721a;
  color: #333333;
  border: 1px solid #6e9c72;
}
.course-text {
  width: 100%;
  line-height: 1.5;
  white-space: normal;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  text-align: center;
}

.course-tag:hover {
  background-color: #6e9c7259;
  border-color: #6e9c72;
}

/* 选中课程的高亮样式 */
.course-tag.selected-course {
  background-color: #618e6585;
  color: white;
  border-color: #618e65;
}

.qa-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  height: calc(100vh - 70px);
  padding-bottom: 120px;
}

/* 回答区域样式 */
.answer-container {
  flex: 1;
  overflow: hidden;
  padding: 20px;
  background-color: #fff;
  height: calc(100% - 120px);
}

.chat-scroll {
  height: 99%;
  overflow-y: auto;
  padding-bottom: 20px;
  scroll-behavior: smooth;
}

.empty-answer {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-size: 20px;
}

.chat-messages {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-message {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 8px;
  line-height: 1.6;
}

.user-message {
  align-self: flex-end;
  background-color: #0a4a1f;
  color: #fff;
}

.ai-message {
  align-self: flex-start;
  background-color: #f5f7fa;
  border: 1px solid #eaecef;
}

.message-role {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-message .message-role {
  color: #fff;
}

.ai-message .message-role {
  color: #333;
}

.message-time {
  font-size: 12px;
  font-weight: normal;
  opacity: 0.7;
}

.message-content {
  font-size: 15px;
  white-space: pre-wrap;
}

.typing-dot {
  animation: blink 1s infinite;
  margin-left: 4px;
}
@keyframes blink {
  0%, 100% { opacity: 0; }
  50% { opacity: 1; }
}

.message-sources {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #eee;
}
.message-sources h4 {
  font-size: 14px;
  margin-bottom: 8px;
  color: #666;
}
.source-link {
  display: block;
  margin-bottom: 6px;
  color: #0a4a1f;
  font-size: 13px;
}

/* 提问区域样式 */
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
  box-sizing: border-box;
}

/* 课程引用标签样式 */
.reference-tags {
  margin-bottom: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.course-reference-tag {
  cursor: pointer;
}

.query-input {
  width: 100%;
  border-radius: 12px;
  border: 1px solid #ddd;
  padding: 12px 16px;
  background-color: #fff;
  resize: vertical;
  font-size: 15px;
}
.query-input:focus {
  border-color: #0a4a1f;
  box-shadow: 0 0 0 2px rgba(10, 74, 31, 0.1);
  outline: none;
}

.query-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 终止按钮样式 */
.stop-btn {
  color: #f56c6c;
}
.stop-btn:hover {
  color: #e34e4e;
  background-color: transparent;
}

.clear-btn {
  color: #666;
}
.clear-btn:hover {
  color: #0a4a1f;
  background-color: transparent;
}

.submit-btn {
  padding: 8px 20px;
  font-size: 14px;
  border-radius: 8px;
  background-color: #0a4a1f;
  border-color: #0a4a1f;
}
.submit-btn:hover {
  background-color: #073416;
  border-color: #073416;
}
.submit-btn:disabled {
  background-color: #9ca3af;
  border-color: #9ca3af;
  cursor: not-allowed;
}
.submit-btn:disabled:hover {
  background-color: #9ca3af;
  border-color: #9ca3af;
  cursor: not-allowed;
}

::v-deep .el-progress-bar__inner {
  transition: width 0.3s ease;
  background-color: #0a4a1f;
}
</style>