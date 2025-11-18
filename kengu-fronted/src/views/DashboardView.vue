<template>
  <div class="dashboard-page">
    <el-progress
      v-if="isUpdating"
      :percentage="updateProgress"
      :status="updateStatus"
      stroke-width="4"
      style="position: fixed; top: 60px; left: 0; right: 0; z-index: 100; background: white; padding: 5px 20px;"
    >
      <template #default>
        <span style="margin-right: 15px; font-size: 14px; font-weight: 500;">Updating assignments:</span>
        <span style="margin-left: 10px; font-size: 14px;">{{ updateMessage }}</span>
      </template>
    </el-progress>

    <!-- 头部区域 -->
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
        <el-button 
            size="small" 
            type="primary" 
            icon="Refresh" 
            @click="loadAllAssignments"
            :loading="isLoading || isUpdating"
            style="margin-bottom: 8px;"
          >
            Update Assignments
          </el-button>
        <el-card class="calendar-card">
          <!-- 日历头部 -->
          <div class="calendar-header">
            <el-button 
              size="small" 
              icon="ArrowLeft" 
              @click="changeMonth('prev')"
              class="month-nav-btn"
            />
            <div class="title-group">
              <h4 class="month-title">{{ formatMonthYear(currentYear, currentMonth) }}</h4>
              <el-button 
                type="primary" 
                size="small" 
                icon="Refresh" 
                @click="goToToday"
                class="today-btn"
                title="Back to today"
              />
            </div>
            <el-button 
              size="small" 
              icon="ArrowRight" 
              @click="changeMonth('next')"
              class="month-nav-btn"
            />
          </div>

          <!-- 日历表格 - 42天布局 -->
          <div class="calendar-table">
            <div class="calendar-week">
              <div v-for="weekday in weekdays" :key="weekday" class="calendar-weekday">
                {{ weekday }}
              </div>
            </div>
            <div class="calendar-days">
              <div 
                v-for="(date, index) in calendarDays" 
                :key="index"
                :class="[
                  'calendar-day',
                  { 'current-day': isCurrentDay(date) },
                  { 'event-day': hasEvent(date) },
                  { 'other-month': !isSameMonth(date) },
                  { 'selected-day': isSelectedDay(date) }
                ]"
                @click="handleDateClick(date)"
              >
                <div class="day-number">{{ date.getDate() }}</div>
                <div class="day-events" v-if="hasEvent(date)">
                  <div 
                    v-for="(event, idx) in getDayEvents(date)" 
                    :key="idx"
                    class="event-item"
                  >
                    <span class="event-icon">●</span>
                    {{ truncateText(event.name, 12) }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 中间待办列表 -->
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
                <div class="todo-desc" v-html="event.description"></div>
              </div>
            </div>
          </div>
          <div v-else class="no-todos">No tasks scheduled for this day</div>
        </el-card>
      </div>

      <!-- 右侧聊天区域 -->
      <div class="chat-container">
        <h3 class="section-title">KengU Assistant</h3>
        <div class="qa-container">
          <div class="answer-container">
            <el-scrollbar class="chat-scroll">
              <div v-if="chatHistory.length === 0" class="empty-answer">
                <p>Welcome to KengU. How can I help you?</p>
              </div>
              
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
                  
                  <!-- RAG参考文本区域 -->
                  <div v-if="msg.role === 'assistant' && msg.ragTexts && msg.ragTexts.length" class="rag-container">
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
                        <span v-if="msg.sources[idx]?.relevance" class="rag-relevance">
                          {{ (msg.sources[idx].relevance * 100).toFixed(0) }}% match
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div class="message-content" v-html="formatMessage(msg.content)"></div>
                  
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
                
                <div v-if="isGenerating" class="chat-message ai-message generating" ref="typingRef">
                  <div class="message-role">
                    KengU Assistant
                    <span class="message-time">{{ new Date().toLocaleString() }}</span>
                  </div>
                  <div class="message-content-wrapper">
                    <div
                      class="message-content"
                      v-html="formatMessage(currentAiContent)"
                    ></div>
                    <span class="typing-dot">●</span>
                  </div>
                </div>
              </div>
            </el-scrollbar>
          </div>

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
              rows="2"
              placeholder="Please Enter your question..."
              class="query-input"
              @keydown.enter.prevent="submitQuestion"
              :disabled="isLoading || isGenerating || isUpdating"
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
                :loading="isLoading || isGenerating || isUpdating"
                :disabled="(!question.trim() && selectedCourses.length === 0) || isGenerating || isUpdating"
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
import { ref, watch, nextTick, onMounted, onUnmounted, computed, onDeactivated } from 'vue';
import { useRouter } from 'vue-router';
import { marked } from 'marked';   // Markdown 解析库
import DOMPurify from 'dompurify'; // HTML 安全过滤库
import { useUserStore } from '../stores/user';
import { User, ArrowDown, Search, Document } from '@element-plus/icons-vue';
import { ElMessage, ElLoading, ElMessageBox, ElProgress } from 'element-plus';
import { 
  get_assignments_by_date_range, 
  getCourses,
  mark_assignment_complete,
  mark_assignment_pending,
  getUpdateProgress
} from '../services/api';

// 状态管理与路由
const userStore = useUserStore();
const router = useRouter();

// 核心状态
const question = ref('');
const isLoading = ref(false);
const isGenerating = ref(false);
const chatHistory = ref([]);
const currentAiContent = ref('');
const abortController = ref(null);
const selectedCourses = ref([]);
const currentDate = ref(new Date());
const selectedDateEvents = ref([]);
const eventsData = ref([]);
const currentYear = ref(new Date().getFullYear());
const currentMonth = ref(new Date().getMonth());
const typingRef = ref(null);
const messageRefs = ref([]);

// 进度跟踪相关状态 - 与query页面风格统一
const isUpdating = ref(false);
const updateProgress = ref(0);
const updateMessage = ref('Initializing update...');
const updateStatus = computed(() => {
  if (updateMessage.value.includes('Failed')) return 'exception';
  if (updateProgress.value === 100) return 'success';
  return 'active';
});
let progressPollTimer = null;

// RAG折叠状态管理
const activeRagCollapse = ref('');

// 日历配置 - 星期表头
const weekdays = ['Sun', 'Mon', 'Tue', 'Wen', 'Thu', 'Fri', 'Sat'];

const formatMonthYear = (year, month) => {
  // 月份英文名称数组（0 = 1月，11 = 12月）
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  return `${monthNames[month]} ${year}`;
};
// 计算42天日历
const calendarDays = computed(() => {
  const days = [];
  const firstDay = new Date(currentYear.value, currentMonth.value, 1);
  const firstDayWeekday = firstDay.getDay();
  
  for (let i = firstDayWeekday; i > 0; i--) {
    const date = new Date(currentYear.value, currentMonth.value, -i + 1);
    days.push(date);
  }
  
  const lastDay = new Date(currentYear.value, currentMonth.value + 1, 0);
  const totalDays = lastDay.getDate();
  for (let i = 1; i <= totalDays; i++) {
    const date = new Date(currentYear.value, currentMonth.value, i);
    days.push(date);
  }
  
  const remaining = 42 - days.length;
  for (let i = 1; i <= remaining; i++) {
    const date = new Date(currentYear.value, currentMonth.value + 1, i);
    days.push(date);
  }
  
  return days;
});

// RAG相关方法
const isRagExpanded = (index) => {
  return activeRagCollapse.value === `rag-${index}`;
};

const toggleRagExpand = (index) => {
  if (isRagExpanded(index)) {
    activeRagCollapse.value = '';
  } else {
    activeRagCollapse.value = `rag-${index}`;
  }
};

// URL去重工具函数
const deduplicateSources = (sources) => {
  const uniqueSources = [];
  const urlSet = new Set();
  
  for (const s of sources) {
    if (!s.url) continue;
    
    const normalizedUrl = s.url.replace(/\/$/, '');
    if (!urlSet.has(normalizedUrl)) {
      urlSet.add(normalizedUrl);
      uniqueSources.push(s);
    }
  }
  
  return uniqueSources;
};

// 工具函数：检查日期有效性
const isValidDate = (date) => {
  return date && date instanceof Date && !isNaN(date.getTime());
};

// 滚动到最新消息
const scrollToLatest = async () => {
  await nextTick();
  if (isGenerating.value && typingRef.value) {
    typingRef.value.scrollIntoView({ behavior: 'smooth', block: 'end' });
  } else if (messageRefs.value.length > 0) {
    messageRefs.value[messageRefs.value.length - 1].scrollIntoView({ behavior: 'smooth', block: 'end' });
  }
};

// 课程引用功能
const removeCourseReference = (courseId) => {
  selectedCourses.value = selectedCourses.value.filter(course => course.id !== courseId);
};

// 导航方法
const goToQuery = () => router.push('/query');
const goToDashboard = () => router.push('/dashboard');
const goToProfile = () => router.push('/profile');

// 回到今日
const goToToday = () => {
  const today = new Date();
  currentYear.value = today.getFullYear();
  currentMonth.value = today.getMonth();
  currentDate.value = today;
  loadAllAssignments();
  ElMessage.success('Back to today');
};

// 查询更新进度 - 与query页面风格统一
const checkUpdateProgress = async () => {
  const taskId = userStore.eventTaskId;
  if (!taskId) {
    console.log('No task ID found, stopping progress check');
    stopProgressPolling();
    return;
  }

  try {
    console.log('Checking update status for task:', taskId);
    const response = await getUpdateProgress(taskId);
    
    if (!response) {
      throw new Error('Invalid response from server');
    }

    if (response.success) {
      const percent = response.percent;
      const message = response.message;
      const completed = response.completed;
      const failed = response.failed;
      const error = response.error;
      
      // 强制更新进度状态
      updateProgress.value = Math.min(100, Math.max(0, percent || 0));
      updateMessage.value = message || 'Updating data...';
      isUpdating.value = true;

      console.log(`Update progress: ${updateProgress.value}% - ${updateMessage.value}`);

      // 处理完成状态
      if (completed) {
        updateStatus.value; // 触发计算属性更新
        ElMessage.success('Data update completed! Refreshing tasks...');
        stopProgressPolling();
        await loadAllAssignments();
        setTimeout(() => {
          isUpdating.value = false;
          updateProgress.value = 0;
          userStore.setEventTaskId(null);
        }, 2000);
      }

      // 处理失败状态
      if (failed) {
        updateMessage.value = `Updating Failed: ${error || 'Unknown error'}`;
        updateStatus.value; // 触发计算属性更新
        ElMessage.error(updateMessage.value);
        stopProgressPolling();
        setTimeout(() => {
          isUpdating.value = false;
          updateProgress.value = 0;
        }, 3000);
      }
    } else {
      updateMessage.value = response.message || 'Update in progress...';
      isUpdating.value = true;
    }
  } catch (error) {
    console.error('Error checking update status:', error);
    updateMessage.value = `Failed to query progress: ${error.message}`;
    isUpdating.value = true;
    
    // 仅在有任务ID时重试
    if (taskId) {
      setTimeout(checkUpdateProgress, 2000);
    } else {
      stopProgressPolling();
    }
  }
};

// 启动进度轮询
const startProgressPolling = () => {
  if (progressPollTimer) {
    clearInterval(progressPollTimer);
  }
  
  if (userStore.eventTaskId) {
    console.log('Starting progress polling for task:', userStore.eventTaskId);
    checkUpdateProgress();
    progressPollTimer = setInterval(checkUpdateProgress, 1000);
  } else {
    console.log('No event task ID, cannot start polling');
  }
};

// 停止进度轮询
const stopProgressPolling = () => {
  if (progressPollTimer) {
    clearInterval(progressPollTimer);
    progressPollTimer = null;
    console.log('Progress polling stopped');
  }
};

// 获取作业数据
const fetchAssignmentsByDateRange = async (startDate, endDate) => {
  const loading = ElLoading.service({
    lock: false,
    text: 'Loading assignments...',
    background: 'rgba(255, 255, 255, 0.7)'
  });

  try {
    const result = await get_assignments_by_date_range(startDate, endDate, userStore.id);
    loading.close();
    return result.success ? result.data : [];
  } catch (error) {
    loading.close();
    console.error('获取作业数据出错:', error);
    ElMessage.error('Network error');
    return [];
  }
};

// 标记作业完成
const markAssignmentComplete = async (assignmentId) => {
  try {
    return await mark_assignment_complete(assignmentId);
  } catch (error) {
    console.error('更新作业状态出错:', error);
    return { success: false, error: 'Network error' };
  }
};

// 标记作业为待处理状态
const markAssignmentPending = async (assignmentId) => {
  try {
    return await mark_assignment_pending(assignmentId);
  } catch (error) {
    console.error('更新作业为待处理状态出错:', error);
    return { success: false, error: 'Network error' };
  }
};

// 初始化加载作业和启动进度轮询
onMounted(async () => {
  console.log('Dashboard mounted, checking user status');
  if (!userStore.email) {
    router.push('/');
    return;
  }
  
  await loadAllAssignments();
  
  // 确保任务ID存在时才启动轮询
  console.log('User event task ID:', userStore.eventTaskId);
  if (userStore.eventTaskId) {
    startProgressPolling();
  } else {
    console.log('No event task ID found on mount');
  }
});

// 组件清理
onUnmounted(cleanup);
onDeactivated(cleanup);

function cleanup() {
  stopProgressPolling();
  if (abortController.value) {
    abortController.value.abort();
  }
}

const getCourseName = async (courseId) => {
  try {
    const courseIdNum = Number(courseId);
    const courseResult = await getCourses(courseIdNum);
    return `${courseResult?.data || 'Unknown'}`;
  } catch (error) {
    console.error('获取课程失败：', error);
    return 'Course: Unknown (获取失败)';
  }
};

// 加载作业
const loadAllAssignments = async () => {
  const startDate = new Date(calendarDays.value[0]);
  startDate.setHours(0, 0, 0, 0);
  const endDate = new Date(calendarDays.value[41]);
  endDate.setHours(23, 59, 59, 999);
  
  const startDateStr = startDate.toISOString().split('T')[0];
  const endDateStr = endDate.toISOString().split('T')[0];
  
  const assignments = await fetchAssignmentsByDateRange(startDateStr, endDateStr);
  
  const processedAssignments = await Promise.all(
  assignments.map(async (assignment) => {
    const courseName = await getCourseName(assignment.course_id);
    return { ...assignment, courseName };
  })
);
  
  eventsData.value = processedAssignments.map(assignment => ({
    date: new Date(assignment.due_date),
    name: assignment.title,
    description: `Course: ${assignment.courseName || 'Unknown'}\n Description: ${assignment.description || 'N/A'}\n Attachment: ${assignment.attachment_path ? `<a href="${assignment.attachment_path}" target="_blank">${assignment.attachment_path}</a>` : 'N/A'}`,
    completed: assignment.status === 'completed',
    assignmentId: assignment.id
  })).filter(item => isValidDate(item.date));

  selectedDateEvents.value = getSelectedDateEvents();
};

// 聊天相关方法
const clearInput = () => {
  question.value = '';
  selectedCourses.value = [];
};

const formatMessage = (content) => {
  if (!content) return '';
  try {
    // 1. 用 marked 将 Markdown 解析为原始 HTML
    const rawHtml = marked.parse(content);
    // 2. 用 DOMPurify 过滤危险 HTML（防止 XSS 攻击）
    return DOMPurify.sanitize(rawHtml);
  } catch (e) {
    // 异常 fallback：仅替换换行符为 <br>
    return content.replace(/\n/g, '<br/>');
  }
};

const stopGeneration = () => {
  if (abortController.value) {
    abortController.value.abort();
    
    let finalContent = currentAiContent.value;
    const currentRagTexts = [];
    
    const uniqueSources = window.currentRetrievalSources ? deduplicateSources(window.currentRetrievalSources) : [];
    currentRagTexts.push(...uniqueSources.map(s => s.text).filter(Boolean));
    
    if (finalContent.trim()) {
      chatHistory.value.push({
        role: 'assistant',
        content: finalContent,
        time: new Date().toLocaleString(),
        sources: uniqueSources,
        ragTexts: currentRagTexts
      });
    }
    
    isGenerating.value = false;
    currentAiContent.value = '';
    window.currentRetrievalSources = [];
    scrollToLatest();
    ElMessage.info('Answer generation terminated');
  }
};

const fetchAskQuestion = (user_request, user_id, email, messages) => {
  const backendURL = window.location.hostname.includes('natapp')
    ? 'http://kengu-api.natapp1.cc/api/chat/stream'
    : 'http://localhost:8009/api/chat/stream'
  
  return fetch(backendURL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
    body: JSON.stringify({ 
      user_request, 
      user_id: user_id ? Number(user_id) : null, 
      user_email: email, 
      messages,
      selected_course_ids: selectedCourses.value.map(c => c.id)
    }),
    signal: abortController.value?.signal
  });
};

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
                
                const newSources = sources.map(s => ({
                  name: s.title || 'Unknown sources',
                  url: s.source_url || '#',
                  relevance: s.relevance_score || 0,
                  text: s.text || ''
                }))
                
                const mergedSources = [...(window.currentRetrievalSources || []), ...newSources]
                window.currentRetrievalSources = deduplicateSources(mergedSources)
                
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
      const uniqueSources = window.currentRetrievalSources ? deduplicateSources(window.currentRetrievalSources) : []
      const ragTexts = uniqueSources.map(s => s.text).filter(Boolean)
      
      chatHistory.value.push({
        role: 'assistant',
        content: currentAiContent.value,
        time: new Date().toLocaleString(),
        sources: uniqueSources,
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
};

// 切换月份
const changeMonth = (type) => {
  if (type === 'prev') {
    currentMonth.value--;
    if (currentMonth.value < 0) {
      currentMonth.value = 11;
      currentYear.value--;
    }
  } else {
    currentMonth.value++;
    if (currentMonth.value > 11) {
      currentMonth.value = 0;
      currentYear.value++;
    }
  }
  loadAllAssignments();
};

// 日期格式化
const formatDate = (date) => {
  return isValidDate(date) ? date.toLocaleDateString('en-US', { 
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
  }) : '';
};

// 日期字符串生成
const getLocalDateStr = (date) => {
  if (!isValidDate(date)) return '';
  const d = new Date(date);
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, '0'),
    String(d.getDate()).padStart(2, '0')
  ].join('-');
};

