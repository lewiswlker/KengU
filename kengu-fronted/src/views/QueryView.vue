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
                
                <!-- RAG参考文本区域（优化版） -->
                <div v-if="msg.role === 'assistant' && msg.ragTexts && msg.ragTexts.length" class="rag-container">
                  <!-- 折叠/展开按钮 -->
                  <div 
                    class="rag-toggle" 
                    :class="{ 'expanded': isRagExpanded(index) }"
                    @click="toggleRagExpand(index)"
                  >
                    <span>
                      <el-icon class="thought-icon"><Search /></el-icon>
                      Reference texts ({{ msg.ragTexts.length }})
                    </span>
                    <el-icon class="rag-toggle-icon"><ArrowDown /></el-icon>
                  </div>
                  
                  <!-- 参考文本内容（展开时显示） -->
                  <div 
                    class="rag-content" 
                    v-show="isRagExpanded(index)"
                  >
                    <div class="rag-content-header">
                      <el-icon class="thought-icon"><Search /></el-icon>
                      Detailed reference texts
                    </div>
                    <div 
                      v-for="(text, idx) in msg.ragTexts" 
                      :key="idx" 
                      class="rag-item"
                      :data-index="idx + 1"
                    >
                      {{ text }}
                      <!-- 相关性分数标签 -->
                      <span v-if="msg.sources[idx]?.relevance" class="rag-relevance">
                        {{ (msg.sources[idx].relevance * 100).toFixed(0) }}% match
                      </span>
                    </div>
                  </div>
                </div>
                
                <!-- AI 回答内容 -->
                <div class="message-content" v-html="formatMessage(msg.content)"></div>
                
                <!-- 参考来源链接 -->
                <div v-if="msg.role === 'assistant' && msg.sources?.length" class="message-sources">
                  <h4>References:</h4>
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

        <!-- 右下角固定提问区域 -->
        <div class="fixed-input-container">
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
import { updateKnowledgeBase, getUpdateProgress } from '../services/api'
import { User, ArrowDown, Search, Document, Refresh, Loading } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'

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
const updatePollInterval = ref(null)

// 折叠状态管理（存储当前展开的面板索引）
const activeRagCollapse = ref('')

// 进度条相关状态
const showProgress = ref(false)
const progressPercent = ref(0)
const progressText = ref('Ready to update...')
const progressStatus = computed(() => {
  if (progressText.value.includes('Fail')) return 'exception'
  if (progressPercent.value === 100) return 'success'
  return 'active'
})

// DOM引用
const messageRefs = ref([])
const typingRef = ref(null)

// 判断指定索引的RAG面板是否展开
const isRagExpanded = (index) => {
  return activeRagCollapse.value === `rag-${index}`
}

// 切换RAG面板展开/折叠状态
const toggleRagExpand = (index) => {
  if (isRagExpanded(index)) {
    activeRagCollapse.value = ''  // 收起
  } else {
    activeRagCollapse.value = `rag-${index}`  // 展开
  }
}

// 滚动到最新消息
const scrollToLatest = async () => {
  await nextTick()
  if (isGenerating.value && typingRef.value) {
    typingRef.value.scrollIntoView({ behavior: 'smooth', block: 'end' })
  } else if (messageRefs.value.length > 0) {
    messageRefs.value[messageRefs.value.length - 1].scrollIntoView({ behavior: 'smooth', block: 'end' })
  }
}

// 课程引用相关方法
const addCourseReference = (course) => {
  const isAlreadySelected = selectedCourses.value.some(item => item.id === course.id)
  if (!isAlreadySelected) {
    selectedCourses.value.push(course)
  }
}

const removeCourseReference = (courseId) => {
  selectedCourses.value = selectedCourses.value.filter(course => course.id !== courseId)
}

const isCourseSelected = (courseId) => {
  return selectedCourses.value.some(course => course.id === courseId)
}

// 导航方法
const goToQuery = () => router.push('/query')
const goToDashboard = () => router.push('/dashboard')
const goToProfile = () => router.push('/profile')

// 页面初始化
onMounted(async () => {
  if (!userStore.email) {
    router.push('/')
    return
  }
  if (userStore.courses.length === 0) {
    await userStore.loadCourses()
  }
  handleUpdateAllCourses()
})

// 组件卸载清理
onUnmounted(() => {
  if (abortController.value) abortController.value.abort()
  if (updatePollInterval.value) clearInterval(updatePollInterval.value)
})

// 清空输入
const clearInput = () => {
  question.value = ''
  selectedCourses.value = []
}

// 格式化消息
const formatMessage = (content) => {
  return content.replace(/\n/g, '<br/>')
}

