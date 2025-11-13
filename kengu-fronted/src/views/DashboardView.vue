<template>
  <div class="dashboard-page">
    <!-- 统一头部 -->
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
          style="color: #0a4a1f; font-weight: 600;"
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

    <!-- 主体内容 -->
    <div class="dashboard-main">
      <!-- 左侧日历区域 -->
      <div class="calendar-container">
        <h3 class="section-title">Calendar</h3>
        <el-card class="calendar-card">
          <!-- 自定义日历头部（含月份切换） -->
          <template #header="headerProps">
            <el-button-group size="small">
              <el-button @click="changeMonth('prev-month')">
                <el-icon><ArrowLeft /></el-icon>
              </el-button>
              <span class="month-title">{{ headerProps.date ? formatMonth(headerProps.date) : '' }}</span>
              <el-button @click="changeMonth('next-month')">
                <el-icon><ArrowRight /></el-icon>
              </el-button>
            </el-button-group>
          </template>

          <!-- 日历组件 -->
          <el-calendar v-model="currentDate">
            <template #date-cell="scope">
              <div class="calendar-cell" v-if="scope.date">
                <span :class="{ 
                  'current-day': isToday(scope.date), 
                  'event-day': hasEvent(scope.date) 
                }">
                  {{ scope.date.getDate() }}
                </span>
                <!-- 事件标记 -->
                <div v-if="hasEvent(scope.date)" class="event-dot"></div>
              </div>
            </template>
          </el-calendar>
        </el-card>
      </div>

      <!-- 中间 To Do List 区域 -->
      <div class="todo-container">
        <h3 class="section-title">To Do List</h3>
        <el-card class="todo-card">
          <div v-if="currentDate" class="todo-header">
            <h4>{{ formatDate(currentDate) }}</h4>
          </div>
          <div v-if="selectedDateEvents.length > 0" class="todo-list">
            <div v-for="(event, idx) in selectedDateEvents" :key="idx" class="todo-item">
              <el-checkbox v-model="event.completed" @change="updateTodoStatus(event)"></el-checkbox>
              <div class="todo-content">
                <div class="todo-name" :class="{ 'completed': event.completed }">{{ event.name }}</div>
                <div class="todo-desc">{{ event.description }}</div>
              </div>
            </div>
          </div>
          <div v-else class="no-todos">No tasks scheduled for this day</div>
        </el-card>
      </div>

      <!-- 右侧聊天助手区域（与Query页面完全一致） -->
      <div class="chat-container">
        <h3 class="section-title">KengU Assistant</h3>
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

          <!-- 固定提问区域（与Query页面完全一致） -->
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
              rows="2"
              placeholder="Please Enter your question..."
              class="query-input"
              @keydown.enter.prevent="submitQuestion"
              :disabled="isLoading || isGenerating"
            ></textarea>
            
            <div class="query-actions">
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
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { User, ArrowDown, Search, ArrowLeft, ArrowRight, Document} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const router = useRouter()

// 核心状态（与Query页面完全一致）
const question = ref('')
const isLoading = ref(false)
const isGenerating = ref(false)
const chatHistory = ref([])
const currentAiContent = ref('')
const abortController = ref(null)
const selectedCourses = ref([])  // 课程引用功能
const currentDate = ref(new Date())
const selectedDateEvents = ref([])

// DOM引用（与Query页面一致）
const messageRefs = ref([])
const typingRef = ref(null)

// 模拟日历事件数据
const eventsData = ref([
  {
    date: new Date(new Date().setDate(new Date().getDate() + 1)),
    name: 'COMP7103 Lecture',
    description: '14:30 - 16:00 | Room 201, Main Building',
    completed: false
  },
  {
    date: new Date(new Date().setDate(new Date().getDate() + 3)),
    name: 'Final Exam Review',
    description: '10:00 - 12:00 | Online Zoom',
    completed: false
  },
  {
    date: new Date(),
    name: 'Assignment Deadline',
    description: 'COMP7747 Assignment 2 Due Today',
    completed: false
  },
  {
    date: new Date(new Date().setDate(new Date().getDate() + 5)),
    name: 'Group Project Meeting',
    description: '15:00 - 17:00 | Library Study Room 3',
    completed: false
  }
])

