<template>
  <div class="login-page">
    <el-card class="login-card" shadow="hover">
      <div class="login-header">
        <el-icon class="logo-icon"><Book /></el-icon>
        <h2>KengU</h2>
        <p>Your study partner at the University of Hong Kong</p>
      </div>

      <el-form 
        ref="loginFormRef" 
        :model="loginForm" 
        :rules="loginRules" 
        class="login-form"
      >
        <el-form-item prop="email">
          <el-input 
            v-model="loginForm.email" 
            placeholder="Enter your HKU email (xxx@connect.hku.hk or xxx@hku.hk)" 
            clearable
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="password">
          <el-input 
            v-model="loginForm.password" 
            type="password" 
            placeholder="Enter your HKU Portal password" 
            show-password
            clearable
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item>
          <el-button 
            type="primary" 
            class="login-btn" 
            @click="handleLogin"
            :loading="isLoading"
          >
            Log In
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 首次登录提示弹窗 -->
    <el-dialog
      v-model="showFirstLoginTip"
      title="Notice"
      :closable="false"
      :show-close="false"
      :modal="true"
      width="350px"
    >
      <div class="tip-content">
        <el-icon class="tip-icon"><InfoFilled /></el-icon>
        <p>If this is your first login, it may take more time to initialize your data. Please be patient.</p>
      </div>
      <template #footer>
        <el-button type="primary" @click="handleFirstLoginConfirm">
          I understand
        </el-button>
      </template>
    </el-dialog>

    <!-- 数据初始化进度弹窗（首次登录专用） -->
    <el-dialog
      v-model="showInitProgress"
      title="Initializing Data"
      :closable="false"
      :show-close="false"
      :modal="true"
      width="400px"
    >
      <div class="progress-content">
        <el-progress
          :percentage="initProgress"
          :status="initStatus"
          stroke-width="6"
          style="margin-bottom: 15px;"
        ></el-progress>
        <p class="progress-text">{{ initProgressText }}</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { verifyHkuAuth, getEventUpdate, getUpdateProgress } from '../services/api'