// 终止生成
const stopGeneration = () => {
  if (abortController.value) {
    abortController.value.abort()
    console.log('Answer manually terminated')
    
    let finalContent = currentAiContent.value
    const currentRagTexts = []
    if (window.currentRetrievalSources?.length) {
      currentRagTexts.push(...window.currentRetrievalSources.map(s => s.text))
    }
    
    if (finalContent.trim()) {
      chatHistory.value.push({
        role: 'assistant',
        content: finalContent,
        time: new Date().toLocaleString(),
        sources: window.currentRetrievalSources || [],
        ragTexts: currentRagTexts
      })
    }
    
    isGenerating.value = false
    currentAiContent.value = ''
    window.currentRetrievalSources = []
    scrollToLatest()
    ElMessage.info('Answer generation terminated')
  }
}

// 请求接口
const fetchAskQuestion = (user_request, user_id, email, messages) => {
  const backendURL = window.location.hostname.includes('natapp')
    ? 'http://kengu-api.natapp1.cc/api/chat/stream'
    : 'http://localhost:8009/api/chat/stream'
  
  return fetch(backendURL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream'
    },
    body: JSON.stringify({
      user_request,
      user_id: user_id ? Number(user_id) : null,
      user_email: email,
      messages,
      selected_course_ids: selectedCourses.value.map(c => c.id)
    }),
    signal: abortController.value?.signal
  })
}

// 提交问题
const submitQuestion = async () => {
  let finalQuestion = question.value.trim()
  if (selectedCourses.value.length > 0) {
    const courseNames = selectedCourses.value.map(c => c.name).join('、')
    finalQuestion = `[Courses: ${courseNames}] ${finalQuestion}`
  }

  if (!finalQuestion) return

  window.currentRetrievalSources = []

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
      throw new Error('The backend did not return a valid streaming response')
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
            
            if (chunk.startsWith('__SOURCES__:') && chunk.includes('__END_SOURCES__')) {
              const sourcesJson = chunk.replace('__SOURCES__:', '').replace('__END_SOURCES__', '')
              try {
                const sources = JSON.parse(sourcesJson)
                window.currentRetrievalSources = sources.map(s => ({
                  name: s.title || 'Unknown sources',
                  url: s.source_url || '#',
                  relevance: s.relevance_score || 0,
                  text: s.text || ''
                }))
              } catch (e) {
                console.error('Failed to parse source data:', e)
              }
            } else {
              currentAiContent.value += chunk
              await nextTick()
              scrollToLatest()
            }
          } catch (e) {
            console.error('Failed to parse streaming data:', e)
          }
        }
      }
      buffer = lines[lines.length - 1] || ''
    }

    isGenerating.value = false
    if (currentAiContent.value) {
      const ragTexts = window.currentRetrievalSources.map(s => s.text).filter(Boolean)
      
      chatHistory.value.push({
        role: 'assistant',
        content: currentAiContent.value,
        time: new Date().toLocaleString(),
        sources: window.currentRetrievalSources || [],
        ragTexts: ragTexts
      })
      
      currentAiContent.value = ''
      window.currentRetrievalSources = []
      await nextTick()
      scrollToLatest()
    }

  } catch (error) {
    isGenerating.value = false
    if (error.name !== 'AbortError') {
      console.error('Failed to submit the question', error)
      ElMessage.error('Query failed. Please try again!')
      chatHistory.value.pop()
    }
    window.currentRetrievalSources = []
  } finally {
    abortController.value = null
  }
}

// 退出登录
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
}

