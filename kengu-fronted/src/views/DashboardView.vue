<template>
  <div class="dashboard-page">
    <!-- 头部区域 -->
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
          <!-- 日历头部 -->
          <div class="calendar-header">
            <el-button 
              size="small" 
              icon="ArrowLeft" 
              @click="changeMonth('prev')"
              class="month-nav-btn"
            />
            <div class="title-group">
              <h4 class="month-title">{{ currentYear }}年{{ currentMonth + 1 }}月</h4>
              <el-button 
                type="primary" 
                size="small" 
                icon="Refresh" 
                @click="goToToday"
                class="today-btn"
                title="回到今日"
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
                <div class="todo-desc">{{ event.description }}</div>
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
                  <div class="message-content" v-html="formatMessage(msg.content)"></div>
                  
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
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '../stores/user';
import { User, ArrowDown, Search, Document } from '@element-plus/icons-vue';
import { ElMessage, ElLoading } from 'element-plus';
import { 
  get_assignments_by_date_range, 
  mark_assignment_complete,
  mark_assignment_pending  // 导入新增的API函数
} from '../services/api';

// 状态管理与路由
const userStore = useUserStore();
const router = useRouter();

// 核心状态（保持不变）
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

// 日历配置 - 星期表头
const weekdays = ['日', '一', '二', '三', '四', '五', '六'];

// 计算42天日历（保持不变）
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

// 工具函数：检查日期有效性（保持不变）
const isValidDate = (date) => {
  return date && date instanceof Date && !isNaN(date.getTime());
};

// 滚动到最新消息（保持不变）
const scrollToLatest = async () => {
  await nextTick();
  if (isGenerating.value && typingRef.value) {
    typingRef.value.scrollIntoView({ behavior: 'smooth', block: 'end' });
  } else if (messageRefs.value.length > 0) {
    messageRefs.value[messageRefs.value.length - 1].scrollIntoView({ behavior: 'smooth', block: 'end' });
  }
};

// 课程引用功能（保持不变）
const removeCourseReference = (courseId) => {
  selectedCourses.value = selectedCourses.value.filter(course => course.id !== courseId);
};

// 导航方法（保持不变）
const goToQuery = () => router.push('/query');
const goToDashboard = () => router.push('/dashboard');
const goToProfile = () => router.push('/profile');

// 回到今日（保持不变）
const goToToday = () => {
  const today = new Date();
  currentYear.value = today.getFullYear();
  currentMonth.value = today.getMonth();
  currentDate.value = today;
  loadAllAssignments();
  ElMessage.success('已回到今日');
};

// 获取作业数据（保持不变）
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
    ElMessage.error('网络错误，无法获取作业数据');
    return [];
  }
};

// 标记作业完成（保持不变）
const markAssignmentComplete = async (assignmentId) => {
  try {
    console.log(`调用接口：POST /api/assignments/mark-complete`);
    console.log(`请求参数：assignment_id=${assignmentId}`);
    return await mark_assignment_complete(assignmentId);
  } catch (error) {
    console.error('更新作业状态出错:', error);
    return { success: false, error: '网络错误' };
  }
};

// 新增：标记作业为待处理状态
const markAssignmentPending = async (assignmentId) => {
  try {
    console.log(`调用接口：POST /api/assignments/mark-pending`);
    console.log(`请求参数：assignment_id=${assignmentId}`);
    return await mark_assignment_pending(assignmentId);
  } catch (error) {
    console.error('更新作业为待处理状态出错:', error);
    return { success: false, error: '网络错误' };
  }
};

// 初始化加载作业（保持不变）
onMounted(async () => {
  if (!userStore.email) {
    router.push('/');
    return;
  }
  await loadAllAssignments();
});