// 滚动到最新消息（与Query页面一致）
const scrollToLatest = async () => {
  await nextTick()
  if (isGenerating.value && typingRef.value) {
    typingRef.value.scrollIntoView({ behavior: 'smooth', block: 'end' })
  } else if (messageRefs.value.length > 0) {
    messageRefs.value[messageRefs.value.length - 1].scrollIntoView({ behavior: 'smooth', block: 'end' })
  }
}

// 课程引用功能（与Query页面完全一致）
const removeCourseReference = (courseId) => {
  selectedCourses.value = selectedCourses.value.filter(course => course.id !== courseId)
}

// 导航方法
const goToQuery = () => router.push('/query')
const goToDashboard = () => router.push('/dashboard')
const goToProfile = () => router.push('/profile')

// 页面初始化
onMounted(() => {
  if (!userStore.email) router.push('/')
  // 加载课程（与Query页面一致）
  if (userStore.courses.length === 0) userStore.loadCourses()
  // 初始化日历
  if (!currentDate.value || !(currentDate.value instanceof Date) || isNaN(currentDate.value.getTime())) {
    currentDate.value = new Date()
  }
  selectedDateEvents.value = getSelectedDateEvents()
})

// 组件卸载时中断请求（与Query页面一致）
onUnmounted(() => {
  if (abortController.value) {
    abortController.value.abort()
  }
})

// 清空输入框（与Query页面一致）
const clearInput = () => {
  question.value = ''
  selectedCourses.value = []
}

// 格式化消息（与Query页面一致）
const formatMessage = (content) => {
  return content.replace(/\n/g, '<br/>')
}

// 终止生成（与Query页面一致）
const stopGeneration = () => {
  if (abortController.value) {
    abortController.value.abort()
    console.log('已终止回答')
    
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

// 请求方法（与Query页面完全一致）
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

// 提交问题（与Query页面完全一致）
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

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    if (!response.body || typeof response.body.getReader !== 'function') {
      throw new Error('无效的流式响应')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let t = true

    while (t) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ') && line.trim() !== 'data: ') {
          try {
            const { chunk } = JSON.parse(line.slice(6))
            currentAiContent.value += chunk
            await nextTick()
            scrollToLatest()
          } catch (e) {
            console.error('解析错误:', e)
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
      scrollToLatest()
    }

  } catch (error) {
    isGenerating.value = false
    if (error.name !== 'AbortError') {
      console.error('提问失败:', error)
      ElMessage.error('查询失败，请重试')
      chatHistory.value.pop()
    }
  } finally {
    abortController.value = null
  }
}

// 退出登录（与Query页面一致）
const handleLogout = () => {
  if (confirm('确定要退出登录吗？')) {
    if (abortController.value) abortController.value.abort()
    userStore.logout()
    router.push('/')
  }
}

// 日历相关方法
const changeMonth = (type) => {
  let newDate
  if (currentDate.value && currentDate.value instanceof Date && !isNaN(currentDate.value.getTime())) {
    newDate = new Date(currentDate.value)
  } else {
    newDate = new Date()
  }

  if (type === 'prev-month') {
    newDate.setMonth(newDate.getMonth() - 1)
  } else if (type === 'next-month') {
    newDate.setMonth(newDate.getMonth() + 1)
  }
  currentDate.value = newDate
}

const formatMonth = (date) => {
  if (!date || !(date instanceof Date) || isNaN(date.getTime())) return ''
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long' })
}

const formatDate = (date) => {
  if (!date || !(date instanceof Date) || isNaN(date.getTime())) return ''
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
  })
}

const isToday = (date) => {
  if (!date || !(date instanceof Date) || isNaN(date.getTime())) return false
  const today = new Date()
  return date.getDate() === today.getDate() &&
         date.getMonth() === today.getMonth() &&
         date.getFullYear() === today.getFullYear()
}

const hasEvent = (date) => {
  if (!date || !(date instanceof Date) || isNaN(date.getTime())) return false
  return eventsData.value.some(event => 
    event.date.getDate() === date.getDate() &&
    event.date.getMonth() === date.getMonth() &&
    event.date.getFullYear() === date.getFullYear()
  )
}

const getSelectedDateEvents = () => {
  if (!currentDate.value || !(currentDate.value instanceof Date) || isNaN(currentDate.value.getTime())) {
    return []
  }
  return eventsData.value.filter(event => 
    event.date.getDate() === currentDate.value.getDate() &&
    event.date.getMonth() === currentDate.value.getMonth() &&
    event.date.getFullYear() === currentDate.value.getFullYear()
  )
}