// 更新课程
const handleUpdateAllCourses = async () => {
  if (!userStore.email || !userStore.password) {
    ElMessage.warning('Please login first')
    router.push('/')
    return
  }

  if (isUpdateLoading.value) return

  showProgress.value = true
  progressPercent.value = 0
  progressText.value = 'Starting the update task...'
  isUpdateLoading.value = true

  try {
    const startRes = await updateKnowledgeBase(
      userStore.email, 
      userStore.password, 
      userStore.id
    )

    if (!startRes.success || !startRes.task_id) {
      throw new Error(startRes.error || 'Failed to start the update task')
    }
    const taskId = startRes.task_id

    if (updatePollInterval.value) clearInterval(updatePollInterval.value)

    updatePollInterval.value = setInterval(async () => {
      try {
        const progressRes = await getUpdateProgress(taskId)
        
        if (progressRes.completed) {
          clearInterval(updatePollInterval.value)
          progressPercent.value = 100
          progressText.value = 'Update completed!'
          await userStore.loadCourses()
          setTimeout(() => showProgress.value = false, 2000)
        } else if (progressRes.failed) {
          clearInterval(updatePollInterval.value)
          progressText.value = `Updating Falied:${progressRes.error || 'Unknown'}`
          ElMessage.error(progressRes.error || 'An error occurred during the update')
          setTimeout(() => showProgress.value = false, 3000)
        } else {
          progressPercent.value = progressRes.percent || 0
          progressText.value = progressRes.status || `Updating(${progressRes.percent || 0}%)`
        }
      } catch (e) {
        clearInterval(updatePollInterval.value)
        progressText.value = `Failed to query progress:${e.message}`
        setTimeout(() => showProgress.value = false, 3000)
      }
    }, 1000)

  } catch (error) {
    console.error('Failed to update', error)
    progressText.value = `Failed to start:${error.message}`
    ElMessage.error(error.message || 'Network error')
    setTimeout(() => showProgress.value = false, 3000)
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

::v-deep .message-sources .source-link a {
  text-decoration: none !important;
}

::v-deep .message-sources .source-link a:hover {
  text-decoration: none !important; 
}

::v-deep .source-link {
  display: block;
  margin-bottom: 6px;
  color: #0a4a1f;
  font-size: 13px;
  transition: all 0.2s ease;
  text-decoration: none !important;
}

::v-deep .source-link:hover {
  background-color: #0734161f;
  color: #073416;
  border-color: #073416;
  text-decoration: none !important;
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

/* RAG 相关样式优化 */
.rag-container {
  margin: 12px 0;
  border-radius: 6px;
  overflow: hidden;
  transition: all 0.2s ease;
}

/* 折叠/展开控制按钮 */
.rag-toggle {
  width: 100%;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #f5f7fa;
  border: 1px solid #eaecef;
  cursor: pointer;
  font-size: 13px;
  color: #0a4a1f;
  transition: background-color 0.2s;
}

.rag-toggle:hover {
  background-color: #eef2f5;
}

.rag-toggle-icon {
  transition: transform 0.3s ease;
  font-size: 14px;
}

/* 展开时旋转图标 */
.rag-toggle.expanded .rag-toggle-icon {
  transform: rotate(180deg);
}

/* 参考文本内容区 */
.rag-content {
  padding: 16px;
  background-color: #fff;
  border: 1px solid #eaecef;
  border-top: none;
  max-height: 400px;
  overflow-y: auto;
  transition: max-height 0.3s ease;
}

/* 内容区标题 */
.rag-content-header {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #eaecef;
  display: flex;
  align-items: center;
}

.rag-content-header .thought-icon {
  margin-right: 8px;
  color: #0a4a1f;
}

/* 单条参考文本样式 */
.rag-item {
  position: relative;
  padding: 10px 12px;
  margin-bottom: 10px;
  background-color: #fafafa;
  border-radius: 4px;
  border-left: 3px solid #0a4a1f;
  font-size: 14px;
  line-height: 1.6;
  color: #444;
  transition: transform 0.1s ease;
}

.rag-item:hover {
  transform: translateX(3px);
}

.rag-item:last-child {
  margin-bottom: 0;
}

/* 序号样式 */
.rag-item::before {
  content: attr(data-index);
  position: absolute;
  left: -8px;
  top: 10px;
  width: 16px;
  height: 16px;
  background-color: #0a4a1f;
  color: white;
  border-radius: 50%;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 相关性分数标签 */
.rag-relevance {
  display: inline-block;
  margin-left: 8px;
  padding: 1px 6px;
  background-color: rgba(10, 74, 31, 0.1);
  color: #0a4a1f;
  font-size: 11px;
  border-radius: 10px;
}

/* 弹窗样式 */
.el-message-box {
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  width: 400px;
}
.el-message-box__title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  padding: 20px 24px 12px;
}
.el-message-box__message {
  padding: 0 24px 16px;
  font-size: 14px;
  color: #666;
}
.el-message-box__btns {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 12px 24px;
}
.el-button--primary {
  background-color: #0a4a1f;
  border-color: #0a4a1f;
}
.el-button--primary:hover {
  background-color: #073416;
  border-color: #073416;
}
.el-button--default {
  color: #666;
  border-color: #ddd;
}
.el-button--default:hover {
  color: #333;
  border-color: #bbb;
  background-color: #f5f5f5;
}

::v-deep .el-dropdown-menu__item {
  color: #0a4a1f !important; /* 自定义默认颜色 */
  background-color: rgba(255, 255, 255, 0.05) !important;
}

/* 悬停状态：设置高亮颜色 */
::v-deep .el-dropdown-menu__item:hover {
  color: #0a4a1f !important; /* 自定义悬停颜色 */
  background-color: rgba(10, 74, 31, 0.05) !important;
}

/* 分割线样式 */
::v-deep .el-dropdown-menu__item.divided {
  border-top-color: #eee !important;
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