// 加载作业（保持不变）
const loadAllAssignments = async () => {
  const startDate = new Date(calendarDays.value[0]);
  startDate.setHours(0, 0, 0, 0);
  const endDate = new Date(calendarDays.value[41]);
  endDate.setHours(23, 59, 59, 999);
  
  const startDateStr = startDate.toISOString().split('T')[0];
  const endDateStr = endDate.toISOString().split('T')[0];
  
  const assignments = await fetchAssignmentsByDateRange(startDateStr, endDateStr);
  eventsData.value = assignments.map(assignment => ({
    date: new Date(assignment.due_date),
    name: assignment.title,
    description: `Course: ${assignment.course_name || 'Unknown'}\nType: ${assignment.assignment_type || 'N/A'}`,
    completed: assignment.status === 'completed',
    assignmentId: assignment.id
  })).filter(item => isValidDate(item.date));

  selectedDateEvents.value = getSelectedDateEvents();
};

// 组件卸载时清理（保持不变）
onUnmounted(() => {
  if (abortController.value) abortController.value.abort();
});

// 聊天相关方法（保持不变）
const clearInput = () => {
  question.value = '';
  selectedCourses.value = [];
};

const formatMessage = (content) => content.replace(/\n/g, '<br/>');

const stopGeneration = () => {
  if (abortController.value) {
    abortController.value.abort();
    if (currentAiContent.value.trim()) {
      chatHistory.value.push({
        role: 'assistant',
        content: currentAiContent.value,
        time: new Date().toLocaleString(),
        sources: []
      });
    }
    isGenerating.value = false;
    currentAiContent.value = '';
    scrollToLatest();
    ElMessage.info('已终止回答生成');
  }
};

const fetchAskQuestion = (user_request, user_id, email, messages) => {
  return fetch('http://localhost:5000/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
    body: JSON.stringify({ user_request, user_id: user_id ? Number(user_id) : null, user_email: email, messages }),
    signal: abortController.value?.signal
  });
};

const submitQuestion = async () => {
  let finalQuestion = question.value.trim();
  if (selectedCourses.value.length > 0) {
    const courseNames = selectedCourses.value.map(course => course.name).join('、');
    finalQuestion = `[课程: ${courseNames}] ${finalQuestion}`;
  }

  if (!finalQuestion) return;

  chatHistory.value.push({
    role: 'user',
    content: finalQuestion,
    time: new Date().toLocaleString()
  });
  question.value = '';
  selectedCourses.value = [];
  isGenerating.value = true;
  currentAiContent.value = '';

  try {
    abortController.value = new AbortController();
    const response = await fetchAskQuestion(
      finalQuestion,
      userStore.id,
      userStore.email,
      chatHistory.value.map(msg => ({ role: msg.role, content: msg.content }))
    );

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let done = false;

    while (!done) {
      const { done: readerDone, value } = await reader.read();
      done = readerDone;
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ') && line.trim() !== 'data: ') {
          try {
            const { chunk } = JSON.parse(line.slice(6));
            currentAiContent.value += chunk;
            await nextTick();
            scrollToLatest();
          } catch (e) { console.error('解析错误:', e); }
        }
      }
      buffer = lines[lines.length - 1] || '';
    }

    isGenerating.value = false;
    if (currentAiContent.value) {
      chatHistory.value.push({
        role: 'assistant',
        content: currentAiContent.value,
        time: new Date().toLocaleString(),
        sources: []
      });
      currentAiContent.value = '';
      scrollToLatest();
    }

  } catch (error) {
    isGenerating.value = false;
    if (error.name !== 'AbortError') {
      console.error('提问失败:', error);
      ElMessage.error('查询失败，请重试');
      chatHistory.value.pop();
    }
  } finally {
    abortController.value = null;
  }
};

// 退出登录（保持不变）
const handleLogout = () => {
  if (confirm('确定要退出登录吗？')) {
    if (abortController.value) abortController.value.abort();
    userStore.logout();
    router.push('/');
  }
};

// 切换月份（保持不变）
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

// 日期格式化（保持不变）
const formatDate = (date) => {
  return isValidDate(date) ? date.toLocaleDateString('en-US', { 
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
  }) : '';
};