watch(currentDate, () => {
  selectedDateEvents.value = getSelectedDateEvents()
}, { deep: true })

const updateTodoStatus = (event) => {
  const targetEvent = eventsData.value.find(item => 
    item.name === event.name && item.description === event.description
  )
  if (targetEvent) targetEvent.completed = event.completed
}
</script>

<style scoped>
/* 基础样式 */
.dashboard-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* 头部样式 */
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

.header-left { display: flex; align-items: center; }
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

.header-right { display: flex; align-items: center; }
.user-info { display: flex; align-items: center; cursor: pointer; }
.user-icon { margin-right: 8px; font-size: 18px; }
.user-name { font-size: 14px; margin-right: 5px; }
.dropdown-icon { font-size: 16px; }

/* 主体容器 */
.dashboard-main {
  display: flex;
  gap: 20px;
  flex: 1;
  padding: 20px;
  box-sizing: border-box;
  overflow: hidden;
}

/* 左侧日历样式 */
.calendar-container {
  width: 33%;
  min-width: 350px;
  display: flex;
  flex-direction: column;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 15px 0;
  color: #333;
  padding-bottom: 10px;
  border-bottom: 2px solid #0a4a1f;
}

.calendar-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0;
  box-sizing: border-box;
  overflow: hidden;
  border: 1px solid #ddd;
  border-radius: 4px;
}

/* 日历头部 */
:deep(.el-calendar__header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #eee;
}
.month-title { font-size: 16px; font-weight: 600; color: #333; }

/* 日历单元格 */
:deep(.el-calendar-table td) { height: 60px; vertical-align: top; }
.calendar-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  height: 100%;
  padding-top: 8px;
}
.current-day {
  background-color: #0a4a1f;
  color: white;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
}
.event-dot {
  width: 6px;
  height: 6px;
  background-color: #e34e4e;
  border-radius: 50%;
  margin-top: 4px;
}

/* 中间To Do List */
.todo-container {
  width: 33%;
  min-width: 300px;
  display: flex;
  flex-direction: column;
}
.todo-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  box-sizing: border-box;
  overflow: hidden;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.todo-header { margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
.todo-list { max-height: calc(100% - 80px); overflow-y: auto; }
.todo-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
}
.todo-item:last-child { border-bottom: none; }
.todo-name { font-weight: 500; font-size: 14px; margin-bottom: 3px; }
.todo-desc { font-size: 13px; color: #666; }
.completed { text-decoration: line-through; color: #999; }
.no-todos {
  color: #666;
  text-align: center;
  padding: 20px 0;
  font-size: 14px;
}

/* 右侧聊天区域（与Query页面完全一致） */
.chat-container {
  width: 30%;
  min-width: 300px;
  display: flex;
  flex-direction: column;
}

.qa-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  height: 100%;
}

/* 回答区域 */
.answer-container {
  flex: 1;
  overflow: hidden;
  padding: 20px;
  background-color: #fff;
  height: calc(100% - 120px);
}
.chat-scroll {
  height: 95%;
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
.chat-messages { display: flex; flex-direction: column; gap: 16px; }
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
.user-message .message-role { color: #fff; }
.ai-message .message-role { color: #333; }
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
@keyframes blink { 0%,100%{opacity:0}50%{opacity:1} }

/* 参考来源 */
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

/* 提问区域（与Query页面完全一致） */
.fixed-input-container {
  position: sticky;
  bottom: 0;
  background-color: #fff;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
  z-index: 10;
  padding: 15px 20px;
  border-top: 1px solid #eaecef;
  box-sizing: border-box;
}

.reference-tags {
  margin-bottom: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.course-reference-tag { cursor: pointer; }

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
.stop-btn { color: #f56c6c; }
.stop-btn:hover { color: #e34e4e; background-color: transparent; }
.clear-btn { color: #666; }
.clear-btn:hover { color: #0a4a1f; background-color: transparent; }
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

/* 响应式调整 */
@media (max-width: 1200px) {
  .dashboard-main { flex-wrap: wrap; }
  .calendar-container, .todo-container, .chat-container {
    width: 100%;
    margin-bottom: 20px;
  }
}
</style>