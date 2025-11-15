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
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { verifyHkuAuth } from '../services/api'
import { Book, User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const loginFormRef = ref()
const isLoading = ref(false)
const router = useRouter()
const userStore = useUserStore()

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
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' }  // 增强密码验证
  ]
}

const handleLogin = async () => {
  try {
    await loginFormRef.value.validate()
  } catch (error) {
    return ElMessage.warning('Please complete the form correctly')
  }

  isLoading.value = true
  try {
    const authResult = await verifyHkuAuth(loginForm.email, loginForm.password)
    
    if (!authResult.success) {
      return ElMessage.error(`Authentication failed: ${authResult.message || 'Invalid email or password'}`)
    }

    const userId = authResult.data?.id
    if (!userId) {
      return ElMessage.error('Failed to get user information')
    }
    
    // 第一步：调用 setLogin 批量设置用户信息
    userStore.setLogin(loginForm.email, loginForm.password, userId)
    
    // 第二步：单独调用 setUserId 确保 id 存储成功（双重保险）
    // 避免 setLogin 中可能的逻辑遗漏，确保 userId 可靠写入本地存储和 Pinia
    userStore.setUserId(userId)
    console.log('原始 userId:', userId, '类型:', typeof userId)
    console.log('Pinia 中的 id:', userStore.id, '类型:', typeof userStore.id)
    // 验证 id 是否存储成功（可选，增强健壮性）
    if (!userStore.id || userStore.id !== userId) {
      throw new Error('Failed to save user ID')
    }

    await userStore.loadCourses()
    if (userStore.courses.length === 0) {
      ElMessage.info('No courses found, please update your course data after login')
    }

    ElMessage.success('Login successful!')
    router.push('/query')

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
</style>