// 日期字符串生成（保持不变）
const getLocalDateStr = (date) => {
  if (!isValidDate(date)) return '';
  const d = new Date(date);
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, '0'),
    String(d.getDate()).padStart(2, '0')
  ].join('-');
};

// 判断日期是否有事件（保持不变）
const hasEvent = (date) => {
  if (!isValidDate(date)) return false;
  const targetStr = getLocalDateStr(date);
  return eventsData.value.some(event => getLocalDateStr(event.date) === targetStr);
};

// 获取指定日期的事件（保持不变）
const getDayEvents = (date) => {
  if (!isValidDate(date)) return [];
  const targetStr = getLocalDateStr(date);
  return eventsData.value.filter(event => getLocalDateStr(event.date) === targetStr);
};

// 判断是否为当天（保持不变）
const isCurrentDay = (date) => {
  if (!isValidDate(date)) return false;
  const today = new Date();
  return (
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate()
  );
};

// 判断是否为当月（保持不变）
const isSameMonth = (date) => {
  if (!isValidDate(date)) return false;
  return (
    date.getFullYear() === currentYear.value &&
    date.getMonth() === currentMonth.value
  );
};

// 判断是否为选中日期（保持不变）
const isSelectedDay = (date) => {
  if (!isValidDate(date) || !isValidDate(currentDate.value)) return false;
  return (
    date.getFullYear() === currentDate.value.getFullYear() &&
    date.getMonth() === currentDate.value.getMonth() &&
    date.getDate() === currentDate.value.getDate()
  );
};

// 文本截断（保持不变）
const truncateText = (text, length) => {
  return text.length > length ? text.substring(0, length) + '...' : text;
};

// 获取选中日期的事件（保持不变）
const getSelectedDateEvents = () => {
  return isValidDate(currentDate.value) 
    ? getDayEvents(currentDate.value) 
    : [];
};

// 监听日期变化更新待办列表（保持不变）
watch(currentDate, () => {
  selectedDateEvents.value = getSelectedDateEvents();
}, { deep: true });

// 日期点击事件（保持不变）
const handleDateClick = (date) => {
  if (!isSameMonth(date)) {
    currentYear.value = date.getFullYear();
    currentMonth.value = date.getMonth();
    loadAllAssignments();
  }
  currentDate.value = new Date(date);
};

// 修改：更新作业状态（根据勾选状态切换完成/待处理）
const updateTodoStatus = async (event) => {
  const targetEvent = eventsData.value.find(item => item.assignmentId === event.assignmentId);
  if (targetEvent) targetEvent.completed = event.completed;

  if (event.assignmentId) {
    // 根据勾选状态调用不同的API
    const result = event.completed 
      ? await markAssignmentComplete(event.assignmentId)  // 勾选：标记为完成
      : await markAssignmentPending(event.assignmentId);  // 取消勾选：标记为待处理

    if (!result.success) {
      // 失败时回滚状态
      if (targetEvent) targetEvent.completed = !event.completed;
      ElMessage.error(result.error || '更新失败');
    } else {
      ElMessage.success(event.completed ? '已标记为完成' : '已恢复为待处理');
    }
  }
};
</script>

<style scoped>
/* 样式保持不变 */
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
.kengu-btn {
  font-size: 20px;
  font-weight: bold;
  color: #0a4a1f !important;
  padding: 0 !important;
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
}
.todo-header { margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
.todo-list { flex: 1; overflow-y: auto; }
.todo-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
}
.todo-name { font-weight: 500; font-size: 14px; margin-bottom: 3px; }
.todo-desc { font-size: 13px; color: #666; white-space: pre-line; }
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
}

.qa-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}

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

/* 响应式调整 */
@media (max-width: 1200px) {
  .dashboard-main { flex-wrap: wrap; }
  .calendar-container, .todo-container, .chat-container {
    width: 100%;
    margin-bottom: 20px;
  }
}
</style>