// 判断日期是否有事件
const hasEvent = (date) => {
  if (!isValidDate(date)) return false;
  const targetStr = getLocalDateStr(date);
  return eventsData.value.some(event => getLocalDateStr(event.date) === targetStr);
};

// 获取指定日期的事件
const getDayEvents = (date) => {
  if (!isValidDate(date)) return [];
  const targetStr = getLocalDateStr(date);
  return eventsData.value.filter(event => getLocalDateStr(event.date) === targetStr);
};

// 判断是否为当天
const isCurrentDay = (date) => {
  if (!isValidDate(date)) return false;
  const today = new Date();
  return (
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate()
  );
};

// 判断是否为当月
const isSameMonth = (date) => {
  if (!isValidDate(date)) return false;
  return (
    date.getFullYear() === currentYear.value &&
    date.getMonth() === currentMonth.value
  );
};

// 判断是否为选中日期
const isSelectedDay = (date) => {
  if (!isValidDate(date) || !isValidDate(currentDate.value)) return false;
  return (
    date.getFullYear() === currentDate.value.getFullYear() &&
    date.getMonth() === currentDate.value.getMonth() &&
    date.getDate() === currentDate.value.getDate()
  );
};

// 文本截断
const truncateText = (text, length) => {
  return text.length > length ? text.substring(0, length) + '...' : text;
};

