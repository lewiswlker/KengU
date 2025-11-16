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
      :duration="0"
      width="350px"
    >
      <div class="tip-content">
        <el-icon class="tip-icon"><InfoFilled /></el-icon>
        <p>If this is your first login, it may take more time to initialize your data. Please be patient.</p>
      </div>
      <template #footer>
        <el-button type="primary" @click="showFirstLoginTip = false">
          I understand
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { verifyHkuAuth, getEventUpdate } from '../services/api'
import { Book, User, Lock, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const loginFormRef = ref()
const isLoading = ref(false)
const router = useRouter()
const userStore = useUserStore()
// 新增：控制首次登录提示弹窗显示
const showFirstLoginTip = ref(false)

const loginForm = reactive({
  email: '',
  password: ''
})

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

// 新增：后台获取事件更新
const fetchEventsInBackground = async (email, password, userId) => {
  try {
    // 计算日期范围：过去30天到未来90天
    const today = new Date()
    const startDate = new Date(today.setDate(today.getDate() - 10)).toISOString().split('T')[0]
    
    const futureDate = new Date()
    const endDate = new Date(futureDate.setDate(futureDate.getDate() + 40)).toISOString().split('T')[0]

    // 调用事件更新接口
    const response = await getEventUpdate(email, password, startDate, endDate, userId)
    
    if (response.data.success && response.data.task_id) {
      userStore.setEventTaskId(response.data.task_id)
      console.log('事件更新任务已启动，任务ID：', response.data.task_id)
    } else {
      console.warn('启动事件更新任务失败')
    }
  } catch (error) {
    console.error('后台获取事件失败：', error)
  }
}

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
    
    if (!authResult.success) {
      return ElMessage.error(`Authentication failed: ${authResult.message || 'Invalid email or password'}`)
    }

    const userId = authResult.data?.id
    if (!userId) {
      return ElMessage.error('Failed to get user information')
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
      ElMessage.info('Initializing your data, please wait...')
    }

    // 后台启动事件更新（不阻塞登录流程）
    setTimeout(() => {
      fetchEventsInBackground(loginForm.email, loginForm.password, userId)
    }, 0)

    // 登录成功处理
    ElMessage.success('Login successful!')
    // 如果是首次登录，等用户点击弹窗确认后再跳转
    if (isFirstLogin) {
      showFirstLoginTip.value = true

      // 绑定关闭事件（使用$on在setup中需要通过ref获取组件实例）
      // 实际项目中可使用组件的close事件
    } else {
      router.push('/query')
    }

  } catch (error) {
    console.error('Login error:', error)
    const errorMsg = error.response?.data?.message || 
                    error.message || 
                    'Login failed, please check your network or try again later'
    ElMessage.error(`Error: ${errorMsg}`)
  } finally {
    isLoading.value = false
  }
}
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
</style>