import { Book, User, Lock, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 表单与基础状态
const loginFormRef = ref()
const isLoading = ref(false)
const router = useRouter()
const userStore = useUserStore()
const showFirstLoginTip = ref(false)

// 进度弹窗状态（首次登录专用）
const showInitProgress = ref(false)
const initProgress = ref(0)
const initProgressText = ref('Preparing your data...')
const initStatus = ref('active')
let progressPollTimer = null // 进度轮询定时器

// 登录表单数据
const loginForm = reactive({
  email: '',
  password: ''
})

// 表单验证规则
const loginRules = {
  email: [
    { required: true, message: 'Please enter your HKU email', trigger: 'blur' },
    { pattern: /@(connect\.hku\.hk|hku\.hk)$/, message: 'Please use a valid HKU email', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please enter your password', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' }
  ]
}

// 轮询检查初始化进度
const checkInitProgress = async (taskId) => {
  if (!taskId) return

  try {
    const progressResponse = await getUpdateProgress(taskId)
    
    // 必须先判断响应是否有效（防止 undefined 错误）
    if (!progressResponse) {
      throw new Error('Invalid progress response')
    }

    const percent = progressResponse.percent
    const message = progressResponse.message
    const completed = progressResponse.completed
    const failed = progressResponse.failed
    const error = progressResponse.error
    initProgress.value = Math.min(100, Math.max(0, percent || 0))
    initProgressText.value = message || `Processing (${initProgress.value}%)`

    // 处理完成/失败状态
    if (completed) {
      clearInterval(progressPollTimer)
      initStatus.value = 'success'
      initProgressText.value = 'Data initialization completed! Redirecting...'
      setTimeout(() => {
        showInitProgress.value = false
        router.push('/query') // 完成后跳转
      }, 1500)
    } else if (failed) {
      clearInterval(progressPollTimer)
      initStatus.value = 'exception'
      initProgressText.value = `Failed: ${error || 'Unknown error'}`
      ElMessage.error(initProgressText.value)
    }
  } catch (error) {
    console.error('进度查询失败：', error)
    initProgressText.value = 'Failed to get progress, retrying...'
  }
}

// 启动事件更新并跟踪进度
const fetchEventsWithProgress = async (email, password, userId) => {
  try {
    // 计算日期范围（过去30天到未来90天）
    const today = new Date()
    const startDate = new Date(today.setDate(today.getDate())).toISOString().split('T')[0]
    
    const futureDate = new Date()
    const endDate = new Date(futureDate.setDate(futureDate.getDate() + 30)).toISOString().split('T')[0]

    console.log('事件更新参数：', { email, startDate, endDate, userId })

    // 调用事件更新接口（带错误捕获）
    const response = await getEventUpdate(email, password, startDate, endDate, userId)
    console.log(response.success)
    
    // 严格判断响应有效性（核心修复点）
    if (!response) {
      throw new Error('No response from server')
    }

    // 处理接口返回结果
    if (response.success && response.task_id) {
      const taskId = response.task_id
      userStore.setEventTaskId(taskId)
      console.log('事件更新任务启动，任务ID：', taskId)

      // 启动进度轮询
      showInitProgress.value = true
      checkInitProgress(taskId) // 立即查询一次
      progressPollTimer = setInterval(() => checkInitProgress(taskId), 1000)
      return true
    } else {
      throw new Error(`Server error: ${response.message || 'Unknown reason'}`)
    }
  } catch (error) {
    console.error('事件更新失败：', error)
    ElMessage.error(`Data initialization failed: ${error.message}`)
    showInitProgress.value = false
    return false
  }
}

// 首次登录弹窗确认处理
const handleFirstLoginConfirm = () => {
  showFirstLoginTip.value = false
  // 启动初始化并显示进度
  fetchEventsWithProgress(loginForm.email, loginForm.password, userStore.id)
}

// 登录处理逻辑
const handleLogin = async () => {
  try {
    // 表单验证
    await loginFormRef.value.validate()
  } catch (error) {
    return ElMessage.warning('Please complete the form correctly')
  }

  isLoading.value = true
  try {
    // 验证用户身份
    const authResult = await verifyHkuAuth(loginForm.email, loginForm.password)
    
    // 验证响应有效性（防止 undefined 错误）
    if (!authResult || !authResult.success) {
      throw new Error(authResult?.message || 'Authentication failed')
    }

    const userId = authResult.data?.id
    if (!userId) {
      throw new Error('Failed to get user ID')
    }
    
    // 存储用户信息
    userStore.setLogin(loginForm.email, loginForm.password, userId)
    userStore.setUserId(userId)

    // 检查是否为首次登录（通过课程数量判断）
    await userStore.loadCourses()
    const isFirstLogin = userStore.courses.length === 0
    
    // 首次登录显示提示弹窗
    if (isFirstLogin) {
      showFirstLoginTip.value = true
    } else {
      // 非首次登录：后台更新数据，直接跳转
      setTimeout(() => {
        fetchEventsWithProgress(loginForm.email, loginForm.password, userId)
      }, 1000)
      router.push('/query')
    }

    ElMessage.success('Login successful!')

  } catch (error) {
    console.error('Login error:', error)
    ElMessage.error(`Error: ${error.message || 'Login failed'}`)
  } finally {
    isLoading.value = false
  }
}

// 组件卸载时清理定时器（防止内存泄漏）
onUnmounted(() => {
  if (progressPollTimer) {
    clearInterval(progressPollTimer)
  }
})
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background-color: #e1e5e8ff;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 600px;
  border-radius: 10px;
  overflow: hidden;
}

.login-header {
  text-align: center;
  padding: 10px 0 25px;
}

.logo-icon {
  font-size: 48px;
  color: #073416ff;
  margin-bottom: 15px;
}

.login-page h2 {
  font-size: 40px;
  color: #073416ff;
  font-weight: 600;
  margin-bottom: 15px;
}

.login-page p {
  font-size: 20px;
  margin-bottom: 5px;
  color: #666;
}

.login-form {
  padding: 10px 20px 10px;
}

.login-btn {
  background-color: #0a4a1fff;
  color: #fff;
  border: none;
  width: 100%;
  height: 45px;
  font-size: 20px;
}

.login-btn:hover {
  background-color: #073416ff;
}

/* 输入框聚焦样式优化 */
:deep(.el-input__wrapper:focus-within) {
  box-shadow: 0 0 0 2px rgba(10, 74, 31, 0.2);
  border-color: #0a4a1f;
}

/* 提示弹窗样式 */
.tip-content {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px 0;
}

.tip-icon {
  color: #409eff;
  font-size: 24px;
}

.tip-content p {
  margin: 0;
  line-height: 1.6;
}

/* 进度弹窗样式 */
.progress-content {
  padding: 10px 0;
}

.progress-text {
  color: #666;
  text-align: center;
  margin: 0;
  font-size: 14px;
}
</style>