// 获取选中日期的事件
const getSelectedDateEvents = () => {
  return isValidDate(currentDate.value) 
    ? getDayEvents(currentDate.value) 
    : [];
};

// 监听日期变化更新待办列表
watch(currentDate, () => {
  selectedDateEvents.value = getSelectedDateEvents();
}, { deep: true });

// 日期点击事件
const handleDateClick = (date) => {
  if (!isSameMonth(date)) {
    currentYear.value = date.getFullYear();
    currentMonth.value = date.getMonth();
    loadAllAssignments();
  }
  currentDate.value = new Date(date);
};

// 更新作业状态
const updateTodoStatus = async (event) => {
  const targetEvent = eventsData.value.find(item => item.assignmentId === event.assignmentId);
  if (targetEvent) targetEvent.completed = event.completed;

  if (event.assignmentId) {
    const result = event.completed 
      ? await markAssignmentComplete(event.assignmentId)
      : await markAssignmentPending(event.assignmentId);

    if (!result.success) {
      if (targetEvent) targetEvent.completed = !event.completed;
      ElMessage.error(result.error || 'Failed to update');
    } else {
      ElMessage.success(event.completed ? 'Marked as completed' : 'Restored to pending');
    }
  }
};
</script>

<style scoped>
/* 基础样式 */
.dashboard-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
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
.kengu-btn {
  font-size: 20px;
  font-weight: bold;
  color: #0a4a1f !important;
  padding: 0 !important;
}

.kengu-logo {
  width: 40px;
  height: 40px;
  object-fit: contain;
  border-radius: 4px;
}

.kengu-btn:hover .kengu-logo {
  opacity: 0.9;
}

.header-nav {
  flex: 1;
  margin-left: 40px;
}
.dashboard-btn { font-size: 17px !important; }

.header-right { display: flex; align-items: center; }
.user-info { display: flex; align-items: center; cursor: pointer; }
.user-icon { margin-right: 8px; font-size: 18px; }
.user-name { font-size: 14px; margin-right: 5px; }

/* 主体容器 */
.dashboard-main {
  display: flex;
  gap: 20px;
  flex: 1;
  padding: 20px;
  box-sizing: border-box;
  overflow: hidden;
  /* 为顶部进度条留出空间 */
  margin-top: 0;
  padding-top: 10px;
}

/* 日历样式 */
.calendar-container {
  width: 60%;
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
  overflow: hidden;
}

/* 日历头部 */
.calendar-header {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #eee;
  background-color: #fff;
}

.month-nav-btn {
  color: #42b983;
  border: none;
  background: transparent;
  margin-right: 15px;
}

.month-nav-btn:hover {
  color: #31a266;
}

.title-group {
  display: flex;
  align-items: center;
  flex-grow: 1;
  justify-content: center;
}

.month-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #333;
}

.today-btn {
  margin-left: 10px;
}

/* 日历表格 */
.calendar-table {
  width: 100%;
  border-collapse: collapse;
}

.calendar-week {
  display: flex;
  background-color: #f8f9fa;
}

.calendar-weekday {
  width: 14.28%;
  padding: 10px;
  text-align: center;
  font-weight: 600;
  color: #495057;
}

.calendar-days {
  display: flex;
  flex-wrap: wrap;
}

.calendar-day {
  width: 14.28%;
  padding: 10px;
  border: 1px solid #eee;
  box-sizing: border-box;
  min-height: 80px;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s;
}

.calendar-day:hover {
  background-color: #f1f3f5;
}

.calendar-day.selected-day {
  background-color: rgba(10, 74, 31, 0.1);
  border: 2px solid #0a4a1f;
}

.calendar-day.other-month {
  color: #ccc;
  background-color: #f9f9f9;
}

.calendar-day.current-day .day-number {
  background-color: #0a4a1f;
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.day-number {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 5px;
}

.day-events {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
}

.event-item {
  display: flex;
  align-items: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.event-icon {
  color: #dc3545;
  margin-right: 3px;
  font-size: 10px;
}

/* 待办列表样式 */
.todo-container {
  width: 33%;
  min-width: 300px;
  display: flex;
  flex-direction: column;
}
.todo-card {
  flex: 1;
  padding: 20px;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 180px);
  min-height: 400px;
  box-sizing: border-box;
}
.todo-header { margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
.todo-list { 
  flex: 1; 
  overflow-y: auto; 
  padding-right: 8px;
  max-height: calc(100vh - 250px);
}

.todo-list::-webkit-scrollbar {
  width: 6px;
}
.todo-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}
.todo-list::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}
.todo-list::-webkit-scrollbar-thumb:hover {
  background: #aaa;
}

.todo-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
}
.todo-name { font-weight: 500; font-size: 15px; margin-bottom: 3px; }
.todo-desc { font-size: 11px; color: #666; white-space: pre-line; }
::v-deep .todo-desc a {color: #0a4a1f;text-decoration: underline;}
::v-deep .todo-desc a:hover {color: #073416; /* hover 时加深颜色 */text-decoration: none;}
.completed { text-decoration: line-through; color: #999; }
.no-todos {
  color: #666;
  text-align: center;
  padding: 20px 0;
  font-size: 14px;
}

/* 聊天区域样式 */
.chat-container {
  width: 30%;
  min-width: 300px;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px); 
}

.qa-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #eaecef;
  border-radius: 8px;
}

.answer-container {
  flex: 1;
  overflow: hidden;
  padding: 20px;
  background-color: #fff;
  height: calc(100% - 120px);
  max-height: calc(100% - 100px); 
  box-sizing: border-box;
}
.chat-scroll {
  height: 99%;
  overflow-y: auto;
  padding-bottom: 20px;
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
}
.message-time {
  font-size: 12px;
  font-weight: normal;
  opacity: 0.7;
}
.message-content { font-size: 15px; white-space: pre-wrap; }
.typing-dot {
  animation: blink 1s infinite;
  margin-left: 4px;
}
@keyframes blink { 0%,100%{opacity:0}50%{opacity:1} }

.message-sources {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #eee;
}
.source-link {
  display: block;
  margin-bottom: 6px;
  color: #0a4a1f;
  font-size: 13px;
}

.fixed-input-container {
  position: sticky;
  bottom: 0;
  background-color: #fff;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
  padding: 15px 20px;
  border-top: 1px solid #eaecef;
}

.reference-tags {
  margin-bottom: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.query-input {
  width: 100%;
  border-radius: 12px;
  border: 1px solid #ddd;
  padding: 12px 16px;
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
.stop-btn { color: #f56c6c !important; }
.clear-btn { color: #666 !important; }
.submit-btn {
  background-color: #0a4a1f !important;
  border-color: #0a4a1f !important;
}

/* RAG 相关样式 */
.rag-container {
  margin: 12px 0;
  border-radius: 6px;
  overflow: hidden;
  transition: all 0.2s ease;
}

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

.rag-toggle.expanded .rag-toggle-icon {
  transform: rotate(180deg);
}

.rag-content {
  padding: 16px;
  background-color: #fff;
  border: 1px solid #eaecef;
  border-top: none;
  max-height: 400px;
  overflow-y: auto;
  transition: max-height 0.3s ease;
}

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

/* 复选框样式 */
::v-deep .el-checkbox__inner {
  border-color: #ccc !important;
  transition: all 0.2s !important;
}

::v-deep .el-checkbox:hover .el-checkbox__inner {
  border-color: #0a4a1f !important;
}

::v-deep .el-checkbox__input.is-checked .el-checkbox__inner {
  background-color: #0a4a1f !important;
  border-color: #0a4a1f !important;
}

::v-deep .el-checkbox__input.is-checked .el-checkbox__inner::after {
  border-color: white !important;
}

::v-deep .el-checkbox__input.is-disabled .el-checkbox__inner {
  background-color: #f5f5f5 !important;
  border-color: #ddd !important;
}
::v-deep .el-checkbox__input.is-disabled.is-checked .el-checkbox__inner {
  background-color: #e6e6e6 !important;
  border-color: #e6e6e6 !important;
}

/* 进度条样式 - 与query页面保持一致 */
::v-deep .el-progress-bar__inner {
  background-color: #0a4a1f !important;
  transition: width 0.3s ease !important;
}

::v-deep .el-progress__text {
  color: #666 !important;
  font-size: 14px !important;
}

::v-deep .el-progress--exception .el-progress-bar__inner {
  background-color: #f56c6c !important;
}

::v-deep .el-progress--success .el-progress-bar__inner {
  background-color: #52c41a !important;
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

/* 响应式调整 */
@media (max-width: 1200px) {
  .dashboard-main { flex-wrap: wrap; }
  .calendar-container, .todo-container, .chat-container {
    width: 100%;
    margin-bottom: 20px;
  }
}

::v-deep .message-content {
  /* 确保内容块有足够间距 */
  line-height: 1.8;
}

/* 1. 标题样式（h1-h6） */
::v-deep .message-content h1 {
  font-size: 22px;
  margin: 16px 0 8px;
  font-weight: 600;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 4px;
}
::v-deep .message-content h2 {
  font-size: 20px;
  margin: 14px 0 6px;
  font-weight: 600;
}
::v-deep .message-content h3 {
  font-size: 18px;
  margin: 12px 0 4px;
  font-weight: 600;
}
::v-deep .message-content h4,
::v-deep .message-content h5,
::v-deep .message-content h6 {
  font-size: 16px;
  margin: 10px 0 2px;
  font-weight: 600;
}

/* 2. 段落与换行 */
::v-deep .message-content p {
  margin: 10px 0;
}

/* 3. 列表（有序/无序） */
::v-deep .message-content ul,
::v-deep .message-content ol {
  margin: 10px 0 10px 24px;
  padding: 0;
}
::v-deep .message-content li {
  margin: 6px 0;
  line-height: 1.6;
}
/* 有序列表数字颜色 */
::v-deep .message-content ol li::marker {
  font-weight: 500;
}

/* 4. 链接样式 */
::v-deep .message-content a {
  color: #0a4a1f;
  text-decoration: underline;
  padding: 0 2px;
  border-radius: 2px;
  transition: all 0.2s;
}
::v-deep .message-content a:hover {
  color: #073416;
  background-color: rgba(10, 74, 31, 0.05);
  text-decoration: none;
}

/* 5. 代码块与行内代码 */
/* 行内代码 */
::v-deep .message-content code {
  background-color: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 14px;
  font-family: monospace;
}
/* 代码块 */
::v-deep .message-content pre {
  background-color: #f5f7fa;
  border-radius: 6px;
  padding: 12px 16px;
  margin: 12px 0;
  overflow-x: auto;
  line-height: 1.5;
}
::v-deep .message-content pre code {
  background: transparent;
  padding: 0;
  font-size: 13px;
}

/* 6. 引用块 */
::v-deep .message-content blockquote {
  border-left: 3px solid #0a4a1f;
  padding: 8px 12px 8px 16px;
  margin: 12px 0;
  background-color: rgba(10, 74, 31, 0.03);
  color: #555;
  border-radius: 0 4px 4px 0;
}

/* 7. 分隔线 */
::v-deep .message-content hr {
  border: none;
  border-top: 1px dashed #eaecef;
  margin: 16px 0;
}

/* 8. 表格（如果需要支持） */
::v-deep .message-content table {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
}
::v-deep .message-content th,
::v-deep .message-content td {
  border: 1px solid #eaecef;
  padding: 8px 12px;
  text-align: left;
}
::v-deep .message-content th {
  background-color: rgba(10, 74, 31, 0.05);
  font-weight: 600;
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
/* 弹窗样式 */
.custom-logout-box .el-message-box {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.custom-logout-box .el-message-box__title {
  color: #0a4a1f !important;
}

.custom-logout-box .el-message-box__message {
  color: #555 !important;
  font-size: 14px !important;
}

.custom-logout-box .el-button--primary {
  background-color: #0a4a1f !important;
  border-color: #0a4a1f !important;
  color: white !important;
}

.custom-logout-box .el-button--primary:hover {
  background-color: #073416 !important;
  border-color: #073416 !important;
}

.custom-logout-box .el-button--default {
  background-color: #f5f5f5 !important;
  border-color: #ddd !important;
  color: #666 !important;
}

.custom-logout-box .el-button--default:hover {
  background-color: #e6e6e6 !important;
  border-color: #ccc !important;
  color: #333 !important;
}
</style>